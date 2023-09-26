from fastapi import FastAPI
import os
import sys
from datetime import datetime
import redis

redisClient = redis.Redis(host=os.getenv('REDIS_HOST'),
                port=os.getenv('REDIS_PORT', 6379),
                password=os.getenv('REDIS_AUTH'),
                decode_responses=True)

app = FastAPI()


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
