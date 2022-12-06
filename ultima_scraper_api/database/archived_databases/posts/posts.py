### posts.py ###

# type: ignore
from ultima_scraper_api.database.databases.user_data.models.api_table import api_table
from ultima_scraper_api.database.databases.user_data.models.media_table import template_media_table
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class api_table(api_table, Base):
    api_table.__tablename__ = "posts"


class template_media_table(template_media_table, Base):
    pass
