import os
from pathlib import Path
from sqlalchemy.orm.session import Session, sessionmaker
from alembic.config import Config
from alembic import command
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.functions import func
# import sqlalchemy.ext.asyncio as sqlalchemy_asyncio





def run_revisions(alembic_directory: str, database_path: str = ""):
    while True:
        try:
            ini_path = os.path.join(alembic_directory, "alembic.ini")
            script_location = os.path.join(alembic_directory, "alembic")
            full_database_path = f"sqlite:///{database_path}"
            alembic_cfg = Config(ini_path)
            alembic_cfg.set_main_option("script_location", script_location)
            alembic_cfg.set_main_option("sqlalchemy.url", full_database_path)
            command.upgrade(alembic_cfg, "head")
            command.revision(alembic_cfg, autogenerate=True, message="content")
            break
        except Exception as e:
            print(e)
            print






def create_auth_array(item):
    auth_array = item.__dict__
    auth_array["support_2fa"] = False
    return auth_array


def get_or_create(session: Session, model, defaults=None, fbkwargs: dict = {}):
    fbkwargs2 = fbkwargs.copy()
    instance = session.query(model).filter_by(**fbkwargs2).one_or_none()
    if instance:
        return instance, True
    else:
        fbkwargs2 |= defaults or {}
        instance = model(**fbkwargs2)
        try:
            session.add(instance)
            session.commit()
        except IntegrityError:
            session.rollback()
            instance = session.query(model).filter_by(**fbkwargs2).one()
            return instance, False
        else:
            return instance, True


def get_count(q):
    count_q = q.statement.with_only_columns([func.count()]).order_by(None)
    count: int = q.session.execute(count_q).scalar()
    return count
