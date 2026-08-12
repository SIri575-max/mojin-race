# -*- coding: utf-8 -*-
"""检查 duotest 用户的双人记录状态"""
import sqlite3, os
dbp = os.path.join(os.path.dirname(__file__), "..", "mojin.db")
con = sqlite3.connect(dbp)
con.row_factory = sqlite3.Row
cur = con.cursor()
print("== 所有 duotest 用户 ==")
for r in cur.execute("SELECT id, username, nickname FROM users WHERE username LIKE 'duotest%'"):
    print(dict(r))
print("\n== 所有 duotest 成绩记录 ==")
rows = cur.execute("""
    SELECT r.id, u.username, r.match_id, r.is_duo, r.submit_type, r.explore_value,
           r.confirmed, r.event_id, r.time_start, r.time_end
    FROM results r JOIN users u ON u.id = r.user_id
    WHERE u.username LIKE 'duotest%'
    ORDER BY r.id
""").fetchall()
for r in rows:
    print(dict(r))
print("\n== 开放中的赛事 ==")
for r in cur.execute("SELECT id, name, status FROM events WHERE status='open'"):
    print(dict(r))
con.close()
