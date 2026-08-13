import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

import ocr_service
import vision_api
from auth import hash_password, verify_password, create_token, get_current_user, require_admin
from database import init_db, get_db, User, Event, Result
from ranking import get_rankings

app = FastAPI(title="第五人格摸金娱乐赛")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UI_DIR = Path(__file__).resolve().parent.parent / "ui"

# ---- 请求模型 ----


class RegisterIn(BaseModel):
    nickname: str
    qq: str
    password: str
    game_id: str            # 第五人格游戏ID
    game_username: str      # 第五人格游戏用户名


class LoginIn(BaseModel):
    account: str            # QQ号（或管理员用户名）
    password: str           # 登录密码


class EventIn(BaseModel):
    name: str
    description: str = ""


class ResultConfirmIn(BaseModel):
    image_path: str
    match_id: str
    is_duo: bool = False
    submit_type: str = "total"          # total=总价值列表求和 / best=单场最高
    time_start: str = ""                # 列表求和时间段起点（ISO 格式）
    time_end: str = ""                  # 列表求和时间段终点（ISO 格式）
    explore_value: float = 0
    takeout_value: float = 0
    kills: int = 0                      # 击败异象总个数
    kills_score: float = 0              # 击败异象总分（Σ 图标分值×数量，新规则）
    kills_detail: str = ""              # 异象图标明细 JSON
    calc_explore: float | None = None   # 选手自算探索价值（校对）
    calc_takeout: float | None = None   # 选手自算带出价值（校对）
    calc_kills: int | None = None       # 选手自算击败异象总个数（校对）
    calc_kills_score: float | None = None  # 选手自算击败异象总分（校对）
    partner_qq: str = ""               # 双人场次时填队友QQ号


# ---- 注册 / 登录 ----


def _user_dict(user: User) -> dict:
    return {
        "uid": user.id,
        "nickname": user.nickname,
        "qq": user.qq or user.username,
        "game_id": user.game_id or "",
        "game_username": user.game_username or "",
        "role": user.role,
    }


@app.post("/api/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    qq = data.qq.strip()
    nickname = data.nickname.strip()
    game_id = data.game_id.strip()
    game_username = data.game_username.strip()
    password = data.password
    if not qq or not nickname or not game_id or not game_username or not password:
        raise HTTPException(status_code=400, detail="昵称、QQ号、第五ID、第五用户名、密码均不能为空")
    if db.query(User).filter((User.username == qq) | (User.qq == qq)).first():
        raise HTTPException(status_code=400, detail="该QQ号已注册，请直接登录")
    user = User(
        username=qq,            # 内部账号 = QQ号
        qq=qq,
        password_hash=hash_password(password),
        nickname=nickname,
        game_id=game_id,
        game_username=game_username,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": create_token(user.id), "user": _user_dict(user)}


@app.post("/api/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    account = data.account.strip()
    user = db.query(User).filter((User.username == account) | (User.qq == account)).first()
    if not user:
        raise HTTPException(status_code=400, detail="账号不存在，请先注册")
    if not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="密码错误")
    return {"token": create_token(user.id), "user": _user_dict(user)}


@app.get("/api/me")
def me(user: User = Depends(get_current_user)):
    return _user_dict(user)


# ---- 赛事 ----


@app.get("/api/events")
def list_events(db: Session = Depends(get_db)):
    events = db.query(Event).order_by(Event.id.desc()).all()
    return [
        {"id": e.id, "name": e.name, "description": e.description, "status": e.status}
        for e in events
    ]


@app.post("/api/events", dependencies=[Depends(require_admin)])
def create_event(data: EventIn, db: Session = Depends(get_db)):
    event = Event(name=data.name, description=data.description)
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"id": event.id, "name": event.name}


@app.get("/api/icons/list")
def icon_list():
    """返回击败异象图标库：13 种异象的名称与分值，供前端人工录入表格使用。"""
    icons = vision_api.load_icons()
    items = [{"name": name, "score": score} for name, (score, _p) in sorted(icons.items(), key=lambda kv: kv[1][0])]
    return {"icons": items}


# ---- 图片上传与 OCR ----


def _parse_time(s: str) -> datetime:
    """解析前端传来的时间段（ISO 格式），返回本地时间"""
    if not s:
        raise HTTPException(status_code=400, detail="缺少时间段参数")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"时间格式错误: {s}（需 ISO 格式如 2026-08-08T00:00）")


def _match_time_to_datetime(time_str: str, start: datetime, end: datetime) -> datetime:
    """把列表截图中的 "MM/DD HH:MM" 转成完整时间。

    年份取 start 所在年份；若跨年（截图时间远早于 start），自动加一年。
    """
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})[\s/]*(\d{1,2}):(\d{2})\s*", time_str)
    if not m:
        return None
    month, day, hour, minute = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    year = start.year
    dt = datetime(year, month, day, hour, minute)
    # 跨年处理：截图日期比 start 早超过半年，说明属于上一年底跨到下一年初
    if dt < start and (start - dt).days > 180:
        dt = datetime(year + 1, month, day, hour, minute)
    return dt


@app.post("/api/ocr")
def ocr_upload(
    file: UploadFile = File(...),
    engine: str = Form("auto"),
    mode: str = Form("single"),
    time_start: str = Form(""),
    time_end: str = Form(""),
):
    """上传战绩图识别。

    mode:
      - single: 单场结算图，识别探索价值/带出价值/击败异象
      - list:   战绩列表截图，需同时传 time_start/time_end，识别时间段内各场探索价值并求和
    engine: auto=先AI后OCR回退 / ai=只用视觉AI / ocr=只用本地OCR
    """
    ext = Path(file.filename or "shot.png").suffix.lower() or ".png"
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        raise HTTPException(status_code=400, detail="仅支持 png/jpg/jpeg/webp/bmp 图片")
    data = file.file.read()
    path = ocr_service.save_image(data, ext)

    if mode == "list":
        return _ocr_list(path, engine, time_start, time_end)

    def run_ai() -> dict:
        if not vision_api.is_configured():
            raise RuntimeError("视觉AI未配置：请设置 VISION_API_KEY / VISION_BASE_URL / VISION_MODEL")
        return vision_api.analyze_image(path)

    def run_ocr() -> dict:
        text = ocr_service.ocr_image(path)
        if not text:
            raise RuntimeError("本地OCR未识别到文字，请换一张更清晰完整的战绩图")
        return ocr_service.extract_result(text)

    if engine == "ai":
        try:
            parsed = run_ai()
        except Exception as e:
            return JSONResponse(status_code=500, content={"detail": str(e)})
    elif engine == "ocr":
        try:
            parsed = run_ocr()
        except Exception as e:
            return JSONResponse(status_code=500, content={"detail": str(e)})
    else:  # auto：AI 优先，失败自动回退本地 OCR
        ai_error = None
        if vision_api.is_configured():
            try:
                parsed = run_ai()
            except Exception as e:
                ai_error = str(e)
        if ai_error is not None or not vision_api.is_configured():
            try:
                parsed = run_ocr()
                parsed["fallback"] = "ocr"
            except Exception as e:
                detail = f"AI: {ai_error or '未配置'}；OCR: {e}" if ai_error else str(e)
                return JSONResponse(status_code=422, content={"detail": detail})
        else:
            parsed["engine"] = "ai"

    # 击败异象新规则：识别图标种类与数量，计算总分
    use_ai = engine != "ocr" and vision_api.is_configured()
    _enrich_kills(parsed, path, use_ai=use_ai)

    parsed["image_path"] = Path(path).name
    return parsed


def _enrich_kills(parsed: dict, path: str, use_ai: bool = True) -> dict:
    """击败异象（提速版）：只读取「击败异象总个数」（kills），不识别具体图标种类。

    具体各异象数量由选手在「异象计分」表格中手动填写；识别只保留一次视觉 AI 调用
    （analyze_image），不再触发原 analyze_kills_icons 的多次采样/放大/逐格扫描，耗时大幅缩短。
    """
    kills = parsed.get("kills")
    try:
        parsed["kills_total"] = int(kills) if kills is not None else 0
    except (TypeError, ValueError):
        parsed["kills_total"] = 0
    # 不识别具体图标：总分与明细留空，交由前端按人工填写数量实时计算
    parsed.setdefault("kills_score", None)
    parsed.setdefault("kills_detail", [])
    return parsed


@app.post("/api/ocr/batch")
def ocr_batch(
    files: list[UploadFile] = File(...),
    engine: str = Form("auto"),
    time_start: str = Form(""),
    time_end: str = Form(""),
):
    """总价值榜：时间段内上传多张对局照片，逐张识别并累加探索价值。

    每张图优先按「战绩列表截图」识别时间段内场次并求和；
    若识别不到场次（0 场），则按「单场结算图」识别探索价值计入。
    返回每张图的明细与总累加值。
    """
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一张图片")
    start = _parse_time(time_start)
    end = _parse_time(time_end)
    if end <= start:
        raise HTTPException(status_code=400, detail="时间段结束时间必须晚于开始时间")
    if (end - start).total_seconds() > 2 * 3600:
        raise HTTPException(status_code=400, detail="时间段不能超过 2 小时")
    if (end - start).total_seconds() < 60:
        raise HTTPException(status_code=400, detail="时间段至少 1 分钟")

    items = []
    grand_total = 0.0
    for f in files:
        ext = Path(f.filename or "shot.png").suffix.lower() or ".png"
        if ext not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            items.append({"filename": f.filename, "error": "不支持的图片格式", "sub_total": 0})
            continue
        try:
            data = f.file.read()
            path = ocr_service.save_image(data, ext)
            item = _ocr_single_to_total(path, engine, start, end)
            item["filename"] = f.filename or ""
            items.append(item)
            grand_total += item.get("sub_total", 0) or 0
        except RuntimeError as e:
            items.append({"filename": f.filename, "error": str(e), "sub_total": 0})

    return {
        "mode": "list",
        "engine": engine,
        "time_start": start.isoformat(),
        "time_end": end.isoformat(),
        "items": items,
        "total_in_range": round(grand_total, 2),
    }


def _ocr_single_to_total(path: str, engine: str, start: datetime, end: datetime) -> dict:
    """识别单张图：优先列表截图，识别不到场次则按单场结算图取探索价值。"""
    matches = []
    engine_used = engine
    if engine in ("ai", "auto"):
        if vision_api.is_configured():
            try:
                matches = vision_api.analyze_list(path)
                engine_used = "ai"
            except RuntimeError:
                pass
    if not matches and engine in ("ocr", "auto"):
        try:
            text = ocr_service.ocr_image(path)
            if text:
                matches = ocr_service.extract_list_result(text)
                engine_used = "ocr"
        except RuntimeError:
            pass

    in_range = []
    for m in matches:
        dt = _match_time_to_datetime(str(m.get("time", "")), start, end)
        if dt is None:
            continue
        m["time_dt"] = dt.isoformat()
        if start <= dt <= end:
            in_range.append(m)

    if in_range:
        total = sum(float(m.get("explore_value", 0) or 0) for m in in_range)
        in_range.sort(key=lambda x: x["time_dt"])
        return {
            "filename": Path(path).name,
            "image_path": Path(path).name,
            "kind": "list",
            "engine": engine_used,
            "matches": matches,
            "in_range": [
                {"time": m["time"], "time_dt": m["time_dt"], "explore_value": m["explore_value"]}
                for m in in_range
            ],
            "sub_total": round(total, 2),
        }

    # 单场结算图：取探索价值计入（用户承诺图片在时间段内）
    try:
        if engine == "ocr" or (engine == "auto" and not vision_api.is_configured()):
            text = ocr_service.ocr_image(path)
            if not text:
                raise RuntimeError("本地OCR未识别到文字")
            parsed = ocr_service.extract_result(text)
        else:
            if not vision_api.is_configured():
                raise RuntimeError("视觉AI未配置")
            parsed = vision_api.analyze_image(path)
            engine_used = "ai"
    except RuntimeError as e:
        return {"filename": Path(path).name, "image_path": Path(path).name, "kind": "unknown", "error": str(e), "sub_total": 0}

    value = float(parsed.get("explore_value", 0) or 0)
    return {
        "filename": Path(path).name,
        "image_path": Path(path).name,
        "kind": "single",
        "engine": engine_used,
        "explore_value": value,
        "sub_total": round(value, 2),
    }


def _ocr_list(path: str, engine: str, time_start: str, time_end: str):
    """战绩列表截图：识别各场时间与探索价值，按时间段过滤并求和"""
    start = _parse_time(time_start)
    end = _parse_time(time_end)
    if end <= start:
        raise HTTPException(status_code=400, detail="时间段结束时间必须晚于开始时间")
    if (end - start).total_seconds() > 2 * 3600:
        raise HTTPException(status_code=400, detail="时间段不能超过 2 小时")
    if (end - start).total_seconds() < 60:
        raise HTTPException(status_code=400, detail="时间段至少 1 分钟")

    def run_ai_list() -> list:
        if not vision_api.is_configured():
            raise RuntimeError("视觉AI未配置")
        return vision_api.analyze_list(path)

    def run_ocr_list() -> list:
        text = ocr_service.ocr_image(path)
        if not text:
            raise RuntimeError("本地OCR未识别到文字，请换一张更清晰完整的截图")
        return ocr_service.extract_list_result(text)

    if engine == "ai":
        try:
            matches = run_ai_list()
        except RuntimeError as e:
            return JSONResponse(status_code=500, content={"detail": str(e)})
        engine_used = "ai"
    elif engine == "ocr":
        try:
            matches = run_ocr_list()
        except RuntimeError as e:
            return JSONResponse(status_code=500, content={"detail": str(e)})
        engine_used = "ocr"
    else:
        ai_error = None
        if vision_api.is_configured():
            try:
                matches = run_ai_list()
            except RuntimeError as e:
                ai_error = str(e)
        if ai_error is not None or not vision_api.is_configured():
            try:
                matches = run_ocr_list()
            except RuntimeError as e:
                detail = f"AI: {ai_error or '未配置'}；OCR: {e}" if ai_error else str(e)
                return JSONResponse(status_code=422, content={"detail": detail})
            engine_used = "ocr"
        else:
            engine_used = "ai"

    # 汇总：标记是否在时间段内，计算总和
    in_range = []
    total = 0.0
    for m in matches:
        dt = _match_time_to_datetime(str(m.get("time", "")), start, end)
        if dt is None:
            continue
        m["time_dt"] = dt.isoformat()
        if start <= dt <= end:
            in_range.append(m)
            total += float(m.get("explore_value", 0) or 0)

    in_range.sort(key=lambda x: x["time_dt"])
    return {
        "mode": "list",
        "engine": engine_used,
        "image_path": Path(path).name,
        "time_start": start.isoformat(),
        "time_end": end.isoformat(),
        "matches": matches,
        "in_range": [
            {"time": m["time"], "time_dt": m["time_dt"], "explore_value": m["explore_value"]}
            for m in in_range
        ],
        "total_in_range": round(total, 2),
    }


# ---- 成绩提交 ----


@app.post("/api/results", dependencies=[Depends(get_current_user)])
def submit_result(data: ResultConfirmIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.status == "open").order_by(Event.id.desc()).first()
    if not event:
        raise HTTPException(status_code=400, detail="当前没有开放中的赛事")

    if data.submit_type not in ("total", "best"):
        raise HTTPException(status_code=400, detail="submit_type 必须为 total 或 best")

    # 解析时间段（total 模式必填）
    time_start = time_end = None
    if data.submit_type == "total":
        try:
            time_start = datetime.fromisoformat(data.time_start)
            time_end = datetime.fromisoformat(data.time_end)
        except ValueError:
            raise HTTPException(status_code=400, detail="时间段格式错误")
        if (time_end - time_start).total_seconds() > 2 * 3600:
            raise HTTPException(status_code=400, detail="时间段不能超过 2 小时")

    # 双人场次校验队友
    partner = None
    if data.is_duo:
        if not data.partner_qq.strip():
            raise HTTPException(status_code=400, detail="双人场次需要填写队友QQ号")
        partner = db.query(User).filter(
            (User.username == data.partner_qq.strip()) | (User.qq == data.partner_qq.strip())
        ).first()
        if not partner:
            raise HTTPException(status_code=400, detail=f"队友「{data.partner_qq}」不存在，请让队友先注册")
        if partner.id == user.id:
            raise HTTPException(status_code=400, detail="队友不能是自己")

    match_id = data.match_id or uuid.uuid4().hex[:12]

    common = dict(
        submit_type=data.submit_type,
        time_start=time_start,
        time_end=time_end,
        explore_value=data.explore_value,
        takeout_value=data.takeout_value,
        kills=data.kills,
        kills_score=data.kills_score,
        kills_detail=data.kills_detail,
        calc_explore=data.calc_explore,
        calc_takeout=data.calc_takeout,
        calc_kills=data.calc_kills,
        calc_kills_score=data.calc_kills_score,
        image_path=data.image_path,
        confirmed=True,
    )

    # 自己的记录：若已有占位记录则更新补全，否则新建；已确认过则拒绝重复提交
    own = db.query(Result).filter(
        Result.match_id == match_id, Result.user_id == user.id
    ).first()
    if own:
        if own.confirmed:
            raise HTTPException(status_code=400, detail="该场次已提交过成绩，请勿重复提交")
        for k, v in common.items():
            setattr(own, k, v)
    else:
        db.add(Result(
            user_id=user.id,
            event_id=event.id,
            match_id=match_id,
            is_duo=data.is_duo,
            **common,
        ))

    # 双人：为队友创建占位记录（队友本人用同一组队码提交时自动更新补全）
    if partner:
        exists = db.query(Result).filter(
            Result.match_id == match_id, Result.user_id == partner.id
        ).first()
        if not exists:
            db.add(Result(
                user_id=partner.id,
                event_id=event.id,
                match_id=match_id,
                is_duo=True,
                submit_type=data.submit_type,
                confirmed=False,
            ))
    db.commit()
    return {"ok": True, "match_id": match_id}


@app.get("/api/my/results")
def my_results(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Result)
        .filter(Result.user_id == user.id)
        .order_by(Result.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "match_id": r.match_id,
            "is_duo": r.is_duo,
            "submit_type": r.submit_type,
            "time_start": r.time_start.isoformat() if r.time_start else None,
            "time_end": r.time_end.isoformat() if r.time_end else None,
            "explore_value": r.explore_value,
            "takeout_value": r.takeout_value,
            "kills": r.kills,
            "kills_score": r.kills_score,
            "kills_detail": r.kills_detail,
            "calc_explore": r.calc_explore,
            "calc_takeout": r.calc_takeout,
            "calc_kills": r.calc_kills,
            "calc_kills_score": r.calc_kills_score,
            "confirmed": r.confirmed,
            "image_path": r.image_path,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ---- 排行榜 ----


@app.get("/api/rankings/{event_id}")
def rankings(event_id: int, db: Session = Depends(get_db)):
    return get_rankings(db, event_id)


# ---- 静态资源 ----


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


@app.on_event("startup")
def on_startup():
    init_db()
    db = next(get_db())
    if db.query(Event).count() == 0:
        db.add(Event(name="第五人格摸金娱乐赛", description="限时2小时摸金，多场累计总价值，击败异象数取单场最高"))
        db.commit()
    db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
