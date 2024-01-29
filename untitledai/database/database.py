from sqlmodel import SQLModel, create_engine
from sqlalchemy.orm import sessionmaker
from ..core.config import DatabaseConfiguration

class Database:
    def __init__(self, config: DatabaseConfiguration):
        self.engine = create_engine(config.url, pool_size=20, max_overflow=40, echo=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def init_db(self):
        SQLModel.metadata.create_all(bind=self.engine)

    def get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
