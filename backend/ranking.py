from sqlalchemy.orm import Session
from database import Result, User


def _user_best(rows, value_key):
    """通用：每个用户取最高值的那条记录（含图片依据）。

    rows: 可迭代的 (user, result)
    value_key: Result 上的数值字段名
    返回按分数降序的榜单列表。
    """
    best = {}
    for user, r in rows:
        v = getattr(r, value_key) or 0
        cur = best.get(user.id)
        if cur is None or v > cur["value"]:
            best[user.id] = {
                "uid": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "value": v,
                "image_path": r.image_path or "",
                "result_id": r.id,
            }
    ranked = sorted(best.values(), key=lambda x: x["value"], reverse=True)
    return ranked


def single_total_ranking(db: Session, event_id: int):
    """榜单1：单人总价值 = 该用户所有 total 提交中【最高的一次】时间段探索价值总和。
    每个用户只保留最高成绩，并附带该次提交的截图依据。
    """
    rows = (
        db.query(User, Result)
        .join(Result, Result.user_id == User.id)
        .filter(
            Result.event_id == event_id,
            Result.is_duo.is_(False),
            Result.submit_type == "total",
            Result.confirmed.is_(True),
        )
        .all()
    )
    best = _user_best(rows, "explore_value")
    return [
        {
            "rank": i + 1,
            "uid": r["uid"],
            "username": r["username"],
            "nickname": r["nickname"],
            "total_value": round(float(r["value"]), 2),
            "image_path": r["image_path"],
        }
        for i, r in enumerate(best)
    ]


def duo_total_ranking(db: Session, event_id: int):
    """榜单2：双人总价值 = 同组队码两人探索价值相加；
    同一对组合（成员相同）多次提交时取最高一次，附带该次两人截图依据。
    """
    rows = (
        db.query(User, Result)
        .join(User, User.id == Result.user_id)
        .filter(
            Result.event_id == event_id,
            Result.is_duo.is_(True),
            Result.submit_type == "total",
            Result.confirmed.is_(True),
        )
        .all()
    )
    # 先按 match_id 聚合（两人共享组队码）
    matches = {}
    for user, r in rows:
        if not r.match_id:
            continue
        rec = matches.setdefault(
            r.match_id,
            {"members": [], "total": 0.0, "images": {}},
        )
        # 同一 match_id 下同一用户只算一条
        if any(m["uid"] == user.id for m in rec["members"]):
            continue
        rec["members"].append(
            {"uid": user.id, "username": user.username, "nickname": user.nickname}
        )
        rec["total"] += float(r.explore_value or 0)
        rec["images"][user.id] = r.image_path or ""

    # 同一对组合（成员集合相同）多次提交时取最高一次
    pairs = {}
    for rec in matches.values():
        key = frozenset(m["uid"] for m in rec["members"])
        cur = pairs.get(key)
        if cur is None or rec["total"] > cur["total"]:
            pairs[key] = rec
    ranked = sorted(pairs.values(), key=lambda p: p["total"], reverse=True)
    return [
        {
            "rank": i + 1,
            "members": [
                {
                    "uid": m["uid"],
                    "username": m["username"],
                    "nickname": m["nickname"],
                    "image_path": p["images"].get(m["uid"], ""),
                }
                for m in p["members"]
            ],
            "total_value": round(p["total"], 2),
        }
        for i, p in enumerate(ranked)
    ]


def best_takeout_ranking(db: Session, event_id: int):
    """榜单3：单场最高带出价值 = 该用户所有 best 提交中最高一次（含截图依据）"""
    rows = (
        db.query(User, Result)
        .join(Result, Result.user_id == User.id)
        .filter(
            Result.event_id == event_id,
            Result.submit_type == "best",
            Result.confirmed.is_(True),
        )
        .all()
    )
    best = _user_best(rows, "takeout_value")
    return [
        {
            "rank": i + 1,
            "uid": r["uid"],
            "username": r["username"],
            "nickname": r["nickname"],
            "best_value": round(float(r["value"]), 2),
            "image_path": r["image_path"],
        }
        for i, r in enumerate(best)
    ]


def best_kills_ranking(db: Session, event_id: int):
    """榜单4：击败异象最高分 = 按新规则（Σ 图标分值×数量）取该用户最高一次，含截图依据"""
    rows = (
        db.query(User, Result)
        .join(Result, Result.user_id == User.id)
        .filter(
            Result.event_id == event_id,
            Result.submit_type == "best",
            Result.confirmed.is_(True),
        )
        .all()
    )
    best = {}
    for user, r in rows:
        v = float(r.kills_score or 0)
        cur = best.get(user.id)
        if cur is None or v > cur["value"]:
            best[user.id] = {
                "uid": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "value": v,
                "kills": int(r.kills or 0),
                "detail": r.kills_detail or "",
                "image_path": r.image_path or "",
                "result_id": r.id,
            }
    ranked = sorted(best.values(), key=lambda x: x["value"], reverse=True)
    return [
        {
            "rank": i + 1,
            "uid": r["uid"],
            "username": r["username"],
            "nickname": r["nickname"],
            "best_kills": r["value"],
            "kills_total": r["kills"],
            "kills_detail": r["detail"],
            "image_path": r["image_path"],
        }
        for i, r in enumerate(ranked)
    ]


def get_rankings(db: Session, event_id: int) -> dict:
    return {
        "single_total": single_total_ranking(db, event_id),
        "duo_total": duo_total_ranking(db, event_id),
        "best_takeout": best_takeout_ranking(db, event_id),
        "best_kills": best_kills_ranking(db, event_id),
    }
