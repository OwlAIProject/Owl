from sqlmodel import SQLModel, create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from ..core.config import DatabaseConfiguration
from alembic.config import Config
from alembic import command

class Database:
    def __init__(self, config: DatabaseConfiguration):
        self.engine = create_engine(
            config.url,
            pool_size=50,
            max_overflow=100,
            echo=False,
            pool_timeout=30,
            pool_recycle=1800
        )
        self.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.SessionLocal = scoped_session(self.session_factory)

    def init_db(self):
        alembic_cfg = Config("./alembic.ini")
        alembic_cfg.set_main_option('sqlalchemy.url', str(self.engine.url))
        command.upgrade(alembic_cfg, "head")

    def get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
            self.SessionLocal.remove() 