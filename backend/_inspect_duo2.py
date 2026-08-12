# -*- coding: utf-8 -*-
"""直接检查 results 表结构 + TEAM 记录"""
import sqlite3, os
dbp = os.path.join(os.path.dirname(__file__), "..", "mojin.db")
print("db file:", dbp, "exists:", os.path.exists(dbp))
con = sqlite3.connect(dbp)
con.row_factory = sqlite3.Row
cur = con.cursor()
print("\n== results 表结构 ==")
for r in cur.execute("PRAGMA table_info(results)"):
    print(" ", r["name"], r["type"], "default=", r["dflt_value"])
print("\n== results 中 match_id LIKE 'TEAM%' ==")
for r in cur.execute("SELECT * FROM results WHERE match_id LIKE 'TEAM%'"):
    print(" ", dict(r))
print("\n== users 中 duotest% ==")
for r in cur.execute("SELECT * FROM users WHERE username LIKE 'duotest%'"):
    print(" ", dict(r))
con.close()
