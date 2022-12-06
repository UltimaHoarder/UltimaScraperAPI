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
from ultima_scraper_api.classes.prepare_directories import DirectoryManager
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
        Session, engine = await self.create_database_session()
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
                print
            print
        print
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

    async def legacy_database_fixer(
        self, database_path: Path, database, database_name, database_exists
    ):
        database_directory = os.path.dirname(database_path)
        old_database_path = database_path
        old_filename = os.path.basename(old_database_path)
        new_filename = f"Pre_Alembic_{old_filename}"
        pre_alembic_path = os.path.join(database_directory, new_filename)
        pre_alembic_database_exists = False
        if os.path.exists(pre_alembic_path):
            database_path = pre_alembic_path
            pre_alembic_database_exists = True
        datas = []
        if database_exists:
            db_manager = DBManager(database_path)
            Session, engine = await db_manager.create_database_session()
            database_session = Session()
            result = inspect(engine).has_table("alembic_version")
            if not result:
                if not pre_alembic_database_exists:
                    os.rename(old_database_path, pre_alembic_path)
                    pre_alembic_database_exists = True
        if pre_alembic_database_exists:
            Session, engine = db_helper.create_database_session(pre_alembic_path)
            database_session = Session()
            api_table = database.api_table()
            media_table = database.media_table()
            legacy_api_table = api_table.legacy(database_name)
            legacy_media_table = media_table.legacy()
            result = database_session.query(legacy_api_table)
            post_db = result.all()
            for post in post_db:
                post_id = post.id
                created_at = post.created_at
                new_item: dict[str, Any] = {}
                new_item["post_id"] = post_id
                new_item["text"] = post.text
                new_item["price"] = post.price
                new_item["paid"] = post.paid
                new_item["postedAt"] = created_at
                new_item["medias"] = []
                result2 = database_session.query(legacy_media_table)
                media_db = result2.filter_by(post_id=post_id).all()
                for media in media_db:
                    new_item2 = {}
                    new_item2["media_id"] = media.id
                    new_item2["post_id"] = media.post_id
                    new_item2["links"] = [media.link]
                    new_item2["directory"] = media.directory
                    new_item2["filename"] = media.filename
                    new_item2["size"] = media.size
                    new_item2["media_type"] = media.media_type
                    new_item2["downloaded"] = media.downloaded
                    new_item2["created_at"] = created_at
                    new_item["medias"].append(new_item2)
                datas.append(new_item)
            print
            database_session.close()
            await self.export_sqlite2(
                old_database_path, datas, database_name, legacy_fixer=True
            )

    async def export_sqlite2(
        self, archive_path, datas, parent_type, legacy_fixer=False
    ):
        metadata_directory = os.path.dirname(archive_path)
        os.makedirs(metadata_directory, exist_ok=True)
        cwd = getfrozencwd()
        api_type: str = os.path.basename(archive_path).removesuffix(".db")
        database_path = archive_path
        database_name = parent_type if parent_type else api_type
        database_name = database_name.lower()
        db_collection = db_helper.database_collection()
        database = db_collection.database_picker(database_name)
        if not database:
            return
        alembic_location = os.path.join(cwd, "database", "databases", database_name)
        database_exists = os.path.exists(database_path)
        if database_exists:
            if os.path.getsize(database_path) == 0:
                os.remove(database_path)
                database_exists = False
        if not legacy_fixer:
            await self.legacy_database_fixer(
                database_path, database, database_name, database_exists
            )
        db_helper.run_migrations(alembic_location, database_path)
        print
        Session, engine = db_helper.create_database_session(database_path)
        database_session = Session()
        api_table = database.api_table
        media_table = database.media_table

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
                media_id = media.get("media_id", None)
                result = database_session.query(media_table)
                media_db = result.filter_by(media_id=media_id).first()
                if not media_db:
                    media_db = result.filter_by(
                        filename=media["filename"], created_at=date_object
                    ).first()
                    if not media_db:
                        media_db = media_table()
                if legacy_fixer:
                    media_db.size = media["size"]
                    media_db.downloaded = media["downloaded"]
                media_db.media_id = media_id
                media_db.post_id = post_id
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
                print
            print
        print

        database_session.commit()
        database_session.close()
        return Session, api_type, database

    async def fix_sqlite(
        self,
        directory_manager: DirectoryManager,
    ):
        for final_metadata in directory_manager.user.legacy_metadata_directories:
            archived_database_path = final_metadata.joinpath("Archived.db")
            if archived_database_path.exists():
                Session2, engine = db_helper.create_database_session(
                    archived_database_path
                )
                database_session: Session = Session2()
                cwd = getfrozencwd()
                for api_type, value in api.ContentTypes():
                    database_path = os.path.join(final_metadata, f"{api_type}.db")
                    database_name = api_type.lower()
                    alembic_location = os.path.join(
                        cwd, "database", "archived_databases", database_name
                    )
                    result = inspect(engine).has_table(database_name)
                    if result:
                        db_helper.run_migrations(
                            alembic_location, archived_database_path
                        )
                        db_helper.run_migrations(alembic_location, database_path)
                        Session3, engine2 = db_helper.create_database_session(
                            database_path
                        )
                        db_collection = db_helper.database_collection()
                        database_session2: Session = Session3()
                        database = db_collection.database_picker("user_data")
                        if not database:
                            return
                        table_name = database.table_picker(api_type, True)
                        if not table_name:
                            return
                        archived_result = database_session.query(table_name).all()
                        for item in archived_result:
                            result2 = (
                                database_session2.query(table_name)
                                .filter(table_name.post_id == item.post_id)
                                .first()
                            )
                            if not result2:
                                item2 = item.__dict__
                                item2.pop("id")
                                item2.pop("_sa_instance_state")
                                item = table_name(**item2)
                                item.archived = True
                                database_session2.add(item)
                        database_session2.commit()
                        database_session2.close()
                database_session.commit()
                database_session.close()
                new_filepath = Path(
                    archived_database_path.parent,
                    "__legacy_metadata__",
                    archived_database_path.name,
                )
                new_filepath.parent.mkdir(exist_ok=True)
                shutil.move(archived_database_path, f"{new_filepath}")
