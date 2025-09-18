"""Outlook 일정 서비스"""

import httpx
from typing import List, Dict, Any
from app.models import EventRequest
from app.config import settings
import msal


class OutlookService:
    """Microsoft Graph API를 통한 Outlook 일정 서비스"""
    
    def __init__(self):
        self.client_id = settings.microsoft_graph_client_id
        self.client_secret = settings.microsoft_graph_client_secret
        self.tenant_id = settings.microsoft_graph_tenant_id
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scope = ["https://graph.microsoft.com/.default"]
    
    async def get_access_token(self) -> str:
        """Microsoft Graph API 액세스 토큰 획득"""
        try:
            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret
            )
            
            result = app.acquire_token_silent(self.scope, account=None)
            if not result:
                result = app.acquire_token_for_client(scopes=self.scope)
            
            if "access_token" in result:
                return result["access_token"]
            else:
                raise Exception(f"토큰 획득 실패: {result.get('error_description', 'Unknown error')}")
                
        except Exception as e:
            print(f"액세스 토큰 획득 오류: {e}")
            raise
    
    async def create_event(self, user_id: str, event_request: EventRequest) -> bool:
        """Outlook 일정 생성"""
        try:
            access_token = await self.get_access_token()
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            event_data = {
                "subject": event_request.subject,
                "start": {
                    "dateTime": event_request.start_datetime,
                    "timeZone": "Asia/Seoul"
                },
                "end": {
                    "dateTime": event_request.end_datetime,
                    "timeZone": "Asia/Seoul"
                },
                "location": {
                    "displayName": event_request.location
                },
                "attendees": [
                    {
                        "emailAddress": {
                            "address": attendee,
                            "name": attendee
                        },
                        "type": "required"
                    } for attendee in event_request.attendees
                ],
                "body": {
                    "contentType": "text",
                    "content": event_request.description or ""
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://graph.microsoft.com/v1.0/users/{user_id}/events",
                    headers=headers,
                    json=event_data
                )
                
                return response.status_code == 201
                
        except Exception as e:
            print(f"일정 생성 오류: {e}")
            return False
    
    async def get_user_calendar(self, user_id: str) -> List[Dict[str, Any]]:
        """사용자 캘린더 조회"""
        try:
            access_token = await self.get_access_token()
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://graph.microsoft.com/v1.0/users/{user_id}/events",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json().get("value", [])
                return []
                
        except Exception as e:
            print(f"캘린더 조회 오류: {e}")
            return []
