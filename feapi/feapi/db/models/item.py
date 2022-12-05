from enum import Enum

from mongoengine import (
    BooleanField,
    Document,
    EnumField,
    FloatField,
    IntField,
    ListField,
    StringField,
)


class Status(Enum):
    na = "N/A"
    ready = "Ready"
    placed = "Placed"


class Items(Document):
    itemid = StringField(max_length=50)
    width = FloatField()
    height = FloatField()
    depth = FloatField()
    x = FloatField()
    y = FloatField()
    z = FloatField()
    gross_weight = FloatField()
    r = FloatField()
    color = StringField(max_length=255)
    name = StringField(max_length=255)
    descr = StringField(max_length=255)
    Fragile = BooleanField()
    TopSideUp = BooleanField()
    Heavy = BooleanField()
    MustBeOnTop = BooleanField()
    Flammable = BooleanField()
    Dangerous = BooleanField()
    PackedAlone = BooleanField()
    Stackable = BooleanField()
    LoadCapacity = BooleanField()
    Unit = IntField()
    Hedgehog = BooleanField()
    Ddata = ListField()
    status = EnumField(Status, default=Status.na)
    # meta = {"db_alias": "default"}

    @classmethod
    def insert_new(cls, data: dict) -> bool:
        item = cls(**data, status="Ready")
        item.save()
        return True

    @classmethod
    def update_images(cls, ID: str, images: list) -> bool:
        item = cls.find_by_id(ID)
        if item is None:
            return False
        item.Ddata = images
        item.save()
        return True

    @classmethod
    def findall(cls) -> list:
        return cls.objects().order_by("i")

    @classmethod
    def find_by_id(cls, id: str) -> Document:
        return cls.objects(itemid=id).first()

    @classmethod
    def update_status(cls, ID: str, status: str) -> bool:
        item = cls.find_by_id(ID)
        if item is None:
            return False
        item.status = status
        item.save()
        return True

    @classmethod
    def delete_by_id(cls, id: str) -> bool:
        item = cls.find_by_id(id)
        if item:
            item.delete()
            return True
        return False
