# 项目契约

`python <技能目录>/scripts/studio.py init <项目目录>` 生成起点；新义合成使用 `--preset xyzchem`，直接建立 1080×1440 项目。明确严格 30 秒时加 `--duration-mode max --seconds 30`，约 30 秒用 `approx`。所有路径相对项目根，不允许逃出根目录；中文和含空格路径可用。Python API 在 `studio.py`，命令说明见 runtime.md。

## project.json

- `contract_version: 2`：新项目默认。每幕 `content_kind: factual / nonfactual` 分类覆盖旁白、页面文字和图片所表达的结论；factual 必须有 claim_ids，nonfactual 必须写 nonfactual_reason。程序检查缺项，作者仍需判断每项关键结论是否被证据支持。旧场景已有 claim_ids 时按 factual 检查，不机械重写项目；无引用的旧场景重新生产前需明确分类。分类变更会失效对应稿件身份。
- `duration`（有用户时长要求时必填）：`{mode: "max" | "approx", seconds: 30, tolerance_seconds: 2}`。max 在发送付费请求前按已有音轨/剩余估时检查，导出前检查真实时间线，编码后检查容器实测时长，超限阻断；approx 超出容差仅报告 outside_target，不擅自加速。估时不是实际时长保证。未配置则明确报告 unspecified，不伪称满足上限。
- `brand_component: "xyzchem-fixed-outro-v2"`：由 xyzchem preset 或片尾装配命令设置，配音前要求固定片尾为唯一最后一幕，且画幅兼容。

- `profile`: width/height（正偶数）、fps、caption_px。改变画幅必须重新设计 HTML；1920×1080、30fps、48px 是起点。
- `visual_system`（竖版视频原生项目）：`{style,theme}`。`style` 为 `swiss` 或 `editorial`，`theme` 必须属于该风格的 social-card 官方 palette；整个项目固定一个模式和主题，逐幕不得混搭。
- `voice`: MiniMax voice_id、speed、vol、pitch，可附已试听的 emotion；场景的 voice 为局部覆盖。
- `voice.text_normalization` / `voice.latex_read`：可选布尔值，分别用于数字规范化和公式朗读。`voice_modify`：可选 pitch/intensity/timbre 整数 -100～100、sound_effects；场景同名字段局部覆盖，默认不添加声音效果。
- `sources`: `[{id,path,url,title}]`。path 是保存的原始资料/网页快照；URL 本身不能代替存档。
- `claims`: `[{id,source_id,locator,quote}]`。每幕 claim_ids 绑定相关事实；人工负责判断引文是否支持结论。
- `assets`: `[{id,status,path,source,purpose,prompt,ratio,source_pixels,render_slot,composition,factual_constraints}]`。status 为 ready 或 waiting_external；`ratio/source_pixels` 记录最终图片实际比例和像素尺寸，`render_slot` 记录计划接入的场景图槽或画面区域，三者必须与真实版式一致。场景 assets 引用这些 ID。
- `cover`（可选）：`{path,title,ratio,source,sha256}`，绑定发布封面 PNG、平台标题、画幅、素材来源和最终文件哈希；封面改版新增版本，不覆盖旧文件。
- `protected_terms`: 不能拆开的词、术语、产品名、完整型号以及“数字+单位”，例如 `speech-2.8-hd`、`128 GB`。自动补充 ASCII 连续串，不能替代项目词表。
- `waiting / next_action`: 具体缺项、责任方和下一步。恢复时先读这些字段和 status，别从头制作。
- `test_mode`: 仅工具验收项目可为 true；正式项目省略。测试 attempt 不能成为正式音频。

## 每个 scenes[]

稳定 `id`；`html` 指完整场景 HTML；`narration` 是唯一可读旁白；`intent / visual_notes / claim_ids / assets` 用于作者审核。

竖版视频原生场景可同时记录 `template` 与 `theme`；`scenes/<id>/plan.json` 保存模板、语言、主题、尺寸及源文件哈希。模板字段说明创作起点，不等于该场景已填写、已配图或已审核。六类模板及命令见 design-inheritance.md。

可选 `role: "brand-outro"` 标识公司收束；它仍是正常最后一幕，当前引擎不对 role 做特殊调度或自动补稿。品牌元数据只存资料，旁白在 scenes[].narration 保持唯一，详见 [公司收束场景](brand-outro.md)。

`visual_plan: {medium,reason}` 记录媒介选择与表达理由，配音前预览工具据此检查素材引用；`estimated_duration` 为正数秒数，包含该幕停顿与尾部留白，配音前按帧取整用于预算检查，实测音轨到位后替代估时。图片资产额外记录 `sha256`，HTML 图片用 `data-asset-id` 绑定素材 ID，详见 [视觉规划](visual-planning.md)。图片原图比例与实际显示框不一致时，`object-fit: cover` 属于内容裁切而不是适配，预检必须阻断。

`dependencies` 显式列出由 JS 动态加载或 import 的本地资源；HTML/CSS 的 src、href、url() 会自动跟踪。不能引用整个项目目录充当依赖，否则破坏局部复用。画面不允许依赖未声明网络资源、系统时间或随机生成内容。生产环境字体应落到项目 assets 并通过 @font-face 引用，保证换机器可复现；测试可用已安装中文字体并记录运行环境。

`caption_phrases` 是 narration 的原文切片，拼接必须逐字等于 narration，包含标点和空格。作者按语义和画面宽度提出分段，程序用分词及保护词拒绝词内切割。程序不会凭空均分时间：如分段落在 provider 的一个 token 内，需选择实际词边界，或对原音频做可溯源强制对齐，不能重写起止秒数。

`beats`: `[{id:"reveal-proof",after:"旁白开头已经说完的完整前缀"}]`。前缀须正好止于一个真实时间戳边界。渲染器把结果放入 window.productionBeats，HTML 用 `beat.at` 决定局部展开时间。较长语义段内可有多个画面节拍，不必为了换画面把声音切碎。

`tail_seconds` 为音频后留白，默认 .25 秒；用实测可读性决定，不可以偷偷截短音轨。每幕时长向上取整到完整视频帧，WAV 补齐等量静音，后续场景不会累计漂移。不要给每句加长静音。

`pauses`: `[{offset:12,seconds:.4}]`，offset 为 Python 字符位置，不能在词内，不能在开头/结尾或同位置重复；请求载荷添加标签，旁白原文不变。`pronunciation`: 官方 `tone` 数组，比如 `处理/(chu3)(li3)`。若供应商返回的文字已被拼音替换导致原文校验失败，保留音频，检查原始结果，补显式读音映射/强制对齐适配器并测试；不能放宽为忽略词语差异。

停顿优先写作 `[{after:"旁白开头的完整前缀，",seconds:0.25}]`，与 offset 二选一；修改原文后前缀不匹配会报错，避免数字偏移悄悄插错位置。秒数须 0.01～99.99、最多两位小数，两个标记之间必须存在可发音文字。词内切割仍需作者检查。

## 场景 HTML 契约

`window.renderAt(t,duration)` 必须支持任意顺序 seek，并对相同 t 返回相同画面。不能用 setTimeout 播动画、Date.now 或无 seed 的 Math.random。CSS 动画在导出时禁用，用 renderAt 设置 transform/opacity/clip 等。所有资源本地化；图片 await decode，字体 await document.fonts.ready。给关键文字、图表和主体容器标 `data-safe-check`，导出自动检查字幕安全区碰撞；未标元素仍需目视检查。

播放器、导出均以同一实际 timeline 为准。默认硬切，场景内部可做淡入/展开/移动；跨场景交叠转场未内置，需要显式设计同一场景内部两层叠化并测试，不能只在播放器做出不同效果。视频素材需要额外实现 renderAt 中的 currentTime seek 和 seeked 等待；本版重点是 HTML/CSS 与静态图片，不声称任意视频嵌入已通过验证。

## 失效传播

| 修改 | 需要更新 | 复用 |
|---|---|---|
| 图片/裁切/CSS | 该场景渲染、视听遮挡检查、最终封装 | 稿件、TTS、字幕文字与时间 |
| 旁白字词、来源证据 | 受影响稿件确认、对应 TTS、音频确认、字幕、视频 | 其他场景 TTS/画面 |
| 音色/速度/停顿/读音 | 对应 TTS 与下游 | 稿件文字确认、其他场景 |
| 字幕分段 | 字幕、该幕画面、视听 QA | TTS、用户音频确认 |
| 场景重排/留白 | 时间线、全局字幕与封装 | TTS，未变的局部渲染可缓存 |
| 仅叙事说明字段 | 作者记录 | 未受影响产物 |

每幕 `design_review` 指向当前已导入的设计审核记录。正式导出重新检查素材语义核验、静态 PNG/画面身份和有效稿件审核；撤销结论或修改审核文件也会失效下游身份。记录准备与导入命令见 design-inheritance.md。

没有审批就不能自动填 approval。`.history/` 是本地可审计证据，不是防恶意篡改的签名系统。已确认的文件不能原地覆盖；新版本替换 state 引用，旧版本保留。恢复语音请求时先用 `recover` 下载未完成结果。`recover / attach` 均以原始 transport.json 的 mode/unit 为准；显式参数不一致会拒绝，缺原始模式不能猜成 final。`attach` 在新历史目录处理副本，不覆盖来源 WAV/词时间戳；已登记目录、重复输入与已完成 attempt 不能原地重做。部分转换失败后保留原件，通过 attach 在新目录恢复，不重发付费请求。

## 可选音乐

`music` 配置、音乐状态、确认与增量导出见 [项目音乐契约](project-music.md)。未配置时保持纯旁白。

## 当前能力边界

`studio init` 的 generic 默认仍是 1920×1080，并继续使用 `assets/scene.html`；新义合成使用 `--preset xyzchem` 的 1080×1440，首个场景默认从 `opening` 视频模板创建。现有项目不会自动改变画幅、替换模板或补填未知时长。固定片尾只能通过显式 `attach_brand_outro.py` 装配，role 本身不触发导入。旧导出文件保留；重新生产时缺当前设计审核需按实际静态查看记录补齐，不自动伪造通过。
