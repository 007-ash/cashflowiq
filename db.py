from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from config import DATABASE_URL


class Model(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL)
Session = sessionmaker(engine)
