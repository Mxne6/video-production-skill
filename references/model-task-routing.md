# 低成本 worker 任务分层

本文件把“机械执行”和“全局判断”拆开。它不自动切换模型，也不把低成本模型的技术通过写成整片质量通过。

## L0：确定性脚本

优先交给脚本，不消耗模型：

- 复制 Guizang seed/template；
- 按 manifest 生成页面目录；
- 图片尺寸、文件名、哈希和依赖登记；
- PNG/HTML 渲染；
- overflow、最小字号、页面数量、比例字段校验；
- 缩略图、contact sheet、SRT/媒体格式转换；
- 预览清单和 provenance 生成。

## L1：低成本模型

只有在主 Agent 已锁定输入后才委派：

- 按已确定的 scene contract 填写局部 HTML/CSS；
- 替换已指定的图片路径；
- 处理已明确的文字换行、字号微调和间距微调；
- 根据错误报告做 1–40px 级别的机械修复；
- 批量渲染多个页面并返回结构化结果；
- 生成页面 PNG、contact sheet 和失败清单；
- 把字幕、图片和 recipe 字段整理到既定 manifest。

L1 不得自行：

- 选择风格、主题或 recipe；
- 改写旁白、改变故事顺序或增加事实；
- 自行换图、改变主体裁切或判断版权；
- 把页面技术检查当作审美通过；
- 自动升级到更贵模型；
- 越过用户预览确认继续正式视频渲染。

## P：主 Agent

主 Agent 保留：

- 材料理解、内容策划和整片结构；
- 每幕的 role、style、theme、ratio、recipe 和素材任务；
- 主体位置、裁切优先级、证据真实性和版权判断；
- 跨页面节奏、密度和风格连续性；
- 调度 worker、读取结构化输出、处理异常；
- 每页预览展示、用户反馈解释和最终验收；
- 正式旁白试听、字幕与整片交付决策。

## S/人工升级

只有发生以下情况，才请求强模型或人工介入，并在记录中写明：

- worker 连续失败或无法定位错误；
- 需要重新选择 recipe、风格或构图；
- 主体、截图、事实或版权判断有歧义；
- 用户对页面提出需要重新设计的反馈；
- 正式音频试听、整片节奏和最终发布判断。

## Worker 输入输出契约

每个 worker 任务必须携带：

- `task_id`、`scene_ids`、目标 `style_mode/theme/ratio/recipe`；
- 可修改范围和禁止修改范围；
- 输入文件与哈希；
- 期望输出路径；
- `actual_model`、`reasoning_effort`、usage 状态；
- 失败原因、重试次数和 intervention 记录。

worker 输出必须区分：

- `mechanical_checks`：尺寸、哈希、溢出、页面数量、文件存在性；
- `worker_output`：实际生成文件和结构化摘要；
- `human_or_primary_review`：默认 pending，不得由 worker 填 pass；
- `interventions`：主 Agent、人工或其他模型的修复。

页面 PNG 展示给用户后，状态仍是 `pending_user_review`。只有用户明确批准，才进入后续动效、旁白、字幕和正式导出。修改意见只重做受影响页面，并保留上一版文件与哈希。
