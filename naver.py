#!/usr/bin/env python3
"""
네이버 검색 Open API 테스트 코드
"""

import requests
import json
import os
from typing import Dict, Any, Optional


class NaverSearchAPI:
    """네이버 검색 API 클라이언트"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://openapi.naver.com/v1"
        self.headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }
    
    def search_news(self, query: str, display: int = 10, start: int = 1, sort: str = "sim") -> Optional[Dict[str, Any]]:
        """뉴스 검색"""
        url = f"{self.base_url}/search/news"
        params = {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"뉴스 검색 오류: {e}")
            return None
    
    def search_blog(self, query: str, display: int = 10, start: int = 1, sort: str = "sim") -> Optional[Dict[str, Any]]:
        """블로그 검색"""
        url = f"{self.base_url}/search/blog"
        params = {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"블로그 검색 오류: {e}")
            return None
    
    def search_webkr(self, query: str, display: int = 10, start: int = 1, sort: str = "sim") -> Optional[Dict[str, Any]]:
        """웹문서 검색"""
        url = f"{self.base_url}/search/webkr"
        params = {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"웹문서 검색 오류: {e}")
            return None
    
    def search_shop(self, query: str, display: int = 10, start: int = 1, sort: str = "sim") -> Optional[Dict[str, Any]]:
        """쇼핑 검색"""
        url = f"{self.base_url}/search/shop"
        params = {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"쇼핑 검색 오류: {e}")
            return None


def print_search_results(results: Dict[str, Any], search_type: str):
    """검색 결과를 보기 좋게 출력"""
    if not results:
        print(f"{search_type} 검색 결과가 없습니다.")
        return
    
    print(f"\n=== {search_type} 검색 결과 ===")
    print(f"총 검색 결과 수: {results.get('total', 0)}")
    print(f"시작 위치: {results.get('start', 0)}")
    print(f"표시 개수: {results.get('display', 0)}")
    
    items = results.get('items', [])
    for i, item in enumerate(items, 1):
        print(f"\n--- 결과 {i} ---")
        print(f"제목: {item.get('title', 'N/A')}")
        print(f"링크: {item.get('link', 'N/A')}")
        print(f"설명: {item.get('description', 'N/A')}")
        
        # 뉴스의 경우 추가 정보
        if search_type == "뉴스":
            print(f"발행일: {item.get('pubDate', 'N/A')}")
        
        # 블로그의 경우 추가 정보
        elif search_type == "블로그":
            print(f"블로거명: {item.get('bloggername', 'N/A')}")
            print(f"블로그명: {item.get('bloggername', 'N/A')}")
        
        # 쇼핑의 경우 추가 정보
        elif search_type == "쇼핑":
            print(f"가격: {item.get('lprice', 'N/A')}원")
            print(f"브랜드: {item.get('brand', 'N/A')}")
            print(f"제조사: {item.get('maker', 'N/A')}")


def main():
    """메인 함수"""
    # 환경변수에서 API 키 가져오기
    client_id = os.getenv('NAVER_CLIENT_ID')
    client_secret = os.getenv('NAVER_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("오류: NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET 환경변수를 설정해주세요.")
        print("예시:")
        print("export NAVER_CLIENT_ID='your_client_id'")
        print("export NAVER_CLIENT_SECRET='your_client_secret'")
        return
    
    # API 클라이언트 생성
    api = NaverSearchAPI(client_id, client_secret)
    
    # 테스트 검색어
    test_query = "파이썬 프로그래밍"
    
    print(f"검색어: '{test_query}'")
    print("=" * 50)
    
    # 1. 뉴스 검색 테스트
    print("\n1. 뉴스 검색 테스트")
    news_results = api.search_news(test_query, display=5)
    print_search_results(news_results, "뉴스")
    
    # 2. 블로그 검색 테스트
    print("\n2. 블로그 검색 테스트")
    blog_results = api.search_blog(test_query, display=5)
    print_search_results(blog_results, "블로그")
    
    # 3. 웹문서 검색 테스트
    print("\n3. 웹문서 검색 테스트")
    web_results = api.search_webkr(test_query, display=5)
    print_search_results(web_results, "웹문서")
    
    # 4. 쇼핑 검색 테스트
    print("\n4. 쇼핑 검색 테스트")
    shop_results = api.search_shop("맥북", display=5)
    print_search_results(shop_results, "쇼핑")
    
    print("\n" + "=" * 50)
    print("네이버 검색 API 테스트 완료!")


if __name__ == "__main__":
    main()
