from datetime import datetime, timedelta
from fastapi import APIRouter, Body, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from .models import OrderModel, MatchModel

router = APIRouter()


@router.get("/listPopular", response_description="List most popular stocks in the last hour")
async def list_popular(request: Request):
    current_time = datetime.utcnow() - timedelta(days=1)
    matched_orders = await request.app.mongodb["matchbook"].find({"date": {"$gte": current_time.strftime("%Y-%m-%dT%H:%M:%S.%f")}}).to_list(length=100)
    print(matched_orders)
    if matched_orders:
        securities = {}
        for matched_order in matched_orders:
            if matched_order["security"] not in securities:
                securities[matched_order["security"]] = matched_order["qty"] * matched_order["price"]
            else:
                securities[matched_order["security"]] += matched_order["qty"] * matched_order["price"]
        securities = [{'security': k, 'total volume (quantity x price)': v} for k, v in sorted(securities.items(), key=lambda item: item[1])]
        return JSONResponse(status_code=status.HTTP_200_OK, content=securities)
    else:
        raise HTTPException(status_code=404, detail="No popular orders found")

@router.get("/listAllOrders", response_description="List all orders")
async def list_orders(request: Request):
    orders = []
    for doc in await request.app.mongodb["orderbook"].find().to_list(length=100):
        orders.append(doc)
    return orders

@router.get("/listOrders/{user}", response_description="Get orders by user")
async def list_orders_for_user(user: str, request: Request):
    orders = []
    if (orders_found := await request.app.mongodb["orderbook"].find_one({"user": user})) is not None:
        for doc in await request.app.mongodb["orderbook"].find({"user": user}).to_list(length=100):
            orders.append(doc)
        return orders
    
    raise HTTPException(status_code=404, detail=f"User {user} not found")

@router.get("/listAllMatches", response_description="List all matches")
async def list_matches(request: Request):
    matches = []
    for doc in await request.app.mongodb["matchbook"].find().to_list(length=100):
        matches.append(doc)
    return matches

@router.get("/listMatches/{user}", response_description="Get matches by user")
async def list_matches_for_user(user: str, request: Request):
    matches = []
    if (matches_found := await request.app.mongodb["matchbook"].find_one({"buyer": user})) is not None:
        for doc in await request.app.mongodb["matchbook"].find({"buyer": user}).to_list(length=100):
            matches.append(doc)
    if (matches_found := await request.app.mongodb["matchbook"].find_one({"seller": user})) is not None:
        for doc in await request.app.mongodb["matchbook"].find({"seller": user}).to_list(length=100):
            matches.append(doc)
    return matches
    
    raise HTTPException(status_code=404, detail=f"User {user} not found")


@router.post("/add", response_description="Add new order")
async def create_order(request: Request, order: OrderModel = Body(...)):
    delete_id = ""
    order = jsonable_encoder(order)
    if (existing := await request.app.mongodb["orderbook"].find_one({"user": order["user"], "side": order["side"], "security": order["security"], "price": order["price"]})) is not None:
        order["qty"] = order["qty"] + existing["qty"]
        delete_id = existing["_id"]
    
    if (delete_id != ""):
        await request.app.mongodb["orderbook"].delete_one({"_id": delete_id})
    
    await request.app.mongodb["orderbook"].insert_one(order)

    ### Start matching
    other_side = "BUY" if order["side"] == "SELL" else "SELL"
    comparer = "$lte" if order["side"] == "BUY" else "$gte"
    matched_orders = await request.app.mongodb["orderbook"].find({"side": other_side, "security": order["security"], "price": {comparer: order["price"]}}).sort("date", -1).to_list(length=100)
    if matched_orders:
        print(matched_orders)
        for matched_order in matched_orders:
            if matched_order["qty"] > order["qty"]:
                print("case 1")
                # Delete
                await request.app.mongodb["orderbook"].delete_one({"_id": matched_order["_id"]});
                # Add new
                matched_order["qty"] = matched_order["qty"] - order["qty"]
                await request.app.mongodb["orderbook"].insert_one(matched_order)

                #order = await request.app.mongodb["orderbook"].find_one({"_id": matched_order["_id"]})
                if order["side"] == "BUY":
                    new_match = MatchModel(buyer=order["user"], seller=matched_order["user"], security=order["security"], price=matched_order["price"], qty=order["qty"])
                else:
                    new_match = MatchModel(buyer=matched_order["user"], seller=order["user"], security=order["security"], price=order["price"], qty=order["qty"])
                new_match = jsonable_encoder(new_match)
                await request.app.mongodb["matchbook"].insert_one(new_match)
                order["qty"] = 0
                break
            else:
                print("case else")
                order["qty"] -= matched_order["qty"]
                await request.app.mongodb["orderbook"].delete_one({"_id": matched_order["_id"]})
                if order["side"] == "BUY":
                    new_match = MatchModel(buyer=order["user"], seller=matched_order["user"], security=order["security"], price=matched_order["price"], qty=matched_order["qty"])
                else:
                    new_match = MatchModel(buyer=matched_order["user"], seller=order["user"], security=order["security"], price=order["price"], qty=matched_order["qty"])
                new_match = jsonable_encoder(new_match)
                await request.app.mongodb["matchbook"].insert_one(new_match)
                if order["qty"] == 0:
                    break
    if order["qty"] > 0:
        await request.app.mongodb["orderbook"].delete_one({"_id": order["_id"]}) 
        await request.app.mongodb["orderbook"].insert_one(order)
    else:
        await request.app.mongodb["orderbook"].delete_one({"_id": order["_id"]})

    return JSONResponse(status_code=status.HTTP_201_CREATED)


@router.post("/del", response_description="Delete Order")
async def delete_order(request: Request, order: OrderModel = Body(...)):
    order = jsonable_encoder(order)
    if (existing := await request.app.mongodb["orderbook"].find_one({"user": order["user"], "side": order["side"], "security": order["security"], "price": order["price"]})) is not None:
        order["qty"] = existing["qty"] - order["qty"]
        if order["qty"] > 0:
            await request.app.mongodb["orderbook"].insert_one(order)
        
    delete_result = await request.app.mongodb["orderbook"].delete_one({"_id": existing["_id"]})

    if delete_result.deleted_count == 1:
        return JSONResponse(status_code=status.HTTP_200_OK)

    raise HTTPException(status_code=404, detail=f"Order to delete not found")


