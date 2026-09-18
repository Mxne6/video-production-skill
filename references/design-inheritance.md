# 设计实现与视频交接

## 职责与优先关系

creative.md 的整片策划是唯一内容计划。视觉实现按项目类型选择入口：新义合成竖版正文使用 `templates/video/` 的可执行模板，generic 横版继续使用旧场景起点；Social card 负责封面、单页重点卡以及字体、主题和组件参考。不能把 `S06`、`M16` 等配方标签当成真实视频模板，也不能因更换主题重新编写故事。

原版以独立阅读的社交卡为主要场景；用于本用户的视频时，以下边界优先：

- 视频的幕数、信息取舍与时长按 creative.md，不把图文章节数或字数对应的页数当视频要求。
- 已有用户授权为自主 image2 配图，不重复执行选图来源提问；外部提示词模式仅在用户明确选择或工具不可用时使用。图像规则统一见 visual-planning.md。
- 视频的页眉页脚、字幕留白及图文关系按 visual-planning.md，不照搬装饰元数据条。密度 advisory 不能驱使添加重复文字；可调整真实视觉主体或换版式，也可记录有观看节奏依据的留白理由。实际溢出和不可读内容仍须修复。
- 静态技术核验属于本项目已授权流程，不另问是否可以运行自动检查；用户实际稿件/音频/整片反馈仍按主流程保留。
- 新义合成公司片尾用 brand-outro.md 的固定组件，这是用户指定模板，不重新设计或选片尾版式。
- 竖版视频原生模板提供六类可选结构：`opening` 开场结论、`product-hero` 产品主体、`mechanism` 机理关系、`proof-data` 数据证据、`application` 应用场景、`summary` 正文结论。
- 模板只决定初始结构与信息关系，主题决定 visual tokens；每幕仍需按内容重新组织构图。模板类型不是幕数清单，可跳过或复用。常规改版优先换主题、换图片或选择更合适的模板，不累计创建几十个近重复配方。

以上只明确视频适配范围，不修改上游快照。`references/upstream/` 是历史兼容资料，不是另一个设计入口。

## 竖版视频原生模板

只有 `1080×1440` 新义合成项目进入此入口。初稿必须复制真实模板，不得手工从空白 HTML 复制一套近似结构：

```powershell
python scripts/create_video_scene.py P --scene s02 --type mechanism
```

项目级视觉系统在建项时固定，例如 `studio init P --preset xyzchem --style swiss --theme ikb`。一个项目只能使用一个 social-card 模式和一个官方 palette，后续场景继承，不逐幕混搭。Swiss 可选 `ikb / lemon-yellow / lemon-green / safety-orange`；Editorial 可选 `ink-classic / indigo-porcelain / forest-ink / kraft-paper / dune / midnight-ink`。命令从 Skill 原始模板复制 HTML 和共享 CSS/JS，写入模板语言、模式、主题、尺寸和哈希到 `scenes/<scene>/plan.json`，并追加到固定片尾之前。英文项目必须通过该入口新建自己的场景，不得复制中文项目的 scene 后翻译文字；模板类型、scene id 和顺序由英语稿独立决定，幕数不受六类模板数量约束。模板选择按信息任务而不是装饰偏好：产品主体看 `product-hero`，过程与因果关系看 `mechanism`，数字与对比看 `proof-data`，使用场景看 `application`，正文收束看 `summary`。已有场景内容变化时使用新 scene ID 或明确的局部改版流程，不覆盖历史证据。

填写模板时保留 `window.renderAt(t,duration)` 确定性接口，但默认网格、字号层级、空白图槽和标题句式只是起点，不是成品。必须根据本幕内容重新组织构图，删除空证据条、内部说明、重复标题和无效留白；只替换占位文字不算完成。把图片和字体写入项目并声明依赖，图片原图比例必须与最终图槽一致。`data-mode` 固定为 `swiss` 或 `editorial`；Swiss 按 social card 使用 `data-accent`，Editorial 使用 `data-theme`，值均取官方 palette。不得引入当前 package 外的 accent 或另一套字体。Social card 的 style-system、components、theme-presets 和 qa-checklist 是视觉权威，模板只复用其 token 和组件，不重写视觉体系。

静态交付需要 1080×1440 PNG，并实际查看主体、文字、图片和字幕安全区。视频原生模板没有 `section.poster`，不运行 social card 的覆盖率校验器；审核直接绑定当前场景 HTML、PNG 和实际观察记录：

```powershell
python scripts/design_review.py P --scene s02 --png scenes/s02/output.png
# 实际查看 PNG 后填写 pending 记录，再导入。
python scripts/design_review.py P --scene s02 --import-report review/design-review-s02-<版本>.json
```

固定片尾仍走 brand-outro.md 的 create/attach 工具。generic `1920×1080` 项目继续使用 `create_design_page.py` 和原 `section.poster` validator，不套用这套竖版尺寸门禁。

## Social card 单页与封面

当场景明确使用 social card 种子或单页卡片时，生成 output.png 后先单独查看，再运行本技能包装的原校验器。该入口不改 upstream 规则，增加检查覆盖数量和绑定 HTML 的 JSON 证据：

```powershell
node scripts/run_design_validator.cjs P/design/s01/index.html --style=swiss --expected-pages=1 --report=P/review/validator-s01-v1.json
python scripts/design_review.py P --scene s01 --png design/s01/output.png --validator-report review/validator-s01-v1.json
# 实际查看 PNG、读取原 qa-checklist 和校验报告后，填写生成的 pending 记录。
python scripts/design_review.py P --scene s01 --import-report review/design-review-s01-<版本>.json
```

Node 依赖按 runtime.md 安装到随附设计目录，包装入口会从该目录解析本地 Playwright；只有自定义安装位置时才设置 NODE_PATH。单幕设计默认要求恰好 1 个 section.poster；多页 HTML 明确传实际预期页数。0 页、数量不符、原规则 FAIL 或检查期间 HTML 变化都失败，报告不覆盖旧版本。不能直接调用原脚本的“0 fails”绕过覆盖检查。WARN 须依据实际图像记录处理理由，不能凑内容填密度。逐幕导入设计审核使用该幕独立 HTML 的 1 页报告；若视频壳仅接 PNG，校验对象仍是生成 PNG 的设计 HTML。

交审前逐幕核对：plan 中的原配方与实际结构、原字体/主题与实际样式、PNG 的主体与手机可读性、原校验覆盖结果及 WARN 理由、所有场景的 design-review 记录。先直接看 PNG，确认每幕有单一主导信息、图文层级清楚、图片完整可见、没有空图槽或内部说明、没有把同一长标题重复放进图片和 HTML，也不需要靠大面积空白撑版面；任何一项成立都重新设计，不能因预检无报错而放行。缺失或失败先修复，不把“视频预检无字幕溢出、可以解码”称为设计通过。技术校验不会判断审美，也不能证明模型真实执行了阅读动作。

准备命令填写 scene、content_key、files 哈希，status=pending、viewed=false；social card 路径带 --validator-report 时绑定原校验 JSON 与设计 HTML，视频原生模板路径直接绑定当前 HTML 与 PNG。导入/导出会重验报告覆盖和文件身份。旧审核记录保持兼容。实际审阅后填写 reviewer、observed，并据实设 viewed=true / status=pass；可保留原模板/入口哈希、校验结果与 WARN 理由等字段。导入复制到新 `.history/` 版本并设置 scenes[].design_review。内容有变重新准备；不能手改 content_key 使旧结论冒充新审阅。需要撤销时可将带实际观察结论的 rejected 记录通过同一命令导入为新版本，旧证据保留，正式导出会阻断。

正式导出会重验该记录及 PNG 哈希、素材语义结论，审核字节变化会失效 QA；技术记录不证明作者真的看过，也不代替内容判断。现有历史项目不自动补写 pass。

## 视频交接

静态页优先直接接入原 PNG；画面文件、颜色、字体和排版不再由视频层重建。静态 PNG 与相同时间下的视频画面应一致，独立字幕层除外。若设计采用局部动画，由同一 DOM 的 renderAt 接口控制，核对静态与动态对应关系。

将 HTML、图片、字体与依赖写入项目，遵循 project.md；字幕区域及固定片尾的覆盖样式同样保留。播放器与导出都在场景 DOM 注入同一 caption_css / #vp-caption 字幕层，场景覆盖样式在两者中一致生效。先完成视觉查看再渲染视频，禁止同一个工具调用先返回截图、未查看就启动视频生产。

设计变更重查对应场景并更新哈希，不覆盖已确认历史版本，不因仅换布局重做未变旁白。当前工作区的其他任务项目不因 Skill 修改自动重写。

发布封面独立按 short-video-cover-title.md 交付，不把封面当作视频场景交接入口。
