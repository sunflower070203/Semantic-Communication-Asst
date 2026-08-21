# 语义通信助手 — 进度恢复文档

> 最后更新：2026-08-21 23:40（Asia/Shanghai）
> 用途：平台会话中断后，按此文档恢复全部进度。所有关键标识符和待办在此记录。

## 1. 平台侧资产（账号 sunhao / 东南大学 OpenTrek）

### 智能体
| 名称 | agentCode | 版本 | 引擎 | 状态 |
|---|---|---|---|---|
| 语义通信助手 | `eb3a4ce1-2037-4dbd-938b-5f3357676455` | `1787321985242` | processAgentEngine | 流程：开始→脚本任务→结果渲染任务；脚本为出网探测（沙箱禁网，见第 3 节） |
| 语义通信知识问答 | `fcae0115-ea0f-4c86-b688-56ac9c88db05` | `1787326166654` | processAgentEngine | 完整 RAG 流程已保存并绑定语义通信知识库；运行时断在"术语库检索"（待修，见第 4 节） |
| 论文问答（参考/保底） | `d2d3f9ec-37c2-4f1d-ba4a-afaaf58cd398` | `1783783312184` | processAgentEngine | 已验证可用的知识问答 RAG 流程，绑定"论文知识库" `zbyny1fu224y` |
| 东南大学论文助手 | `97f5a8f2-dd4b-414c-a16f-29853a0c1444` | `1783782865950` | processAgentEngine | 旧草稿，勿动 |

### 知识库
| 名称 | code | 说明 |
|---|---|---|
| 语义通信知识库 | `ryekr4gqw2pn` | 5 篇已解析（2006.10685、2401.13387、2401.14160、2312.05062、2206.02596）；4 篇失败（1809.01733、2201.01389、2102.00202、2302.02287）；1 篇排队（2212.01485） |
| 论文知识库 | `zbyny1fu224y` | 用户个人论文，6 篇已解析；论文问答在用 |

## 2. 本地资产（本机 C:\Users\Sunny\Documents\ChatGPT\agent-demo）

- `papers/`：10 篇语义通信论文 PDF（arXiv 下载，可重新下载：`https://arxiv.org/pdf/<id>`，ID 见 `kb/paper_list.md`）
- `agent/node_script.py` + `tests/test_retrieval.py`：检索脚本（本地 13/13 测试通过），平台脚本沙箱无法使用（见第 3 节）
- `prompts/intent_split.md`、`prompts/brief_generator.md`：提示词
- `kb/paper_list.md`、`kb/terminology.md`：知识库材料
- `docs/superpowers/specs/`、`docs/superpowers/plans/`：设计文档与实施计划

## 3. 关键平台发现（决定设计，勿重蹈）

1. **脚本沙箱禁止网络**：支持模块仅 `re/json/string/math/random/set/frozenset/DateTime/uuid`，无网络库；`urllib.request` 报 "not supported module"。内置 request 只是请求 ID。→ 检索不能走脚本节点。
2. **流程节点映射由平台 UI 生成**：API 直接构造 saveProcess 会报"图解析异常/节点缺失入参配置/引用关系已变更"。节点间 input/output 映射必须在 UI 里拖线生成。
3. **调试运行**：`/designer/run` API 常报 10003 会话锁；UI 调试面板可用。调试面板输入需真人键入（自动化注入 React 不认）。
4. **知识库上传**：`/kortex/kb/doc/file/list` 可查状态；上传用详情页"导入"按钮（原生文件选择器，自动化无法注入）。kbdetail 页"添加文件"按钮禁用，要用 `#/app-pc-kb/kbase/detail?code=<kbcode>` 页的"导入"。
5. **引擎升级**：quick/create 建的是 defaultAgentEngine；需调 `/agent/version/upgradeNewProcessAgentRefVersion` 升级为 processAgentEngine 才能跑流程。
6. 智能体"空"（Agent Is Empty）：流程未保存/校验通过时会报此错；流程必须通过 saveProcess 校验。

## 4. 待办（按优先级）

### P0：让"语义通信知识问答"真正能回答（B 方案收尾）
- 路线 1（推荐）：在 UI 打开 语义通信知识问答 流程（flowNew），删除"术语库检索、知识召回处理、知识改写、问答库检索、标准问答召回"节点，把"多轮改写"直接连到"文档召回"，其余不动 → 校验 → 调试
- 路线 2（保底）：把 `papers/` 的 PDF 上传到"论文知识库" `zbyny1fu224y`，直接用"论文问答" agent 回答

### P1：A 方案验证（工具节点能否出网）
- 在"工具箱/工具任务"里建一个 HTTP 工具指向 arXiv，测试连通性（此前未验证）

### P2：知识库补全
- 重试 4 篇失败论文（1809.01733 等；失败原因疑似深解析模型 qwen-vl-plus 或大文件）
- 等 2212.01485 排队完成

### P3：交付物（8 月 31 日前）
- Demo 视频、项目策划书（docs/plan_book.md 待写）、技术文档（docs/technical_report.md 待写）、zip 打包提交

## 5. 提交信息（GitHub: sunflower070203/Semantic-Communication-Asst）

- 本地 main 分支有提交：设计文档、实施计划、检索脚本+测试、知识库材料、提示词
- `papers/` 已加入 .gitignore（PDF 可重新下载，不占仓库）
