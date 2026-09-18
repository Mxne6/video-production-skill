---
name: video-production
description: 从产品名称、资料或文章制作中文、英语或法语讲解视频；从公司知识库检索，按目标时长策划，使用 HTML 与 image2 配图、MiniMax 旁白、真实时间戳字幕、固定公司片尾及背景音乐，交付 MP4、封面和标题。支持暂停续作与局部修改。
---

# 中英法视频生产

负责从材料到可播放 MP4 的完整流程。项目放在工作区 `projects/<slug>/`；Skill 只保存可复用工具、模板和资产。恢复已有项目先读当前状态并运行 `scripts/studio.py status P`，以实际文件与依赖为准，不从聊天记忆猜审批。

英语或法语制作先读 [语言版本](references/languages.md)。中文和英文是两个独立制作项目：共用引擎、视觉系统和设计方法，但不复制中文项目的稿件、分幕、scene HTML、语言相关图片、音频或审批。默认不得把已完成的中文视频页面逐页翻译成英文；英文必须从原始资料重新编写和新建设计。

## 核心设计原则

视频不是“先判断 scene 类型，再把内容填进模板”。新义合成竖版正文默认走 [内容优先构图系统](references/composition-system.md)：

1. 先确定本幕观众要理解什么、第一眼看什么、什么由旁白承担；
2. 再判断视觉主角是图片、产品、数字、关系、过程还是一句话；
3. 根据时长确定画面能承载的 attention stops；
4. 再决定构图、图片占幅、留白、文字层级和 reveal；
5. 最后才实现 HTML，并与前后 scene 一起检查整片视觉节奏。

`opening / product-hero / mechanism / proof-data / application / summary` 六个旧结构继续保留，供兼容旧项目或内容确实吻合时作为 starter；它们不再是新场景的语义路由规则。不能仅因为“这是数据幕”就选择 `proof-data`，也不能仅因为“这是应用幕”就选择 `application`。

## 按当前阶段读取与执行

1. **资料与规格**：用户只给产品名称时，按 [知识库检索](references/product-knowledge-base.md) 找原始资料，不先让用户重复上传。核对观众、画幅、用途和目标时长；保留来源。用户当前要求优先，已有明确规格直接沿用。已知时长写入 duration；新义合成建项使用 `--preset xyzchem`。字段与失效规则见 [项目契约](references/project.md)。
2. **一次策划**：读 [内容策划](references/creative.md)，一起确定故事、幕数、每幕画面与旁白、配图任务和预计时长。先解决内容与时长，不在这里提前锁版式。每幕写清 `intent`、`visual_plan` 和旁白/画面分工。新义合成视频首次分镜即纳入 [固定片尾组件](references/brand-outro.md)，正文正常创作，片尾不另写一稿。
3. **逐幕设计 brief**：读 [内容优先构图系统](references/composition-system.md)，完成 `scenes[].design`。至少明确 `message / viewer_task / dominant / attention_order / on_screen / narration_only / image_role / visual_share / density / intensity / composition_reason`。先写这些，再决定 `layout_family` 与 `layout_signature`。如果换一款产品仍可原样沿用同一 layout signature，说明构图还没有被内容真正决定。
4. **视觉实现**：读 [视觉与素材](references/visual-planning.md) 与 [设计交接](references/design-inheritance.md)。新 scene 默认 `python scripts/create_video_scene.py P --scene s02`，得到低预设的 `adaptive` seed；只有内容本身与旧 starter 高度吻合时才显式传 `--type mechanism` 等。模板和 CSS 只提供 visual tokens、字体、网格与 primitive，不替 Agent 决定几何。图片先确定其在构图中的角色和占幅，再确定最终比例与尺寸；禁止先拿一张图再硬塞进预留容器。先静态渲染、查看全尺寸与缩略图、比较相邻 scene，再接动画。
5. **整片节奏检查**：正文 scene brief 都 ready 后运行 `python scripts/scene_design.py P`，再用 `python scripts/visual_review.py P --render` 生成预览与自动 `contact-sheet.png`。连续三幕出现同一 `layout_signature` 默认视为失败，除非重复本身承担明确的比较/连续性任务并写 `continuity_reason`。不要为了变化而轮换版式；变化必须来自故事中视觉主角、密度、强度或媒介的变化。
6. **声音**：按 [运行与声音](references/runtime.md) 使用已有声音偏好；未要求更改时用其中的用户默认值，不重复选声。完整稿件确认后，正文和片尾在同一正常流程中逐段合成；不导入或复用固定片尾录音。保存原请求、音频及真实时间戳，未知结果先查记录，不盲目重发付费请求。
7. **字幕与整片**：新音频经用户试听确认后，按真实词边界生成单行字幕。需要背景音乐时按 [项目音乐](references/project-music.md) 准备多条候选，先试听，再随机或按用户指定选定，最后由 studio 正式导出统一混音。检查实际画面、字幕同步、声音衔接和实测总时长；技术检查不能冒充听感、内容或设计通过。
8. **交付**：输出 MP4、SRT、WAV 和版本/来源记录；发布时按 [封面与标题](references/short-video-cover-title.md) 同时交付 image2 封面与标题。生产导出须符合当前有效审核，历史版本不覆盖。
9. **生产记录**：确定产品或语言后先按 [生产记录](references/production-registry.md) 查重；正式导出成功后立即登记实际导出文件。记录表回答“该产品中文/英文是否做过”，不是草稿、试听或未导出项目的替代品。

## 视觉判断的硬要求

- 一幕只有一个主导信息。图片是主角时，图片应真正决定画面的比例、文字位置与负空间；数字是主角时，不把它缩进 metric card；关系是主角时，让关系本身形成空间结构；一句话是主角时，不为了“丰富”补小图、标签和卡片。
- 画面文字不是旁白全文的字幕版。短时长 scene 通常只有 1–3 个 attention stops，其余解释交给旁白。
- 留白必须有任务：保护主体、隔离数字、形成安静节奏、给字幕让位或强化尺度。剩下没东西放的区域不叫 Editorial 留白。
- Guizang 的继承重点是 hierarchy、typography、asymmetry、grid、image-as-evidence、克制配色和“越大越轻”的字重关系，不是把 M/S recipe 或 social-card chrome 搬进视频。
- Swiss 不默认变成 Dashboard；Editorial 不默认变成“米色纸 + serif 标题”。少用容器，多用尺度、对齐、规则线、列、图像和真实空间关系建立层级。
- Motion 只负责引导注意力或表达状态变化，不能拯救静态构图。静态 PNG 不成立时不得进入正式动画渲染。

## 一致的协作边界

- 首轮集中给稿件、分镜、代表画面及总时长；不机械逐幕审批。沿用未变化内容的有效确认，修改只更新实际受影响部分。画面、旁白、字幕和音乐各自的确认不能互相替代。
- `project.json` 为项目编辑源，`state.json` 保存产物引用，`.history/` 保存不可覆盖的版本证据，`journal.jsonl` 记录操作。程序不会产生用户授权。缺项时完成独立准备并记录下一步，不把占位、缺图或待试听产物称为完成。
- 继续制作不等于修改工具。工具以工作区 Skill 为权威源码，修改后同步安装版；原 social card 快照与 upstream 不修改。现有项目不因规则更新自动改版。
- 新义合成 `1080×1440` 新项目使用 content-first design contract + `adaptive` seed；六个命名 starter 保留兼容。generic `1920×1080` 项目继续使用 `assets/scene.html`，不虚称已拥有同等自适应竖版设计系统。
- 默认模型由用户选择，不自动升级。独立模型基准不进入日常生产入口；测试项目必须标明 test_mode，测试音轨和模拟批准不能进入正式项目。
