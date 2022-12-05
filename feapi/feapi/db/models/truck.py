from enum import Enum

from mongoengine import Document, EnumField, ListField, StringField

from feapi.db.models.pallett import Pallet


class Status(Enum):
    na = "N/A"
    in_progress = "InProgress"
    ready = "Ready"
    completed = "Completed"


class Trucks(Document):
    ID = StringField(max_length=50)
    pallets = ListField()
    n = StringField(max_length=255)
    brand = StringField(max_length=255)
    status = EnumField(Status, default=Status.na)
    # meta = {"db_alias": "default"}

    @classmethod
    def insert_new(cls, data: dict) -> bool:
        pallet_ids = [pallet["ID"] for pallet in data["box"]]
        truck = cls(ID=data["ID"], pallets=pallet_ids, n="truck", status="Ready", brand=data["brand"])
        truck.save()
        return True

    @classmethod
    def findall(cls) -> list:
        return cls.objects().order_by("ID")

    @classmethod
    def find_by_id(cls, id: str) -> Document:
        return cls.objects(ID=id).first()

    @classmethod
    def delete_by_id(cls, id: str) -> bool:
        truck = cls.objects(ID=id).first()
        for palletID in truck.pallets:
            Pallet.delete_by_id(palletID)
        truck.delete()
        return True

    @classmethod
    def update_status(cls, ID: str, status: str) -> bool:
        truck = cls.find_by_if(ID)
        truck.status = status
        truck.save()
        return True
