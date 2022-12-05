"""Common procedurs callint FastAPI routes to use in unit and end-to-end or integration tests

Each one calls the route 2 times to emulate work with >1 device
"""

import json
import logging
from typing import Dict, List, Optional

from fastapi.testclient import TestClient
from pymongo import MongoClient

from feapi.feapp import app

# Initialisation logging
log = logging.getLogger("feapi.feapp")

placement_global = {"546354": "", "455421": ""}

DEVICES = [{"id": "546354", "password": "84ngb6sdab"}, {"id": "455421", "password": "2nc043nycx"}]


def get_device_password(hw_id: str) -> Optional[str]:
    for hw in DEVICES:
        if hw["id"] == hw_id:
            return hw["password"]
    return None


def get_auth(hw_id: str, dbconnect: MongoClient) -> str:
    with TestClient(app) as client:
        response = client.post(
            "/auth",
            json={"hw_id": hw_id, "password": get_device_password(hw_id)},
        )
        assert response.status_code == 200
        token = response.json()["accessToken"]
        db = dbconnect[f"backend_{hw_id}"]
        db["Session"].delete_many({})
        db["Session"].insert_one({"token": token})
        return token


def get_token(hw_id: str, dbconnect: MongoClient) -> str:
    db = dbconnect[f"backend_{hw_id}"]
    token_ = db["Session"].find_one()
    if token_:
        return token_["token"]
    else:
        return get_auth(hw_id, dbconnect)


def one_file(path: str) -> bytes:
    im_path = path
    with open(im_path, "rb") as f:
        return f.read()


async def check_item(dbconnect: MongoClient, itemid: str, hw_id: str) -> str:
    status = ""
    db = dbconnect[f"backend_{hw_id}"]
    pallets = db["pallet"].find()
    for p in pallets:
        for i in p["items"]:
            if i == itemid:
                item = db["itgems"].find_one({"itemid": itemid})
                if item:
                    status = item["status"]
    return status


async def _auth(test_client: TestClient, dbconnect: MongoClient) -> None:
    """Calls /auth app route, autorizes and sets token into cached mongoDB

    Args:
        test_client - client imported from TestClient,
        allows to emulate request from frontend device
        dbconnect - the MongoClient instance to work with mongoDB
    """
    for hw in DEVICES:
        auth = get_auth(hw["id"], dbconnect)
        token = get_token(hw["id"], dbconnect)
        assert auth == token


async def _init(test_client: TestClient, dbconnect: MongoClient) -> None:
    """Calls /init app route, fills all data in DB

    Args:
        test_client - client imported from TestClient,
        allows to emulate request from frontend device
        dbconnect - the MongoClient instance to work with mongoDB
    """
    orders_devices = []

    for hw in DEVICES:
        hw_id = hw["id"]
        token = get_token(hw_id, dbconnect)
        response = test_client.post(
            "/init",
            json={"hw_id": hw_id, "batStatus": 28, "screenRes": "1920x1080"},
            headers={
                "Authorization": token,
            },
        )
        assert response.status_code == 200
        assert all(len(order["itemCount"]) > 0 for order in response.json()["orders"])

        db = dbconnect[f"backend_{hw_id}"]
        orders = db["orders"]
        order = orders.find_one()
        if order:
            orders_devices.append(order["hw_id"])
            assert order["hw_id"] == hw_id
            assert len(order["items_uniq"]) >= 1
    if len(orders_devices) > 0:
        assert orders_devices[0] != orders_devices[1]


async def _get_order_list(test_client: TestClient, dbconnect: MongoClient) -> str:
    """Calls /order app route, returns a pallet to load

    Args:
        test_client - client imported from TestClient,
        allows to emulate request from frontend device
        dbconnect - the MongoClient instance to work with mongoDB
    Returns:
        pallet_current - number of the next pallet to load
    """
    pallet_current = ""
    for hw in DEVICES:
        hw_id = hw["id"]
        token = get_token(hw_id, dbconnect)
        response = test_client.get(
            "/order",
            params={"order_id": "TRO-11-000000012"},
            headers={
                "Authorization": token,
            },
        )
        pallets_sample = ["#1", "#2", "#3", "#4", "#5"]
        pallet_current = str(json.loads(response.text)["palletId"])
        assert response.status_code == 200
        assert pallets_sample.count(pallet_current) == 1
        assert json.loads(response.text)["truckId"] == "1"

    order_list = []
    pallet_list = []

    for hw_id in ["546354", "455421"]:
        db = dbconnect[f"backend_{hw_id}"]
        order = db["orders"].find_one({"ID": "TRO-11-000000012"})
        if order:
            order_list.append(order["ID"])
        truck_id = order["trucks"][0]
        truck = db["trucks"].find_one({"ID": truck_id})

        if truck:
            palletes = truck["pallets"]
            pallet_list.append(palletes)
        assert order["ID"] == "TRO-11-000000012"
        assert palletes == ["1", "2"] or palletes == ["3", "4", "5"]

    assert order_list[0] == order_list[1]
    assert pallet_list[0] == pallet_list[1]

    return pallet_current


async def _get_items_list(test_client: TestClient, dbconnect: MongoClient, pallet_current: str) -> List[Dict]:
    """Calls /items app route, returns list of item for current pallete

    Args:
        test_client - client imported from TestClient,
        allows to emulate request from frontend device
        dbconnect - the MongoClient instance to work with mongoDB
    Returns:
        pallet_current - number of the next pallet to load
    """
    res: List[Dict] = []
    for hw in DEVICES:
        hw_id = hw["id"]
        token = get_token(hw_id, dbconnect)
        log.debug(f"hw_id = {hw_id}")
        log.debug("before response from /items route")

        response = test_client.get(
            "/items",
            params={"order_id": "TRO-11-000000012"},
            headers={
                "Authorization": token,
            },
        )

        assert response.status_code == 200
        res = json.loads(response.text)["items"]

    items_bases = []
    for hw_id in ["546354", "455421"]:
        items = []
        db = dbconnect[f"backend_{hw_id}"]
        for pallet in db["pallet"].find({}):
            for i in pallet["items"]:
                item = db["items"].find_one({"itemid": i})
                if item:
                    items.append(dict({"ID": item["itemid"], "name": item["name"], "images": item["Ddata"]}))

        assert len(items) >= 1
        items_bases.append(items)

    assert items_bases[0] == items_bases[1]
    return res


async def _placement(
    test_client: TestClient, test_image: str, dbconnect: MongoClient, item_id: str, pallet_current: str
) -> bool:
    """Calls /items/{item_id}/placement app route, returns placement ID and images

    Args:
        test_client - client imported from TestClient,
        allows to emulate request from frontend device
        dbconnect - the MongoClient instance to work with mongoDB
    Returns:
        placement - placement ID of the item
    """
    items_list = []
    for hw in DEVICES:
        hw_id = hw["id"]
        token = get_token(hw_id, dbconnect)
        response = test_client.get(
            f"/item/{item_id}/placement",
            headers={
                "Authorization": token,
            },
        )
        assert response.status_code == 200

        items_status = await check_item(dbconnect, item_id, hw_id)
        items_list.append(items_status)
    assert items_list[0] == items_list[1]

    return True


async def _placed(test_client: TestClient, dbconnect: MongoClient, item_id: str, pallet_id: str = None) -> None:
    """Calls /items/{item_id}/placed app route, changes item status to Placed

    Args:
        test_client - client imported from TestClient,
        allows to emulate request from frontend device
        dbconnect - the MongoClient instance to work with mongoDB
    """
    items_list = []
    for hw in DEVICES:
        hw_id = hw["id"]
        token = get_token(hw_id, dbconnect)
        response = test_client.put(
            f"/item/{item_id}/placed",
            headers={
                "Authorization": token,
            },
        )

        assert response.status_code == 200
        assert response.text == "null"

        items_status = await check_item(dbconnect, item_id, hw_id)
        items_list.append(items_status)
    assert items_list[0] == items_list[1]


async def _abort(test_client: TestClient, dbconnect: MongoClient) -> None:
    """Calls /abort route, just interrunpts process and does nothing

    Args:
        test_client - client imported from TestClient
    """
    for hw in DEVICES:
        token = get_token(hw["id"], dbconnect)
        response = test_client.post(
            "/abort",
            json={"reason": "lunch"},
            headers={
                "Authorization": token,
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Abort"


async def _image(test_client: TestClient, dbconnect: MongoClient) -> None:
    """Calls /abort route, just interrunpts process and does nothing

    Args:
        test_client - client imported from TestClient
    """
    for hw in DEVICES:
        token = get_token(hw["id"], dbconnect)
        for path in ["1.gif", "2.png", "3.png"]:
            response = test_client.get(
                f"/image/placement_imgs/4ALC0060/{path}",
                headers={
                    "Authorization": token,
                },
            )
            assert response.status_code == 200
            res = response.content
            # print("response.content", type(response.content), len(response.content))
            assert type(res) == bytes
            assert len(res) > 0


async def _order_status(test_client: TestClient, dbconnect: MongoClient) -> None:
    """Calls /order/{order_id}/status app route, sends order status

    Args:
        test_client - client imported from TestClient,
        allows to emulate request from frontend device
        dbconnect - the MongoClient instance to work with mongoDB
    """
    for hw in DEVICES:
        hw_id = hw["id"]
        token = get_token(hw_id, dbconnect)
        response = test_client.get(
            "/order/TRO-11-000000012/status",
            headers={
                "Authorization": token,
            },
        )
        assert response.status_code == 200
        assert (
            response.json()["message"] == "InProgress"
            or response.json()["message"] == "Ready"
            or response.json()["message"] == "Completed"
            or response.json()["message"] == "N/A"
        )

    orders_list = []
    for hw_id in ["546354", "455421"]:
        db = dbconnect[f"backend_{hw_id}"]
        order = db["orders"].find_one({"ID": "TRO-11-000000012"})
        if order:
            status = order["status"]
            orders_list.append(status)
    assert orders_list[0] == orders_list[1]


async def _truck_status(test_client: TestClient, dbconnect: MongoClient) -> None:
    """Calls /truck/{truck_id}/status app route, sends truck status

    Args:
        test_client - client imported from TestClient,
        allows to emulate request from frontend device
        dbconnect - the MongoClient instance to work with mongoDB
    """
    for hw in DEVICES:
        hw_id = hw["id"]
        token = get_token(hw_id, dbconnect)
        response = test_client.get(
            "/truck/1/status",
            headers={
                "Authorization": token,
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Ready"

    trucks_list = []

    for hw in DEVICES:
        hw_id = hw["id"]
        db = dbconnect[f"backend_{hw_id}"]
        truck = db["trucks"].find_one({"ID": "1"})
        if truck:
            status = truck["status"]
            trucks_list.append(status)

    assert trucks_list[0] == trucks_list[1]


async def _quit(test_client: TestClient, dbconnect: MongoClient) -> None:
    """Calls /quit app route, droppes the database

    Args:
        test_client - client imported from TestClient,
        allows to emulate request from frontend device
        dbconnect - the MongoClient instance to work with mongoDB
    """
    for hw in DEVICES:
        hw_id = hw["id"]
        token = get_token(hw_id, dbconnect)
        response = test_client.post(
            "/quit",
            json={"hw_id": hw_id},
            headers={
                "Authorization": token,
            },
        )
        assert response.status_code == 200 or response.status_code == 404
        assert response.text == "null"
        db = dbconnect[f"backend_{hw_id}"]
        db["orders"].find_one({"ID": "1"})
        assert db["orders"].find_one({}) is None

    for hw in DEVICES:
        hw_id = hw["id"]
        db = dbconnect[f"backend_{hw_id}"]
        db["orders quit"].find_one({"ID": "1"})
