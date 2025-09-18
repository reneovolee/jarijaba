"""회식 장소 추천 에이전트 (LangGraph)"""

from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from app.services.naver_search_service import NaverSearchService
from app.models import RestaurantRecommendation
from app.config import settings
from app.logger import get_logger

# 로거 초기화
logger = get_logger("restaurant_agent")


class AgentState(TypedDict):
    """에이전트 상태"""
    user_query: str
    query_type: str
    location: str
    preferences: Dict[str, Any]
    search_results: List[RestaurantRecommendation]
    recommendations: List[RestaurantRecommendation]
    response: str


class RestaurantRecommendationAgent:
    """회식 장소 추천 에이전트"""
    
    def __init__(self):
        logger.info("RestaurantRecommendationAgent 초기화 시작")
        
        # LLM 초기화
        try:
            logger.info(f"Azure OpenAI 설정 - Endpoint: {settings.azure_openai_endpoint}")
            logger.info(f"Deployment: {settings.azure_openai_deployment_name}")
            logger.info(f"API Version: {settings.azure_openai_api_version}")
            logger.info(f"API Key (첫 10자): {settings.azure_openai_api_key[:10]}...")
            
            # 설정 검증
            if not settings.azure_openai_api_key or settings.azure_openai_api_key == "your_azure_openai_api_key":
                raise ValueError("Azure OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
            
            if not settings.azure_openai_endpoint or settings.azure_openai_endpoint == "https://your-resource.openai.azure.com/":
                raise ValueError("Azure OpenAI 엔드포인트가 설정되지 않았습니다. .env 파일을 확인하세요.")
            
            if not settings.azure_openai_deployment_name or settings.azure_openai_deployment_name == "your_deployment_name":
                raise ValueError("Azure OpenAI 배포명이 설정되지 않았습니다. .env 파일을 확인하세요.")
            
            self.llm = AzureChatOpenAI(
                azure_deployment=settings.azure_openai_deployment_name,
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
            logger.info("LLM 초기화 완료")
        except Exception as e:
            logger.error(f"LLM 초기화 오류: {str(e)}", exc_info=True)
            raise
        
        # 검색 서비스 초기화
        try:
            self.search_service = NaverSearchService()
            logger.info("검색 서비스 초기화 완료")
        except Exception as e:
            logger.error(f"검색 서비스 초기화 오류: {str(e)}", exc_info=True)
            raise
        
        # 그래프 구성
        try:
            self.graph = self._build_graph()
            logger.info("그래프 구성 완료")
        except Exception as e:
            logger.error(f"그래프 구성 오류: {str(e)}", exc_info=True)
            raise
        
        logger.info("RestaurantRecommendationAgent 초기화 완료")
    
    def _build_graph(self) -> StateGraph:
        """LangGraph 그래프 구성"""
        workflow = StateGraph(AgentState)
        
        # 노드 추가
        workflow.add_node("classify_query", self._classify_query)
        workflow.add_node("extract_preferences", self._extract_preferences)
        workflow.add_node("search_restaurants", self._search_restaurants)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        workflow.add_node("format_response", self._format_response)
        
        # 엣지 추가
        workflow.set_entry_point("classify_query")
        workflow.add_edge("classify_query", "extract_preferences")
        workflow.add_edge("extract_preferences", "search_restaurants")
        workflow.add_edge("search_restaurants", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "format_response")
        workflow.add_edge("format_response", END)
        
        return workflow.compile()
    
    async def _classify_query(self, state: AgentState) -> AgentState:
        """쿼리 분류: 일반 질의인지 회식 장소 추천인지 판단"""
        logger.info(f"쿼리 분류 시작: {state['user_query'][:100]}...")
        
        try:
            messages = [
                SystemMessage(content="""
                사용자의 질문을 분석하여 다음 중 하나로 분류하세요:
                1. "restaurant_recommendation" - 회식 장소 추천 요청
                2. "general" - 일반적인 질문
                
                회식, 식당, 맛집, 회식 장소, 식사, 점심, 저녁 등의 키워드가 포함되면 "restaurant_recommendation"으로 분류하세요.
                """),
                HumanMessage(content=state["user_query"])
            ]
            
            logger.info("쿼리 분류 LLM 호출 시작")
            import asyncio
            try:
                response = await asyncio.wait_for(
                    self.llm.ainvoke(messages), 
                    timeout=60.0
                )
                logger.info("쿼리 분류 LLM 호출 완료")
            except Exception as llm_error:
                logger.error(f"LLM 호출 중 오류 발생: {type(llm_error).__name__}: {str(llm_error)}")
                logger.error(f"오류 상세 정보: {repr(llm_error)}")
                raise
            
            query_type = response.content.strip().lower()
            logger.info(f"쿼리 분류 결과: {query_type}")
            
            return {
                **state,
                "query_type": query_type
            }
        except asyncio.TimeoutError:
            logger.error("쿼리 분류 LLM 호출 타임아웃 (15초)")
            # 키워드 기반으로 간단한 분류 시도
            query_lower = state["user_query"].lower()
            if any(keyword in query_lower for keyword in ["회식", "식당", "맛집", "회식 장소", "식사", "점심", "저녁", "삼겹살"]):
                query_type = "restaurant_recommendation"
            else:
                query_type = "general"
            logger.info(f"타임아웃 후 키워드 기반 분류 결과: {query_type}")
            return {
                **state,
                "query_type": query_type
            }
        except Exception as e:
            logger.error(f"쿼리 분류 오류: {str(e)}", exc_info=True)
            logger.error(f"오류 타입: {type(e).__name__}")
            logger.error(f"오류 상세: {repr(e)}")
            # 키워드 기반으로 간단한 분류 시도
            query_lower = state["user_query"].lower()
            if any(keyword in query_lower for keyword in ["회식", "식당", "맛집", "회식 장소", "식사", "점심", "저녁", "삼겹살"]):
                query_type = "restaurant_recommendation"
            else:
                query_type = "general"
            logger.info(f"오류 후 키워드 기반 분류 결과: {query_type}")
            return {
                **state,
                "query_type": query_type
            }
    
    async def _extract_preferences(self, state: AgentState) -> AgentState:
        """사용자 선호도 및 요구사항 추출"""
        if state["query_type"] != "restaurant_recommendation":
            return state
        
        logger.info("선호도 추출 시작")
        
        try:
            messages = [
                SystemMessage(content="""
                사용자의 회식 장소 추천 요청에서 다음 정보를 추출하여 JSON 형태로 응답하세요:
                {
                    "location": "지역 또는 주소",
                    "budget": "예산 수준 (1-4)",
                    "cuisine_type": "음식 종류",
                    "group_size": "인원수",
                    "occasion": "회식 목적",
                    "special_requirements": "특별 요구사항"
                }
                
                정보가 명시되지 않은 경우 null로 설정하세요.
                """),
                HumanMessage(content=state["user_query"])
            ]
            
            logger.info("선호도 추출 LLM 호출 시작")
            import asyncio
            response = await asyncio.wait_for(
                self.llm.ainvoke(messages), 
                timeout=60.0
            )
            logger.info("선호도 추출 LLM 호출 완료")
            
            # JSON 파싱 (실제로는 더 안전한 파싱 필요)
            try:
                import json
                preferences = json.loads(response.content)
                logger.info(f"추출된 선호도: {preferences}")
            except Exception as parse_error:
                logger.error(f"JSON 파싱 오류: {parse_error}")
                preferences = {
                    "location": "서울",
                    "budget": None,
                    "cuisine_type": None,
                    "group_size": None,
                    "occasion": None,
                    "special_requirements": None
                }
            
            return {
                **state,
                "preferences": preferences,
                "location": preferences.get("location", "서울")
            }
            
        except asyncio.TimeoutError:
            logger.error("선호도 추출 LLM 호출 타임아웃 (15초)")
            # 기본 선호도 설정
            preferences = {
                "location": "서울",
                "budget": None,
                "cuisine_type": None,
                "group_size": None,
                "occasion": None,
                "special_requirements": None
            }
            return {
                **state,
                "preferences": preferences,
                "location": "서울"
            }
        except Exception as e:
            logger.error(f"선호도 추출 오류: {str(e)}", exc_info=True)
            # 기본 선호도 설정
            preferences = {
                "location": "서울",
                "budget": None,
                "cuisine_type": None,
                "group_size": None,
                "occasion": None,
                "special_requirements": None
            }
            return {
                **state,
                "preferences": preferences,
                "location": "서울"
            }
    
    async def _search_restaurants(self, state: AgentState) -> AgentState:
        """네이버 검색 API를 통한 식당 검색"""
        if state["query_type"] != "restaurant_recommendation":
            return state
        
        preferences = state["preferences"]
        logger.info(f"식당 검색 시작 - 위치: {state['location']}, 선호도: {preferences}")
        
        try:
            # 검색 파라미터 설정
            keyword = preferences.get("cuisine_type")
            price_level = preferences.get("budget")
            rating = 4.0  # 최소 평점
            
            logger.info(f"검색 파라미터 - 키워드: {keyword}, 가격대: {price_level}, 최소평점: {rating}")
            
            search_results = await self.search_service.search_restaurants(
                location=state["location"],
                keyword=keyword,
                cuisine_type=preferences.get("cuisine_type"),
                price_level=price_level,
                rating=rating
            )
            
            logger.info(f"검색 결과 개수: {len(search_results)}")
            for i, result in enumerate(search_results[:3]):  # 상위 3개만 로그
                logger.info(f"검색 결과 {i+1}: {result.name} (평점: {result.rating})")
            
            return {
                **state,
                "search_results": search_results
            }
        except Exception as e:
            logger.error(f"식당 검색 오류: {str(e)}", exc_info=True)
            return {
                **state,
                "search_results": []
            }
    
    async def _generate_recommendations(self, state: AgentState) -> AgentState:
        """LLM을 통한 추천 생성"""
        if state["query_type"] != "restaurant_recommendation":
            return state
        
        search_results = state["search_results"]
        preferences = state["preferences"]
        
        if not search_results:
            return {
                **state,
                "recommendations": [],
                "response": "죄송합니다. 해당 지역에서 적합한 식당을 찾을 수 없습니다."
            }
        
        # 검색 결과를 텍스트로 변환
        restaurants_text = "\n".join([
            f"- {r.name} (평점: {r.rating}, 주소: {r.address}, 설명: {r.description})"
            for r in search_results[:10]  # 상위 10개만
        ])
        
        messages = [
            SystemMessage(content=f"""
            다음 식당 목록에서 사용자의 요구사항에 맞는 최고의 추천 3-5개를 선택하고 설명하세요.
            각 식당 이름은 정확한 이름이 아닐 수 있습니다. 식당의 설명 부분에 식당 이름이 있다면 그 이름을 식당 이름으로 사용하세요.

            사용자 요구사항:
            - 지역: {preferences.get('location', '서울')}
            - 예산: {preferences.get('budget', '제한없음')}
            - 음식 종류: {preferences.get('cuisine_type', '제한없음')}
            - 인원수: {preferences.get('group_size', '제한없음')}
            - 목적: {preferences.get('occasion', '일반 회식')}
            - 특별 요구사항: {preferences.get('special_requirements', '없음')}
            
            각 추천에 대해 다음을 포함하세요:
            1. 식당명
            2. 추천 이유
            3. 특징 및 장점
            4. 주소 및 연락처 (있는 경우)
            """),
            HumanMessage(content=f"검색된 식당 목록:\n{restaurants_text}")
        ]
        
        logger.info("LLM 호출 시작")
        try:
            timeout = 300.0
            import asyncio
            response = await asyncio.wait_for(
                self.llm.ainvoke(messages), 
                timeout=timeout
            )
            logger.info("LLM 호출 완료")
        except asyncio.TimeoutError:
            logger.error(f"LLM 호출 타임아웃 ({timeout}초)")
            return {
                **state,
                "recommendations": search_results[:3],  # 기본 추천
                "response": "죄송합니다. AI 분석 중 시간이 초과되었습니다. 검색된 식당 중 상위 3개를 추천드립니다."
            }
        except Exception as e:
            logger.error(f"LLM 호출 오류: {str(e)}", exc_info=True)
            return {
                **state,
                "recommendations": search_results[:3],  # 기본 추천
                "response": f"AI 분석 중 오류가 발생했습니다. 검색된 식당 중 상위 3개를 추천드립니다. (오류: {str(e)})"
            }
        
        # 추천 결과를 원본 데이터와 매칭
        recommendations = []
        for restaurant in search_results[:5]:  # 상위 5개만 추천
            recommendations.append(restaurant)
        
        return {
            **state,
            "recommendations": recommendations,
            "response": response.content
        }
    
    async def _format_response(self, state: AgentState) -> AgentState:
        """최종 응답 포맷팅"""
        if state["query_type"] != "restaurant_recommendation":
            return {
                **state,
                "response": "죄송합니다. 회식 장소 추천 기능만 지원합니다. 회식 장소에 대한 질문을 해주세요."
            }
        
        recommendations = state["recommendations"]
        response_text = state["response"]
        
        # Teams 적응형 카드 형태로 포맷팅
        formatted_response = f"""
                                🍽️ **회식 장소 추천**

                                {response_text}

                                **추천 식당 목록:**
                                """
        
        for i, restaurant in enumerate(recommendations, 1):
            formatted_response += f"""
                                    {i}. **{restaurant.name}**
                                    - 평점: {restaurant.rating}⭐
                                    - 주소: {restaurant.address}
                                    - 전화: {restaurant.phone_number or '정보 없음'}
                                    """
        
        return {
            **state,
            "response": formatted_response
        }
    
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """사용자 쿼리 처리"""
        initial_state = {
            "user_query": user_query,
            "query_type": "",
            "location": "",
            "preferences": {},
            "search_results": [],
            "recommendations": [],
            "response": ""
        }
        
        result = await self.graph.ainvoke(initial_state)
        
        return {
            "query_type": result["query_type"],
            "recommendations": result["recommendations"],
            "response": result["response"]
        }
