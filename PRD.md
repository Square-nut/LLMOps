# LLMOps 产品需求文档（PRD）

| 项目 | 内容 |
|---|---|
| 产品名称 | LLMOps 本地知识库与模型运营平台 |
| 文档版本 | v1.1 |
| 适用阶段 | MVP 与本地模型运营增强 |
| 目标用户 | 内部知识库使用者、系统管理员、开发者 |
| 产品形态 | Web 管理平台 |

## 1. 背景与目标

### 1.1 背景

团队需要在本地运行知识库问答系统：文档通过本地 GPU Embedding 向量化并检索，回答阶段可先使用在线 Chat 模型，后续可切换到本地 Chat 模型。当前已有文档入库、FAISS 检索、RAG 问答、运行状态检查，以及 Xinference 模型查询、缓存、部署和停止等基础能力。

现阶段的产品任务是将这些能力整合为可由页面完成的稳定流程，减少用户在命令行、环境变量和多个管理页面之间反复切换。

### 1.2 产品目标

1. 用户可以录入文本或文件，建立可检索的本地知识库。 
2. 用户可以通过 Chat 页面进行 RAG 问答，并了解是否使用知识库上下文。
3. 管理员可以维护模型目录，部署、停止并切换 Chat / Embedding 模型。
4. 管理员可以检查数据库、向量索引、Embedding 和 Chat 服务，并处理可定位的异常。
5. 模型密钥仅保留在服务端运行环境，不在浏览器或数据库中明文保存。

### 1.3 非目标

- 本期不建设通用 Agent 编排、工作流引擎或多租户 SaaS。
- 本期不替代 Xinference 的模型生态和 GPU 调度能力。
- 本期不引入 Kubernetes、消息队列或独立向量数据库集群。
- Vision/YOLO 业务能力不属于当前 PRD 范围。

## 2. 用户需求

| 用户角色 | 核心诉求 | 典型任务 |
|---|---|---|
| 知识库用户 | 快速获得基于内部资料的可靠回答 | 上传资料、提问、查看回答是否命中知识库 |
| 系统管理员 | 不依赖命令行完成日常模型和服务维护 | 检查服务、重建索引、选择模型、部署/停止模型 |
| 开发者 | 便于本地调试、扩展 Provider 与模型 | 查看状态、调整非敏感运行配置、调用 API |

当前 MVP 默认为内部使用。登录、角色权限和操作审计作为后续增强；在完成前，模型部署、运行配置修改等能力仅应向可信管理员开放。

## 3. 功能列表

| 编号 | 功能 | 用户价值 | 优先级 | 当前状态 |
|---|---|---|---|---|
| CHAT-01 | Chat 问答与 RAG 开关 | 可按需基于知识库获得回答 | P0 | 已实现 |
| CHAT-02 | 回答元数据展示 | 知道模型、耗时、Token、RAG 使用情况 | P1 | 部分实现 |
| INGEST-01 | 文本录入与向量化 | 建立本地知识库 | P0 | 已实现 |
| INGEST-02 | 文件录入 | 降低资料导入成本 | P1 | 部分实现 |
| RAG-01 | 状态检查与索引重建 | 快速发现索引、服务或模型问题 | P0 | 已实现 |
| CONFIG-01 | 当前 Chat / Embedding 模型切换 | 页面化控制推理与检索模型 | P0 | 已实现 |
| CONFIG-02 | 非敏感运行配置编辑 | 无需修改 `.env` 即可调整常用参数 | P1 | 待完善 |
| MODEL-01 | 产品侧模型目录 CRUD | 维护可选模型及运行参数 | P0 | 已实现 |
| MODEL-02 | Xinference 模型查询与筛选 | 区分可用、已下载、运行中的模型 | P0 | 已实现 |
| MODEL-03 | 部署与停止 Xinference 模型 | 通过 GUI 管理模型实例 | P0 | 已实现 |
| MODEL-04 | 下载/加载进度与失败重试 | 清楚了解长任务结果 | P1 | 待实现 |
| MODEL-05 | 统一模型登记列表与多维筛选 | 快速定位需维护的模型记录 | P0 | 待完善 |
| MODEL-06 | 模型健康检查 | 区分“实例在运行”和“请求可用” | P1 | 待实现 |
| MODEL-07 | 来源与部署方式联动表单 | 仅展示当前模型来源所需的配置，降低误配 | P0 | 待实现 |
| LOG-01 | 对话和入库日志 | 问题追溯与运行分析 | P1 | 部分实现 |
| MONITOR-01 | 监控大屏 | 集中判断系统、模型与 RAG 链路健康度 | P1 | 待实现 |
| MONITOR-02 | 指标告警 | 在服务或资源异常前提示管理员 | P1 | 待实现 |

## 4. 页面说明

### 4.1 Chat 页面

| 项目 | 说明 |
|---|---|
| 使用者 | 知识库用户、管理员 |
| 页面内容 | 问题输入框、发送按钮、RAG 开关、回答列表、模型与耗时信息 |
| 关键操作 | 发送问题；选择是否启用 RAG |
| 结果反馈 | 显示回答、是否命中 RAG、模型名、耗时、Token；失败时显示可理解的错误说明 |

### 4.2 知识库录入页面

| 项目 | 说明 |
|---|---|
| 使用者 | 知识库用户、管理员 |
| 页面内容 | 文本编辑区、文件选择、提交按钮、处理结果 |
| 关键操作 | 提交文本或允许格式的文件 |
| 结果反馈 | 返回文档标识、Chunk 数、向量数量、使用的 Embedding 模型及版本 |

### 4.3 系统状态页面

| 项目 | 说明 |
|---|---|
| 使用者 | 管理员、开发者 |
| 页面内容 | API、PostgreSQL、FAISS、Chat、Embedding 状态卡片；检查与重建按钮 |
| 关键操作 | 手动检查 Chat / Embedding；重建 FAISS 索引 |
| 结果反馈 | 显示服务可用性、模型名称、维度、耗时及明确失败原因 |

### 4.4 运行配置页面

| 项目 | 说明 |
|---|---|
| 使用者 | 管理员 |
| 页面内容 | 当前 Chat 模型、当前 Embedding 模型、RAG 状态、非敏感配置项 |
| 关键操作 | 从模型目录选择并激活 Chat 或 Embedding 模型 |
| 结果反馈 | 成功后显示当前生效模型；切换 Embedding 时明确提示需要重建索引 |

### 4.5 模型管理页面

| 项目 | 说明 |
|---|---|
| 使用者 | 管理员、开发者 |
| 页面内容 | 模型登记主表、Xinference 运行时列表、筛选器、分页、新增/编辑弹窗 |
| 主表字段 | 名称、UUID、Code、类型、来源、部署方式、启用状态、运行状态、健康状态、当前使用、更新时间、操作 |
| 筛选条件 | 名称或 Code、类型（Chat / Embedding / Rerank / Vision）、来源（官方 API / 中转站 / 本地）、部署方式（API / Xinference / Ollama）、启用、运行、健康、当前使用状态 |
| 新增/编辑字段 | 自动生成且只读的 UUID、名称、唯一 Code、启用开关、备注、类型、来源；其余字段依来源和部署方式动态显示 |
| 表单联动 | 来源为官方 API / 中转站时，显示模型标识、Endpoint、密钥引用；来源为本地时才显示部署方式；本地 + Xinference 时显示模型选择器、已选模型摘要、Endpoint、Embedding 维度与高级运行参数；本地 + Ollama 时显示 Ollama 模型标识、Endpoint 与运行参数 |
| 关键操作 | 新增、编辑、删除、启用/停用、健康检查、设为当前；本地模型可部署/启动、停止 |
| 结果反馈 | 明确区分登记、启用、运行、健康、当前使用，以及“已下载缓存”状态；展示 Endpoint、维度和启动参数 |

### 4.6 日志页面

| 项目 | 说明 |
|---|---|
| 使用者 | 管理员、开发者 |
| 页面内容 | 对话日志、入库日志、模型运行与配置变更日志、时间和模型筛选条件；Chat 日志展示输入 Token、输出 Token、总 Token |
| 关键操作 | 按时间、请求状态、模型、操作类型查询和定位单次问题 |
| 结果反馈 | 展示输入摘要、输出摘要、模型、耗时、输入 Token、输出 Token、总 Token、Chunk 数、操作人/来源和失败原因 |

### 4.7 监控大屏

| 项目 | 说明 |
|---|---|
| 使用者 | 管理员、开发者 |
| 页面目标 | 以聚合指标、趋势图、状态卡片和告警列表判断系统整体健康度，不替代日志的单请求排障能力 |
| 刷新方式 | 页面打开时加载；默认每 30 秒刷新，可手动刷新；异常状态需醒目标记 |
| 总览指标 | 今日请求数、成功率、今日 Chat Token 消耗、在线 API 估算费用（可配置单价时）、在线用户数（具备认证后）、异常数、当前 Chat 模型、当前 Embedding 模型、GPU 显存占用 |
| RAG 指标 | RAG 开启率、检索命中率、空检索率、平均检索耗时、索引向量数、索引版本与最近重建时间 |
| 模型指标 | Chat 请求量、输入/输出/总 Token、按模型的 Token 趋势与占比、平均耗时、P95 耗时、失败率、最近健康检查时间和连续失败次数；Embedding 单独展示请求数、文本量和向量数 |
| 基础设施指标 | FastAPI、PostgreSQL、FAISS、Xinference 状态，GPU 利用率、显存占用和本地模型运行状态 |
| 知识库指标 | 文档数、Chunk 数、今日入库数、入库成功率、最近入库时间 |
| 告警列表 | 展示告警级别、对象、触发时间、当前状态、说明和跳转至相关日志的入口 |

## 5. 交互逻辑

### 5.1 文档入库

1. 用户提交文本或文件。
2. 系统保存原始文档并切分为 Chunk。
3. 系统调用当前激活的 Embedding 模型生成向量。
4. 向量写入 FAISS，文档、分块和 Embedding 版本写入 PostgreSQL。
5. 页面显示处理成功或失败结果；Embedding 不可用时，不写入不完整索引并提示用户检查服务。

### 5.2 RAG 问答

1. 用户输入问题，选择是否启用 RAG。
2. 启用 RAG 时，系统先以当前 Embedding 模型向量化问题，再从 FAISS 检索 Top-K 分块。
3. 系统将问题、系统提示词和检索上下文提交给当前 Chat 模型。
4. 页面显示回答及元数据，后台记录对话日志。
5. Chat 鉴权失败、Xinference 不可用、索引不存在等场景必须返回面向用户的错误说明，而非原始堆栈或笼统 500。

### 5.3 模型切换与索引一致性

1. 管理员在运行配置页选择模型目录中的 Chat 或 Embedding 模型。
2. 系统保存激活状态，并让后续请求使用新模型。
3. 若切换 Chat 模型，后续对话立即生效。
4. 若切换 Embedding 模型、维度或 Provider，系统标记索引需要重建并给出入口。
5. 管理员确认重建后，系统从 PostgreSQL 中的文档重新向量化并更新 FAISS。

### 5.4 模型登记、可用性与运行管理

1. 管理员创建模型时，系统自动生成 UUID；管理员填写名称、唯一 Code、类型、来源、启用状态和备注。
2. `来源` 是表单的一级分支：官方 API、中转站或本地。只有选择“本地”后，才显示必填的 `部署方式`，可选 Xinference 或 Ollama。
3. 来源为官方 API 或中转站时，表单仅展示模型标识、Endpoint 和密钥引用；密钥引用仅保存环境变量名称。
4. 来源为本地且部署方式为 Xinference 时，模型标识不允许手工填写。管理员点击“更换模型”打开 Xinference 模型库选择器，按名称、类型、引擎、下载状态筛选并选择模型。
5. 选择 Xinference 模型后，系统自动回填模型标识、模型类型、Embedding 维度、模型引擎、模型格式、量化方式和下载源到 `runtime_config`；表单显示已选模型摘要。高级区域允许管理员调整 GPU、下载源等运行参数。
6. 来源为本地且部署方式为 Ollama 时，显示 Ollama 模型标识、Endpoint 和适用运行参数，不显示 Xinference 专属字段。
7. 模型记录存在即为“登记”；启用表示允许被选择、部署或调用；运行表示本地实例已启动；健康表示实际请求测试成功；当前使用表示该模型已被选为当前 Chat 或 Embedding。
8. API 和中转站模型没有启动/停止操作，仅支持启用、停用和健康检查；本地模型支持部署/启动、停止和健康检查。
9. 删除仅删除平台内的模型登记记录，不删除 Xinference 模型缓存或本地模型文件；删除当前使用模型前必须先切换同类型模型。

### 5.5 Xinference 模型管理

1. 管理员查询 Xinference 目录，并按模型名称、参数、类型、已下载/未下载状态筛选和分页浏览。
2. 新增或编辑产品侧模型时，可保存 Endpoint、模型类型、维度及 `runtime_config`。
3. 点击部署后，后端将模型名和允许的启动参数提交给 Xinference；若模型已有缓存，复用缓存。
4. 页面轮询或刷新运行状态，显示下载、加载、运行或失败结果。
5. 停止操作仅终止运行实例，不删除本地缓存。

### 5.6 日志与监控大屏

1. 每次问答、入库、模型部署/停止、模型健康检查和配置变更均写入可查询的事件或日志。
2. 日志页面展示可追溯的单次记录，支持按时间范围、模型、请求状态和事件类型筛选。
3. 监控大屏按固定时间窗口聚合日志、状态检查和资源采集数据，展示当前值与趋势，不直接展示原始问题或密钥。
4. 当指标命中告警阈值时，大屏生成或更新告警项；管理员可跳转日志页面查看关联记录。
5. WSL2 GPU 利用率、显存、Xinference 状态由后端采集；其余业务指标从对话日志、入库日志、模型健康检查和 RAG 状态聚合。

## 6. 数据需求

### 6.1 核心数据实体

| 实体 | 核心字段 | 数据用途 |
|---|---|---|
| documents | content、source、created_at | 保存原始知识库文档 |
| chunks | document_id、chunk_text、embedding_version | 保存分块及其向量版本 |
| FAISS 索引 | vector、chunk 映射、索引版本 | 本地相似度检索 |
| llm_logs | input、output、model、input_tokens、output_tokens、total_tokens、latency、rag_enabled | 对话追溯与运营分析 |
| model_pricing | model_id、input_token_price、output_token_price、currency、effective_at | 在线 API / 中转站模型的 Token 单价与费用估算 |
| model_configs | id（UUID）、model_key（Code）、display_name、model_type、source、deployment_type、model_name、endpoint、credential_ref、dimension、enabled、is_active | 模型登记、调用配置与当前激活状态 |
| model_configs.runtime_config | 引擎、格式、量化、GPU、下载源等 | Xinference 启动参数持久化 |
| model_runtime_status | model_id、running、healthy、checked_at、error_message | 本地实例运行状态和最近健康检查结果 |
| metric_snapshots | metric_name、value、dimensions、observed_at | 时间序列监控指标快照，可按模型、服务和状态维度聚合 |
| alerts | alert_key、level、status、first_seen_at、last_seen_at、message | 活跃和历史告警，关联相关对象或日志 |

### 6.2 数据规则

- Embedding 模型、向量维度、Embedding 版本与 FAISS 索引必须一致。
- `.env` 保存密钥和启动默认值；数据库只保存非敏感运行配置和模型元数据。
- API Key、数据库连接串不得通过 API 返回给浏览器，也不得写入模型目录。
- 激活的 Chat / Embedding 模型在 API 重启后应可恢复。
- 删除模型目录前必须校验其不是当前激活模型；停止模型不得删除 Xinference 缓存。
- `model_key`（Code）必须唯一且稳定；UUID 由后端生成，不允许前端提交或修改。
- 密钥只可通过 `credential_ref` 引用环境变量名，禁止保存密钥实际值。
- 当 `source` 为 `official_api` 或 `gateway` 时，`deployment_type` 固定为 `api`；当 `source` 为 `local` 时，`deployment_type` 必填且仅允许 `xinference` 或 `ollama`。
- Xinference 模型的 `model_name`、`dimension` 和 `runtime_config` 默认来自 Xinference 模型目录；管理员仅在高级配置中修改允许覆盖的运行参数。
- 日志保留完整内容应遵循留存策略；监控指标默认仅保存聚合值、摘要、长度和脱敏维度。
- 监控趋势数据以固定窗口聚合，避免监控大屏直接查询全量业务日志。
- Chat Token 必须拆分保存输入、输出与总量；总量应等于输入与输出之和。模型未返回 Token 时，字段可为空并标注为“未提供”。
- 仅在线 API 或中转站且配置单价的 Chat 模型计算估算费用；本地模型仅统计 Token 消耗，不计算费用。
- Embedding 不与 Chat Token 混合统计，应单独记录请求数、输入文本长度或 Token（服务可提供时）、向量数和耗时。

## 7. 埋点需求

埋点用于产品使用分析和故障定位，不记录用户原始密钥；问题和文档内容默认只存摘要、长度或脱敏标识，完整内容仅按日志留存策略保存。

| 事件名 | 触发时机 | 核心属性 | 指标用途 |
|---|---|---|---|
| `chat_submit` | 用户发送问题 | rag_enabled、chat_model、question_length | 问答量与 RAG 使用率 |
| `chat_result` | 问答结束 | success、latency_ms、token_count、rag_hit_count、error_code | 成功率、耗时、检索命中率 |
| `chat_token_usage` | Chat 请求结束 | model_id、input_tokens、output_tokens、total_tokens、estimated_cost | Token 消耗与在线模型费用分析 |
| `embedding_usage` | Embedding 请求结束 | model_id、request_count、text_length、input_tokens（可选）、vector_count、latency_ms | Embedding 使用量与性能分析 |
| `ingest_submit` | 提交资料 | source_type、content_length、embedding_model | 入库量与来源分布 |
| `ingest_result` | 入库结束 | success、chunk_count、vector_count、latency_ms、error_code | 入库成功率与性能 |
| `embedding_check` | 执行服务检查 | model、dimension、latency_ms、success | Embedding 健康度 |
| `reindex_result` | 索引重建结束 | success、document_count、vector_count、latency_ms | 索引重建成功率与耗时 |
| `model_switch` | 激活模型 | model_type、from_model、to_model、success | 模型切换频次和失败率 |
| `model_deploy_result` | 部署结束 | model_name、model_type、cached、success、latency_ms、error_code | 下载/部署成功率与缓存复用率 |
| `model_stop_result` | 停止结束 | model_name、success、latency_ms | 模型实例管理情况 |
| `model_health_check` | 模型健康检查结束 | model_id、source、provider、success、latency_ms、error_code | 模型真实可用率 |
| `model_config_change` | 新增、编辑、启停或删除模型登记 | model_id、action、model_type、source、provider、success | 模型配置变更审计 |
| `monitor_snapshot` | 采集监控指标 | metric_name、value、dimensions、observed_at | 大屏趋势和容量分析 |
| `alert_state_change` | 告警创建、恢复或升级 | alert_key、level、from_status、to_status | 告警治理与故障回顾 |

## 8. 验收标准

### 8.1 P0 验收

- 完成“上传文档 → 本地 BGE 向量化 → FAISS 检索 → Chat 回答”的闭环。
- Chat 页面可在启用/关闭 RAG 两种模式下完成问答，并明确显示失败原因。
- 管理员可在页面选择并激活 Chat 与 Embedding 模型。
- 切换 Embedding 模型、维度或 Provider 后，系统明确提示并可执行索引重建。
- 模型管理可按名称、参数、下载状态查询 Xinference 模型，支持分页，并可区分缓存和运行状态。
- 模型登记主表支持按名称/Code、类型、来源、部署方式、启用、运行、健康和当前使用状态筛选。
- 新增模型时由后端生成 UUID；Code 唯一；密钥仅以环境变量引用形式保存和展示。
- UI 明确区分登记、启用、运行、健康、当前使用状态；API/中转站模型不展示启动或停止操作。
- 模型表单随来源动态切换字段：官方 API / 中转站不展示部署方式；本地模型必须选择 Xinference 或 Ollama；Xinference 专属字段不在其他分支显示。
- 选择 Xinference 模型后，模型标识、类型、维度、引擎、格式、量化和下载源自动回填；普通表单中不可手工修改模型标识。
- 管理员可部署或停止模型，已缓存模型部署时可复用缓存。
- 日志页面可按时间、模型、事件类型和状态定位单次问答、入库、模型或配置问题。
- 单条 Chat 日志可展示输入 Token、输出 Token 和总 Token；Token 不可用时明确标记“未提供”。
- 监控大屏可展示总览、RAG、模型、基础设施和知识库指标的当前值及趋势，并可跳转关联日志。
- 监控大屏展示今日 Chat Token 消耗、按模型的 Token 趋势/占比；仅对配置单价的在线 API 或中转站模型展示估算费用。Embedding 请求量、文本量和向量数独立展示。
- 以下告警至少可触发并展示：Chat 或 Embedding 连续 3 次健康检查失败、Chat 失败率超过 5%、Embedding 失败率超过 2%、P95 问答耗时超过 15 秒、FAISS 索引缺失或版本/维度不一致、GPU 显存超过 90%、PostgreSQL 不可连接、当前本地模型未运行。
- 无效 Chat API Key、Xinference 未启动、Embedding 未加载等问题不会向前端暴露 Python 堆栈。

### 8.2 P1 验收

- 文件入库显示可追踪的处理结果和 Embedding 版本。
- 回答展示模型、耗时、Token 和 RAG 命中信息。
- 模型下载与加载显示进度、失败原因，并支持重试。
- 管理员可从 Xinference 模型目录一键导入常用模型，自动预填推荐参数。
- 非敏感运行配置可通过 GUI 修改并持久化；密钥始终不可见。
- 本地 Chat 模型可替换默认在线 Chat 模型，且不改变既有 RAG 调用链。

## 附录 A：技术实现边界

当前部署边界为：Windows 运行 Vue 与 FastAPI，Docker 运行 PostgreSQL，WSL2 运行 Xinference；FAISS 由后端本地持久化。当前本地 Embedding 使用 `bge-base-zh-v1.5`（768 维），默认 Chat 可使用在线 API，后续可部署本地 Qwen 7B GGUF 等模型。

后端负责 RAG 编排、模型目录 CRUD、模型激活和 Xinference API 代理；Xinference 负责模型下载、缓存、启动和停止。模型下载/加载属于长任务，后续应采用可查询状态或轮询机制，而不是阻塞页面请求。

## 附录 B：版本规划

| 版本 | 范围 |
|---|---|
| 已完成 | 基础 RAG、状态检查、索引重建、WSL2 Xinference BGE、模型目录、模型切换、Xinference 查询/部署/停止 |
| P1 | 模型下载进度与重试、一键导入、运行配置 GUI、日志完善、本地 Chat 模型、管理员权限与操作审计 |
| P2 | Vision/YOLO、多 Provider 路由、可选集中式向量库、多用户和部署自动化 |
