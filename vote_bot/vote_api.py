import requests

API_BASE = "http://localhost:8000"  # 우리가 만든 FastAPI 투표 서버 주소

def create_poll(title: str, options: list[str]):
    resp = requests.post(f"{API_BASE}/polls", json={"title": title, "options": options})
    return resp.json()

def vote_poll(poll_id: str, option: str):
    resp = requests.post(f"{API_BASE}/polls/{poll_id}/vote", json={"option": option})
    return resp.json()
