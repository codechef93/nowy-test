from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import sys
from datetime import datetime
import redis
import cloudbeds_api
import evisitor_api

# TEMP_CROATIA_API_KEY = 'cbat_FZKDFEyGhoE42DWsvde9gDqZxc5Z48mn'
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
    
@app.post("/post-webhook")
def post_webhook(property_id: str, objectname:str, action:str):
    api_key = redisClient.get(property_id) 
    if api_key is None:
        return {"error": 'There is no API key for this property id.'}
    else:
        result = cloudbeds_api.post_webhook(property_id, objectname, action, api_key)
        return {"guest_list_result": result.json()}


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

    if event == 'reservation/created':
        result = evisitor_api.checkin(payload, apikey)
    elif event == 'reservation/status_changed':
        if(payload['status'] == 'checked_in'):
            result = evisitor_api.checkin(payload, apikey)
        elif(payload['status'] == 'checked_out'):
            result = evisitor_api.checkout(payload, apikey)
    elif event == 'reservation/deleted':
        print('reservation_deleted')
    elif event == 'reservation/dates_changed':
        print('reservation_dates_changed')
    else:
        print('reservation other event')
        return JSONResponse(
            status_code=501, content={"message": "Police's log => Event is not implemented"}
        )
    return JSONResponse(status_code=200, content={f'handle_webhook_{event}': result})

@app.get("/all-clear-redis")
def all_clear_redis(payerpin: str): # payerpin is the same as account username(/PIN)
    app.redisClient.delete(f"evisitor_ttpayer_{payerpin}", f"evisitor_facility_{payerpin}", f"evisitor_accommodationUnitType_{payerpin}", f"evisitor_ttpaymentCategory")
    return 'All is cleared'

@app.get("/login-evisitor")
def login_evisitor(username:str, password:str, apikey:str):
    evisitor_api.login(username, password, apikey)
    return 'login succeed'