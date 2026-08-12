"""启动入口：自动加载 .env 配置后启动服务"""
import os
from pathlib import Path


def load_env():
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not os.environ.get(key):
            os.environ[key] = value


if __name__ == "__main__":
    load_env()
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
