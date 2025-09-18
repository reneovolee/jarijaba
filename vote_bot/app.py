from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import uuid, os, json
from sqlalchemy.orm import Session

from db import Poll, PollOption, get_db, init_db
from adaptive_cards import poll_card

# --------------------------
# FastAPI 앱
# --------------------------
app = FastAPI(title="Vote Bot API (SQLite + JSON Export + AdaptiveCard Update)", version="1.0.0")

# DB 및 결과 폴더 초기화
init_db()
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# --------------------------
# Pydantic 모델
# --------------------------
class PollRequest(BaseModel):
    title: str = "회식 날짜"
    options: List[str] = ["2025.09.17", "2025.09.18", "2025.09.19"]

class VoteRequest(BaseModel):
    option: str

# --------------------------
# 투표 생성 API
# --------------------------
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

    return {
        "status": "poll_created",
        "poll": {"poll_id": poll_id, "title": poll_req.title, "options": poll_req.options},
        "card": card
    }

# --------------------------
# 투표 API
# --------------------------
@app.post("/polls/{poll_id}/vote")
async def vote_poll(poll_id: str, vote: VoteRequest, db: Session = Depends(get_db)):
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(404, "Poll not found")
    if poll.is_closed:
        raise HTTPException(400, "Poll already closed")

    option = db.query(PollOption).filter(
        PollOption.poll_id == poll_id, PollOption.option == vote.option
    ).first()
    if not option:
        raise HTTPException(404, "Option not found")

    option.votes += 1
    db.commit()

    options = db.query(PollOption).filter(PollOption.poll_id == poll_id).all()
    votes = {o.option: o.votes for o in options}

    return {"poll_id": poll_id, "votes": votes}

# --------------------------
# 투표 종료 API (+ JSON export)
# --------------------------
@app.post("/polls/{poll_id}/close")
async def close_poll(poll_id: str, db: Session = Depends(get_db)):
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(404, "Poll not found")

    poll.is_closed = True
    db.commit()

    options = db.query(PollOption).filter(PollOption.poll_id == poll_id).all()
    results = {o.option: o.votes for o in options}
    winner = max(results, key=results.get) if results else None

    output = {"poll_id": poll_id, "title": poll.title, "results": results, "winner": winner}
    filepath = os.path.join(RESULTS_DIR, f"poll_{poll_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output

# --------------------------
# BotFramework 엔드포인트 (AdaptiveCard 업데이트)
# --------------------------
@app.post("/api/messages", include_in_schema=False)
async def messages(request: Request, db: Session = Depends(get_db)):
    from botbuilder.core import BotFrameworkAdapterSettings, TurnContext, BotFrameworkAdapter
    from botbuilder.schema import Activity

    APP_ID = "YOUR_BOT_APP_ID"
    APP_PASSWORD = "YOUR_BOT_PASSWORD"
    adapter_settings = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
    adapter = BotFrameworkAdapter(adapter_settings)

    body = await request.json()
    activity = Activity().deserialize(body)

    async def turn_call(turn_context: TurnContext):
        if activity.type == "message":
            data = activity.value
            if data:
                poll_id = data.get("poll_id")
                option = data.get("option")

                # DB 반영
                option_row = db.query(PollOption).filter(
                    PollOption.poll_id == poll_id, PollOption.option == option
                ).first()
                if option_row:
                    option_row.votes += 1
                    db.commit()

                poll = db.query(Poll).filter(Poll.id == poll_id).first()
                options = db.query(PollOption).filter(PollOption.poll_id == poll_id).all()
                votes = {o.option: o.votes for o in options}

                # Adaptive Card 갱신
                updated_card = poll_card(poll_id, poll.title, [o.option for o in options], votes, poll.is_closed)

                updated_activity = Activity(
                    type="message",
                    id=activity.reply_to_id,  # 원래 메시지 ID 필요
                    attachments=[{
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": updated_card
                    }]
                )
                await turn_context.update_activity(updated_activity)

    await adapter.process_activity(activity, "", turn_call)
    return {}
