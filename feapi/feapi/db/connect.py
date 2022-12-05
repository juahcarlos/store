import os

from mongoengine import connect
from pymongo import MongoClient
from sentry_sdk import capture_exception


def dbconn(hw_id: str) -> MongoClient:
    db_name = f"backend_{hw_id}"
    if (connection_string := os.getenv("MONGODB_CONNECTION")) is None:
        connection_string = "mongodb://mongo-db"
    try:
        connect(host=connection_string, db=db_name, alias="default", uuidRepresentation="standard")
    except Exception as ex:
        capture_exception(ex)
    dbc = connect(host=connection_string, db=db_name, alias=db_name, uuidRepresentation="standard")
    return dbc
