### messages.py ###

import copy
from typing import Optional, cast

import sqlalchemy
from ultima_scraper_api.database.databases.user_data.models.api_table import api_table
from ultima_scraper_api.database.databases.user_data.models.media_table import template_media_table
from sqlalchemy.orm.decl_api import declarative_base
from sqlalchemy.sql.schema import Column, ForeignKey, Table
from sqlalchemy.sql.sqltypes import Integer

Base = declarative_base()
LegacyBase = declarative_base()


class profiles_table(Base):
    __tablename__ = "profiles"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    user_id = cast(int, sqlalchemy.Column(sqlalchemy.Integer, nullable=False))
    username = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)


class stories_table(api_table, Base):
    api_table.__tablename__ = "stories"


class posts_table(api_table, Base):
    api_table.__tablename__ = "posts"


class messages_table(api_table, Base):
    api_table.__tablename__ = "messages"
    user_id = cast(Optional[int], sqlalchemy.Column(sqlalchemy.Integer))

    class api_legacy_table(api_table, LegacyBase):
        pass


class products_table(api_table, Base):
    api_table.__tablename__ = "products"
    title = sqlalchemy.Column(sqlalchemy.String)


class others_table(api_table, Base):
    api_table.__tablename__ = "others"


# class comments_table(api_table,Base):
#     api_table.__tablename__ = "comments"


class media_table(template_media_table, Base):
    class media_legacy_table(template_media_table().legacy_2(LegacyBase), LegacyBase):
        pass


def table_picker(table_name: str, legacy: bool = False):
    match table_name:
        case "Stories":
            table = stories_table
        case "Posts":
            table = posts_table
        case "Messages":
            table = messages_table if not legacy else messages_table().api_legacy_table
        case "Products":
            table = products_table
        case "Others":
            table = others_table
        case _:
            raise Exception(f'"{table_name}" is an invalid table name')
    return table
