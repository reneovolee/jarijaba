# db.py
from sqlalchemy import create_engine, Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = "sqlite:///./polls.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Poll(Base):
    __tablename__ = "polls"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    is_closed = Column(Boolean, default=False)
    options = relationship("PollOption", back_populates="poll")


class PollOption(Base):
    __tablename__ = "poll_options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(String, ForeignKey("polls.id"))
    option = Column(String)
    votes = Column(Integer, default=0)

    poll = relationship("Poll", back_populates="options")


# DB 초기화 함수
def init_db():
    Base.metadata.create_all(bind=engine)


# DB 세션 가져오기
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
