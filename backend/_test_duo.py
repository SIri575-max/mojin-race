# -*- coding: utf-8 -*-
"""测试双人提交逻辑：组队码 + 队友用户名 → 双人榜合计"""
import json, urllib.request, urllib.error, time

BASE = "http://127.0.0.1:8000"

def call(path, method="GET", body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"detail": e.reason}

import random
suffix = random.randint(1000, 9999)
u1 = f"duotest_a{suffix}"
u2 = f"duotest_b{suffix}"
pwd = "test1234"
code = "TEAM" + str(suffix)

print("== 1. 注册两个选手 ==")
print("A:", call("/api/register", "POST", {"username": u1, "password": pwd, "nickname": "测试选手A"}))
print("B:", call("/api/register", "POST", {"username": u2, "password": pwd, "nickname": "测试选手B"}))

t1 = call("/api/login", "POST", {"username": u1, "password": pwd}).get("token")
t2 = call("/api/login", "POST", {"username": u2, "password": pwd}).get("token")
print("A登录:", "OK" if t1 else "FAIL", " B登录:", "OK" if t2 else "FAIL")

print("\n== 2. A 以组队码提交双人总价值（B 尚未提交）==")
r = call("/api/results", "POST", {
    "image_path": "", "match_id": code, "is_duo": True, "submit_type": "total",
    "time_start": "2026-08-12T10:00:00", "time_end": "2026-08-12T11:00:00",
    "explore_value": 800, "takeout_value": 0, "kills": 0, "kills_score": 0,
    "kills_detail": "[]", "calc_explore": None, "calc_takeout": None,
    "calc_kills": None, "calc_kills_score": None, "partner_username": u2,
}, t1)
print("A提交结果:", r)
print("  提示: 首次提交为确认自己记录 + 创建队友占位（待确认）")

print("\n== 3. B 用同一组队码提交（关联同一场）==")
r2 = call("/api/results", "POST", {
    "image_path": "", "match_id": code, "is_duo": True, "submit_type": "total",
    "time_start": "2026-08-12T10:00:00", "time_end": "2026-08-12T11:00:00",
    "explore_value": 1200, "takeout_value": 0, "kills": 0, "kills_score": 0,
    "kills_detail": "[]", "calc_explore": None, "calc_takeout": None,
    "calc_kills": None, "calc_kills_score": None, "partner_username": u1,
}, t2)
print("B提交结果:", r2)

print("\n== 3.5 检查数据库真实状态 ==")
import sqlite3, os
dbp = os.path.join(os.path.dirname(__file__), "..", "mojin.db")
con = sqlite3.connect(dbp)
con.row_factory = sqlite3.Row
cur = con.cursor()
for r in cur.execute("""
    SELECT r.id, u.username, r.match_id, r.is_duo, r.explore_value, r.confirmed, r.event_id
    FROM results r JOIN users u ON u.id = r.user_id
    WHERE u.username IN (?,?)
""", (u1, u2)):
    print("  DB:", dict(r))
con.close()

print("\n== 4. 查看双人榜是否合计 = A(800)+B(1200)=2000 ==")
rk = call("/api/rankings/1")
duo = rk.get("duo_total", [])
hit = [d for d in duo if any(m.get("username") == u1 for m in d.get("members", []))]
print("双人榜组队记录:", json.dumps(hit, ensure_ascii=False, indent=1))
names = [m.get("username") for d in hit for m in d.get("members", [])]
if all(u in names for u in (u1, u2)):
    print("✔ 双人合计 =", hit[0].get("total_value"), "(应为 2000)")
else:
    print("✘ 双人未完整入榜")

print("\n== 5. 重复提交同一组队码（应被拒绝/幂等）==")
r3 = call("/api/results", "POST", {
    "image_path": "", "match_id": code, "is_duo": True, "submit_type": "total",
    "time_start": "2026-08-12T10:00:00", "time_end": "2026-08-12T11:00:00",
    "explore_value": 9999, "takeout_value": 0, "kills": 0, "kills_score": 0,
    "kills_detail": "[]", "calc_explore": None, "calc_takeout": None,
    "calc_kills": None, "calc_kills_score": None, "partner_username": u2,
}, t1)
print("重复提交结果:", r3)

print("\n== 6. 单人（非双人）提交是否正常 ==")
r4 = call("/api/results", "POST", {
    "image_path": "", "match_id": "", "is_duo": False, "submit_type": "best",
    "time_start": "", "time_end": "", "explore_value": 0,
    "takeout_value": 66, "kills": 5, "kills_score": 12.5,
    "kills_detail": json.dumps([{"name": "盗匪", "count": 3, "score": 1, "sub": 3}, {"name": "叹息球", "count": 2, "score": 1.5, "sub": 3}], ensure_ascii=False),
    "calc_explore": None, "calc_takeout": None, "calc_kills": None, "calc_kills_score": None,
    "partner_username": "",
}, t1)
print("单人提交结果:", r4)

# 清理测试用户数据（避免污染排行榜）
print("\n== 7. 清理测试数据 ==")
try:
    import sqlite3, os
    dbp = os.path.join(os.path.dirname(__file__), "..", "mojin.db")
    con = sqlite3.connect(dbp)
    cur = con.cursor()
    cur.execute("DELETE FROM results WHERE user_id IN (SELECT id FROM users WHERE username IN (?,?))", (u1, u2))
    cur.execute("DELETE FROM users WHERE username IN (?,?)", (u1, u2))
    con.commit()
    cur.execute("SELECT changes()")
    print("已删除测试记录:", cur.fetchone()[0])
    con.close()
except Exception as e:
    print("清理失败(可忽略):", e)

print("\n全部测试完成")
