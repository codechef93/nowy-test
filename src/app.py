from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import sys
from datetime import datetime
import redis
import cloudbeds_api
import evisitor_api
import json

redisClient = redis.Redis(host=os.getenv('REDIS_HOST'),
                port=os.getenv('REDIS_PORT', 6379),
                password=os.getenv('REDIS_AUTH'),
                decode_responses=True)

app = FastAPI()

@app.get("/get-api-key")
async def get_api_key(code: str):    
    result = cloudbeds_api.auth(code) 
    if 'api_key' in result:
        redisClient.set(result['property_id'], result['api_key'])
    
    return {"auth_result": result}
    
@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/set-time")
def set_time():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    redisClient.set('last-time', current_time)
    return {"set_time": current_time}

@app.get("/get-time")
def get_time():
    last_time = redisClient.get('last-time')
    return {"last_time": last_time}

@app.get("/get-api-key-with-property-id")
def get_api_key_with_property_id(property_id: str):
    api_key = redisClient.get(property_id)    
    if api_key is None:
        return {"error": 'There is no API key for this property id.'}
    else:
        return {"api_key": api_key}
    
@app.get("/set-api-key")
async def get_api_key(property_id: str, api_key: str):    
    redisClient.set(property_id, api_key)
    
    return {"set_result": 'saved'}

@app.get("/get-reservations")
async def get_reservations(property_id: str):   
    api_key = redisClient.get(property_id) 
    if api_key is None:
        return {"error": 'There is no API key for this property id.'}
    else:
        result = cloudbeds_api.reservations(api_key, {})
        return {"reservations_result": result.json()}

@app.get("/get-hotels")
def get_hotels(property_id: str):    
    api_key = redisClient.get(property_id) 
    if api_key is None:
        return {"error": 'There is no API key for this property id.'}
    else:
        result = cloudbeds_api.hotels(api_key, {})
        return {"hotels_result": result.json()}

@app.get("/get-guest-list")
def guest_list(property_id: str):
    api_key = redisClient.get(property_id) 
    if api_key is None:
        return {"error": 'There is no API key for this property id.'}
    else:
        result = cloudbeds_api.guest_list(api_key, {property_id: property_id})
        return {"guest_list_result": result.json()}
    
@app.get("/post-webhook")
def post_webhook(property_id: str, objectname:str, action:str):
    api_key = redisClient.get(property_id) 
    if api_key is None:
        return {"error": 'There is no API key for this property id.'}
    else:
        result = cloudbeds_api.post_webhook(property_id, objectname, action, api_key)
        return result.json()


@app.post("/callback-webhook", status_code=200)
async def handle_webhook(request: Request): #request need to redefine
    print('handle_webhook')
    payload = await request.json()
    print(payload)
    event = payload.get("event")
    property_id = payload.get("propertyID")
    apikey = redisClient.get(property_id)
    result = []
    if not apikey or not property_id:
        return JSONResponse(
            status_code=401, content={"message": "Police's log => Invalid propertyID"}
        )

    # if event == 'reservation/created':
    #     result = evisitor_api.checkin(payload, apikey)
    if event == 'reservation/status_changed' or event == 'reservation/dates_changed':
        cookies = evisitor_api.login()
        if event == 'reservation/status_changed':
            if(payload['status'] == 'checked_in'):
                result = evisitor_api.checkin(payload, apikey, cookies)
            elif(payload['status'] == 'checked_out'):
                result = evisitor_api.checkout(payload, apikey, cookies)
            elif(payload['status'] == 'canceled'):
                result = evisitor_api.cancelCheckin(payload, apikey, cookies)
        # elif event == 'reservation/deleted':
        #     print('reservation_deleted')
        elif event == 'reservation/dates_changed':
            result = evisitor_api.datechanged(payload, apikey, cookies, False)
        evisitor_api.logout(cookies)
    else:
        print('reservation other event')
        return JSONResponse(
            status_code=501, content={"message": "Police's log => Event is not implemented"}
        )
    return JSONResponse(status_code=200, content={f'handle_webhook_{event}': result})

@app.get("/all-clear-redis")
def all_clear_redis(payerpin: str): # payerpin is the same as account username(/PIN)
    redisClient.delete(f"evisitor_ttpayer_{payerpin}", f"evisitor_facility_{payerpin}", f"evisitor_accommodationUnitType_{payerpin}", "evisitor_account")
    return 'All is cleared'

@app.get("/login-evisitor")
def login_evisitor():
    login = evisitor_api.login()
    return login

@app.get("/get-reservation")
def get_reservation(property_id:str, reservation_id:str):
    api_key = redisClient.get(property_id)
    if api_key is None:
        return {"error": 'There is no API key for this property id.'}
    else:
        result = cloudbeds_api.get_reservation(property_id, reservation_id, api_key)
        reservation_json = result.json()
        print('reservation:', reservation_json)
        if reservation_json['success'] == False:
            return {'error': 'reservation not exists in cloudbeds'}
        i = 0
        guestList = reservation_json['data']['guestList']
        print('guestList:', guestList)
        for key in guestList:
            guest = guestList[key]
            # print('guest:', guest['guestLastName'])
        return result.json()

@app.get("/set-accountInfo")
def get_tourist(userName:str, password:str, apikey:str):
    auth = {
        'UserName': userName,
        'Password': password,
        'Apikey': apikey
    }
    redisClient.set('evisitor_account', json.dumps(auth))
    return {'success': auth}