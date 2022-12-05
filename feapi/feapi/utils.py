import json
import logging
import os
from contextlib import contextmanager
from typing import Iterator, List

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi_keycloak import FastAPIKeycloak, OIDCUser
from mongoengine import Document
from mongoengine.context_managers import switch_db
from sentry_sdk import capture_exception

from feapi.db.connect import dbconn
from feapi.db.models.item import Items
from feapi.db.models.item_count import ItemsCount
from feapi.db.models.order import Orders
from feapi.db.models.pallett import Pallet
from feapi.db.models.truck import Trucks
from feapi.models import Image

app = FastAPI(
    openapi_url="/docs/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

log = logging.getLogger(__name__)


@app.middleware("http")
async def log_headers(request: Request, call_next):  # type: ignore
    log.debug(f"Headers {request.headers}")
    return await call_next(request)


@contextmanager
def shift_db(hw_id: str) -> Iterator[Document]:
    """Accepts device ID hw_id and swithes to DB backend_{hw_id}

    Swithes to db named from device ID when quering from collections

    Args:
        hw_id: string parameter means device ID

    Yields:
        Orders_, Items_, Trucks_, Pallet_, Placement_: iterator of Document
    """
    with switch_db(Orders, f"backend_{hw_id}") as Orders_, switch_db(Items, f"backend_{hw_id}") as Items_, switch_db(
        Trucks, f"backend_{hw_id}"
    ) as Trucks_, switch_db(Pallet, f"backend_{hw_id}") as Pallet_:
        yield Orders_, Items_, Trucks_, Pallet_


def prepare_db(hw_id: str) -> bool:

    db = dbconn(hw_id)
    db[f"backend_{hw_id}"]

    with open(os.path.abspath(__file__ + "/../") + "/resources/data.json", "r") as f:
        data = json.load(f)

    with switch_db(Orders, f"backend_{hw_id}") as Orders_, switch_db(Items, f"backend_{hw_id}") as Items_, switch_db(
        Trucks, f"backend_{hw_id}"
    ) as Trucks_, switch_db(Pallet, f"backend_{hw_id}") as Pallet_:

        for order in data["orders"]:

            items_uniq: dict[str, int] = {}
            order["hw_id"] = hw_id

            truck_ids = [truck["ID"] for truck in order["trucks"]]
            order_db = Orders_(
                ID=order["ID"],
                hw_id=order["hw_id"],
                status="Ready",
                phase=1,
                trucks=truck_ids,
                items_uniq=[],
            )
            for truck in order["trucks"]:
                if not Trucks_.find_by_id(truck["ID"]):
                    Trucks_.insert_new(truck)

                for pallet in truck["box"]:
                    if not Pallet_.find_by_id(pallet["ID"]):
                        pallet["truckID"] = truck["ID"]
                        try:
                            Pallet_.insert_new(pallet)
                        except Exception as ex:
                            print(f"insert_new Pallet ex={ex}")
                        try:
                            Pallet_.update_all_finished(False)
                        except Exception as ex:
                            print(f"update_all_finished Pallet ex={ex}")

                    for item in pallet["items"]:
                        item["name"].replace("\\u", "\\u")
                        itemid = item["itemid"]
                        if itemid not in items_uniq.keys():
                            items_uniq[itemid] = 1
                        else:
                            items_uniq[itemid] += 1

                        if not Items_.find_by_id(itemid):
                            item["descr"] = ""
                            item["Fragile"] = True
                            item["TopSideUp"] = True
                            item["Heavy"] = True
                            item["MustBeOnTop"] = True
                            item["Flammable"] = True
                            item["Dangerous"] = True
                            item["PackedAlone"] = True
                            item["Stackable"] = True
                            item["LoadCapacity"] = True
                            item["Unit"] = 123
                            item["Hedgehog"] = True
                            item["Ddata"] = b""
                            Items_.insert_new(item)
            palettes = []
            truckIDs = order_db.trucks

            for truckID in truckIDs:
                palettes.extend([p["ID"] for p in Pallet_.findall_in_truck(truckID)])

            order_db.items_uniq = [ItemsCount(id=key, count=val) for key, val in items_uniq.items()]
            order_db.save()

    return True


def get_one_order(order_id: str, Orders_: Document) -> Document:
    order = Orders_.find_by_id(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"couldn't get Orders.objects with parameters ID={order_id}")
    return order


idp = FastAPIKeycloak(
    server_url="https://keycloak.bluemotion-packer.com",
    client_id="feapi",
    client_secret="pPkANuC1XFTRCOf2gD6WxTCpRn7Jh5CL",
    admin_client_secret="BfIO8YuZrfNoBHLSt36QUa4ffWkc9qzg",
    realm="intelligent-warehouse",
    callback_uri="http://0.0.0.0:5000/callback",
)
idp.add_swagger_config(app)


async def db_preload(user: OIDCUser = Depends(idp.get_current_user())) -> None:
    hw_id = user.preferred_username
    dbconn(hw_id)


async def clear_db(hw_id: str) -> None:
    """deleting all the data from the mongo cache database

    Args:
        hw_id: string ID of the device

    Returns:
        None
    """
    with shift_db(hw_id) as [Orders_, Items_, Trucks_, Pallet_]:
        Orders_.findall().delete()
        Orders_.drop_collection()
        Trucks_.findall().delete()
        Trucks_.drop_collection()
        Pallet_.findall().delete()
        Pallet_.drop_collection()
        Items_.findall().delete()
        Items_.drop_collection()


def one_file(ipath: str, path: str) -> bytes:
    """Accepts path and filename and opens file

    It's temporary, in future image data will be imported from the Solver DB.

    Args:
        ipath: path to dir with file
        path: filename

    Returns:
        bytes: raw opened file data
    """
    im_path = path + "/" + ipath
    with open(im_path, "rb") as f:
        return f.read()


def pathes(path: str, item_id: str) -> list:
    """scans directory with images and returns list of their filenames

    It's temporary, in future image data will be imported from the Solver DB.

    Args:
        path: path to dir with files
        item_id: id of the item

    Returns:
        img_pathes: list of strings filenames

    """
    try:
        img_pathes = os.listdir(path)
    except Exception as ex:
        capture_exception(ex)
        raise HTTPException(status_code=404, detail=f"couldn't get img_pathes with parameter item_id={item_id}")

    return img_pathes


def placement_images(item_id: str) -> List[Image]:
    """Accepts item_id and get all imagets for

    It's temporary, in future image data will be imported from the Solver DB.

    Args:
        item_id: id of the item

    Returns:
        images: list of pydantic classes with images base64 encoded
    """
    images = []

    # the code below to '--//--' should be replaced with query to Solver DB when it'll appear
    img_pathes = []
    # path = os.path.abspath(__file__ + "/../") + f"/placement_imgs/{item_id}"
    # DON'T FORGET TO UNCOMMENT IT WHEN REAL IMAGES WILL COME!
    path = os.path.abspath(__file__ + "/../") + "/placement_imgs/4ALC0060"
    try:
        img_pathes = os.listdir(path)
    except Exception as ex:
        capture_exception(ex)
        raise HTTPException(status_code=404, detail=f"couldn't get img_pathes with parameter item_id={item_id}")

    img_pathes = sorted(img_pathes)

    for image in sorted(img_pathes):
        if image:
            images.append(Image(image=f"/image/placement_imgs/{item_id}/{image}"))

    for img in images:
        print("Image", img)

    # --//--

    return images


'''
def placement_images(item_id: str) -> List[Image]:
    """Accepts item_id and get all imagets for

    It's temporary, in future image data will be imported from the Solver DB.

    Args:
        item_id: id of the item

    Returns:
        images: list of pydantic classes with images base64 encoded
    """
    images = []

    # the code below to '--//--' should be replaced with query to Solver DB when it'll appear
    img_pathes = []
    # path = os.path.abspath(__file__ + "/../") + f"/placement_imgs/{item_id}"
    # DON'T FORGET TO UNCOMMENT IT WHEN REAL IMAGES WILL COME!
    path = os.path.abspath(__file__ + "/../") + "/placement_imgs/4ALC0060"
    try:
        img_pathes = os.listdir(path)
    except Exception as ex:
        capture_exception(ex)
        raise HTTPException(status_code=404, detail=f"couldn't get img_pathes with parameter item_id={item_id}")

    img_pathes = sorted(img_pathes)

    for img in sorted(img_pathes):
        image_type = "data:image/png;base64,"
        if ".gif" == img[-4:]:
            image_type = "data:image/gif;base64,"
        elif ".jpg" == img[-4:]:
            image_type = "data:image/jpeg;base64,"
        elif ".jpeg" == img[-5:]:
            image_type = "data:image/jpeg;base64,"
        elif ".png" == img[-4:]:
            image_type = "data:image/png;base64,"

        image = one_file(img, path)
        if image:
            images.append(Image(image=image_type + base64.b64encode(image).decode("utf-8")))

    # --//--

    return images
'''
