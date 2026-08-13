#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据备份/恢复脚本（配合后端 /api/admin/export 与 /api/admin/import 接口）。

用途：解决"云托管容器无持久化存储、每次重新部署丢账号/成绩"的问题。
部署前导出线上数据到本地备份文件，部署后从备份文件恢复，账号与成绩不丢失。

用法：
  python backup_restore.py export <线上地址>     # 导出线上数据 -> backup/mojin_data.json
  python backup_restore.py import <线上地址>     # 从 backup/mojin_data.json 恢复到线上

管理密钥默认读取环境变量 ADMIN_KEY，缺省为 mojin-race-dev-secret（与部署时注入的 SECRET_KEY 一致）。
"""
import json
import os
import sys
import urllib.request

DEFAULT_KEY = os.environ.get("ADMIN_KEY", "mojin-race-dev-secret")
BACKUP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup", "mojin_data.json")


def _req(url, path, key, method="GET", body=None):
    req = urllib.request.Request(url.rstrip("/") + path, method=method)
    req.add_header("X-Admin-Key", key)
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode("utf-8")
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw


def cmd_export(base):
    data = _req(base, "/api/admin/export", DEFAULT_KEY)
    os.makedirs(os.path.dirname(BACKUP_FILE), exist_ok=True)
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    c = data.get("counts", {}) if isinstance(data, dict) else {}
    print("已导出到", BACKUP_FILE)
    print("用户", c.get("users", "?"), "· 赛事", c.get("events", "?"), "· 成绩", c.get("results", "?"))


def cmd_import(base):
    if not os.path.isfile(BACKUP_FILE):
        print("找不到备份文件", BACKUP_FILE)
        sys.exit(1)
    with open(BACKUP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    body = {
        "users": data.get("users", []),
        "events": data.get("events", []),
        "results": data.get("results", []),
        "overwrite": True,
    }
    resp = _req(base, "/api/admin/import", DEFAULT_KEY, method="POST", body=body)
    print("已恢复：", resp.get("imported") if isinstance(resp, dict) else resp)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    action, base = sys.argv[1], sys.argv[2]
    if action == "export":
        cmd_export(base)
    elif action == "import":
        cmd_import(base)
    else:
        print(__doc__)
        sys.exit(1)
