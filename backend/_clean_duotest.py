# -*- coding: utf-8 -*-
"""清理 backend/mojin.db 中 duotest 测试数据"""
import sqlite3, os
dbp = os.path.join(os.path.dirname(__file__), "mojin.db")
con = sqlite3.connect(dbp)
cur = con.cursor()
ids = [r[0] for r in cur.execute("SELECT id FROM users WHERE username LIKE 'duotest%'")]
print("待清理用户:", ids)
n1 = cur.execute(f"DELETE FROM results WHERE user_id IN ({','.join('?'*len(ids))})", ids).rowcount if ids else 0
n2 = cur.execute("DELETE FROM users WHERE username LIKE 'duotest%'").rowcount
con.commit()
print(f"已删除 results={n1} users={n2}")
print("剩余用户数:", cur.execute("SELECT COUNT(*) FROM users").fetchone()[0])
print("剩余记录数:", cur.execute("SELECT COUNT(*) FROM results").fetchone()[0])
con.close()
