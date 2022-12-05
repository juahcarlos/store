"""The file contains all fixtures importing in the tests
in the different test modules.

Using conftest file is standard pytest practice for import puposes.
"""


import base64
import os
from typing import AsyncGenerator, Iterator

import pytest
from fastapi.testclient import TestClient
from mongoengine import connect
from pymongo import MongoClient

from feapi.utils import app, clear_db, prepare_db


@pytest.fixture(scope="package")
def test_client() -> Iterator[TestClient]:
    """creates client that emulates device
    who can perform the requests from applications routes /init, /items, etc.

    Yelds: the client
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="package")
def dbconnect() -> MongoClient:
    """Connecting to the mongoDB databases

    Returns: Mongoclient to perform all standart operations with the DB
    """
    print("MONGODB_CONNECTION", os.getenv("MONGODB_CONNECTION"))
    if (connection_string := os.getenv("MONGODB_CONNECTION")) is None:
        connection_string = "mongodb://mongo-db"
    dbc = connect(host=connection_string, alias="test", uuidRepresentation="standard")
    return dbc


async def init_start() -> bool:  # AsyncGenerator[int, None]:
    """Fills all data to mongoDB databases on start one or more tests

    Returns: True if succeed
    """
    for hw_id in ["546354", "455421"]:
        prepare_db(hw_id)
    return True


async def init_finish() -> bool:
    """Deletes all data to mongoDB databases
    on start one or more tests

    Returns: True if succeed
    """
    for hw_id in ["546354", "455421"]:
        await clear_db(hw_id)

    return True


def one_file(path: str) -> bytes:
    """Just opens file

    Returns: raw data of opened file
    """
    im_path = path
    with open(im_path, "rb") as f:
        return f.read()


@pytest.fixture(scope="package")
def test_image() -> str:
    """Creates fake image to emulate the image
    would be loaded from main database

    Returns: base64 encoded string with the image data
    """
    path = "tests/placement_imgs/1847/1.png"
    image = one_file(path)
    return base64.b64encode(image).decode("utf-8")


@pytest.fixture()
async def init_fixt(test_client: TestClient, dbconnect: MongoClient) -> AsyncGenerator[int, None]:
    """Creates database and all data before and destroys
    after call each test using the fixture

    Yields: yield just using to start
    executing the test who imports the fixture
    """
    await init_start()
    yield 1
    await init_finish()
