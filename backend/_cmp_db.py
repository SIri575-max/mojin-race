# -*- coding: utf-8 -*-
"""对比根目录 mojin.db 与 backend/mojin.db 的用户/记录数"""
import sqlite3, os
for p in [os.path.join(os.path.dirname(__file__), "..", "mojin.db"),
          os.path.join(os.path.dirname(__file__), "mojin.db")]:
    print("=" * 50)
    print("DB:", p)
    try:
        con = sqlite3.connect(p)
        cur = con.cursor()
        print("  users:", cur.execute("SELECT COUNT(*) FROM users").fetchone()[0])
        print("  results:", cur.execute("SELECT COUNT(*) FROM results").fetchone()[0])
        print("  events:", cur.execute("SELECT id,name,status FROM events").fetchall())
        print("  最近用户:", cur.execute("SELECT id,username,nickname,role FROM users ORDER BY id DESC LIMIT 8").fetchall())
        con.close()
    except Exception as e:
        print("  错误:", e)
