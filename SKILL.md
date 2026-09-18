---
name: video-production
description: 从产品名称、资料或文章制作中文或英语讲解视频；从公司知识库检索，按目标时长策划，使用 HTML 与 image2 配图、MiniMax 旁白、真实时间戳字幕、固定公司片尾及背景音乐，交付 MP4、封面和标题。支持暂停续作与局部修改。
---

# 中英文视频生产

负责从材料到可播放 MP4 的完整流程。项目放在工作区 `projects/<slug>/`；Skill 只保存可复用工具、模板和资产。恢复已有项目先读当前状态并运行 `scripts/studio.py status P`，以实际文件与依赖为准，不从聊天记忆猜审批。

英语制作先读 [语言版本](references/languages.md)，英语音色、字幕和固定片尾按该文档执行。

Skill 设计和维护阶段的委派规则见 [Skill 维护阶段的子 Agent 分工](references/skill-maintenance-delegation.md)。主 Agent 先冻结目标、文件边界和验收标准，再把文件枚举、引用检查、测试、格式化和同步等机械任务交给低成本子 Agent；架构、审美、用户决策和最终验收由主 Agent 保留。

## 页面预览与低成本执行

页面 PNG 完成后，先按页展示给用户并等待明确的视觉反馈；页面展示不等于用户批准。默认逐页确认，只有用户明确选择批量预览时才批量展示。用户批准前不得进入轻动效、旁白、字幕或正式视频导出。展示与反馈记录使用 `scripts/show_design_previews.py` 和 `scripts/record_preview_review.py`。

机械工作优先交给 L0/L1 worker：复制 seed、按已锁定的 scene contract 填充局部 HTML、替换指定素材、批量渲染 PNG、尺寸/哈希/溢出/页面数量校验、contact sheet 和 manifest。主 Agent 保留内容策划、风格/主题/recipe 选择、主体裁切、跨页节奏、用户沟通、异常处理和最终验收。worker 不得改写旁白、换 recipe、自动升级模型或越过 review gate。详细边界见 [低成本 worker 任务分层](references/model-task-routing.md)。

## Guizang visual kernel（视频适配）

视频视觉以 [视频视觉适配层](references/video-visual-adapter.md) 为工作区契约，复用 `design/guizang-social-card` 的 style system、theme、components、image treatment 与 recipe 语义。当前默认主画幅为 3:4；16:9、9:16 与 4:3 作为比例适配接口，不能把 3:4 成品盲目裁切后交付。

每一幕在实现前必须确定 `style_mode`、`theme`、`ratio`、`recipe`、`focal_point`、`subtitle_safe_area` 和 `motion`。先渲染静态场景并完成视觉检查，再加入静态卡片轻动效、旁白和字幕。动效不得重新安排已经确认的版式层级。

## 按当前阶段读取与执行

1. **资料与规格**：用户只给产品名称时，按 [知识库检索](references/product-knowledge-base.md) 找原始资料，不先让用户重复上传。核对观众、画幅、用途和目标时长；保留来源。用户当前要求优先，已有明确规格直接沿用。已知时长写入 duration；新义合成建项使用 `--preset xyzchem`。字段与失效规则见 [项目契约](references/project.md)。
2. **一次策划**：读 [内容策划](references/creative.md)，一起确定故事、幕数、每幕画面与旁白、配图任务和预计时长。先解决内容与时长，再选版式。新义合成视频首次分镜即纳入 [固定片尾组件](references/brand-outro.md)，正文正常创作，片尾不另写一稿。
3. **视觉实现**：读 [视觉与素材](references/visual-planning.md)，依据画面任务自主调用 image2，不固定配图页码、数量、占幅或比例。中英文设计均完整执行 [原 social card](design/guizang-social-card/SKILL.md)，从其种子、配方和组件实现当前内容，不以中文旧项目或自写简化版替代；视频专用约定与原版适用边界见 [设计交接](references/design-inheritance.md)。先渲染并查看静态图，按设计交接导入当前设计审核，再接视频；不能在返回截图的同次调用里提前启动视频渲染。
4. **声音**：按 [运行与声音](references/runtime.md) 使用已有声音偏好；未要求更改时用其中的用户默认值，不重复选声。稿件确认后合成正文；固定片尾优先导入匹配的已确认通用录音。保存原请求、音频及真实时间戳，未知结果先查记录，不盲目重发付费请求。
5. **字幕与整片**：新音频经用户试听确认后，按真实词边界生成单行字幕。需要背景音乐时按 [项目音乐](references/project-music.md) 配置，由 studio 正式导出统一混音。检查实际画面、字幕同步、声音衔接和实测总时长；技术检查不能冒充听感或内容通过。
6. **交付**：输出 MP4、SRT、WAV 和版本/来源记录；发布时按 [封面与标题](references/short-video-cover-title.md) 同时交付 image2 封面与标题。生产导出须符合当前有效审核，历史版本不覆盖。

## 一致的协作边界

- 首轮集中给稿件、分镜、代表画面及总时长；不机械逐幕审批。沿用未变化内容的有效确认，修改只更新实际受影响部分。画面、旁白、字幕和音乐各自的确认不能互相替代。
- `project.json` 为项目编辑源，`state.json` 保存产物引用，`.history/` 保存不可覆盖的版本证据，`journal.jsonl` 记录操作。程序不会产生用户授权。缺项时完成独立准备并记录下一步，不把占位、缺图或待试听产物称为完成。
- 继续制作不等于修改工具。工具以工作区 Skill 为权威源码，修改后同步安装版；原 social card 快照与 upstream 不修改。现有项目不因规则更新自动改版。
- 默认模型由用户选择，不自动升级。维护工具、故障定位或验证目标模型时才读 [重复生产与验证](references/repeatable-production.md)。测试项目必须标明 test_mode，测试音轨和模拟批准不能进入正式项目。
