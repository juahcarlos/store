"""Packing Manager Front End application server based on FastAPI.

This module imports and loads orders data from Solver DB
to the local caching mongoDB database and leads all process
loading items on pallets while order becomes complete.

Process includes all steps of loading -
initialising a device,
loading data,
accepting list of items,
pallets to load,
receiving data for each item placement,
placing,
changing status of the item,
pallet - when it finished,
order - when it will complete.

When the order will complete loading, docker should call route /quit
to clear the local cache database and export data to main Solver DB.
"""

import logging
import os
import time
from typing import Optional, Union

from fastapi import Depends
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi_keycloak import KeycloakToken, OIDCUser
from mongoengine.context_managers import switch_db
from prometheus_fastapi_instrumentator import Instrumentator
from sentry_sdk import capture_exception

from bluelib.utils.log_utils import init_logging
from bluelib.utils.start_sentry import start_sentry
from feapi.db.models.item import Items
from feapi.db.models.order import Orders
from feapi.db.models.pallett import Pallet
from feapi.db.models.truck import Trucks
from feapi.models import (
    Abort,
    AuthRequest,
    AuthResponse,
    InitRequest,
    InitResponse,
    Item,
    ItemCount,
    ItemsResponse,
    Order,
    OrderResponse,
    PlacementResponse,
    ResponseMessage,
)
from feapi.utils import (
    app,
    clear_db,
    db_preload,
    get_one_order,
    idp,
    placement_images,
    prepare_db,
)

# Initialisation logging
log = logging.getLogger("feapi.app")


# implementation of prometheus instrumentator
Instrumentator().instrument(app).expose(app)


"""
autentication routes
"""


@app.post("/auth", response_model=AuthResponse, tags=["auth"])
def login(data: AuthRequest) -> AuthResponse:
    """Models the password OAuth2 flow. Exchanges username and password for an access token. Will raise detailed
    errors if login fails due to requiredActions
    Args:
        username (str): Username used for login
        password (str): Password of the user
    Returns:
        KeycloakToken: If the exchange succeeds
    (this and follows docstrings in auth routes was taken from GitHub)
    """
    username = data.hw_id
    password = data.password
    log.info(f"username={username} password={password}")
    token: KeycloakToken = idp.user_login(username=username, password=password)
    return AuthResponse(access_token=str(token), token_type="str")


@app.get("/login-link", tags=["auth-flow"])
def login_redirect() -> RedirectResponse:
    return RedirectResponse(idp.login_uri)


@app.get("/callback", tags=["auth-flow"])
def callback(session_state: str, code: str) -> KeycloakToken:
    """Models the authorization code OAuth2 flow. Opening the URL provided by `login_uri` will result in a
    callback to the configured callback URL. The callback will also create a session_state and code query
    parameter that can be exchanged for an access token.

    Args:
        session_state (str): Salt to reduce the risk of successful attacks
        code (str): The authorization code

    Returns:
        KeycloakToken: If the exchange succeeds

    Raises:
        KeycloakError: If the resulting response is not a successful HTTP-Code (>299)
    """
    return idp.exchange_authorization_code(session_state=session_state, code=code)


@app.get("/logout", tags=["auth-flow"])
def logout() -> str:
    """The logout endpoint URL"""
    return idp.logout_uri


"""
main routes
"""


@app.post("/init", response_model=InitResponse, dependencies=[Depends(db_preload)])
async def init(data: InitRequest, user: OIDCUser = Depends(idp.get_current_user())) -> InitResponse:
    """Accepts and returns pydantic formatted data

    Serving FastAPI route /init - get device ID, fills all data for processing the order

    Args:
        data: InitRequest pydantic class contains:
            bat_status: int (will clarify later)
            screen_res: str (will clarify later)

    Returns:
        data: InitResponse pydantic class contains:
            phase: int (needs an additioinal clarification because we're already have status for each data collection)
            orders: list of orders (needs to reduce to one order)
    """
    hw_id = user.preferred_username
    ready: bool = False
    response_orders: list[Order] = []

    with switch_db(Orders, f"backend_{hw_id}") as Orders_:
        orders = Orders_.find_by_device(hw_id)
        if not orders:
            try:
                ready = prepare_db(hw_id)
            except Exception as ex:
                print("ex init ready", ex)
                capture_exception(ex)
            if not ready:
                raise HTTPException(status_code=404, detail="init import data into the app cache has been failed")

        for order in Orders_.objects:
            item_count = []
            for itm in order.items_uniq:
                item_count.append(ItemCount(id=itm.id, count=itm.count))
            response_order = Order(id=order.ID, item_count=item_count)
            response_orders.append(response_order)

    return InitResponse(phase=1, orders=response_orders)


@app.get("/order", response_model=OrderResponse, responses={404: {}}, dependencies=[Depends(db_preload)])
async def get_order(
    order_id: str, user: OIDCUser = Depends(idp.get_current_user())
) -> Union[OrderResponse, ResponseMessage]:
    """Accepts and returns pydantic formatted data

    Serving FastAPI route /order - get device ID and order ID, returns truck and pallet to proceed

    Args:
        data: OrderRequest pydantic class contains:
            order_id: string order ID

    Returns:
        data: OrderResponse pydantic class contains:
            truck_id: string ID of the truck
            gate_id: str
            pallet_id: str
            pallet_count: int
    """
    hw_id = user.preferred_username
    order = None
    with switch_db(Orders, f"backend_{hw_id}"):
        order = Orders.objects(ID=order_id, hw_id=hw_id).first()
    if order is None:
        raise HTTPException(
            status_code=404,
            detail=f"couldn't get Orders.objects with parameters ID={order_id}, hw_id={hw_id}",
        )

    truck_id = order.trucks[0]
    truck = None
    palletes = None
    with switch_db(Trucks, f"backend_{hw_id}") as Truck_:
        truck = Truck_.find_by_id(truck_id)
        palletes = truck.pallets

    pallet_id = "0"
    with switch_db(Pallet, f"backend_{hw_id}") as Pallet_:
        pallet = Pallet_.get_nonfinished()
        if pallet:
            if pallet.ID in palletes:
                pallet_id = pallet.ID
        else:
            await clear_db(hw_id)
            return ResponseMessage(message="The order is complete!")

    return OrderResponse(truck_id=truck_id, pallet_id=f"#{pallet_id}", pallet_count=len(palletes), gate_id=truck_id)


@app.get("/items", response_model=ItemsResponse, dependencies=[Depends(db_preload)])
async def get_items(order_id: str, user: OIDCUser = Depends(idp.get_current_user())) -> ItemsResponse:
    """Accepts order_id parameter and returns pydantic formatted data

    Serving FastAPI route /items - get list of items for the pallet to proceed.
    Only items with no status Placed are selected here.

    Args:
        order_id: string pallet ID

    Returns:
        data: ItemsResponse pydantic class contains:
            items: list of the items for the pallet to proceed
    """
    hw_id = user.preferred_username
    items = []

    with switch_db(Orders, f"backend_{hw_id}") as Orders_, switch_db(Items, f"backend_{hw_id}") as Items_, switch_db(
        Trucks, f"backend_{hw_id}"
    ) as Trucks_, switch_db(Pallet, f"backend_{hw_id}") as Pallet_:

        order = get_one_order(order_id, Orders_)

        for truckID in order["trucks"]:
            tr = Trucks_.find_by_id(truckID)
            for p in tr["pallets"]:
                pallet = Pallet_.find_by_id(p)
                for itemid in pallet["items"]:
                    item = Items_.find_by_id(itemid)
                    if item:
                        if item.status != "Placed":
                            items.append(Item(ID=item.itemid, name=item.name, images=[]))
                    if len(items) == 5:
                        break
                else:
                    continue
                break
            else:
                continue
            break

    return ItemsResponse(items=items)


@app.get(
    "/item/{item_id}/placement",
    response_model=PlacementResponse,
    responses={404: {}},
    dependencies=[Depends(db_preload)],
)
async def placement(item_id: str, user: OIDCUser = Depends(idp.get_current_user())) -> PlacementResponse:
    """Accepts item_id parameter and returns pydantic formatted data

    Serving FastAPI route /item/{item_id}/placement - getting data for placing the item.

    Args:
        item_id: string ID of item that will be placed

    Returns:
        data: PlacementResponse pydantic class contains:
            images: list of the placement images for the item that placing
    """
    hw_id = user.preferred_username
    start_time = time.time()
    images = placement_images(item_id)

    with switch_db(Items, f"backend_{hw_id}") as Items_:
        found = Items_.update_images(item_id, images)
        if not found:
            raise HTTPException(status_code=404)

    with switch_db(Orders, f"backend_{hw_id}") as Orders_:
        order = Orders_.findall().first()
        Orders_.update_phase(order.ID, 2)
        Orders_.update_status(order.ID, "InProgress")
    res = PlacementResponse(images=images)
    res_time = time.time() - start_time
    log.info(f"feapi_placement response time = {res_time}")
    return res


@app.put(
    "/item/{item_id}/placed",
    response_model=Optional[ResponseMessage],
    responses={404: {}},
    dependencies=[Depends(db_preload)],
)
async def placed(item_id: str, user: OIDCUser = Depends(idp.get_current_user())) -> Optional[ResponseMessage]:
    """Accepts item_id parameter  and returns pydantic formatted data

    Serving FastAPI route /item/{item_id}/placed -
    gets placement and sets item status to Placed.

    Args:
        item_id: string ID of item that will be placed

    Returns:
        Oprional data: ResponseMessage pydantic class contains
            json string {"message":"placement"}
    """
    hw_id = user.preferred_username

    with switch_db(Orders, f"backend_{hw_id}") as Orders_, switch_db(Items, f"backend_{hw_id}") as Items_, switch_db(
        Trucks, f"backend_{hw_id}"
    ) as Trucks_, switch_db(Pallet, f"backend_{hw_id}") as Pallet_:

        found = Items_.update_status(item_id, "Placed")
        if not found:
            raise HTTPException(
                status_code=404, detail=f"couldn't get  Items.update_status with parameter item_id={item_id}"
            )
        count_nonplaced_order = 0  # Orders.count_status(item_id, 'Placed')

        for order in Orders_.findall():
            for trk in order.trucks:
                truck = Trucks_.find_by_id(trk)
                count_nonplaced_truck = 0
                for pal in truck.pallets:
                    pallet = Pallet_.find_by_id(pal)
                    for itm in pallet.items:
                        item = Items_.find_by_id(itm)
                        if item.status != "Placed":
                            count_nonplaced_order += 1
                            count_nonplaced_truck += 1
                if count_nonplaced_truck == 0:
                    Trucks_.update_status(truck.ID, "Completed")

        if count_nonplaced_order == 0:
            order = Orders_.findall().first()
            order_id = order.ID
            Orders_.update_status(order_id, "Completed")
            return ResponseMessage(message="Done")
    return None


@app.post("/abort", response_model=ResponseMessage, dependencies=[Depends(db_preload)])
async def abort(data: Abort) -> ResponseMessage:
    """interrupts process, does nothing with data in database"""
    return ResponseMessage(message="Abort")


@app.get("/image/{path}/{item_id}/{image}", dependencies=[Depends(db_preload)])
async def image(path: str, item_id: str, image: str) -> FileResponse:
    """Returs image as file"""
    path = os.path.abspath(__file__ + "/../") + "/" + path + "/" + item_id + "/" + image
    # print(path)
    return FileResponse(path)


@app.get(
    "/order/{order_id}/status",
    response_model=ResponseMessage,
    responses={404: {}},
    dependencies=[Depends(db_preload)],
)
async def order_status(order_id: str, user: OIDCUser = Depends(idp.get_current_user())) -> ResponseMessage:
    """Accepts order_id parameter and returns pydantic formatted data

    Serving FastAPI route /order/{order_id}/status -
    returns order status.

    Args:
        order_id: string ID of the order

    Returns:
        data: ResponseMessage pydantic class contains:
            message: json string {"message":"InProgress"} where InProgress is status value
    """
    msg = ""
    hw_id = user.preferred_username
    with switch_db(Orders, f"backend_{hw_id}") as Orders_:
        order = get_one_order(order_id, Orders_)
        msg = order.status.value
    return ResponseMessage(message=msg)


@app.get(
    "/truck/{truck_id}/status",
    response_model=ResponseMessage,
    responses={404: {}},
    dependencies=[Depends(db_preload)],
)
async def truck_status(truck_id: str, user: OIDCUser = Depends(idp.get_current_user())) -> ResponseMessage:
    """Accepts truck_id parameter and returns pydantic formatted data

    Serving FastAPI route /truck/{truck_id}/status -
    returns truck status.

    Args:
        truck_id: string ID of the truck

    Returns:
        data: ResponseMessage pydantic class contains:
            message: json string {"message":"Ready"} where Ready is status value
    """
    msg = ""
    hw_id = user.preferred_username
    with switch_db(Trucks, f"backend_{hw_id}") as Trucks_:
        truck = Trucks_.find_by_id(truck_id)
        if truck is None:
            raise HTTPException(
                status_code=404, detail=f"couldn't get truck with parameter truck_id={truck_id} in truck status"
            )
        msg = truck.status.value

    return ResponseMessage(message=msg)


@app.post("/quit", responses={404: {}}, dependencies=[Depends(db_preload)])
async def quit(user: OIDCUser = Depends(idp.get_current_user())) -> None:
    """Accepts and returns pydantic formatted data

    Serving FastAPI route /quit -
    runs clear_db for deleting all data from database
    when order is complete

    Returns:
        None
    """
    hw_id = user.preferred_username

    with switch_db(Orders, f"backend_{hw_id}") as Orders_, switch_db(Items, f"backend_{hw_id}") as Items_, switch_db(
        Trucks, f"backend_{hw_id}"
    ) as Trucks_, switch_db(Pallet, f"backend_{hw_id}") as Pallet_:
        Orders_.drop_collection()
        Trucks_.drop_collection()
        Pallet_.drop_collection()
        Items_.drop_collection()

    return None


if __name__ == "__main__":
    import uvicorn

    init_logging("feapi")
    start_sentry()

    port = int(os.getenv("PORT", "5000"))

    root_path = os.getenv("ROOT_PATH", "")

    uvicorn.run(app, host="0.0.0.0", port=port, root_path=root_path)
