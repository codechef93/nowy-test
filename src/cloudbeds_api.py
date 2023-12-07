import json
import requests

CLIENT_ID = 'croatia_police_report_Sy1gfLEMQc6DFR8AairY9Chm'
CLIENT_SECRET = '31UhtoAn496HLCl8fBYRjurVMdOSxWEp'
# REDIRECT_URI = 'https://paymenthub.uk/croatia/get-api-key'
REDIRECT_URI = 'https://croatia-police.app-integrations.cloudbeds-dev.com/get-api-key'
CLOUDBEDS_URL = 'https://hotels.cloudbeds.com/api/v1.1/'

def load_secret(api, property_id):
# function to load secrets

    f = open('int.secrets','r')

    secrets = json.loads(f.read())
    # print(secrets)

    return secrets[api][str(property_id)]

def save_secret(api, property_id, secret_value):
# function to save secrets    

    # Read the existing secrets
    try:
        with open('int.secrets', 'r') as f:
            secrets = json.load(f)
    except FileNotFoundError:
        secrets = {}    

    # Update the secret value
    if api not in secrets:
        secrets[api] = {}
    secrets[api][str(property_id)] = secret_value
    
    # Write the updated secrets back to the file
    with open('int.secrets', 'w') as f:
        json.dump(secrets, f)

def call_cb_endpoint_property_id(endpoint, method, property_id, params):

    url = CLOUDBEDS_URL + endpoint
    cb_secret = load_secret('cloudbeds', property_id)
    headers={"x-api-key": cb_secret}

    if method == 'get':
        response = requests.get(url, params=params, headers=headers)
        return response
    elif method == 'post':
        response = requests.post(url, data=params, headers=headers)
        return response

def call_cb_endpoint(endpoint, method, api_key, params): 

    url = CLOUDBEDS_URL + endpoint
    headers={"x-api-key": api_key}

    if method == 'get':
        response = requests.get(url, params=params, headers=headers)
        return response
    elif method == 'post':
        response = requests.post(url, data=params, headers=headers)
        return response

def auth(code):
    token_data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:api-key",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }    

    response_auth = requests.post(CLOUDBEDS_URL + 'access_token', data=token_data)
    json_response_auth = response_auth.json()
    print(json_response_auth) 

    if 'access_token' in json_response_auth:
        api_key = json_response_auth['access_token']
        headers = {"x-api-key": api_key}

        response_property = requests.get(CLOUDBEDS_URL + 'getHotels', headers=headers)    
        json_response_property = response_property.json()
        # print(json_response_property)

        if 'success' in json_response_property and json_response_property['success']:

            property_id = json_response_property['data'][0]['propertyID']
            save_secret('cloudbeds', property_id, api_key)
            
            return {"property_id": property_id, "api_key": api_key}
        else:
            return {"error": "propterty id not found in the response"}
    elif 'error' in json_response_auth:
        if 'error_description' in json_response_auth:
            return {"error": json_response_auth['error'], "error_description": json_response_auth['error_description']}
        else:
            return {"error": json_response_auth['error']}
    else:
        return {"error": "access_token is not found in the response"}
  
def reservations_property_id(property_id, params):
    return call_cb_endpoint_property_id('getReservations', 'get', property_id, params)

def hotels_property_id(property_id, params):
    return call_cb_endpoint_property_id('getHotels', 'get', property_id, params)

def reservations(api_key, params):
    return call_cb_endpoint('getReservations', 'get', api_key, params)

def hotels(api_key, params):
    return call_cb_endpoint('getHotels', 'get', api_key, params)
   
def guest_list(api_key, params):
    return call_cb_endpoint('getGuestList', 'get', api_key, params)

def get_reservation(property_id, reservation_id, api_key, params):
    params = {
        'propertyID': property_id,
        'reservationID': reservation_id
    }
    return call_cb_endpoint('getreservation', 'get', api_key, params)

def post_webhook(property_id: int, object: str, action: str, api_key):
    form_data = {
        "propertyID": property_id,
        "object": object,
        "action": action,
        "endpointUrl": 'https://croatia-police.app-integrations.cloudbeds-dev.com/callback-webhook'
    }
    headers={
        'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': len(form_data),
        'x-api-key': api_key
    }
    response = requests.post(
        f"{CLOUDBEDS_URL}/postWebhook?propertyID={property_id}",
        headers = headers,
        data = form_data
    )
    return response.json()