"""检查视觉AI配置是否就绪"""
import os
import sys
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
    key = os.environ.get("VISION_API_KEY", "").strip()
    base = os.environ.get("VISION_BASE_URL", "").strip()
    model = os.environ.get("VISION_MODEL", "").strip()
    if key and base and model:
        print(f"配置就绪 OK  服务商: {base}  模型: {model}")
    else:
        missing = []
        if not key: missing.append("VISION_API_KEY")
        if not base: missing.append("VISION_BASE_URL")
        if not model: missing.append("VISION_MODEL")
        print(f"配置不完整 缺少: {', '.join(missing)}")
        print("请复制 .env.example 为 .env 并填写任意一家的 Key")
        sys.exit(1)
