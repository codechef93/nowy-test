from fastapi import FastAPI
import os
import sys
from datetime import datetime
import redis
import cloudbeds_api

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