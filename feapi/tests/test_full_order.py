"""End-to-end test, emulate process of full order loading,
item by item, pallet by pallet

Test_client, dbconnect, test_image are the fixtures
imported from and described in the conftest.py
"""
import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from tests.test_full import (
    _auth,
    _get_items_list,
    _get_order_list,
    _init,
    _order_status,
    _placed,
    _placement,
    _quit,
    _truck_status,
)


@pytest.mark.asyncio
async def test_run_all(test_client: TestClient, dbconnect: MongoClient, test_image: str) -> None:
    await _quit(test_client, dbconnect)
    await _auth(test_client, dbconnect)
    await _init(test_client, dbconnect)
    db = dbconnect["backend_546354"]
    pallets = db["pallet"].find()
    for pallet in pallets:
        # !!! -- should be uncomment when /orders will return one pallet, not a list -- !!!
        # pallet_current = await _get_order_list(test_client, dbconnect)
        await _get_order_list(test_client, dbconnect)
        pallet_current = pallet["ID"]
        items = await _get_items_list(test_client, dbconnect, pallet_current)
        print("items test_run_all", len(items))
        if len(items) > 0 and items[0] != {}:
            for item in items:
                await _placement(test_client, test_image, dbconnect, item["ID"], pallet_current)
                await _placed(test_client, dbconnect, item["ID"])
        else:
            continue

    await _order_status(test_client, dbconnect)
    await _truck_status(test_client, dbconnect)
    # await _quit(test_client, dbconnect)
