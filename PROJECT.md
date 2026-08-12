# 第五人格·摸金搜打撤 娱乐赛战绩系统

## 一、项目概况

面向 ≤100 人规模的《第五人格·摸金搜打撤》娱乐赛，提供选手自助注册、战绩截图识别、四大排行榜与个人成绩管理的单页应用。

- **技术栈**：后端 FastAPI + SQLite + JWT；OCR 双引擎（本地 RapidOCR + 智谱视觉 AI）；前端 Vue3 + Element Plus 单页应用
- **运行地址**：`http://127.0.0.1:8000`（前端静态页面由后端托管）
- **后端目录**：`backend/`；前端：`frontend/index.html`；上传图片：`uploads/`

## 二、四大排行榜（业务规则）

| 榜单 | 数据来源 | 计算方式 |
|---|---|---|
| 单人总价值 | **多张对局截图**（列表/单场均可） | 选择 ≤2 小时时间段后**批量上传多张**该时间段内的对局截图，系统逐张识别并累加，每用户取最高一次 |
| 双人总价值 | **多张对局截图**（双方各传） | 两人各自提交时间段内总和，通过组队码（match_id）关联相加 |
| 单场最高价值 | **单场结算图** | 取该场「带出价值」最高的一次（submit_type=best） |
| 击败异象 | **单场结算图** | **新规则**：结算图右下角为各异象图标数量，按「图标分值 × 个数」累加总分，取总分最高一次 |

> 提交类型分为两种：
> - `total`：总价值榜，先选时间段再上传多张截图，`explore_value` = 时间段内探索价值累计总和
> - `best`：单场最高榜，上传单场结算图，`takeout_value` / `kills_score`（异象总分）/ `kills`（只数）

> **唯一值规则**：四个板块一律取该用户「最高的一次」成绩作为唯一上榜成绩，榜单展示 **用户昵称 + 分数 + 提交的截图依据**（缩略图可点击放大；批量提交则展示全部图片）。

## 三、当前进度（2026-08-12）

### 已完成功能
1. **注册/登录/退出**：JWT 鉴权，`hash_password` / `verify_password`
2. **四大排行榜**：`backend/ranking.py` 按 `submit_type` 过滤统计；每用户取最高一次（`_user_best`），榜单含昵称 + 分数 + 图片依据
3. **战绩识别双引擎**：
   - 本地 RapidOCR（`ocr_service.py`）：兼容标签同行/下一行/带单位（"12个"）三种布局；含击杀数上限、探索价值下限防误判；`extract_kills_icons` 按「图标名 + xN」文本行识别异象
   - 智谱视觉 AI（`vision_api.py`）：`glm-4v-flash`，配置于 `backend/.env`；`analyze_image`（单场）+ `analyze_list`（列表截图）+ `analyze_kills_icons`（异象图标）
4. **总价值多图批量累加**（本次新增）：
   - `POST /api/ocr/batch`：一次上传多张对局截图 + `time_start` / `time_end`（≤2 小时）
   - 逐张识别（列表截图按时间段过滤场次，单场结算图直接计入），返回每张 `sub_total` 与累计 `total_in_range`
   - 前端批量上传区支持一次多选/多次追加，结果表格逐张展示图片、类型、引擎与计入价值
5. **击败异象新规则**（本次新增）：
   - 图标库 `example/名字_分值.jpg`（13 种），分值随图片名
   - 视觉 AI **方式B**：不给图鉴，AI 仅描述图标外观 + 个数（采样 2 次取总分最高），服务端 `_best_icon_match` 按颜色变体规则匹配图标分值（如异色贪婪的盗匪 3.5）
   - 结算图右下角数字识别为各图标个数，总分 = Σ 分值×个数；本地 OCR 兜底匹配「图标名 + xN」文本
   - 内置测试图验证：盗匪×7(7) + 红色叹息球×1(2) + 贪婪的盗匪×1(3) + 异色贪婪的盗匪×1(3.5) = **15.5 分** ✓
6. **选手自算数据校对**：录入页提供自算区（含「我自算的异象总分」），与识别结果比对警示；`calc_explore` / `calc_takeout` / `calc_kills` / `calc_kills_score` 一并入库
7. **美术风格**：第五人格·欧利蒂丝庄园哥特风——墨绿+暗金配色、金色铁艺顶线、衬线标题（THE TREASURE HUNT）、卡片❖角饰、排行榜金色表头与奖牌样式
8. **前端交互**：提交类型切换、单人/双人、引擎选择、时间段选择（超 2 小时校验）、异象图标明细表格（图标/数量/分值/小计）、排行榜图片依据（点击放大）
9. **第五人格 UI 素材视觉升级**（2026-08-12，素材来自 `ui/` 目录）：
   - **logo**：`ui/logo.png`（白底深色皇冠图形）经 Pillow 抠白底 + 深色像素着金色渐变，生成 `frontend/logo_web.png` 透明 logo；header 与登录卡片顶部展示
   - **背景**：`ui/1.jpg`（深色庄园图）作为全局背景（cover + fixed + 暗色渐变遮罩）；`ui/6.jpg` 作为主界面顶部横幅背景（hero-banner，含带出之王 / 异象之王 / 我的场次三个数据位）
   - **静态托管**：后端新增 `/ui`（项目根 `ui/` 素材目录）与 `/assets`（`frontend/` 资源目录）两个 StaticFiles 挂载
   - **一键启动**：项目根 `启动.bat`（chcp 65001 + UTF-8），自动装依赖 → 检测 `.env` → 启动 8000 端口并自动打开浏览器

### 本次端到端验证结果
- `POST /api/ocr/batch` 多图批量：返回每张原始文件名、`image_path`、`sub_total`，累计 `total_in_range` ✓
- 排行榜四板块均返回图片依据（`image_path`，双人为双方各自图片）✓
- `best_kills` 含异象总分（`best_kills`）/ 只数（`kills_total`）/ 明细 JSON（`kills_detail`，字段 `name/count/score/sub`）✓
- 异象识别测试图 15.5 分命中、明细 ≥3 类 ✓
- 之前轮次已验证：列表截图 OCR 4 场解析、时间段过滤累计、超 2 小时拒绝、双人组队合并、重复提交拒绝

## 四、关键设计说明

### 列表截图 OCR 解析（`extract_list_result`）
- 时间正则兼容 `08/08 00:22` 与无空格 `08/0800:22`
- 每场取时间后的第一个纯数字（≥1000）作为探索价值，忽略段位积分（`+30`）与主页按钮干扰（`60`）
- 无法读取数值的场次自动跳过

### 总价值多图批量累加（`/api/ocr/batch`）
- 前端批量选择多张截图（picture-card 预览），`runBatch` 组装 FormData 逐张上传
- 后端逐张调 `_ocr_single_to_total`：列表截图先 `analyze_list` 解析每场，再按时间段过滤，仅计 `in_range` 场次；单场结算图直接取 `explore_value`
- 返回 `items[].{filename(原始名), image_path(保存名), kind, engine, sub_total, error}` 与累计 `total_in_range`
- `image_path` 统一存文件名（`Path(path).name`）；批量提交时多张图以逗号连接存入 `image_path`，前端 `imgSrc/imgSrcs` 拆分展示

### 击败异象图标识别（`vision_api.py`）—— 多视角 + 逐格扫描（2026-08-12 大幅重构）
- 图标库：`example/名字_分值.jpg`（13 种），`load_icons()` 解析分值
- **识别流程 `analyze_kills_icons`**（每个视角独立输出 `[{"name","appearance","count"}]`）：
  1. **整图采样 2 次**（temperature 0.0 / 0.3 / 0.7 轮换，覆盖不同漏读组合）
  2. **图标区裁剪放大 2x + 逐格扫描 2 次**：底部 55%-100% 裁剪后强制 AI 按 `row/col` 逐格输出（`DETAIL_KILLS_PROMPT`），对"两行/三行"布局补漏最有效
  3. **底部条带 2 条**：`(0.62,0.85)`、`(0.72,1.0)` 放大 2x（避开 45%-62% 的战利品区，防止"金色鱼形物品/书页"被误认成异象）
- **`_best_icon_match` 匹配**：图鉴精确名 → 颜色纠偏（AI 常按外观颜色叫错变体，如绿/黑衣着才是"贪婪的盗匪"，棕/黄是普通"盗匪"）→ 别名 → 外观关键词转正表 `_ICON_APPEARANCE_RULES`（"灰衣老人/蓝光/骷髅面具/蓝甲"等模糊描述映射到图鉴标准名）
- **`_merge_kills_counts` 多视角合并**：族去抖 `_KILL_FAMILIES`（盗匪族/看守族/叹息球族）——某视角同时见族内多变体→真实共存全保留；否则只取出现频次最高变体，且族内**所有**变体标记已处理防止重复计分（修复了测试3 盗匪×5 重复计分 bug）
- **`_robust_max`**：取各视角最大计数（模型常低估数量，取上限最接近真实值；不再做尖峰抑制，避免把真实 x4 误当幻觉压成 x1）
- 失败回退本地 OCR `extract_kills_icons`（匹配「图标名 + xN」文本）

### 识图训练效果（2026-08-12 实测）
| 测试图 | 期望 | 最初 | 最终 | 结论 |
|---|---|---|---|---|
| 测试2（8种异象） | 38.5 | 24 | 44.0（高估 5.5） | 主要来源：变体/数量微误 |
| 测试3（6种异象） | 52 | 45 | 53.0（+1） | ✅ 达标 |
| 测试4（7种异象） | 43.5 | 26.5 | 47.0（高估 3.5） | 变体区分仍不稳 |

**局限**：`glm-4v-flash`（免费模型）在"异色变体区分"（异色贪婪的盗匪 vs 贪婪的盗匪）与"数量读取"上仍有系统性误差，多次多视角采样+外观规则已基本到达该模型能力上限。**已落地人工录入兜底**（见下）。

### 人工录入异象界面（兜底，2026-08-12 新增）
- **后端** `GET /api/icons/list`：返回 13 种异象 `[{name, score}]`（由 `load_icons()` 生成，按分值升序）
- **前端**（单场模式表单内）：
  - "人工录入异象"表格：13 种异象 × 数量输入框，实时计算人工合计总分/总只数
  - 与 AI 识别结果对比：`manualConsistent` 判断总只数与总分是否一致，一致显示绿✓，不一致显示黄⚠提示
  - **提交时若人工填写过数量（manualTotal>0），以人工数据为准**覆盖 AI 的 kills/kills_score/kills_detail
- 提交后清空人工录入，重新识别后自动初始化

### 待办
1. 全量回归测试（8001 端口：注册→上传结算图→AI识别→人工录入核对→提交→榜单含明细）
2. 告知用户重启 8000/8001 端口加载新代码
3. （可选）后续升级付费模型 `glm-4v-plus` 提升识图精度

### 双人关联
- 前端 `mode=duo` 时要求填写队友用户名 + 组队码
- 后端先查占位记录：队友已提交则更新补全，未提交则为队友创建占位；已确认的场次拒绝重复提交
- 双人总价值 = 两人各自 `explore_value` 之和（按 `match_id` 分组）

### 识别引擎
- `auto`（默认）：视觉 AI 优先，失败自动回退本地 OCR 并标注 `fallback: "ocr"`
- `ai` / `ocr`：强制指定
- 视觉 AI 未配置（无 `.env`）时自动使用本地 OCR

## 五、数据库结构

`results` 表核心字段：

| 字段 | 说明 |
|---|---|
| `user_id` / `event_id` | 归属用户与赛事 |
| `match_id` | 场次标识，双人同队共享 |
| `is_duo` | 是否双人 |
| `submit_type` | `total`（总价值列表） / `best`（单场最高） |
| `time_start` / `time_end` | 总价值模式的时间段 |
| `explore_value` | total: 时间段内总和；best: 单场探索价值 |
| `takeout_value` / `kills` | 带出价值 / 击败异象只数 |
| `kills_score` | 击败异象总分（Σ 图标分值×个数，新规则） |
| `kills_detail` | 图标明细 JSON（`[{name,count,score,sub}]`，String） |
| `calc_explore` / `calc_takeout` / `calc_kills` / `calc_kills_score` | 选手自算值（校对） |
| `confirmed` | 是否已确认提交 |

> SQLite 已有旧库时自动执行轻量迁移（`_migrate`），为已存在的表补充新列。

## 六、配置与启动

1. 安装依赖：`pip install -r backend/requirements.txt`（国内可加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`）
2. 配置视觉 AI（可选）：复制 `backend/.env.example` 为 `backend/.env`，填写智谱 Key
   ```ini
   VISION_API_KEY=你的智谱key
   VISION_BASE_URL=https://open.bigmodel.cn/api/paas/v4
   VISION_MODEL=glm-4v-flash   # 免费；可换 glm-4v-plus 更准
   ```
3. 启动：`python backend/run.py`（自动加载 .env 并启动 uvicorn，端口 8000）
4. 检查配置：`python backend/check_vision.py`

## 七、待办 / 后续可优化

- [ ] **重启 8000 端口后端**以加载新代码（当前 8000 运行的是旧版本，新功能仅在 8001 测试实例验证）
- [ ] 正式比赛前清空测试数据（删除 `backend/mojin.db` 后重启，保留 `uploads/` 即可）
- [ ] 用更多真实战绩图调优列表截图 OCR（不同机型截图、亮度/旋转）
- [ ] 视觉 AI 模型升级 `glm-4v-plus`（付费）进一步提升识别率
- [ ] 管理员后台：赛事开关、成绩复核、异常值标注
- [ ] 前端暗色主题/移动端适配（选手多使用手机上传截图）
- [ ] 导入导出：排行榜 CSV / Excel 导出，公示用

## 八、文件清单

```
backend/
  main.py          # FastAPI 入口：/api/ocr(mode=list/single) /api/ocr/batch /api/results /api/rankings
  database.py      # SQLAlchemy 模型 + 轻量迁移
  auth.py          # JWT 注册登录
  ocr_service.py   # RapidOCR + 单场/列表提取 + 异象图标文本兜底
  vision_api.py    # 智谱视觉 AI（analyze_image / analyze_list / analyze_kills_icons）
  ranking.py       # 四大排行榜（唯一值 + 图片依据）
  run.py           # 启动脚本
  check_vision.py  # 视觉 AI 配置检查
  requirements.txt
  .env.example     # 配置模板
frontend/
  index.html       # 单页应用（Vue3 + Element Plus）
uploads/           # 上传的战绩截图
PROJECT.md         # 本文档
README.md          # 项目说明
```
