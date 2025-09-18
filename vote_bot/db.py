from sqlalchemy import create_engine, Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
import os

# --------------------------
# DB 설정 (SQLite)
# --------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'vote.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# --------------------------
# 모델 정의
# --------------------------
class Poll(Base):
    __tablename__ = "polls"
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    is_closed = Column(Boolean, default=False)
    options = relationship("PollOption", back_populates="poll", cascade="all, delete-orphan")


class PollOption(Base):
    __tablename__ = "poll_options"
    id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(String, ForeignKey("polls.id"))
    option = Column(String, nullable=False)
    votes = Column(Integer, default=0)
    poll = relationship("Poll", back_populates="options")

# --------------------------
# DB 초기화
# --------------------------
def init_db():
    Base.metadata.create_all(bind=engine)

# --------------------------
# DB 세션 의존성
# --------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
