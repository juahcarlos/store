from mongoengine import EmbeddedDocument, IntField, StringField


class ItemsCount(EmbeddedDocument):
    id = StringField()
    count = IntField()
