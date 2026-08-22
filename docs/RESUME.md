# 语义通信助手 — 进度恢复文档

> 最后更新：2026-08-22 11:55（Asia/Shanghai）
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

## 1. 平台侧资产（账号 sunhao / 东南大学 OpenTrek）

### 智能体
| 名称 | agentCode | 版本 | 引擎 | 状态 |
|---|---|---|---|---|
| 语义通信自主Agent3 | `407be567-2e47-4391-8249-729d943d1753` | `1787370379269` | processAgentEngine | **主资产**：角色对话 AutoBotV2，已验证自主问答（带文献引用） |
| 语义通信自主Agent2 | `42c92470-bb63-4b4f-9d4a-9a61abd24586` | v1.0=`1787366954788`（AutoBotV2）；v1.1=`1787369863842`（defaultAgentEngine 空壳） | processAgentEngine | 实验；v1.0 设计页二次访问白屏；v1.1 建议删除 |
| 语义通信助手 | `eb3a4ce1-2037-4dbd-938b-5f3357676455` | `1787321985242` | processAgentEngine | 流程：开始→脚本任务→结果渲染任务；脚本为出网探测（沙箱禁网，见第 3 节） |
| 语义通信知识问答 | `fcae0115-ea0f-4c86-b688-56ac9c88db05` | `1787326166654` | processAgentEngine | 完整 RAG 流程已保存并绑定语义通信知识库；运行时断在"术语库检索"（待修，见第 4 节） |
| 论文问答（参考/保底） | `d2d3f9ec-37c2-4f1d-ba4a-afaaf58cd398` | `1783783312184` | processAgentEngine | 已验证可用的知识问答 RAG 流程，绑定"论文知识库" `zbyny1fu224y` |
| 东南大学论文助手 | `97f5a8f2-dd4b-414c-a16f-29853a0c1444` | `1783782865950` | processAgentEngine | 旧草稿，勿动 |

### 知识库
| 名称 | code | 说明 |
|---|---|---|
| 语义通信知识库 | `ryekr4gqw2pn` | 5 篇已解析（2006.10685、2401.13387、2401.14160、2312.05062、2206.02596）；4 篇失败（1809.01733、2201.01389、2102.00202、2302.02287）；1 篇排队（2212.01485） |
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
4. **知识库上传**：`/kortex/kb/doc/file/list` 可查状态；上传用详情页"导入"按钮（原生文件选择器，自动化无法注入）。kbdetail 页"添加文件"按钮禁用，要用 `#/app-pc-kb/kbase/detail?code=<kbcode>` 页的"导入"。
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
- [ ] 人工给 Agent3 挂工具（联网搜索 + 文档在线解析，见 3.9）
- [ ] 挂完工具后重新测试"找文献+读文献"闭环（让 agent 查 arXiv 并总结）
- [ ] 发布 Agent3（版本列表中"发布"）→ 再试体验页/对外链接
- [ ] 若发布后体验页仍跳转，改用"API调用"获取调用方式
- [ ] 删除 Agent2 v1.1 空壳（版本列表勾选删除，减少干扰）

### P1：让"语义通信知识问答"真正能回答（B 方案收尾）
- 路线 1（推荐）：在 UI 打开 语义通信知识问答 流程（flowNew），删除"术语库检索、知识召回处理、知识改写、问答库检索、标准问答召回"节点，把"多轮改写"直接连到"文档召回"，其余不动 → 校验 → 调试
- 路线 2（保底）：把 `papers/` 的 PDF 上传到"论文知识库" `zbyny1fu224y`，直接用"论文问答" agent 回答

### P2：知识库补全
- 重试 4 篇失败论文（1809.01733 等；失败原因疑似深解析模型 qwen-vl-plus 或大文件）
- 等 2212.01485 排队完成

### P3：交付物（8 月 31 日前）
- Demo 视频、项目策划书（docs/plan_book.md 待写）、技术文档（docs/technical_report.md 待写）、zip 打包提交

## 5. 提交信息（GitHub: sunflower070203/Semantic-Communication-Asst）

- 本地 main 分支有提交：设计文档、实施计划、检索脚本+测试、知识库材料、提示词
- `papers/` 已加入 .gitignore（PDF 可重新下载，不占仓库）
