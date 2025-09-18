"""FastAPI 메인 애플리케이션"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
import json

from app.config import settings
from app.models import UserQuery, EventRequest
from app.agents.restaurant_agent import RestaurantRecommendationAgent
from app.services.outlook_service import OutlookService
from app.logger import get_logger

# 로거 초기화
logger = get_logger("main")


app = FastAPI(
    title="Jarijaba - Teams 회식 장소 추천 앱",
    description="회식 장소 추천, 투표, 일정 등록을 위한 Teams 앱",
    version="0.1.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서비스 초기화
logger.info("서비스 초기화 시작")
try:
    restaurant_agent = RestaurantRecommendationAgent()
    logger.info("RestaurantRecommendationAgent 초기화 완료")
except Exception as e:
    logger.error(f"RestaurantRecommendationAgent 초기화 실패: {str(e)}", exc_info=True)
    raise

try:
    outlook_service = OutlookService()
    logger.info("OutlookService 초기화 완료")
except Exception as e:
    logger.error(f"OutlookService 초기화 실패: {str(e)}", exc_info=True)
    # Outlook 서비스는 선택적이므로 계속 진행

logger.info("모든 서비스 초기화 완료")


class RestaurantRecommendationRequest(BaseModel):
    """회식 장소 추천 요청 모델"""
    query: str
    user_id: str = "default_user"
    channel_id: str = "default_channel"


@app.post("/api/recommend")
async def recommend_restaurants(request: RestaurantRecommendationRequest) -> Dict[str, Any]:
    """회식 장소 추천 엔드포인트"""
    logger.info(f"추천 요청 수신: {request.query[:100]}...")
    logger.info(f"사용자 ID: {request.user_id}, 채널 ID: {request.channel_id}")
    
    try:
        # 회식 장소 추천 에이전트로 처리
        logger.info("에이전트 처리 시작")
        logger.info(f"처리할 쿼리: {request.query}")
        
        result = await restaurant_agent.process_query(request.query)
        
        logger.info(f"에이전트 처리 완료 - 쿼리 타입: {result.get('query_type', 'unknown')}")
        logger.info(f"추천 결과 개수: {len(result.get('recommendations', []))}")
        logger.info(f"응답 길이: {len(result.get('response', ''))}")
        
        if result["query_type"] == "restaurant_recommendation":
            recommendations_data = []
            for i, r in enumerate(result["recommendations"]):
                rec_data = {
                    "name": r.name,
                    "address": r.address,
                    "rating": r.rating,
                    "price_level": r.price_level,
                    "phone_number": r.phone_number,
                    "website": r.website,
                    "description": r.description
                }
                recommendations_data.append(rec_data)
                logger.info(f"추천 {i+1}: {r.name} (평점: {r.rating})")
            
            response_data = {
                "status": "success",
                "query_type": result["query_type"],
                "recommendations": recommendations_data,
                "response": result["response"]
            }
            
            logger.info(f"추천 응답 생성 완료 - 추천 개수: {len(recommendations_data)}")
            return response_data
        else:
            logger.info("일반 질문으로 분류됨")
            return {
                "status": "success",
                "query_type": result["query_type"],
                "message": "안녕하세요! 회식 장소 추천을 도와드립니다. 어떤 지역에서 회식하실 예정인가요?"
            }
    
    except Exception as e:
        logger.error(f"추천 처리 오류: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"추천 처리 오류: {str(e)}")


@app.post("/api/events")
async def create_event(request: EventRequest) -> Dict[str, Any]:
    """Outlook 일정 생성 엔드포인트"""
    try:
        # 사용자 ID는 실제 구현에서 요청에서 받아야 함
        user_id = "default_user"  # 실제로는 요청에서 받아야 함
        
        success = await outlook_service.create_event(user_id, request)
        
        if success:
            return {"status": "success", "message": "일정이 생성되었습니다."}
        else:
            raise HTTPException(status_code=500, detail="일정 생성 실패")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"일정 생성 오류: {str(e)}")


@app.get("/api/health")
async def health_check() -> Dict[str, str]:
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "message": "Jarijaba API is running"}


@app.get("/")
async def root() -> Dict[str, str]:
    """루트 엔드포인트"""
    return {"message": "Jarijaba - Teams 회식 장소 추천 앱"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
