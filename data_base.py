from peewee import *

db = SqliteDatabase('ezz_en_bot.sqlite')


class BaseModel(Model):
    class Meta:
        database = db


class Users(BaseModel):
    chat_id = IntegerField()
    username = CharField(max_length=100)


class Words(BaseModel):
    user = ForeignKeyField(Users, backref='words')
    en_words = CharField(max_length=50)
    ru_words = CharField(max_length=50)


db.create_tables([Users, Words])
db.close()
