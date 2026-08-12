# -*- coding: utf-8 -*-
"""启动后端并验证：首页含 UI 升级元素、logo/素材可访问、图标接口正常"""
import subprocess, sys, time, urllib.request, os

root = r"c:/Users/Lenovo/CodeBuddy/20260807025758"
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--port", "8011"],
    cwd=os.path.join(root, "backend"),
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)

def get(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except Exception as e:
        return None, str(e), b""

ok = True
try:
    # 等待服务就绪
    for _ in range(30):
        st, _, _ = get("http://127.0.0.1:8011/")
        if st == 200:
            break
        time.sleep(0.5)
    else:
        print("FAIL 服务未启动"); ok = False

    # 1. 首页
    st, ct, body = get("http://127.0.0.1:8011/")
    html = body.decode("utf-8", "ignore")
    checks = {
        "首页200": st == 200,
        "含logo-img": "logo-img" in html,
        "含hero-banner": "hero-banner" in html,
        "含auth-logo": "auth-logo" in html,
        "含/ui/1.jpg背景": "/ui/1.jpg" in html,
        "含/assets/logo_web.png": "/assets/logo_web.png" in html,
    }
    for k, v in checks.items():
        print(("PASS " if v else "FAIL ") + k)
        if not v:
            ok = False

    # 2. 素材资源
    for path, expect_ct in [("/assets/logo_web.png", "png"),
                            ("/ui/1.jpg", "jpeg"),
                            ("/ui/6.jpg", "jpeg"),
                            ("/ui/logo.png", "png")]:
        st, ct, body = get("http://127.0.0.1:8011" + path)
        v = st == 200 and expect_ct in (ct or "").lower() and len(body) > 1000
        print(("PASS " if v else "FAIL ") + f"资源 {path} ({st}, {ct}, {len(body)}B)")
        if not v:
            ok = False

    # 3. 图标接口
    st, ct, body = get("http://127.0.0.1:8011/api/icons/list")
    v = st == 200 and b'"icons"' in body and body.count(b'"name"') >= 13
    print(("PASS " if v else "FAIL ") + f"接口 /api/icons/list (13种, {st})")
    if not v:
        ok = False

finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

print("RESULT:", "ALL PASS" if ok else "HAS FAILURE")
