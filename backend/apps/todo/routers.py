from fastapi import APIRouter, Body, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from .models import OrderModel

router = APIRouter()


@router.post("/", response_description="Add new order")
async def create_order(request: Request, order: OrderModel = Body(...)):
    order = jsonable_encoder(order)
    new_order = await request.app.mongodb["orderbook"].insert_one(order)
    created_order = await request.app.mongodb["orderbook"].find_one(
        {"_id": new_order.inserted_id}
    )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_order)


@router.get("/", response_description="List all orders")
async def list_orders(request: Request):
    orders = []
    for doc in await request.app.mongodb["orderbook"].find().to_list(length=100):
        orders.append(doc)
    return orders


@router.get("/{user}", response_description="Get orders by user")
async def show_order(user: str, request: Request):
    if (order := await request.app.mongodb["orderbook"].find({"user": user})) is not None:
        return order

    raise HTTPException(status_code=404, detail=f"User {user} not found")


@router.delete("/{id}", response_description="Delete Order")
async def delete_task(id: str, request: Request):
    delete_result = await request.app.mongodb["orderbook"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Order {id} not found")
