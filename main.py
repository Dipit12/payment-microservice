from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis_om import get_redis_connection, HashModel
from starlette.requests import Request
from dotenv import load_dotenv
import os
import requests
import time

load_dotenv()

INVENTORY_URL = os.getenv('INVENTORY_URL', 'http://localhost:8000')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins = ['*'],
    allow_methods=['*'],
    allow_headers=['*']
)
redis = get_redis_connection(
        host=os.getenv('REDIS_HOST'),
        port=17963,
        decode_responses=True,
        username="default",
        password=os.getenv('REDIS_PASSWORD')
)

class Order(HashModel, index = True):
    product_id:str
    price:float
    fee:float
    total:float
    quantity:int
    status:str # pending, completed, refunded
    class Meta:
        database = redis

@app.get("/orders/{pk}")
async def get(pk: str):
    return Order.get(pk)

@app.post("/orders")
async def create(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    product_id = body['product_id']
    try:
        req = requests.get(f"{INVENTORY_URL}/products/{product_id}", timeout=5)
        req.raise_for_status()
        product = req.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Inventory service error: {e}")
    except ValueError:
        raise HTTPException(status_code=502, detail="Inventory service returned a non-JSON response")
    order = Order(
        product_id = body['product_id'],
        price = product['price'],
        fee = 0.2 * product['price'],
        total = 1.2 * product['price'],
        quantity = body['quantity'],
        status = 'pending'
    )
    order.save()
    background_tasks.add_task(order_completed, order)
    return order

def order_completed(order: Order):
    time.sleep(5)
    order.status = 'completed'
    order.save()