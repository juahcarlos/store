import typing

from mongoengine import BooleanField, Document, FloatField, ListField, StringField

from feapi.db.models.item import Items

if typing.TYPE_CHECKING:
    from feapi.db.models.truck import Trucks


class Pallet(Document):
    ID = StringField(max_length=50)
    n = StringField(max_length=255)
    v = FloatField()
    u = FloatField()
    gross_weight = FloatField()
    width = FloatField()
    height = FloatField()
    depth = FloatField()
    items = ListField()
    truckID = StringField()
    finished = BooleanField()
    # meta = {"db_alias": "default"}

    @classmethod
    def insert_new(cls, data: dict) -> bool:
        items_ids = [str(item["itemid"]) for item in data["items"]]
        pallete = cls(
            ID=data["ID"],
            items=items_ids,
            n="pallet",
            v=data["v"],
            u=data["u"],
            gross_weight=data["gross_weight"],
            width=data["width"],
            height=data["height"],
            depth=data["depth"],
            truckID=data["truckID"],
        )
        pallete.save()
        return True

    @classmethod
    def findall_trucks(cls) -> list["Trucks"]:
        return cls.objects().distinct("truckID")

    @classmethod
    def findall(cls) -> list["Pallet"]:
        return cls.objects().order_by("ID")

    @classmethod
    def findall_in_truck(cls, truckID: str) -> list["Pallet"]:
        return cls.objects(truckID=truckID).order_by("ID")

    @classmethod
    def find_by_id(cls, id: str) -> "Pallet":
        return cls.objects(ID=id).first()

    @classmethod
    def delete_by_id(cls, id: str) -> bool:
        pallet = cls.objects(ID=id).first()
        if pallet:
            for item_id in pallet.items:
                Items.delete_by_id(item_id)
            pallet.delete()
        return pallet is not None

    @classmethod
    def get_nonfinished(cls) -> int:
        return cls.objects(finished=False).first()

    @classmethod
    def get_nonfinished_count(cls) -> int:
        count = 0
        pallets = cls.findall()
        for pallet in pallets:
            if not pallet.finished:
                count += 1
        return count

    @classmethod
    def update_finished(cls, id_: str, value: bool) -> bool:
        pallet = cls.find_by_id(id_)
        pallet.finished = value
        pallet.save()
        return True

    @classmethod
    def update_all_finished(cls, value: bool) -> bool:
        for pallet in cls.findall():
            pallet.finished = value
            pallet.save()
        return True
