"""Unit tests, splitted to make a possibility to test
each route separately

Test_client, dbconnect, test_image, init_fixt are the fixtures
imported from and described in the conftest.py
"""

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from tests.test_full import (
    _abort,
    _auth,
    _get_items_list,
    _get_order_list,
    _image,
    _init,
    _order_status,
    _placed,
    _placement,
    _quit,
    _truck_status,
)


@pytest.mark.asyncio
async def test_auth(test_client: TestClient, dbconnect: MongoClient, init_fixt: None) -> None:
    await _auth(test_client, dbconnect)


@pytest.mark.asyncio
async def test_init(test_client: TestClient, dbconnect: MongoClient, init_fixt: None) -> None:
    await _init(test_client, dbconnect)


@pytest.mark.asyncio
async def test_get_order_list(test_client: TestClient, dbconnect: MongoClient, init_fixt: None) -> None:
    await _get_order_list(test_client, dbconnect)


@pytest.mark.asyncio
async def test_get_items_list(test_client: TestClient, dbconnect: MongoClient, init_fixt: None) -> None:
    await _get_items_list(test_client, dbconnect, "1")


@pytest.mark.asyncio
async def test_placement(test_client: TestClient, test_image: str, dbconnect: MongoClient, init_fixt: None) -> None:
    await _placement(test_client, test_image, dbconnect, "4ALC0060", "1")


@pytest.mark.asyncio
async def test_placed(test_client: TestClient, dbconnect: MongoClient, init_fixt: None) -> None:
    await _placed(test_client, dbconnect, "4ALC0060", "1")


@pytest.mark.asyncio
async def test_abort(test_client: TestClient, dbconnect: MongoClient) -> None:
    await _abort(test_client, dbconnect)


@pytest.mark.asyncio
async def test_image(test_client: TestClient, dbconnect: MongoClient) -> None:
    await _image(test_client, dbconnect)


@pytest.mark.asyncio
async def test_order_status(test_client: TestClient, dbconnect: MongoClient, init_fixt: None) -> None:
    await _order_status(test_client, dbconnect)


@pytest.mark.asyncio
async def test_truck_status(test_client: TestClient, dbconnect: MongoClient, init_fixt: None) -> None:
    await _truck_status(test_client, dbconnect)


@pytest.mark.asyncio
async def test_quit(test_client: TestClient, dbconnect: MongoClient, init_fixt: None) -> None:
    await _quit(test_client, dbconnect)
