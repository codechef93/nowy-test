import json
import requests
import cloudbeds_api
from datetime import datetime, timedelta
import uuid
import app
import pycountry

requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'

EVISITOR_AUTH_URL = 'https://www.evisitor.hr/testApi/Resources/AspNetFormsAuth/Authentication/'
EVISITOR_REST_URL = 'https://www.evisitor.hr/testApi/Rest/Htz/'

Auth = {}

def dateFormated(date_string):

    date_obj = datetime.strptime(date_string, '%Y-%m-%d')
    converted_date = date_obj.strftime('%Y%m%d')

    return converted_date

def get_country_alpha_3(alpha_2_code):
    try:
        country = pycountry.countries.get(alpha_2=alpha_2_code)
        if country:
            # full_name = country.name
            alpha_3 = country.alpha_3
            return alpha_3 #, full_name 
        else:
            return None
    except Exception as e:
        return None #,f"Error: {e}"

def calculate_age(birthdate, reference_date):
    reference_date = datetime.strptime(reference_date, '%Y%m%d')
    birth_date = datetime.strptime(birthdate, '%Y%m%d')
    age = reference_date.year - birth_date.year - ((reference_date.month, reference_date.day) < (birth_date.month, birth_date.day))
    return age

def parse_date_with_offset(date_string):
    timestamp_start = date_string.find('(') + 1
    timestamp_end = date_string.find('+') if date_string.find('+')!= -1 else date_string.find('-')
    timestamp_string = date_string[timestamp_start:timestamp_end]
    timestamp_milliseconds = int(timestamp_string)
    # print(timestamp_start, timestamp_end, timestamp_string)
    offset_start = timestamp_end
    offset_end = timestamp_end + 5
    timezone_offset = date_string[offset_start:offset_end]

    if timezone_offset:
        sign = 1 if timezone_offset[0] == '+' else -1

        timezone = timedelta(hours=sign * int(timezone_offset[1:3]), minutes=sign * int(timezone_offset[3:]))
        datetime_with_offset = datetime.utcfromtimestamp(timestamp_milliseconds / 1000.0) + timezone
    else:
        datetime_with_offset = datetime.utcfromtimestamp(timestamp_milliseconds / 1000.0)

    formatted_string = datetime_with_offset.strftime('%Y%m%d')
    return formatted_string


def login():
    global Auth
    Auth = json.loads(app.redisClient.get('evisitor_account'))
    url = EVISITOR_AUTH_URL + 'Login'
    
    param = {
        'UserName': Auth['UserName'],
        'Password': Auth['Password'],
        'PersistCookie': False,
        'apikey': Auth['Apikey']
    }
    
    headers = {
        'Content-Type': 'application/json',
    }
    
    # print('Login data:', param)
    # app.redisClient.delete(f'evisitor_ttpayer_{username}')
    # app.redisClient.delete(f'evisitor_accommodationUnitType_{username}')
    # app.redisClient.delete(f'evisitor_facility_{username}')
    try:
        response = requests.post(url, data=json.dumps(param), headers=headers)
        response.raise_for_status()  # Check for HTTP errors
        
        # Parse the JSON response if applicable
        response_data = response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text
        cookies = response.cookies
        ttpayer = app.redisClient.get(f'evisitor_ttpayer_{Auth['UserName']}')
        accommodationUnitType = app.redisClient.get(f'evisitor_accommodationUnitType_{Auth['UserName']}')
        facility = app.redisClient.get(f'evisitor_facility_{Auth['UserName']}')
        ttpayer_json = {}
        accommodationUnitType_json = {}
        facility_json = {}
        if ttpayer is None:
            ttpayer_json = getTTPayerByPin(Auth['UserName'], cookies)
            # print('ttpayer:', ttpayer_json)
        else:
            ttpayer_json = json.loads(ttpayer)
        if accommodationUnitType is None:
            accommodationUnitType_json = getAccommodationUnitType(ttpayer_json['ID'], cookies)
            # print('accommodationUnityType:', accommodationUnitType_json)
        else:
            accommodationUnitType_json = json.loads(accommodationUnitType)
        if facility is None:
            facility_json = getFacility(ttpayer_json['ID'], cookies)
            # print('facility:', facility_json)
        else:
            facility_json = json.loads(facility)
        return cookies
    
    except requests.exceptions.RequestException as e:
        print(f"Error during login request: {e}")
        return None


def logout(cookies:str):
    url = EVISITOR_AUTH_URL + 'Logout'
    headers = {
        'Content-Type': 'application/json',
        # 'Content-Length': 0
    }

    response = requests.post(url, headers=headers, cookies=cookies)
    return response

def checkin(payload, apikey, cookies, ischeckin=True):#apikey is for cloudbeds and when ischeckin is false, webhook action is dates_changed
    url = EVISITOR_REST_URL + 'CheckInTourist/'

    property_id = payload['propertyID']
    reservation_id = payload['reservationID']
    # print('reservationID =', reservation_id)

    response_reservation = cloudbeds_api.get_reservation(property_id, reservation_id, apikey)
    reservation_json = response_reservation.json()

    # print('reservation:', reservation_json)
    if reservation_json['success'] == False:
        return {'error': 'getreservation of cloudbeds error'}
    i = 0
    payerpin = Auth['UserName']
    ttpayer = json.loads(app.redisClient.get(f"evisitor_ttpayer_{payerpin}"))
    facility = json.loads(app.redisClient.get(f"evisitor_facility_{payerpin}"))

    # when webhoock action is dates_changed and the reservation status is not checked-in
    if(ischeckin == False and reservation_json['data']['status'] != 'checked_in'):
        print('the reservation is not checked in')
        return {'message': f'this reservation status is not checked in'}

    guestList = reservation_json['data']['guestList']
    # print('facilityID:', facility['ID'])
    # ttpaycategory = getTTpaymentCategory(facility['ID'], Auth['UserName'], cookies)
    # print('ttpaycategory:', ttpaycategory)
    print('guestList:', guestList)
    startDate = reservation_json['data']['startDate']
    endDate = reservation_json['data']['endDate']
    responses = []
    for key in guestList:
        guest = guestList[key]
        # print('guest:', guest)
        _tourist = None
        if ischeckin == False:
            _tourist = getTourist(facility['ID'], guest['guestDocumentNumber'], False, guest['guestFirstName'], guest['guestLastName'], startDate, endDate, cookies)
            # print('tourist:', _tourist)
            if _tourist is None:
                log = {f'{i}': 'Tourist is not exists'}
                continue
        touristToCheckin = {
            'ID': str(uuid.uuid4()) if _tourist is None else _tourist['ID'], #unknown now
            'TTPayerID': '' if ttpayer is None else ttpayer['ID'],
            'AccommodationUnitType': '',#maybe room
            'ArrivalOrganisation': 'I', # personal: 'I' agency:'A' 60day.. : 'O'
            'TouristAgency': '',    # if 'I' then optional field, else mandatory, there is nothing from cloudbeds.
            'Citizenship': guest['guestCountry'] if len(guest['guestCountry'])==3 else get_country_alpha_3(guest['guestCountry']),
            'CityOfBirth': 'Unknown', # optional, there is nothing from cloudbeds.
            'CityOfResidence': guest['guestCity'] if guest['guestCity'] and len(guest['guestCity']) else 'Unknown',
            'CountryOfBirth': guest['guestCountry'] if len(guest['guestCountry'])==3 else get_country_alpha_3(guest['guestCountry']),
            'CountryOfResidence': guest['guestCountry'] if len(guest['guestCountry'])==3 else get_country_alpha_3(guest['guestCountry']),
            'DateOfBirth': dateFormated(guest['guestBirthdate']) if guest['guestBirthdate'] and len(guest['guestBirthdate'])>0 else '19400101',
            'DocumentNumber': guest['guestDocumentNumber'] if guest['guestDocumentNumber'] and len(guest['guestDocumentNumber']) else 'Unknown',
            'DocumentType': getDocumentTypeCode(guest['guestDocumentType'], guest['guestCountry']=='HRV'),
            'Facility': facility['Code'],
            'ForeseenStayUntil': dateFormated(reservation_json['data']['endDate']),
            'Gender': 'Muški' if guest['guestGender'] == 'M' else 'Ženski',
            'IsTTFlatRatePaymentVacationHome': '', #optional
            'OfferedServiceType': 'noćenje',
            'ResidenceAddress': guest['guestAddress'] if guest['guestAddress'] and len(guest['guestAddress'])>0 else 'Unknown',
            'StayFrom': dateFormated(reservation_json['data']['startDate']),
            'TimeEstimatedStayUntil': '06:00', #there is nothing from cloudbeds
            'TimeStayFrom': '05:59', #there is nothing
            'TouristEmail': guest['guestEmail'] if guest['guestEmail'] and len(guest['guestEmail'])>0 else 'Unknown',
            'TouristMiddleName': '', #optional
            'TouristName': guest['guestFirstName'],
            'TouristSurname': guest['guestLastName'],
            'TouristTelephone': guest['guestPhone'] if guest['guestPhone'] and len(guest['guestPhone'])>0 else '0000000000',
            'TTPaymentCategory': '14',#ttpaycategory['Code'],# how to get this param?
        }

        headers = {
        'Content-Type': 'application/json',
        # 'Content-Length': str(len(json.dumps(touristToCheckin))) 
        }
        # print('touristToCheckin: ', touristToCheckin)
        response = requests.post(url, headers=headers, data= json.dumps(touristToCheckin), cookies=cookies)
        response_data = response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text
        log = {f"{i}": response_data['UserMessage'] if 'UserMessage' in response_data else 'success'}
        responses.append(log)
        i = i + 1
    print('checkin result:', responses)
    return responses

def checkout(payload, apikey, cookies):
    url = EVISITOR_REST_URL + 'CheckOutTourist/'
    property_id = payload['propertyID']
    reservation_id = payload['reservationID']
    ttpayer = app.redisClient.get(f'evisitor_ttpayer_{Auth['UserName']}')
    facility = app.redisClient.get(f'evisitor_facility_{Auth['UserName']}')
    facility = json.loads(facility)
    ttpayer = json.loads(ttpayer)
    try:
        response_reservation = cloudbeds_api.get_reservation(property_id, reservation_id, apikey)
        reservation_json = response_reservation.json()
        if reservation_json['success'] == False:
            return {'Error': 'reservation not exists in cloudbeds.'}
        now = datetime.now()
        i = 0
        startDate = reservation_json['data']['startDate']
        endDate = reservation_json['data']['endDate']
        guestList = reservation_json['data']['guestList']
        responses = []
        for key in guestList:
            guest = guestList[key]
            _tourist = getTourist(facility['ID'], guest['guestDocumentNumber'], False, guest['guestFirstName'], guest['guestLastName'], startDate, endDate, cookies)
            if _tourist is None:
                log = {f'{i}': 'Tourist is not exists'}
            else:
                touristToCheckOut = {
                    'ID': _tourist['ID'],
                    'TTPayerID': ttpayer['ID'],
                    'CheckOutDate': now.strftime('%Y%m%d'),
                    'CheckOutTime': now.strftime('%H:%M')
                }
                headers = {
                    'Content-Type': 'application/json',
                    }
                response = requests.post(url, headers=headers, data= json.dumps(touristToCheckOut), cookies=cookies)
                response_data = response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text
                log = {f"{i}": response_data['UserMessage'] if 'UserMessage' in response_data else 'success'}
            responses.append(log)
            i += 1
        print('checkout result:', responses)
        return responses
    except requests.exceptions.RequestException as e:
        print(f"Error during Checkout request: {e}")
        return {'Error': 'Checkout errors'}

def cancelCheckin(payload, apikey, cookies):
    url = EVISITOR_REST_URL + 'CancelTouristCheckIn/'
    property_id = payload['propertyID']
    reservation_id = payload['reservationID']
    ttpayer = app.redisClient.get(f'evisitor_ttpayer_{Auth['UserName']}')
    facility = app.redisClient.get(f'evisitor_facility_{Auth['UserName']}')
    facility = json.loads(facility)
    ttpayer = json.loads(ttpayer)
    try:
        response_reservation = cloudbeds_api.get_reservation(property_id, reservation_id, apikey)
        reservation_json = response_reservation.json()
        if reservation_json['success'] == False:
            return {'Error': 'getreservation of cloudbeds error'}
        now = datetime.now()
        i = 0
        startDate = reservation_json['data']['startDate']
        endDate = reservation_json['data']['endDate']
        guestList = reservation_json['data']['guestList']
        responses = []
        for key in guestList:
            guest = guestList[key]
            _tourist = getTourist(facility['ID'], guest['guestDocumentNumber'], False, guest['guestFirstName'], guest['guestLastName'], startDate, endDate, cookies)
            if _tourist is None:
                log = {f'{i}': 'Tourist is not exists'}
            else:
                touristToCheckOut = {
                    'ID': _tourist['ID'],
                    'TTPayerID': ttpayer['ID'],
                    'Reason': 'Unknown'
                }
                headers = {
                    'Content-Type': 'application/json',
                    }
                response = requests.post(url, headers=headers, data= json.dumps(touristToCheckOut), cookies=cookies)
                response_data = response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text
                log = {f"{i}": response_data['UserMessage'] if 'UserMessage' in response_data else 'success'}
            responses.append(log)
            i += 1
        print('cancelcheckin result:', responses)
        return responses
    except requests.exceptions.RequestException as e:
        print(f"Error during Checkout request: {e}")
        return {'Error': 'CancelCheckin errors'}


def getTTPayerByPin(payerpin, cookies): #payerpin is the same as account pin/username
    # print('payerpin:', payerpin)
    url = EVISITOR_REST_URL + 'TTPayerUnion'
    
    filters = [{'Property': 'Pin', 'Operation': 'equal', 'Value': payerpin}]
    params = {'filters': filters}
    
    try:
        response = requests.get(url, params=json.dumps(params), cookies=cookies)
        response.raise_for_status()  # Check for HTTP errors
        
        response_data = response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text
        # print('response_data', response_data)
        if 'Records' in response_data and len(response_data['Records']) > 0:
            ttpayer_data = response_data['Records'][0]
            # print('ttpayer_data:', json.dumps(ttpayer_data))
            app.redisClient.set(f'evisitor_ttpayer_{payerpin}', json.dumps(ttpayer_data))
            return ttpayer_data
        else:
            print("No records found for the specified payerpin.")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"Error during getTTPayerByPin request: {e}")
        return None

def getFacility(payerid:str, cookies): #ttpayerid is the ID of TTPayer
    url = EVISITOR_REST_URL + 'FacilityBrowse'
    filters = [{"Property":"TTPayerID","Operation":"equal","Value":payerid}]

    params = {'filters': filters}

    try:
        response = requests.get(url, params=json.dumps(params), cookies=cookies)
        response.raise_for_status()  # Check for HTTP errors
        
        response_data = response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text
        # print('response_data', response_data)
        if 'Records' in response_data and len(response_data['Records']) > 0:
            facility_data = response_data['Records'][0]
            # print('facility_data:', json.dumps(facility_data))
            app.redisClient.set(f'evisitor_facility_{Auth['UserName']}', json.dumps(facility_data))
            return facility_data
        else:
            print("No records found for the specified payerpin.")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"Error during getTTPayerByPin request: {e}")
        return None

def getAccommodationUnitType(facilitycode:str, cookies): #facilitycode is the Code of Facility
    url = EVISITOR_REST_URL + 'AccommodationUnitFacilityType'
    
    filters = [{"Property": "FacilityCode", "Operation": "equal", "Value": facilitycode}]
    params = {'filters': filters}
    
    try:
        response = requests.get(url, params=json.dumps(params), cookies=cookies)
        response.raise_for_status()  # Check for HTTP errors
        
        response_data = response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text
        
        if 'Records' in response_data and len(response_data['Records']) > 0:
            accommodation_unit_type = response_data['Records'][0]
            app.redisClient.set(f'evisitor_accommodationUnitType_{Auth['UserName']}', json.dumps(accommodation_unit_type))
            # print('evisitor_accommodationUnitType_:', json.dumps(accommodation_unit_type))
            return accommodation_unit_type
        else:
            print("No records found for the specified facilitycode.")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"Error during getAccommodationUnitType request: {e}")
        return None

def getTourist(facilityId:str, documentNumber: str, ischeckout:bool, firstname: str, surname: str, startDate:str, endDate:str, cookies):
    url = EVISITOR_REST_URL + 'ListOfTouristsExtended'
    # print('surname:', surname, 'firstname:', firstname)
    filters = [
        {"Property": "SurnameAndName", "Operation": "contains", "Value": surname},
        {"Property": "SurnameAndName", "Operation": "contains", "Value": firstname},
        # {"Property":"FacilityID","Operation":"equal","Value":facilityId},
        {"Property":"TravelDocumentTypeNumber","Operation":"contains","Value":documentNumber},
        {"Property":"StayFrom","Operation":"equal","Value":startDate},
        # {"Property":"ForeseenStayUntil","Operation":"equal","Value":endDate},
        # {'Property': 'CheckedOutTourist', 'Operation': 'equal', 'Value':ischeckout}
    ]
    params = {'filters': filters}

    try:
        response = requests.get(url, params=json.dumps(params), cookies=cookies)
        response.raise_for_status()  # Check for HTTP errors
        
        response_data = response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text
        if 'Records' in response_data and len(response_data['Records']) > 0:
            records = response_data['Records']
            # print('records:', response_data['Records'])
            for record in records:
                stayFrom = record['StayFrom'].replace('/', '')
                stayFrom = parse_date_with_offset(stayFrom)
                foreseenStayUntil = record['ForeseenStayUntil'].replace('/', '')
                foreseenStayUntil = parse_date_with_offset(foreseenStayUntil)
                # print('from:', stayFrom, 'to:', foreseenStayUntil)
                documentNumber = 'Unknown' if documentNumber=='' else documentNumber
                if record['SurnameAndName'].find(surname)!= -1 and record['SurnameAndName'].find(firstname)!= -1 and record['TravelDocumentTypeNumber'].find(documentNumber)!=-1 and record['CheckedOutTourist']==False:# and stayFrom==dateFormated(startDate) and foreseenStayUntil==dateFormated(endDate):
                    print('tourist_data:', json.dumps(record))
                    # break
                    return record
                else:
                    # print('nothing')
                    continue
        else:
            print("No records found for the specified tourist.")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"Error during getTourist request: {e}")
        return None

def getTTpaymentCategory(facilityId:str, cookies):
    url = EVISITOR_REST_URL + 'TTPaymentCategoryLookup2'
    filters = [
        {"Property": "ID", "Operation": "equal", "Value": facilityId},
        {"Property": "Active", "Operation": "equal", "Value": True},
        # {"Property": "Code", "Operation": "equal", "Value": "14"}
    ]
    params = {'filters': filters}
    try:
        response = requests.get(url, params=json.dumps(params), cookies=cookies)
        response.raise_for_status()  # Check for HTTP errors
        
        response_data = response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text
        print('response_data', response_data)
        if 'Records' in response_data and len(response_data['Records']) > 0:
            paycategory_data = response_data['Records'][0]
            print('ttpaycategory_data:', json.dumps(paycategory_data))
            return paycategory_data
        else:
            print("No records found for the specified paycategory.")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"Error during getttpaycategory request: {e}")
        return None

def getDocumentTypeCode(doctype_cloudbeds:str, foreign:bool):
    switch_dict = {
        'dni': '96' if foreign else '027', #its name is "Personal identification card (page)"
        'driver-license': '103', #its name is "Vozačka dozvola (domaća)"
        'passport': '029',# its name is "Putni list za strance (strani)"
    }

    return switch_dict.get(doctype_cloudbeds, '039') #039 is default and its Name is 'Ostalo'(Other in english)