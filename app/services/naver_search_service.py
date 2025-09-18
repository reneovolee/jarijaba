"""네이버 검색 API 서비스"""

import requests
import json
from typing import List, Optional, Dict, Any
from app.models import RestaurantRecommendation
from app.config import settings
from app.logger import get_logger

# 로거 초기화
logger = get_logger("naver_search")


class NaverSearchService:
    """네이버 검색 API 서비스"""
    
    def __init__(self):
        # 네이버 검색 Open API 사용
        self.client_id = settings.naver_client_id
        self.client_secret = settings.naver_client_secret
        self.base_url = "https://openapi.naver.com/v1"
        self.headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
    
    async def search_restaurants(
        self, 
        location: str, 
        keyword: Optional[str] = None,
        cuisine_type: Optional[str] = None,
        price_level: Optional[int] = None,
        rating: Optional[float] = None
    ) -> List[RestaurantRecommendation]:
        """맛집 검색 (블로그, 뉴스, 웹 검색 조합)"""
        logger.info(f"맛집 검색 시작 - 위치: {location}, 키워드: {keyword}, 음식종류: {cuisine_type}")
        
        try:
            # 검색 쿼리 구성
            search_query = self._build_search_query(location, keyword, cuisine_type)
            logger.info(f"검색 쿼리: {search_query}")
            
            # 여러 검색 소스에서 정보 수집
            logger.info("블로그 검색 시작")
            blog_results = await self._search_blog(search_query)
            logger.info(f"블로그 검색 결과: {len(blog_results)}개")
            
            logger.info("뉴스 검색 시작")
            news_results = await self._search_news(search_query)
            logger.info(f"뉴스 검색 결과: {len(news_results)}개")
            
            logger.info("웹 검색 시작")
            web_results = await self._search_web(search_query)
            logger.info(f"웹 검색 결과: {len(web_results)}개")
            
            # 결과 통합 및 파싱
            logger.info("결과 통합 및 파싱 시작")
            restaurants = self._parse_and_merge_results(
                blog_results, news_results, web_results, 
                price_level, rating
            )
            
            logger.info(f"최종 추천 결과: {len(restaurants)}개")
            for i, restaurant in enumerate(restaurants[:5]):  # 상위 5개만 로그
                logger.info(f"추천 {i+1}: {restaurant.name} (평점: {restaurant.rating})")
            
            return restaurants[:10]  # 상위 10개만 반환
            
        except Exception as e:
            logger.error(f"네이버 검색 API 오류: {str(e)}", exc_info=True)
            return []
    
    def _build_search_query(self, location: str, keyword: Optional[str], cuisine_type: Optional[str]) -> str:
        """검색 쿼리 구성"""
        query_parts = []
        
        # 지역 정보
        if location:
            query_parts.append(location)
        
        # 음식 종류
        if cuisine_type:
            query_parts.append(cuisine_type)
        else:
            query_parts.append("맛집")
        
        # 추가 키워드
        if keyword:
            query_parts.append(keyword)
        
        return " ".join(query_parts)
    
    async def _search_blog(self, query: str) -> List[Dict[str, Any]]:
        """블로그 검색 (네이버 Open API)"""
        try:
            url = f"{self.base_url}/search/blog"
            params = {
                "query": query,
                "display": 10,
                "start": 1,
                "sort": "sim"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('items', [])
                
        except Exception as e:
            logger.error(f"블로그 검색 오류: {e}")
            return []
    
    async def _search_news(self, query: str) -> List[Dict[str, Any]]:
        """뉴스 검색 (네이버 Open API)"""
        try:
            url = f"{self.base_url}/search/news"
            params = {
                "query": query,
                "display": 5,
                "start": 1,
                "sort": "sim"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('items', [])
                
        except Exception as e:
            logger.error(f"뉴스 검색 오류: {e}")
            return []
    
    async def _search_web(self, query: str) -> List[Dict[str, Any]]:
        """웹 검색 (네이버 Open API)"""
        try:
            url = f"{self.base_url}/search/webkr"
            params = {
                "query": query,
                "display": 5,
                "start": 1,
                "sort": "sim"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('items', [])
                
        except Exception as e:
            logger.error(f"웹 검색 오류: {e}")
            return []
    
    def _parse_and_merge_results(
        self, 
        blog_results: List[Dict[str, Any]], 
        news_results: List[Dict[str, Any]], 
        web_results: List[Dict[str, Any]],
        price_level: Optional[int] = None,
        rating: Optional[float] = None
    ) -> List[RestaurantRecommendation]:
        """검색 결과 파싱 및 통합"""
        restaurants = []
        
        # 블로그 결과에서 맛집 정보 추출
        for item in blog_results:
            restaurant = self._parse_blog_item(item)
            if restaurant and self._filter_restaurant(restaurant, price_level, rating):
                restaurants.append(restaurant)
        
        # 뉴스 결과에서 맛집 정보 추출
        for item in news_results:
            restaurant = self._parse_news_item(item)
            if restaurant and self._filter_restaurant(restaurant, price_level, rating):
                restaurants.append(restaurant)
        
        # 웹 결과에서 맛집 정보 추출
        for item in web_results:
            restaurant = self._parse_web_item(item)
            if restaurant and self._filter_restaurant(restaurant, price_level, rating):
                restaurants.append(restaurant)
        
        # 중복 제거 및 정렬
        unique_restaurants = self._remove_duplicates(restaurants)
        return sorted(unique_restaurants, key=lambda x: x.rating, reverse=True)
    
    def _parse_blog_item(self, item: Dict[str, Any]) -> Optional[RestaurantRecommendation]:
        """블로그 아이템에서 맛집 정보 추출"""
        try:
            title = item.get('title', '').replace('<b>', '').replace('</b>', '')
            description = item.get('description', '').replace('<b>', '').replace('</b>', '')
            link = item.get('link', '')
            bloggername = item.get('bloggername', '')
            
            # 맛집명 추출 (제목에서)
            restaurant_name = self._extract_restaurant_name(title)
            if not restaurant_name:
                return None
            
            # 주소 추출
            address = self._extract_address(description)
            
            # 평점 추출
            rating = self._extract_rating(description)
            
            # 가격대 추출
            price_level = self._extract_price_level(description)
            
            # 전화번호 추출
            phone_number = self._extract_phone_number(description)
            
            return RestaurantRecommendation(
                name=restaurant_name,
                address=address or "주소 정보 없음",
                rating=rating,
                price_level=price_level,
                phone_number=phone_number,
                website=link,
                place_id=f"blog_{hash(link)}",
                description=description[:200] + "..." if len(description) > 200 else description
            )
            
        except Exception as e:
            logger.error(f"블로그 아이템 파싱 오류: {e}")
            return None
    
    def _parse_news_item(self, item: Dict[str, Any]) -> Optional[RestaurantRecommendation]:
        """뉴스 아이템에서 맛집 정보 추출"""
        try:
            title = item.get('title', '').replace('<b>', '').replace('</b>', '')
            description = item.get('description', '').replace('<b>', '').replace('</b>', '')
            link = item.get('link', '')
            pub_date = item.get('pubDate', '')
            
            # 맛집명 추출
            restaurant_name = self._extract_restaurant_name(title)
            if not restaurant_name:
                return None
            
            # 주소 추출
            address = self._extract_address(description)
            
            # 평점 추출
            rating = self._extract_rating(description)
            
            # 가격대 추출
            price_level = self._extract_price_level(description)
            
            return RestaurantRecommendation(
                name=restaurant_name,
                address=address or "주소 정보 없음",
                rating=rating,
                price_level=price_level,
                phone_number=None,
                website=link,
                place_id=f"news_{hash(link)}",
                description=description[:200] + "..." if len(description) > 200 else description
            )
            
        except Exception as e:
            logger.error(f"뉴스 아이템 파싱 오류: {e}")
            return None
    
    def _parse_web_item(self, item: Dict[str, Any]) -> Optional[RestaurantRecommendation]:
        """웹 아이템에서 맛집 정보 추출"""
        try:
            title = item.get('title', '').replace('<b>', '').replace('</b>', '')
            description = item.get('description', '').replace('<b>', '').replace('</b>', '')
            link = item.get('link', '')
            
            # 맛집명 추출
            restaurant_name = self._extract_restaurant_name(title)
            if not restaurant_name:
                return None
            
            # 주소 추출
            address = self._extract_address(description)
            
            # 평점 추출
            rating = self._extract_rating(description)
            
            # 가격대 추출
            price_level = self._extract_price_level(description)
            
            return RestaurantRecommendation(
                name=restaurant_name,
                address=address or "주소 정보 없음",
                rating=rating,
                price_level=price_level,
                phone_number=None,
                website=link,
                place_id=f"web_{hash(link)}",
                description=description[:200] + "..." if len(description) > 200 else description
            )
            
        except Exception as e:
            logger.error(f"웹 아이템 파싱 오류: {e}")
            return None
    
    def _extract_restaurant_name(self, text: str) -> Optional[str]:
        """텍스트에서 맛집명 추출"""
        import re
        
        # 일반적인 맛집명 패턴들
        patterns = [
            r'([가-힣]+(?:식당|레스토랑|카페|맛집|집|점|관|하우스|키친|바|펍))',
            r'([가-힣]{2,10}(?:\s+[가-힣]{2,10})?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                # 너무 짧거나 일반적인 단어 제외
                if len(name) >= 2 and name not in ['맛집', '식당', '레스토랑', '카페']:
                    return name
        
        return None
    
    def _extract_address(self, text: str) -> Optional[str]:
        """텍스트에서 주소 추출"""
        import re
        
        # 주소 패턴 (시/구/동/로/길 등)
        address_patterns = [
            r'([가-힣]+(?:시|도)\s+[가-힣]+(?:구|군|시)\s+[가-힣]+(?:동|읍|면))',
            r'([가-힣]+(?:구|군|시)\s+[가-힣]+(?:동|읍|면))',
            r'([가-힣]+(?:로|길)\s*\d+)',
        ]
        
        for pattern in address_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_rating(self, text: str) -> float:
        """텍스트에서 평점 추출"""
        import re
        
        # 평점 패턴들
        rating_patterns = [
            r'(\d+\.?\d*)\s*점',
            r'(\d+\.?\d*)\s*★',
            r'(\d+\.?\d*)\s*별',
            r'평점[:\s]*(\d+\.?\d*)',
        ]
        
        for pattern in rating_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    rating = float(match.group(1))
                    if 0 <= rating <= 5:
                        return rating
                except ValueError:
                    continue
        
        return 4.0  # 기본값
    
    def _extract_price_level(self, text: str) -> Optional[int]:
        """텍스트에서 가격대 추출"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['고급', '프리미엄', '럭셔리', '비싼']):
            return 4
        elif any(word in text_lower for word in ['중급', '적당', '보통', '평범']):
            return 3
        elif any(word in text_lower for word in ['저렴', '싼', '합리적', '가성비']):
            return 1
        else:
            return 2  # 기본값
    
    def _extract_phone_number(self, text: str) -> Optional[str]:
        """텍스트에서 전화번호 추출"""
        import re
        
        phone_patterns = [
            r'(\d{2,3}-\d{3,4}-\d{4})',
            r'(\d{2,3}\s\d{3,4}\s\d{4})',
            r'(\d{10,11})',
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _filter_restaurant(
        self, 
        restaurant: RestaurantRecommendation, 
        price_level: Optional[int] = None,
        rating: Optional[float] = None
    ) -> bool:
        """맛집 필터링"""
        if price_level and restaurant.price_level and restaurant.price_level != price_level:
            return False
        
        if rating and restaurant.rating < rating:
            return False
        
        return True
    
    def _remove_duplicates(self, restaurants: List[RestaurantRecommendation]) -> List[RestaurantRecommendation]:
        """중복 맛집 제거"""
        seen_names = set()
        unique_restaurants = []
        
        for restaurant in restaurants:
            if restaurant.name not in seen_names:
                seen_names.add(restaurant.name)
                unique_restaurants.append(restaurant)
        
        return unique_restaurants
    
    
    async def get_place_details(self, place_id: str) -> Optional[RestaurantRecommendation]:
        """장소 상세 정보 조회 (호환성을 위한 메서드)"""
        # 네이버 검색 API에서는 상세 정보를 별도로 조회할 수 없으므로
        # 기본 정보만 반환
        return RestaurantRecommendation(
            name="상세 정보 없음",
            address="주소 정보 없음",
            rating=0.0,
            place_id=place_id
        )
