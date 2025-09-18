"""설정 관리 모듈"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # Azure OpenAI 설정
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_api_version: str
    azure_openai_deployment_name: str
    
    # 네이버 검색 API는 무료 공개 API이므로 키가 필요하지 않음
    naver_client_id: str
    naver_client_secret: str

    # Microsoft Graph API 설정
    microsoft_graph_client_id: str
    microsoft_graph_client_secret: str
    microsoft_graph_tenant_id: str
    
    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
