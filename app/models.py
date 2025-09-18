"""데이터 모델 정의"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum


class MessageType(str, Enum):
    """메시지 타입"""
    TEXT = "text"
    CARD = "card"


class TeamsMessage(BaseModel):
    """Teams 메시지 모델"""
    type: str
    text: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class RestaurantRecommendation(BaseModel):
    """식당 추천 모델"""
    name: str
    address: str
    rating: float
    price_level: Optional[int] = None
    phone_number: Optional[str] = None
    website: Optional[str] = None
    place_id: str
    description: Optional[str] = None


class PollOption(BaseModel):
    """투표 옵션 모델"""
    id: str
    text: str
    is_checked: bool = False


class PollRequest(BaseModel):
    """투표 생성 요청 모델"""
    question: str
    options: List[PollOption]
    is_multi_select: bool = False


class EventRequest(BaseModel):
    """일정 등록 요청 모델"""
    subject: str
    start_datetime: str
    end_datetime: str
    location: str
    attendees: List[str]
    description: Optional[str] = None


class UserQuery(BaseModel):
    """사용자 쿼리 모델"""
    text: str
    user_id: str
    channel_id: str
    team_id: Optional[str] = None
