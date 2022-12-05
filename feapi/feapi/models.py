from typing import List, Optional, Union

from humps import camelize
from pydantic import BaseModel


def to_camel(string: str) -> str:
    camelization = camelize(string)
    assert isinstance(camelization, str)
    return camelization


class CamelModel(BaseModel):
    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True


class AuthRequest(CamelModel):
    hw_id: str
    password: str


class AuthResponse(CamelModel):
    access_token: str
    token_type: str


class ResponseMessage(CamelModel):
    message: str


class ImagesResponse(CamelModel):
    images: List


class Image(CamelModel):
    image: str


class PlacementResponse(CamelModel):
    images: Optional[List[Image]]


class InitRequest(CamelModel):
    bat_status: int
    screen_res: str


class OrderRequest(CamelModel):
    order_id: str


class Item(CamelModel):
    ID: str
    name: str
    images: List[Image]


class ItemsResponse(CamelModel):
    items: List[Item]


class Abort(CamelModel):
    reason: str


class ItemCount(CamelModel):
    id: str
    count: int


class Order(CamelModel):
    id: str
    item_count: List[ItemCount]


class OrderResponse(CamelModel):
    truck_id: str
    gate_id: str
    pallet_id: str
    pallet_count: int


class ItemStatusDict(CamelModel):
    order_id: str
    truck_id: str
    gate_id: str
    pallet_no: int


class ItemStatus(CamelModel):
    message: Union[str, ItemStatusDict]


class InitResponse(CamelModel):
    phase: int
    orders: List[Order]


class ImageResponse(CamelModel):
    image: bytes
