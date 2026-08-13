# 第五人格摸金娱乐赛 · 赛事网站

面向 100 人以内娱乐赛的成绩录入与排行系统。

## 在线访问

**前端页面**：https://newperson-d1goip47jd51c941d-1421210724.tcloudbaseapp.com/?v=1

> 注意：当前前端部署于 CloudBase 静态托管。完整功能需要后端 API（云托管容器）提供服务。
> 详见下方「CloudBase 部署」章节。

## CloudBase 部署

| 资源 | 类型 | 状态 |
|------|------|------|
| 环境 ID | `newperson-d1goip47jd51c941d` (体验版) | ap-shanghai |
| 前端 | 静态网站托管 | 已部署 |
| 后端 | 云托管（容器型）服务 `mojin-backend` | ✅ 已部署（版本 005+） |
| 数据库 | SQLite（容器本地） | ✅ 已配数据导出/恢复接口，部署前备份即可不丢 |
| Dockerfile | 项目根目录 | 已就绪 |

### 更新后端上线（已部署，此处为更新流程）

线上后端地址：`https://mojin-backend-296017-11-1421210724.sh.run.tcloudbase.com`

> 注意：环境里还有 `mojintest` 服务，是测试实例，**请部署到 `mojin-backend`**。

**标准部署流程（保证账号/成绩不丢）**：

1. **部署前备份**：`python backup_restore.py export <线上地址>`（导出到 `backup/mojin_data.json`）
2. `git add backup/ && git commit && git push origin main`（仓库 `SIri575-max/mojin-race`，备份快照入库双保险）
3. 通过 MCP 工具 `manageCloudRun deploy`（`serverName=mojin-backend`）触发构建；或到控制台云托管服务页手动触发部署
4. MCP 部署会显示"超时"属正常，后台构建仍在进行，几分钟后查服务详情确认版本号 +1 即成功
5. **部署后恢复**：`python backup_restore.py import <线上地址>`（账号/成绩恢复）

> 前端 `frontend/index.html` 由后端静态托管，**前端改动同样要重新部署后端**才生效。

> ⚠️ 数据库现状：体验版 + 共享集群**无法开通 PostgreSQL/MySQL/NoSQL**（需企业版套餐）。当前数据存容器内 SQLite，**每次重新部署数据会重置**。为此已落地「方案3」：管理密钥（`X-Admin-Key`，值 = `SECRET_KEY`）认证的导出/恢复接口 + 前端「🛠 管理」页签，按上面流程部署即可不丢账号。`database.py` 已支持 PostgreSQL，将来升级后设 `DATABASE_URL` 环境变量即可无缝切换。详见 `PROJECT.md` 第九章。

### 环境变量（后端容器 EnvParams）

| 变量 | 说明 |
|------|------|
| `VISION_API_KEY` | 视觉AI密钥（智谱/阿里百炼） |
| `VISION_BASE_URL` | 视觉AI接口地址 |
| `VISION_MODEL` | 模型名称（如 glm-4v-flash） |
| `SECRET_KEY` | JWT 签名密钥 |

## 功能

- 选手注册 / 登录（JWT）
- 战绩图上传识别（双引擎：本地 RapidOCR 离线识别 + 视觉大模型 AI 识别）
- 四大榜单：
  1. **单人总价值**：所有单人场次探索价值之和
  2. **双人总价值**：同组队码两人探索价值相加
  3. **单场最高带出**：所有场次带出价值最高一次
  4. **击败异象**：所有场次击败异象数量最高一次
- 我的成绩（历史提交记录 + 战绩图回看）
- 管理（🛠 管理页签）：查看全部用户/成绩、导出 JSON 备份、导出 CSV、下载数据库、恢复数据（管理密钥认证）

## 数据备份 / 恢复

体验版无持久化数据库，重新部署会清空数据。通过以下方式备份恢复：

```bash
# 部署前备份
python backup_restore.py export https://mojin-backend-296017-11-1421210724.sh.run.tcloudbase.com

# 部署后恢复
python backup_restore.py import https://mojin-backend-296017-11-1421210724.sh.run.tcloudbase.com
```

也可在前端「🛠 管理」页签内完成同样操作（输入管理密钥 `SECRET_KEY`）。

## 快速启动

```bash
cd backend
pip install -r requirements.txt

# 可选：启用视觉AI识图（更准）。复制并填写任意一家：
copy .env.example .env
python check_vision.py   # 检查配置

python run.py            # 启动，访问 http://127.0.0.1:8000
```

不配置视觉AI也不影响使用——识别引擎会自动回退到本地 RapidOCR。

## 视觉AI配置（二选一推荐）

### ① 智谱AI（免费）
1. 打开 https://open.bigmodel.cn/ 注册登录
2. 控制台 → API密钥 → 创建密钥
3. 在 `.env` 填写：
   ```
   VISION_API_KEY=你的密钥
   VISION_BASE_URL=https://open.bigmodel.cn/api/paas/v4
   VISION_MODEL=glm-4v-flash
   ```

### ② 阿里百炼 qwen-vl-plus（有免费额度）
1. 打开 https://bailian.console.aliyun.com/ 注册
2. 右上角头像 → API-KEY → 创建
3. 在 `.env` 填写：
   ```
   VISION_API_KEY=你的密钥
   VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
   VISION_MODEL=qwen-vl-plus
   ```

其他可选服务商见 `backend/.env.example` 中的注释。

## 使用流程

1. 选手注册登录
2. 「战绩录入」页选择单人/双人 → 选择识别引擎 → 上传战绩图
3. 核对识别出的 探索价值 / 带出价值 / 击败异象，可手动修正
4. 双人场次：填写队友用户名 + 组队码（双方填相同组队码），提交后自动合并
5. 「排行榜」页查看四大榜单

## 项目结构

```
backend/
  main.py          # FastAPI 入口与全部接口
  auth.py          # 注册登录 JWT
  database.py      # SQLAlchemy 数据模型
  ocr_service.py   # 本地 RapidOCR 识别 + 字段提取
  vision_api.py    # 视觉大模型识别（OpenAI 兼容）
  ranking.py       # 四大榜单计算
  run.py           # 启动脚本（自动加载 .env）
  check_vision.py  # 视觉AI配置检查
frontend/
  index.html       # 单页前端（Vue3 + Element Plus）
backup_restore.py  # 数据备份/恢复脚本
backup/            # 数据快照备份目录（随 git 提交）
```
