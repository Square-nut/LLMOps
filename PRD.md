# LLMOps 产品需求文档（PRD）

## 1. 文档信息

| 项目 | 内容 |
|---|---|
| 产品名称 | LLMOps 本地知识库与模型运营平台 |
| 文档版本 | v1.0 |
| 适用阶段 | MVP → 本地模型运营增强 |
| 目标用户 | 内部知识库使用者、系统管理员、开发者 |
| 产品形态 | Vue Web 前端 + FastAPI 后端 + PostgreSQL + FAISS + Xinference |

## 2. 背景与问题

团队需要一个可在本地运行的知识库问答系统：文档不依赖第三方向量服务，检索使用本地 GPU Embedding；最终回答可以先使用在线 Chat 模型，后续再平滑切换到本地 Chat 模型。

当前技术基础已具备：

- Windows 运行 Vue、FastAPI 与 Docker PostgreSQL。
- WSL2 使用 RTX 3060 12GB 运行 Xinference。
- `bge-base-zh-v1.5` 提供本地 768 维 Embedding。
- PostgreSQL 保存文档、分块、日志、模型目录与模型启动参数。
- FAISS 保存向量并支持从完整持久化状态恢复。
- 模型目录支持 Chat / Embedding 激活与 Xinference 模型部署、停止、缓存查询。

现阶段的产品重点是把这些能力整理为稳定、可理解、可操作的产品流程，而不是让用户在多个命令行和管理页面之间切换。

## 3. 产品目标

### 3.1 核心目标

1. 用户可上传文本或文件，建立可检索的本地知识库。
2. 用户可通过 Chat 页面使用 RAG 问答，并知道回答是否使用了知识库上下文。
3. 管理员可在页面中维护 Chat 与 Embedding 模型，部署/停止 Xinference 模型并切换当前模型。
4. 管理员可快速发现数据库、向量索引、Embedding、Chat 服务的异常并完成恢复。
5. 所有模型密钥保留在运行环境中，不通过浏览器或数据库明文保存。

### 3.2 非目标

- 不构建通用工作流引擎、Agent 编排平台或多租户 SaaS。
- 不替代 Xinference 的完整模型生态与底层 GPU 调度能力。
- 不在 MVP 中引入 Kubernetes、消息队列或独立向量数据库集群。
- 不在当前阶段实现 Vision/YOLO 业务页面。

## 4. 用户与权限

| 角色 | 主要任务 | 可用能力 |
|---|---|---|
| 知识库用户 | 问答、上传资料 | Chat、知识库录入、查看基础状态 |
| 管理员 | 模型与运行配置维护 | 模型管理、模型切换、部署/停止、重建索引、服务检查 |
| 开发者 | 本地调试与扩展 | 全部页面、API 文档、环境配置 |

当前 MVP 默认由内部管理员使用；正式多用户部署前需补充登录、角色控制与审计。

## 5. 产品架构与部署边界

```text
用户
  ↓
Vue 前端（Windows，:5173）
  ↓
FastAPI（Windows，:8000）
  ├── PostgreSQL（Docker，文档/分块/日志/模型目录）
  ├── FAISS（本地向量索引）
  ├── 在线 Chat API（默认）
  └── Xinference（WSL2，:9997）
        ├── BGE Embedding（当前）
        └── Qwen 7B GGUF Chat（可选后续）
```

### 5.1 服务职责

| 服务 | 职责 |
|---|---|
| LLMOps 前端 | 用户问答、资料录入、状态展示、运行配置、模型管理 |
| FastAPI | RAG 编排、模型路由、模型目录 CRUD、Xinference API 代理 |
| PostgreSQL | 文档、分块、聊天日志、模型配置、激活状态、启动参数 |
| FAISS | 文档向量和相似度检索 |
| Xinference | 下载、缓存、启动、停止 Embedding / 本地 Chat 模型 |

## 6. 核心业务流程

### 6.1 文档入库

1. 用户在“知识库录入”提交文本或文件。
2. 后端保存原始文档并切分为 Chunk。
3. 后端调用当前 Embedding 模型生成向量。
4. 向量写入 FAISS；分块和 Embedding 版本写入 PostgreSQL。
5. 页面返回文档、分块、向量数量和模型版本。

### 6.2 RAG 问答

1. 用户在 Chat 页面输入问题并选择是否启用 RAG。
2. 后端使用当前 Embedding 模型将问题向量化。
3. FAISS 返回 Top-K 相关分块。
4. 后端把问题、系统提示词和检索上下文提交给当前 Chat 模型。
5. 页面展示回答、模型名、耗时、Token 与是否使用 RAG。
6. 后端记录聊天日志。

### 6.3 Embedding 模型切换

1. 管理员在“运行配置”选择模型目录中的 Embedding 模型。
2. 后端将该记录设为激活状态，并更新当前 API 进程中的 Embedding 配置。
3. 系统提示必须重建 FAISS 索引。
4. 管理员确认后执行“重建索引”。
5. 状态页显示新的模型、维度、版本和索引状态。

### 6.4 Xinference 模型部署

1. 管理员在“模型管理”查询 Xinference 模型目录。
2. 按模型名称、参数、已下载/未下载状态筛选并分页浏览。
3. 管理员新增或编辑产品侧模型记录，保存 Endpoint、维度和 `runtime_config`。
4. 点击“部署到 Xinference”后，后端调用 Xinference `/v1/models`。
5. Xinference 下载或复用缓存并启动模型。
6. 页面刷新后展示已下载、运行中或未运行状态。

## 7. 页面与功能需求

### 7.1 Chat 页面

| 编号 | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| CHAT-01 | 输入问题并发送 | P0 | 可获得 Chat 模型回答或明确错误提示 |
| CHAT-02 | RAG 开关 | P0 | 关闭时不检索；开启时响应标注是否使用 RAG |
| CHAT-03 | 显示模型、耗时、Token | P1 | 每条回答展示结构化元数据 |
| CHAT-04 | 在线模型认证失败提示 | P0 | 不显示笼统 500，提示 API Key/服务认证问题 |

### 7.2 知识库录入页面

| 编号 | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| INGEST-01 | 文本入库 | P0 | 文本写入 PostgreSQL 并生成向量 |
| INGEST-02 | 文件入库 | P1 | 支持项目允许的文件格式并返回处理结果 |
| INGEST-03 | 返回 Chunk 数量与版本 | P1 | 用户可确认入库使用的 Embedding 版本 |

### 7.3 系统状态页面

| 编号 | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| STATUS-01 | 展示 API、数据库、Embedding、FAISS 状态 | P0 | 服务异常可被识别 |
| STATUS-02 | 手动检查 Chat 和 Embedding | P0 | 返回模型、维度/回答、耗时或明确失败原因 |
| STATUS-03 | 重建 FAISS 索引 | P0 | 从 PostgreSQL 文档重新生成向量 |
| STATUS-04 | 检测模型/维度/版本不匹配 | P1 | 提示必须重建索引 |

### 7.4 运行配置页面

| 编号 | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| CONFIG-01 | 展示当前运行配置 | P0 | 显示当前 Chat、Embedding、RAG、数据库状态；密钥仅显示是否已配置 |
| CONFIG-02 | 切换 Chat 模型 | P0 | 从模型目录选择后立即作用于后续对话 |
| CONFIG-03 | 切换 Embedding 模型 | P0 | 切换后提示并支持重建索引 |
| CONFIG-04 | GUI 运行参数编辑 | P1 | 参数持久化到数据库运行配置，不直接暴露或覆写密钥 |

### 7.5 模型管理页面

| 编号 | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| MODEL-01 | 产品侧模型目录 CRUD | P0 | 支持新增、编辑、删除非激活模型 |
| MODEL-02 | 模型参数持久化 | P0 | `runtime_config` 保存引擎、格式、量化、GPU、下载源等参数 |
| MODEL-03 | Xinference 模型列表 | P0 | 支持名称、参数、已下载/未下载筛选和分页 |
| MODEL-04 | 查询已下载缓存与运行模型 | P0 | 区分“已下载”“运行中”“未运行” |
| MODEL-05 | 部署模型 | P0 | 调用 Xinference 启动模型；缓存存在时复用缓存 |
| MODEL-06 | 停止模型 | P1 | 停止运行实例，不删除模型缓存 |
| MODEL-07 | 下载/启动进度 | P1 | 显示排队、下载、加载、成功、失败状态 |
| MODEL-08 | 从 Xinference 模型目录一键导入 | P1 | 自动预填模型名称、类型和推荐参数 |

### 7.6 日志页面

| 编号 | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| LOG-01 | 查询聊天日志 | P1 | 展示输入、输出、模型、Token、耗时与时间 |
| LOG-02 | 查询入库日志 | P1 | 展示来源、内容长度、Chunk 数与 Embedding 版本 |

## 8. 数据与配置要求

### 8.1 关键数据实体

| 实体 | 核心字段 | 用途 |
|---|---|---|
| documents | content, source, created_at | 原始知识库文档 |
| chunks | document_id, chunk_text, embedding_version | 文本分块与版本追踪 |
| llm_logs | input, output, model, tokens, latency | 对话审计与运营分析 |
| model_configs | model_key, model_type, provider, model_name, endpoint, dimension, is_active | 可选模型目录 |
| model_configs.runtime_config | 引擎、格式、量化、GPU、下载源等 | Xinference 启动参数持久化 |

### 8.2 配置与安全原则

- `.env` 是启动默认值与密钥来源。
- PostgreSQL 保存非敏感运行配置、模型目录和启动参数。
- API Key、数据库连接串不得写入模型目录或返回给浏览器。
- 当前激活 Chat / Embedding 模型保存在 PostgreSQL，API 重启后恢复。
- 切换 Embedding 模型、维度或 Provider 必须重建 FAISS。

## 9. API 需求摘要

| API | 用途 |
|---|---|
| `POST /api/chat` | Chat 与 RAG 问答 |
| `POST /api/ingest/text`、`POST /api/ingest/file` | 文档入库 |
| `GET /api/rag/status` | RAG、索引与数据库状态 |
| `POST /api/rag/reindex` | 重建 FAISS |
| `POST /api/rag/model-check` | 检查 Chat 模型 |
| `POST /api/rag/embedding-check` | 检查 Embedding 服务 |
| `GET/POST/PUT/DELETE /api/models` | 模型目录 CRUD |
| `POST /api/models/{id}/activate` | 切换当前 Chat 或 Embedding 模型 |
| `GET /api/models/runtime/catalog` | Xinference 模型目录筛选与分页 |
| `GET /api/models/runtime/cached` | 已下载缓存模型 |
| `GET /api/models/runtime/running` | 当前运行模型 |
| `POST/DELETE /api/models/{id}/deploy` | 部署/停止 Xinference 模型 |

## 10. 非功能需求

| 类别 | 要求 |
|---|---|
| 可用性 | 模型服务失败时返回可理解的错误，不向前端暴露 Python 堆栈 |
| 性能 | Embedding 和检索在本地完成；模型下载/加载使用异步任务或可轮询进度 |
| 兼容性 | 支持 Windows + WSL2；Docker 仅承担 PostgreSQL |
| 可维护性 | 模型路由、Embedding、RAG、Xinference 管理保持模块化 |
| 数据一致性 | Embedding 版本、向量维度与 FAISS 索引必须一致 |
| 安全性 | 管理模型、部署模型、修改运行配置后续需接入管理员权限与审计 |

## 11. 版本规划

### 已完成

- FastAPI + Vue + PostgreSQL + FAISS 基础架构。
- 文档入库、RAG 问答、日志、状态检查与索引重建。
- WSL2 Xinference + BGE 本地 Embedding。
- 产品侧模型目录、模型激活、启动参数持久化。
- Xinference 模型目录、缓存、运行模型查询、部署和停止基础能力。

### 下一版本（P1）

1. Xinference 下载与加载进度展示、失败重试和取消。
2. 从 Xinference 可用模型一键导入到模型目录。
3. 运行配置的非敏感参数 GUI 编辑与持久化。
4. 本地 Qwen 7B GGUF Chat 模型部署、切换和验收。
5. 模型管理和运行配置的管理员权限控制与操作日志。

### 后续版本（P2）

1. Vision/YOLO 检测与区域 OK/NG 页面。
2. 多 Provider 路由与 LiteLLM。
3. FAISS 向量库升级为可选的集中式向量数据库。
4. 多用户、权限、审计与部署自动化。

## 12. 验收标准

### P0 验收

- 可完成“上传文档 → 本地 BGE 向量化 → FAISS 检索 → Chat 回答”的完整闭环。
- Chat、Embedding 模型可分别从 UI 选择并激活。
- 切换 Embedding 后系统明确要求并可执行重建索引。
- 模型管理可查询 Xinference 可用、已下载、运行中的模型，并能部署/停止模型。
- 模型启动参数保存后可重复使用。
- Chat API Key 无效、Xinference 未启动、Embedding 模型未加载等异常均有可理解提示。

### P1 验收

- 模型下载和加载过程可显示进度与失败原因。
- 管理员无需手工填写常用模型的全部参数即可导入、部署和激活模型。
- 本地 Chat 模型可替换默认在线 Chat 模型，RAG 链路无需改造。

