from pathlib import Path
from typing import Any

import ultima_scraper_api

user_types = ultima_scraper_api.user_types
from datetime import datetime

import sqlalchemy
from alembic import command
from alembic.config import Config
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.session import Session, sessionmaker

from ultima_scraper_api.database.databases.user_data import user_database


class DBCollection(object):
    def __init__(self) -> None:
        self.user_database = user_database

    def database_picker(self, database_name: str):
        match database_name:
            case "user_data":
                database = self.user_database
            case _:
                raise Exception(f'"{database_name}" is an invalid database name')
        return database


class DBManager:
    def __init__(
        self, database_path: Path, api_type: str, legacy: bool = False
    ) -> None:
        self.database_path = database_path
        self.alembic_directory = Path(__file__).parent.joinpath(
            f"{'databases' if not legacy else 'archived_databases'}",
            database_path.stem.lower(),
            "alembic",
        )
        self.databases_directory = Path(__file__).parent.joinpath(
            "databases", database_path.stem
        )
        self.archived_databases_directory = Path(__file__).parent.joinpath(
            "archived_databases", api_type.lower()
        )
        pass

    async def export_sqlite(
        self, database_path: Path, api_type: str, datas: list[dict[str, Any]]
    ):
        metadata_directory = database_path.parent
        metadata_directory.mkdir(exist_ok=True)
        await self.run_migrations()
        Session, _engine = await self.create_database_session()
        db_collection = DBCollection()
        database = db_collection.database_picker(database_path.stem)
        database_session = Session()
        api_table = database.table_picker(api_type)
        if not api_table:
            return
        for post in datas:
            post_id = post["post_id"]
            postedAt = post["postedAt"]
            date_object = None
            if postedAt:
                if not isinstance(postedAt, datetime):
                    date_object = datetime.strptime(postedAt, "%d-%m-%Y %H:%M:%S")
                else:
                    date_object = postedAt
            result = database_session.query(api_table)
            post_db = result.filter_by(post_id=post_id).first()
            if not post_db:
                post_db = api_table()
            if api_type == "Products":
                post_db.title = post["title"]
            if api_type == "Messages":
                post_db.user_id = post.get("user_id", None)
            post_db.post_id = post_id
            post_db.text = post["text"]
            if post["price"] is None:
                post["price"] = 0
            post_db.price = post["price"]
            post_db.paid = post["paid"]
            post_db.archived = post["archived"]
            if date_object:
                post_db.created_at = date_object
            database_session.add(post_db)
            for media in post["medias"]:
                if media["media_type"] == "Texts":
                    continue
                created_at = media.get("created_at", postedAt)
                if not isinstance(created_at, datetime):
                    date_object = datetime.strptime(created_at, "%d-%m-%Y %H:%M:%S")
                else:
                    date_object = postedAt
                media_id = media.get("media_id", None)
                result = database_session.query(database.media_table)
                media_db = result.filter_by(media_id=media_id).first()
                if not media_db:
                    media_db = result.filter_by(
                        filename=media["filename"], created_at=date_object
                    ).first()
                    if not media_db:
                        media_db = database.media_table()
                media_db.media_id = media_id
                media_db.post_id = post_id
                if "_sa_instance_state" in post:
                    media_db.size = media["size"]
                    media_db.downloaded = media["downloaded"]
                media_db.link = media["links"][0]
                media_db.preview = media.get("preview", False)
                media_db.directory = media["directory"]
                media_db.filename = media["filename"]
                media_db.api_type = api_type
                media_db.media_type = media["media_type"]
                media_db.linked = media.get("linked", None)
                if date_object:
                    media_db.created_at = date_object
                database_session.add(media_db)
        database_session.commit()
        database_session.close()
        return Session, api_type, database

    async def run_migrations(self) -> None:
        while True:
            try:
                ini_path = self.alembic_directory.parent.joinpath("alembic.ini")
                full_database_path = f"sqlite:///{self.database_path}"
                alembic_cfg = Config(ini_path.as_posix())
                alembic_cfg.set_main_option(
                    "script_location", self.alembic_directory.as_posix()
                )
                alembic_cfg.set_main_option("sqlalchemy.url", full_database_path)
                command.upgrade(alembic_cfg, "head")
                break
            except Exception as e:
                print(e)
                pass

    async def import_database(self):
        _Session, engine = await self.create_database_session()
        database_session: Session = _Session()
        return database_session, engine

    async def create_database_session(
        self,
        connection_type: str = "sqlite:///",
        autocommit: bool = False,
        pool_size: int = 5,
    ) -> tuple[scoped_session, Engine]:
        kwargs = {}
        connection_info = self.database_path
        if connection_type == "mysql+mysqldb://":
            kwargs["pool_size"] = pool_size
            kwargs["pool_pre_ping"] = True
            kwargs["max_overflow"] = -1
            kwargs["isolation_level"] = "READ COMMITTED"

        engine = sqlalchemy.create_engine(
            f"{connection_type}{connection_info}?charset=utf8mb4", **kwargs
        )
        session_factory = sessionmaker(bind=engine, autocommit=autocommit)
        Session = scoped_session(session_factory)
        return Session, engine

    async def legacy_sqlite_updater(
        self,
        legacy_metadata_path: Path,
        api_type: str,
        subscription: user_types,
        delete_metadatas: list[Path],
    ):
        final_result: list[dict[str, Any]] = []
        if legacy_metadata_path.exists():
            await self.run_migrations()
            database_name = "user_data"
            session, _engine = await self.create_database_session()
            database_session: Session = session()
            db_collection = DBCollection()
            database = db_collection.database_picker(database_name)
            if database:
                if api_type == "Messages":
                    api_table_table = database.table_picker(api_type, True)
                else:
                    api_table_table = database.table_picker(api_type)
                media_table_table = database.media_table.media_legacy_table
                if api_table_table:
                    result = database_session.query(api_table_table).all()
                    result2 = database_session.query(media_table_table).all()
                    for item in result:
                        item = item.__dict__
                        item["medias"] = []
                        for item2 in result2:
                            if item["post_id"] != item2.post_id:
                                continue
                            item2 = item2.__dict__
                            item2["links"] = [item2["link"]]
                            item["medias"].append(item2)
                        item["user_id"] = subscription.id
                        item["postedAt"] = item["created_at"]
                        final_result.append(item)
                    delete_metadatas.append(legacy_metadata_path)
            database_session.close()
        return final_result, delete_metadatas
