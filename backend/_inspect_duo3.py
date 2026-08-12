# -*- coding: utf-8 -*-
"""检查 backend/mojin.db 中 TEAM 记录 + 双人榜逻辑验证"""
import sqlite3, os
dbp = os.path.join(os.path.dirname(__file__), "mojin.db")
print("db:", dbp)
con = sqlite3.connect(dbp)
con.row_factory = sqlite3.Row
cur = con.cursor()
print("== results TEAM% ==")
for r in cur.execute("SELECT * FROM results WHERE match_id LIKE 'TEAM%'"):
    print(" ", dict(r))
print("== users duotest% ==")
for r in cur.execute("SELECT id, username, nickname FROM users WHERE username LIKE 'duotest%'"):
    print(" ", dict(r))
print("\n== 复现双人榜查询（confirmed=1, is_duo=1）==")
rows = cur.execute("""
    SELECT r.match_id, r.user_id, u.username, r.explore_value, r.confirmed
    FROM results r JOIN users u ON u.id = r.user_id
    WHERE r.is_duo = 1
    ORDER BY r.match_id
""").fetchall()
for r in rows:
    print(" ", dict(r))
con.close()
