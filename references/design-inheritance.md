# 设计实现与视频交接

## 职责与优先关系

creative.md 的整片策划是唯一内容计划。设计必须进入随附 `design/guizang-social-card/SKILL.md`，使用原版式配方、字体组件、主题、种子模板及校验器实现这个计划；不只摘取几个风格词，也不重新按图文篇幅另排一套视频故事。

原版以独立阅读的社交卡为主要场景；用于本用户的视频时，以下边界优先：

- 视频的幕数、信息取舍与时长按 creative.md，不把图文章节数或字数对应的页数当视频要求。
- 已有用户授权为自主 image2 配图，不重复执行选图来源提问；外部提示词模式仅在用户明确选择或工具不可用时使用。图像规则统一见 visual-planning.md。
- 视频的页眉页脚、字幕留白及图文关系按 visual-planning.md，不照搬装饰元数据条。密度 advisory 不能驱使添加重复文字；可调整真实视觉主体或换版式，也可记录有观看节奏依据的留白理由。实际溢出和不可读内容仍须修复。
- 静态技术核验属于本项目已授权流程，不另问是否可以运行自动检查；用户实际稿件/音频/整片反馈仍按主流程保留。
- 新义合成公司片尾用 brand-outro.md 的固定组件，这是用户指定模板，不重新设计或选片尾版式。

以上只明确视频适配范围，不修改上游快照。`references/upstream/` 是历史兼容资料，不是另一个设计入口。

## 视频适配契约

视频复用 social card 的两套核心风格和主题：Editorial Magazine × E-ink 或 Swiss International。可以按项目选择多个主题和 recipe，但一条视频内部默认保持一种主风格。3:4 先使用原 seed/template 与 M/S recipe 语义；16:9、9:16、4:3 需要对应的几何适配，不能把 3:4 输出盲裁。

每个场景应能在 manifest 或 plan 中定位 `style_mode`、`theme`、`ratio`、`recipe`、`focal_point`、`subtitle_safe_area` 和 `motion`。这组字段由 `references/video-scene-contract.json` 提供起点，缺少 recipe 的自由排版不得进入正式渲染。轻动效只在静态设计通过后执行。

## 用户页面预览门

`output.png` 生成后先运行 `python scripts/show_design_previews.py P --scenes s01`，把输出中的绝对 PNG 路径逐页展示给用户，并等待用户明确反馈。每页默认状态为 `pending_user_review`；技术校验通过、主 Agent 看过或 worker 报告成功都不能代替用户确认。

用户批准后运行 `python scripts/record_preview_review.py P --manifest <manifest> --status approved --reviewer <name> --notes <feedback>`；用户要求修改时记录 `changes_requested`，保留旧 PNG、manifest 和哈希，再只重做受影响页面。任何页面处于 pending、changes_requested 或 rejected，都不能进入轻动效、旁白字幕或正式视频导出。

worker 可以负责页面 PNG、contact sheet、尺寸/溢出/哈希和 manifest；主 Agent 必须负责把页面展示给用户、解释反馈、决定是否改 recipe，并验收整组页面。worker 的 mechanical checks 与 human/user review 分开记录。

## 静态交付

先实际读取原 SKILL 及当前阶段引用：风格/主题看 style-system、theme-presets，选版看 layout-recipes，字体与比例看 components、portrait-fill；制作时看 production-workflow，文字叠图时看 image-overlay，交付前看 qa-checklist。引用均相对于原设计目录。中英文共用这一入口，不从中文旧项目提取另一套制作模板，也不以几个“Swiss”风格词代替原流程。

选好风格和配方后，在项目 design/<page>/ 复制原种子。可用下列命令，S06 仅是示例，配方必须按当前内容选择：

```powershell
python scripts/create_design_page.py P --scene s01 --style swiss --recipe S06 --reason "用原流程版式解释本幕的作用关系"
```

命令原样复制种子及其本地背景依赖，记录入口/种子哈希和选择理由，不覆盖已有目录，不改 project.json、不生成设计批准。它只完成起点，不会选择内容或自动制作完成。按原配方填写 index.html，保留原字体/组件/主题，按原生产流程将字体和外部资源本地化；自定义 CSS 仅用于项目中的必要适配。将完成的设计路径或 PNG 接入场景；仅填写 plan 的 seed 字段不能证明视觉继承成立。固定片尾仍走 brand-outro.md 的 create/attach 工具。

生成 output.png 后先单独查看，再运行本技能包装的原校验器。该入口不改 upstream 规则，增加检查覆盖数量和绑定 HTML 的 JSON 证据：

```powershell
node scripts/run_design_validator.cjs P/design/s01/index.html --style=swiss --expected-pages=1 --report=P/review/validator-s01-v1.json
python scripts/design_review.py P --scene s01 --png design/s01/output.png --validator-report review/validator-s01-v1.json
# 实际查看 PNG、读取原 qa-checklist 和校验报告后，填写生成的 pending 记录。
python scripts/design_review.py P --scene s01 --import-report review/design-review-s01-<版本>.json
```

Node 依赖按环境设置 NODE_PATH。单幕设计默认要求恰好 1 个 section.poster；多页 HTML 明确传实际预期页数。0 页、数量不符、原规则 FAIL 或检查期间 HTML 变化都失败，报告不覆盖旧版本。不能直接调用原脚本的“0 fails”绕过覆盖检查。WARN 须依据实际图像记录处理理由，不能凑内容填密度。逐幕导入设计审核使用该幕独立 HTML 的 1 页报告；若视频壳仅接 PNG，校验对象仍是生成 PNG 的设计 HTML。

交审前逐幕核对：plan 中的原配方与实际结构、原字体/主题与实际样式、PNG 的主体与手机可读性、原校验覆盖结果及 WARN 理由、所有场景的 design-review 记录。缺失或失败先修复，不把“视频预检无字幕溢出、可以解码”称为设计通过。技术校验不会判断审美，也不能证明模型真实执行了阅读动作。

准备命令填写 scene、content_key、files 哈希，status=pending、viewed=false；带 --validator-report 时绑定原校验 JSON 与设计 HTML，导入/导出会重验报告覆盖和文件身份。旧审核记录保持兼容，新制作使用带报告的命令。实际审阅后填写 reviewer、observed，并据实设 viewed=true / status=pass；可保留原模板/入口哈希、校验结果与 WARN 理由等字段。导入复制到新 `.history/` 版本并设置 scenes[].design_review。内容有变重新准备；不能手改 content_key 使旧结论冒充新审阅。需要撤销时可将带实际观察结论的 rejected 记录通过同一命令导入为新版本，旧证据保留，正式导出会阻断。

正式导出会重验该记录及 PNG 哈希、素材语义结论，审核字节变化会失效 QA；技术记录不证明作者真的看过，也不代替内容判断。现有历史项目不自动补写 pass。

## 视频交接

静态页优先直接接入原 PNG；画面文件、颜色、字体和排版不再由视频层重建。静态 PNG 与相同时间下的视频画面应一致，独立字幕层除外。若设计采用局部动画，由同一 DOM 的 renderAt 接口控制，核对静态与动态对应关系。

将 HTML、图片、字体与依赖写入项目，遵循 project.md；字幕区域及固定片尾的覆盖样式同样保留。播放器与导出都在场景 DOM 注入同一 caption_css / #vp-caption 字幕层，场景覆盖样式在两者中一致生效。先完成视觉查看再渲染视频，禁止同一个工具调用先返回截图、未查看就启动视频生产。

设计变更重查对应场景并更新哈希，不覆盖已确认历史版本，不因仅换布局重做未变旁白。当前工作区的其他任务项目不因 Skill 修改自动重写。

发布封面独立按 short-video-cover-title.md 交付，不把封面当作视频场景交接入口。
