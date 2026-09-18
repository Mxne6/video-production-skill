# 面向低成本模型的重复生产

目标是让 Luna max 等目标执行模型依靠模板、明确输入和现成命令完成生产，而不是要求更强模型临场补代码。目标模型与推理档位由用户选定；本文件不切换模型，也不自动调用更贵的模型。不同模型实际效果必须实跑验证。

## 使用范围

日常生产按 SKILL.md 的阶段入口，不在这里维护另一份制作步骤。工具默认服务用户选定模型，不暗中升级；模板、稳定输入输出与可定位错误优先。复现验证和接口故障才继续读下文。

## 常见失败的处理

| 现象 | 处理 | 复用 |
|---|---|---|
| 字幕下载失败 | 已有 response.raw.json 时 recover；不要重发TTS | 已付费音频 |
| 未知时间戳格式 | 留存原始响应，报告字段与最小样本，补明确适配 | 已付费音频 |
| 原文与读音不同 | 检查 word_begin/end 映射；不忽略词语差异 | 原始时间戳 |
| Beat前缀错误 | 从原文复制实际前缀，不改旁白凑节拍 | 音频与稿件批准 |
| 字幕过宽/遮挡 | 改切片或字幕安全区后再检查 | 音频与音频批准 |
| 新项目难以选版式 | 回到原版式配方和内容目的，提供少量静态候选 | 已核实来源 |

## 任务分层：把机械工作交给低成本 worker

优先使用 L0 确定性脚本完成文件枚举、哈希、素材尺寸、PNG/HTML 渲染、contact sheet、溢出和契约校验。L1（例如用户选择的 Luna 等低成本模型）只处理主 Agent 已锁定的 scene contract：局部 HTML/CSS 填充、指定素材替换、批量页面渲染、机械修复和 manifest 整理。

主 Agent 保留材料理解、旁白与故事结构、风格/主题/recipe、主体裁切、跨页面连续性、版权和事实判断、逐页预览、用户确认、异常修复策略、正式音频试听与最终交付。不得自动升级模型；worker 的机械通过不能写成视觉或听感通过。

每个 worker 任务记录 `task_id`、`task_type`、`model_tier`、`assigned_model`、`actual_model`、`reasoning_effort`、实际用量来源、输入/输出哈希、重试和 `interventions`。运行时没有 token/耗时数据时写 `unavailable`，不能用估算冒充实测。主 Agent 或强模型改过 worker 产物后，`independent_reproduction=false`。

标准状态为：`planned → mechanical_in_progress → previews_ready → primary_review_pending → user_review_pending → approved_for_motion → rendered → delivered`。任何页面未展示或未获用户明确批准，都不能进入 `approved_for_motion`。

参考契约见 [低成本 worker 任务分层](model-task-routing.md) 和 [worker 输入输出样例](worker-task-contract.json)。

## 如何证明目标模型能用

新建隔离验证项目，使用另一份真实材料，只给目标模型技能、材料和规格，不能暗中提供本片成品答案。记录执行模型/档位、token或实际可见用量、外部付费调用次数、人工纠正次数、故障和交付结果。高成本模型介入修复必须记作介入，不能算目标模型独立通过。

验收包括来源可追溯、原模板视觉质量、配音与字幕、有效MP4、暂停续作、局部修改复用。先完成当前整条流程，再用目标模型验证新材料。单元测试通过或一条由强模型修过的样片不能证明低成本模型能独立稳定生产。

## 独立验证记录

另一份真实材料与目标执行模型明确后，在隔离项目复制 `assets/production-run.json`。该模板默认所有结果未知，不能提前填写通过。记录实际 model、reasoning_effort；usage 为 `{status: "recorded", evidence: "实际用量及来源"}`，若不可见则为 `{status: "unavailable", evidence: "不可见原因"}`，不能估算为实测。paid_calls 记录真实付费调用次数，interventions 记录人工或其他模型的纠正；正常稿件/音频审核与纠正分开描述。checks 每项用状态、证据文件相对路径及 SHA256 绑定实际产物。resume 与 local_edit_reuse 必须有前后状态、产物哈希或 journal 对照。

运行 `python scripts/check_production_run.py P/production-run.json`，只检查证据完整性，结果为 evidence_complete / incomplete / assisted_or_reused，并明确 independence=not_verified；不得把 evidence_complete 写成目标模型独立生产通过。它不能代替设计/听感审核，也不能认证自报模型或无介入。材料重复、模型介入、缺少证据不算独立通过。工具修复由当前模型完成，须与新材料目标模型实跑分开报告。新材料未提供时完成模板和离线技术验证，报告独立实跑仍待材料；不暗中代替目标模型生产。

## 网络连接阻断

WinError 10013 等连接级错误先用不带密钥、不计费的 TCP/HTTPS 探测，比较受限与获准执行环境。只有对照证据支持才能归因于执行权限；不直接建议关闭防火墙。按运行环境提供的权限机制请求外网执行，不在脚本内绕过限制。连接修复后再发已批准范围的请求；有响应先恢复，不盲目重试，不未经账单核实声称未扣费。
