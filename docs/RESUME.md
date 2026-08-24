# 语义通信助手 — 进度恢复文档

> 最后更新：2026-08-23 19:30（Asia/Shanghai）
> 用途：平台会话中断后，按此文档恢复全部进度。所有关键标识符和待办在此记录。

## 0. 重大进展（A 路线：角色对话 Agent 已验证可自主运行）

**语义通信自主Agent3 是当前主资产**：角色对话型、AutoBotV2、processAgentEngine/ReAct、
qwen3.6-plus + 角色定义Prompt + 约束条件Prompt，**已在调试面板真实运行并给出高质量回答**
（语义通信核心思想 + 4 篇文献引用：Shannon 1949 / DeepSC / Letaief 综述 / Gündüz Beyond Bits）。

- agentCode：`407be567-2e47-4391-8249-729d943d1753`
- agentVersion：`1787370379269`（v1.0，设计中）
- 状态：表单草稿已保存（form/save），运行时读表单草稿；config/list 不显示模型属正常（见 3.7）
- 调试面板发消息方法：textarea focus + CDP `Input.insertText` + 点发送按钮（见 3.8）
- **工具尚未挂载**（见 3.9，需人工 UI 添加）
- Agent3 体验已启用：experienceCode `EXP-W2ITY0`（可重新 enable）

> 注意：设计页表单只在"创建后首次访问"渲染，离开再回来会白屏（平台前端 bug，见 3.5）。
> 配置 Agent3 后尽量不要再进它的设计页；要改配置就新建一个角色对话 Agent 立即配置。

### 0.1 8/23 更新（校内网恢复，续作）
- **Agent3 已发布（ONLINE）**：`/agent/version/online` 成功。
- **配置确认持久化**：`/agent/version/config/query?code=&version=&versionName=` 返回完整表单数据
  （node_model.taskPlanning 含 modelCode `edf7a63d4352499ebeb1a8255f5a9feb` / qwen3.6-plus；
  node_role.role / node_constraint.constraint 全文都在）。**运行时读这份数据，不是 config/list**。
- **运行入口 = 分享链接（最重要发现）**：
  1. `POST /agent/share/create {agentCode, agentVersion}` → shareUuid
  2. 打开 `#/arrange/agentExp?randomCode=<shareUuid>&noLayout=1`（注意是 **shareUuid**，不是 experienceCode）
  3. 页面输入框发消息即可运行。今早验证：Agent3 完整回答"语义通信核心思想+4篇文献引用"。
- **工具可挂载但执行失败（平台限制）**：
  - `POST /task/add {agentCode, agentVersion, tool:{code,name,version,toolType,toolExecuteType:"DEFAULT"}, taskName, taskDesc, taskLimit}` 成功（data:1）
  - 运行时 agent 会规划"调用联网搜索工具"，但执行报 `AGENT_TASK_DEFAULT_FAILED`（任务执行失败）
  - `/tools/debugExecuteApiTool` 直接 500 → **工具执行沙箱/运行器在平台侧故障**（与脚本沙箱禁网一致）
  - 已用 `POST /task/delete {agentCode, agentVersion, taskName}` 删除两个工具任务，恢复干净状态
- **auto/new 体验流不可用**：`/agent/auto/new/session/create {template:"AutoBotV2", relationCode}` 报
  "Failed to create the solution"（solutionCode 为空，平台未部署解决方案）。
- 共享页 UI 输入自动化不稳定：建议用"新开对话"+手动输入，或直接用上面 API + 页面。

### 0.2 8/23 晚：B 路线已修复并验证（语义通信知识问答 RAG 可用）
- **根因**：流程里的"术语库检索/问答库检索"配置为 NewAutoTerm/NewAutoQa 类型，但知识库是文档类型；
  术语分支空转产出垃圾（知识改写输出 "rq"），"综合改写兼容"脚本拿到 "rq" 后 600 秒超时。
- **修复（API 直改流程图）**：
  1. `GET /api/flow/config/get?configTargetType=AGENT&configCode=<agentCode>_<agentVersion>` 取图 JSON
  2. **saveProcess/saveGraph 载荷结构**（关键，之前一直猜错）：
     `POST /api/flow/config/saveProcess {configTargetType, configCode, version, data:{nodes, edges}}`
     —— 图在 **`data`** 字段（不是 showConfig）！
  3. 删除 8 个节点（术语库检索/知识召回处理/知识改写/问答库检索/标准问答召回/选择器1/输出1/综合改写兼容）+ 9 条边
  4. 新增边：多轮改写 → 文档召回；并把 文档召回.query、结果总结.rewrite_query 映射改为 NODE.多轮改写.content
  5. 保存后 11 节点 10 边：开始→多轮改写→文档召回→召回结果处理→选择器→(输出|总结参数→结果总结→meta→文本组合→内容输出)
- **验证通过**：真实运行"什么是语义通信？请结合知识库文献回答"，
  文档召回检索到知识库 chunk（file_code/页码/正文），结果总结生成带 4 条引用的完整中文回答。
- **已发布（ONLINE）**：/agent/version/online 成功。
- 运行时 API：`POST /designer/createRunningSession` → 开 SSE `GET /designer/createCmdChannelNew?sessionId=&clientId=`
  → `POST /designer/run {sessionId, input, clientId}` → `POST /designer/listTask` 查任务与结果。

## 1. 平台侧资产（账号 sunhao / 东南大学 OpenTrek）

### 0.5 8/24：P0 完成（凭据安全 + 脚本加固 + 发布自动化 + FC 重试结论）
- **凭据移出仓库**：三个脚本的 COOKIE/平台地址/agent 标识统一收进 `scripts/config.py`
  （读环境变量或仓库根 `.env`，`.env` 已 gitignore）；新增 `.env.example`。
  旧 Cookie 已过期轮换（浏览器 CDP 取新值）。⚠ 仓库 git 历史仍含旧 Cookie 值，
  若在意可后续做历史清理；平台仅内网可达，风险有限。
- **三个 P2 修复**：
  1. `run_question` 检查 `/designer/run` 响应 errorCode，失败立即返回不再烧满超时；
  2. `kb_upload.py` 注册后校验 `success`，失败抛错并提示清理 minio 对象；
  3. `run_demo_qa.py` 不再覆盖手维护的 `demo/results/README.md`，表格改写入 `qa_index.md`。
- **发布链路自动化**：新增 `scripts/deploy_flow.py`（clone→patch→saveProcess→可选 online 一条龙）
  和 `scripts/flow_patch.py`（补丁逻辑共享模块）；`patch_flow_validation.py` 改为薄封装。
- **Function Calling 重试结论（P0.3）**：平台工具（数学计算器/夸克搜索/网页解析/文档解析，
  toolCategory=openTrek，code 如 `10000baseline`）可正常列出、可挂载（/task/add 成功），
  但运行时工具任务两次实测均后端崩溃：联网搜索(MY_MCP)→`AGENT_TASK_DEFAULT_FAILED`；
  数学计算器→`taskBeforeConfig is null`。→ **平台工具执行沙箱/运行器后端故障 = 天然约束**，
  与 8/23 结论一致，Function Calling 深度演示当前不可行，写进策划书风险表。
- **本次新发现（需注意）**：`/tools/queryPage?toolCategory=openTrek` 返回的平台工具配置里，
  联网搜索 MCP 工具的 mcpConfig 内嵌了一个 DashScope API Key（个人/平台凭据），
  **建议尽快在阿里云百炼控制台轮换**（该值未写入本仓库）。

### 0.4 8/24 凌晨：Agent 化改造完成（引用校验节点 + 确定性 eval）✅
- **背景**：GAN 对抗审查（docs/agent_self_review.md）判定 B 路线是"RAG 聊天机器人 + 工作流外壳"，
  缺：生成后校验、程序化安全拒绝、确定性评测。
- **改造（B 路线 v1.4，agentVersion `1787495161508`，已 ONLINE）**：
  1. `meta` 脚本节点内置**引用校验**：解析结果总结 JSON（容错：去 markdown 围栏 + 截取首个 JSON 对象），
     断言每个引用 idx 存在于本次召回 chunk（all_meta）且答案中每个 【X】 标记都有对应 refs；
     未通过则输出 "⚠ 引用校验：[...] 未能与本次召回内容核实"。
  2. `结果总结` prompt 增加**禁止编造引用**约束（"idx 必须真实存在于参考内容中"）。
  3. 补丁脚本 `scripts/patch_flow_validation.py`：拉取 DRAFT 流程 → 改 meta 脚本 + prompt → saveProcess。
- **版本迭代（平台发布纪律：ONLINE 不可编辑，只能克隆）**：
  - v1.0 `1787326166654`（原始修复版，已下线）
  - v1.1 `1787493573109`（首次加校验，脚本变量名 `_json` 被沙箱拒绝 → 废）
  - v1.2 `1787493757541`（修变量名；严格 json.loads 对围栏输出假阴性 → 废）
  - v1.3 `1787494220819`（容错解析；refs 渲染仍依赖 FUNCTION 映射 → 废）
  - **v1.4 `1787495161508`（最终版，ONLINE）**：meta 脚本完全自解析，渲染+校验同源
- **确定性 eval（scripts/eval_agent.py，3 场景全绿）**：
  - concept：91.9s PASS；multistep：132.8s PASS；tool_require：71.3s PASS
  - 断言：回答存在/无流程错误/正文【X】⊆ 引用列表/校验干净（无 ⚠）/拒绝联网编造/无任务失败
  - eval 含失败重试一次（平台偶发抖动）；报告存 demo/eval/eval_report_*.md
- **已知平台限制**：API 同一 designer 会话连续两次 run（追问）会命中会话锁（流程执行但结果不送达），
  追问能力在分享页 UI 已验证可用（v1.0 实测）；eval 一律新会话跑。
- **新分享链接**：shareUuid `22ddb3160f3e4847ba90f7b5c4f8fb60`
  （`#/arrange/agentExp?randomCode=22ddb3160f3e4847ba90f7b5c4f8fb60&noLayout=1`）

### 0.3 8/23 深夜：知识库补全完成（4 篇失败 PDF 已重新上传并全部解析 ✅）
- **根因定性**：当初上传的 4 篇 PDF 文件本身就是损坏的（arXiv 下载被截断，本地 papers/ 同名文件与平台大小完全对应）
  → 反复 `/kortex/kb/doc/file/reprocess` 都失败（DKE 实例 status=4）。
- **用户下载有效版本**（papers/1809.01733v4 / 2201.01389v5 / 2102.00202v2 / 2302.02287v1）后，
  **绕过 UI 用 API 完成上传**（UI"导入"对话框 CDP 点击无效）：
  1. `GET /aihub/api/v1/sts?type=upload&path=kortex/kb/doc/file/<文件名>&fileId=<任意hash>`
     → 返回 `{accessKeyId, accessKeySecret, securityToken, bucket, endpoint, type:"MINIO", path:"apsara/kortex/kb/doc/file/<随机>/<文件名>"}`
     （不带 type=upload 时只返回 presigned url 没有 secretKey，必须带全三个参数）
  2. 用 AWS SigV4 对 `PUT /minio-test/<sts.path>` 预签名后直传文件（`scripts/kb_upload.py` 已实现并验证 200）
  3. `POST /kortex/kb/doc/file/uploadFromPreUploadPaths {kbCode, paths:[<sts.path>], userMetadata:{}}` 注册，自动触发解析
- **结果**：语义通信知识库 `ryekr4gqw2pn` 现在 **10 篇全部 state=200（解析成功）**：
  1809.01733（41 chunks）/ 2201.01389（57）/ 2102.00202（15）/ 2302.02287（15）+ 原有 6 篇。
  已删除 4 个旧损坏条目（state=500，同名重复），文件清单干净。
- **端到端复验**：B 路线 agent 真实运行"Deep JSCC 和 DeepSC 有什么区别？请结合知识库文献回答"，
  文档召回命中 2302.02287（score 0.95），最终答案带 【I】-【IV】引用，完整跑通。
  （新增运行时取答案方式：`GET /designer/pageListLatestMsg?sessionCode=<uniqueCode>&pageIndex=0&pageSize=50`，
  消息里 `blocks[].blockContent` 是最终文本；`/designer/listTask` 只给中间任务。）

### 智能体
| 名称 | agentCode | 版本 | 引擎 | 状态 |
|---|---|---|---|---|
| 语义通信自主Agent3 | `407be567-2e47-4391-8249-729d943d1753` | `1787370379269` | processAgentEngine | **主资产**：角色对话 AutoBotV2，已验证自主问答（带文献引用） |
| 语义通信自主Agent2 | `42c92470-bb63-4b4f-9d4a-9a61abd24586` | v1.0=`1787366954788`（AutoBotV2）；v1.1=`1787369863842`（defaultAgentEngine 空壳） | processAgentEngine | 实验；v1.0 设计页二次访问白屏；v1.1 建议删除 |
| 语义通信助手 | `eb3a4ce1-2037-4dbd-938b-5f3357676455` | `1787321985242` | processAgentEngine | 流程：开始→脚本任务→结果渲染任务；脚本为出网探测（沙箱禁网，见第 3 节） |
| 语义通信知识问答 v1.4（主） | `fcae0115-ea0f-4c86-b688-56ac9c88db05` | `1787495161508` | processAgentEngine | **ONLINE**：引用校验节点 + 防编造约束，eval 3/3 全绿（见 0.4） |
| 语义通信知识问答 v1.0（旧） | `fcae0115-ea0f-4c86-b688-56ac9c88db05` | `1787326166654` | processAgentEngine | 已下线；无校验的原始修复版 |
| 论文问答（参考/保底） | `d2d3f9ec-37c2-4f1d-ba4a-afaaf58cd398` | `1783783312184` | processAgentEngine | 已验证可用的知识问答 RAG 流程，绑定"论文知识库" `zbyny1fu224y` |
| 东南大学论文助手 | `97f5a8f2-dd4b-414c-a16f-29853a0c1444` | `1783782865950` | processAgentEngine | 旧草稿，勿动 |

### 知识库
| 名称 | code | 说明 |
|---|---|---|
| 语义通信知识库 | `ryekr4gqw2pn` | **10 篇全部已解析**（含 1809.01733 / 2201.01389 / 2102.00202 / 2302.02287 补传成功；2212.01485 已排队完成） |
| 论文知识库 | `zbyny1fu224y` | 用户个人论文，6 篇已解析；论文问答在用 |

### 工具箱
| 工具 | 类型 | code | 说明 |
|---|---|---|---|
| 联网搜索 | MCP | `27772726-fcd1-4cf4-acd7-7f06711d05eb` | 通义检索工程，实时互联网搜索；已在"我的工具"里，可直接挂到 Agent |
| 数学计算器 / 夸克联网搜索 / 网页内容解析 / 文档在线解析工具 | 平台工具（system） | - | 平台工具标签下，网页/文档解析可用于读文献 |

## 2. 本地资产（本机 C:\Users\Sunny\Documents\ChatGPT\agent-demo）

- `papers/`：10 篇语义通信论文 PDF（arXiv 下载，可重新下载：`https://arxiv.org/pdf/<id>`，ID 见 `kb/paper_list.md`）
- `agent/node_script.py` + `tests/test_retrieval.py`：检索脚本（本地 13/13 测试通过），平台脚本沙箱无法使用（见第 3 节）
- `prompts/intent_split.md`、`prompts/brief_generator.md`：提示词
- `kb/paper_list.md`、`kb/terminology.md`：知识库材料
- `docs/superpowers/specs/`、`docs/superpowers/plans/`：设计文档与实施计划

## 3. 关键平台发现（决定设计，勿重蹈）

1. **脚本沙箱禁止网络**：支持模块仅 `re/json/string/math/random/set/frozenset/DateTime/uuid`，无网络库；`urllib.request` 报 "not supported module"。内置 request 只是请求 ID。→ 检索不能走脚本节点。
2. **流程节点映射由平台 UI 生成**：API 直接构造 saveProcess 会报"图解析异常/节点缺失入参配置/引用关系已变更"。节点间 input/output 映射必须在 UI 里拖线生成。
3. **调试运行**：`/designer/run` API 常报 10003 会话锁；UI 调试面板可用。自动化注入文本需 CDP `Input.insertText`（普通 fill 对 React 不认）。
4. **知识库上传（API 直传，已跑通）**：`/kortex/kb/doc/file/list` 可查状态。UI"导入"对话框 CDP 无法注入文件，
   用 `scripts/kb_upload.py`（STS → SigV4 PUT → uploadFromPreUploadPaths）绕过，见 0.3 节。
5. **引擎升级**：quick/create 建的是 defaultAgentEngine；需调 `/agent/version/upgradeNewProcessAgentRefVersion` 升级为 processAgentEngine 才能跑流程。
6. 智能体"空"（Agent Is Empty）：流程未保存/校验通过时会报此错；流程必须通过 saveProcess 校验。
7. **角色对话 Agent 配置保存链路（重要）**：
   - 前端"确定"保存 = form/save（存表单草稿）+ template/save（生成生效配置）。
   - `/agent/version/form/save` 可用（返回 success）；但 `/agent/version/template/save` 在此平台 **404**（前端-后端版本不匹配），
     导致模型/角色 Prompt 不进 config/list，**运行时直接读表单草稿**（Agent3 已验证能跑）。
   - `/agent/version/config/update` 需要 formAttributeNodes（后端生成），直接调报 `formAttributeNodes is null`。
   - `/agent/version/config/prompt?code=&version=&versionName=` 返回"生效 Prompt"，不含草稿里的角色/约束（属正常）。
8. **设计页调试面板可用**：输入框是 textarea，自动化方式 = JS focus → CDP `Input.insertText` 注入文本 → 点发送按钮。
   ReAct 循环真实运行（右侧"智能体任务规划"画布显示任务）。
9. **工具抽屉自动化失败**：选工具（BlockSelectItem 点击）无法提交到 React/Formily 状态，
   校验恒报"请选择工具"，工具列表不更新。**需人工在 UI 添加工具**（见 3.9）。
10. **体验页路由**：`#/arrange/agentExp` 和 `#/arrange/trekAgentExp?randomCode=<code>&noLayout=1` 均被重定向回 agentConfig
    （可能因版本未发布或平台 bug）；体验启用接口 `/agent/auto/new/experience/enable` 可用（返回 experienceCode）。
11. **8/23 新增**：
    - 角色对话 Agent 的配置读取/保存链：`config/query`（读 nodeFormAttribute）↔ `form/save`（写）；`form/save`
      只接受 node_model/node_role/node_constraint/node_combination/node_longTermMemory/shortTermMemory，
      **不接收任务工具**（工具走 `/task/add`）。
    - `/task/add` 需要 `tool.toolExecuteType`（"DEFAULT"），否则报 getToolExecuteType null。
    - 分享运行链路：`/agent/share/create` → `#/arrange/agentExp?randomCode=<shareUuid>` →
      `/agent/share/session/init` → `/designer/createCmdChannelNew`(SSE) → `/designer/run`。
    - `/designer/run` 需先建立 SSE 通道（clientId），否则报"调试器未与服务端建立连接"。

### 3.5 设计页表单渲染 bug（重要）
- 角色对话 Agent 的 agentDesign 页**只在创建后首次访问渲染完整表单**（角色/任务/记忆三栏 + 调试面板）。
- 离开该页再回来（导航/刷新/新标签）→ 只渲染顶栏，配置面板空白，无报错（错误边界外静默失败）。
- 规避：**创建 → 立即配置 → 立即测试**，不要中途离开；要改配置就新建一个角色对话 Agent。
- Agent2 v1.0 的"最近保存"时间戳会自动更新（草稿自动保存），但表单仍白屏。

### 3.8 调试面板发消息（验证 Agent 运行）
```text
1. 定位 textarea（placeholder="请输入问题"）并 focus
2. CDP Input.insertText 注入问题文本
3. 点发送按钮（面板内空文本图标按钮）
4. 等待：出现"停止生成"→ 右侧任务规划画布显示任务 → 输出 v1.0回复
```

### 3.9 给角色对话 Agent 挂工具（需人工，约 2 分钟）
1. 设计页"任务 → 工具"右侧 ➕（若页面白屏，新建角色对话 Agent 后立即操作）
2. 抽屉"我的工具"筛选切到 MCP工具 → 选"联网搜索"
3. 或"平台工具"标签 → 夸克搜索 / 网页内容解析 / 文档在线解析工具
4. 添加 → 填任务名称（如"联网搜索文献"）+ 适用场景 + 能力限制 → 确定
5. 主表单"确定"保存（如页面还活着）

## 4. 待办（按优先级）

### P0：A 路线收尾（主）
- [x] 角色对话 Agent 自主运行验证（Agent3，语义通信问答 + 文献引用）
- [x] 发布 Agent3（ONLINE）
- [x] 确认运行入口（分享链接 + config/query 持久化）
- [ ] **工具执行待平台侧修复**（/task/add 可挂，执行报 AGENT_TASK_DEFAULT_FAILED；/tools/debugExecuteApiTool 500）
- [ ] 找文献+读文献能力：改用 B 路线工作流 RAG（知识库检索），或等平台修工具沙箱
- [ ] 体验页/对外链接：用分享链接 `#/arrange/agentExp?randomCode=18f7c4b5d48b43d1836e883bc3f3e19b`（shareUuid，已生成）
- [ ] 删除 Agent2 v1.1 空壳（版本列表勾选删除，减少干扰）

### P1：B 路线（已完成 ✅）
- [x] 语义通信知识问答 流程修复（删除术语/问答分支，多轮改写直连文档召回）
- [x] 端到端验证：知识库检索 + LLM 总结 + 引用输出
- [x] 已发布 ONLINE
- [x] 补充知识库论文（4 篇失败论文已用 API 补传，10/10 全部解析成功）

### P2：知识库补全
- [x] 4 篇失败论文 API 补传并全部解析（根因：源 PDF 损坏，非解析模型问题）
- [x] 2212.01485 排队完成

### P3：交付物（8 月 31 日前）
- Demo 视频、项目策划书（docs/plan_book.md 待写）、技术文档（docs/technical_report.md 待写）、zip 打包提交

## 5. 提交信息（GitHub: sunflower070203/Semantic-Communication-Asst）

- 本地 main 分支有提交：设计文档、实施计划、检索脚本+测试、知识库材料、提示词
- `papers/` 已加入 .gitignore（PDF 可重新下载，不占仓库）
