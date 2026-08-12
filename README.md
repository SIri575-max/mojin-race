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
| 后端 | 云托管（容器型） | 待开通 |
| 数据库 | SQLite（容器本地） | 依赖云托管 |
| Dockerfile | 项目根目录 | 已就绪 |

### 部署后端（需要手动开通云托管）

1. 在 [CloudBase 控制台](https://console.cloud.tencent.com/tcb) → 环境 `newperson` → 云托管 → 开通服务
2. 开通后重新运行部署命令，或通过 MCP 工具 `manageCloudRun deploy` 部署
3. 后端部署后会获得独立域名，前端可通过 `window.__MOJIN_API_BASE__` 指向该地址

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
```
