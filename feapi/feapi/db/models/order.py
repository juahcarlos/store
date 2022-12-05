from enum import Enum

from mongoengine import (
    Document,
    EmbeddedDocumentField,
    EnumField,
    IntField,
    ListField,
    StringField,
)

from feapi.db.models.item_count import ItemsCount
from feapi.db.models.truck import Trucks


class Status(Enum):
    na = "N/A"
    in_progress = "InProgress"
    ready = "Ready"
    completed = "Completed"


class Orders(Document):
    ID = StringField(max_length=50)
    trucks = ListField()
    status = EnumField(Status, default=Status.na)
    phase = IntField()
    hw_id = StringField()
    items_uniq = ListField(EmbeddedDocumentField(ItemsCount))
    # meta = {"db_alias": "default"}

    @classmethod
    def insert_new(cls, data: dict) -> bool:
        truck_ids = [truck["ID"] for truck in data["trucks"]]
        order = cls(ID=data["ID"], hw_id=data["hw_id"], status="Ready", phase=1, trucks=truck_ids, items_uniq={})
        order.save()
        return True

    @classmethod
    def find_by_id(cls, id: str) -> Document:
        return cls.objects(ID=id).first()

    @classmethod
    def findall(cls) -> list["Orders"]:
        return cls.objects().order_by("ID")

    @classmethod
    def find_by_device(cls, hw_id: str) -> Document:
        return cls.objects(hw_id=hw_id).first()

    @classmethod
    def find_truck_id(cls, id: str) -> list:
        res = []
        order = cls.find_by_id(id)
        for tr in order.trucks:
            res.append(tr)
        return res

    @classmethod
    def delete_by_id(cls, id: str) -> bool:
        order = cls.objects(ID=id).first()
        for truckID in order["trucks"]:
            Trucks.delete_by_id(truckID)
        order.delete()
        return True

    @classmethod
    def update_status(cls, order_id: str, status: str) -> bool:
        order = cls.find_by_id(order_id)
        order.status = status
        order.save()
        return True

    @classmethod
    def update_phase(cls, order_id: str, phase: int) -> bool:
        order = cls.find_by_id(order_id)
        order.phase = phase
        order.save()
        return True

    @classmethod
    def add_uniqs(cls, ID: str, uniqs: dict) -> bool:
        order = cls.find_by_id(ID)
        order.items_uniq = uniqs
        order.save()
        return True
