def poll_card(poll_id: str, title: str, options: list, votes: dict = None, is_closed: bool = False):
    """투표용 Adaptive Card JSON 생성"""
    body = [{"type": "TextBlock", "size": "Large", "weight": "Bolder", "text": title}]

    if votes:
        # 현황 표시
        for opt in options:
            vote_count = votes.get(opt, 0)
            body.append({
                "type": "TextBlock",
                "text": f"{opt}: {vote_count}표",
                "spacing": "None"
            })
    else:
        for opt in options:
            body.append({"type": "TextBlock", "text": opt})

    actions = []
    if not is_closed:
        for opt in options:
            actions.append({
                "type": "Action.Submit",
                "title": opt,
                "data": {"poll_id": poll_id, "option": opt}
            })
    else:
        body.append({"type": "TextBlock", "text": "✅ 투표 종료됨", "weight": "Bolder", "color": "Attention"})

    return {
        "type": "AdaptiveCard",
        "body": body,
        "actions": actions,
        "version": "1.4"
    }
