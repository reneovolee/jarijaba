# app.py
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
import uuid

from db import get_db, init_db, Poll, PollOption

# DB 초기화
init_db()

app = FastAPI(title="Vote Bot API", version="1.0.0")

# 요청 모델
class PollRequest(BaseModel):
    title: str
    options: List[str]

class VoteRequest(BaseModel):
    option: str

@app.get("/ping")
async def ping():
    return JSONResponse(content={"message": "pong"})


# 👉 Adaptive Card 생성 함수
def poll_card(poll_id: str, title: str, options: List[str]) -> dict:
    return {
        "type": "AdaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": title,
                "weight": "Bolder",
                "size": "Medium"
            },
            {
                "type": "ActionSet",
                "actions": [
                    {
                        "type": "Action.Submit",
                        "title": opt,
                        "data": {"poll_id": poll_id, "option": opt}
                    }
                    for opt in options
                ]
            }
        ],
        "version": "1.4",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json"
    }


# 투표 생성
@app.post("/send_poll")
async def send_poll(poll_req: PollRequest, db: Session = Depends(get_db)):
    poll_id = str(uuid.uuid4())
    new_poll = Poll(id=poll_id, title=poll_req.title, is_closed=False)
    db.add(new_poll)
    db.commit()

    for opt in poll_req.options:
        db.add(PollOption(poll_id=poll_id, option=opt))
    db.commit()

    card = poll_card(poll_id, poll_req.title, poll_req.options)

    response = {
        "status": "poll_created",
        "poll": {
            "poll_id": poll_id,
            "title": poll_req.title,
            "options": poll_req.options,
        },
        "card": card   # ✅ dict 그대로 반환 (문자열 아님!)
    }
    return JSONResponse(content=response)


# 투표 참여
@app.post("/polls/{poll_id}/vote")
async def vote_poll(poll_id: str, vote_req: VoteRequest, db: Session = Depends(get_db)):
    option = db.query(PollOption).filter_by(poll_id=poll_id, option=vote_req.option).first()
    if not option:
        return JSONResponse(content={"error": "Invalid option"}, status_code=400)

    option.votes += 1
    db.commit()

    response = {
        "poll_id": poll_id,
        "option": vote_req.option,
        "votes": int(option.votes)  # ✅ int32 문제 방지 위해 int 캐스팅
    }
    return JSONResponse(content=response)


# 투표 종료
@app.post("/polls/{poll_id}/close")
async def close_poll(poll_id: str, db: Session = Depends(get_db)):
    poll = db.query(Poll).filter_by(id=poll_id).first()
    if not poll:
        return JSONResponse(content={"error": "Poll not found"}, status_code=404)

    poll.is_closed = True
    db.commit()

    options = db.query(PollOption).filter_by(poll_id=poll_id).all()
    results = [{"option": opt.option, "votes": int(opt.votes)} for opt in options]

    response = {
        "poll_id": poll_id,
        "title": poll.title,
        "results": results,
    }
    return JSONResponse(content=response)
