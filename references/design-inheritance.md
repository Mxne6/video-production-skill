# 设计实现与视频交接

## 职责与优先关系

creative.md 决定故事和信息取舍；composition-system.md 决定每幕应该如何被看见；visual-planning.md 决定素材角色；本文件负责把这些判断落成可执行 HTML、静态审核和视频交接。

Guizang social-card 是视觉语言和设计方法来源，不是视频页面模板库。视频继承 typography、grid、asymmetry、image-as-evidence、hairline、palette、克制层级与 Editorial / Swiss 的气质；不继承社交卡必须独立刷完一页的密度规则、M/S recipe 标签、issue strip、页码和大量静态正文。

## 新的竖版入口：adaptive 默认，named starter 兼容

只有 `1080×1440` 新义合成项目进入这一套 content-first design contract。新项目：

```powershell
python scripts/studio.py init P --preset xyzchem --style swiss --theme ikb
```

首幕默认使用 `adaptive`。新增 scene 也默认：

```powershell
python scripts/create_video_scene.py P --scene s02
```

如果某一幕内容真的与旧结构高度吻合，可显式选择兼容 starter：

```powershell
python scripts/create_video_scene.py P --scene s03 --type mechanism
```

可用 named starter 仍为 `opening / product-hero / mechanism / proof-data / application / summary`。它们不再决定信息结构，只是可复用的已有 DOM 起点。不得建立“产品主体 → product-hero”“数据 → proof-data”“应用 → application”的自动路由。

项目级视觉系统仍固定为一个 mode + 一个官方 palette：Swiss 用 `ikb / lemon-yellow / lemon-green / safety-orange`；Editorial 用 `ink-classic / indigo-porcelain / forest-ink / kraft-paper / dune / midnight-ink`。统一来自 tokens，而不是靠每幕复制同一布局获得一致性。

## Scene design contract

新项目写 `design_contract_version: 1`。每幕在静态审核前必须完成 `scenes[].design`，字段语义见 composition-system.md。

最关键的字段不是 template，而是：

- `message`：观众这一幕真正带走什么；
- `dominant`：第一眼视觉主角；
- `attention_order`：真实观看顺序；
- `on_screen / narration_only`：画面与声音分工；
- `image_role / visual_share`：图片是否决定构图以及占幅；
- `layout_family / layout_signature`：最终画面属于哪种构图语法、实际轮廓是什么；
- `composition_reason`：为什么这个几何适合这幕；
- `density / intensity / contrast_with_previous`：它在整条视频里的节奏角色。

`layout_signature` 不是模板 ID。写实际视觉轮廓，例如：

- `full-bleed-photo / lower-left-title`
- `type-left / product-right-vertical`
- `number-center / condition-bottom`
- `section-image-top / two-annotation-edges`
- `cause-diagonal / result-anchor-bottom`

只有 brief 完成后才开始改 HTML。

## Adaptive seed 的角色

`templates/video/adaptive.html` 故意很少提供结构：没有默认 rail、图片区、metric grid、footer 或固定 split。它的意义与 Guizang 的 seed template 相同——固化字体加载、palette、renderAt 合约和安全的基础 primitive，把 Agent 的注意力留给“内容应该如何变形”。

adaptive 初始 HTML 带 `data-starter-only="true"`。完成真正构图后必须删除该属性；`design_review.py` 会阻止仍带 starter 标记的新项目进入静态审核。

共享 CSS 提供的是 grammar primitives，而不是 recipe：

- `.scene-grid` + `.span-*`：12 列不对称网格；
- `.scene-stack / .scene-row`：基本流；
- `.type-display / .type-statement / .num-hero`：Guizang 式“越大越轻”的主体 typography；
- `.media-block`：按实际构图定义尺寸的媒体块；
- `.marginal / .hairline`：编辑排版关系；
- `.scene-full-bleed / .full-bleed-media / .overlay-copy`：图片真正成为画面主体时使用。

这些类可以自由组合，也可以写 scene-scoped CSS。不要因为 primitive 存在就每幕都用同一套。

## 图片与构图

图片必须先被定义为 hero / evidence / support / atmosphere / none，然后才决定 slot。

- hero：通常至少 55% visual_share；整幕围绕图片主体、方向和 quiet zone 布局；
- evidence：大到可检查，与 claim/数字直接邻接；
- support：只回答一个具体次级问题；
- atmosphere：用于节奏与环境，不能冒充证据；
- none：不设无意义空图槽。

图片原始比例与最终显示方式不兼容时，改构图或重新生成，不用 `cover` 偷偷裁掉关键主体。Social card 的 subject mapping、object-position 和 thumbnail check 方法继续有效；其具体 recipe 不直接搬过来。

## Editorial / Swiss 继承边界

### Swiss

保留：Inter/Noto Sans、轻字重大号字、严格轴线、12 列网格、hairline、单 accent、强不对称。

避免：把所有信息变成卡片矩阵、KPI dashboard、browser/landing-page 模块。数字可以是一整个画面的主体，图片可以满幅，关系也可以突破 card 容器。

### Editorial

保留：serif display + serif body、宽字距、纸/墨 palette、摄影与 caption、marginalia、规则线、真正有意义的留白。

避免：每幕都铺 paper texture + mono kicker + issue strip，然后误以为这就是杂志。视频中 sparse scene 可以很安静，但留白必须服务主体、字幕或节奏；没有 opposite page 替它吸收欠填。

## 静态审核

scene 先生成 1080×1440 PNG 并实际查看，再进入 motion。新项目准备审核：

```powershell
python scripts/scene_design.py P
python scripts/design_review.py P --scene s02 --png scenes/s02/output.png
```

`design_review.py` 会：

- 验证 scene design brief；
- 阻止 adaptive starter 标记未删除的页面；
- 把 layout_signature、dominant、image_role、visual_share、density、intensity 等写进 review 记录；
- 写入人工查看时应回答的 prompts。

实际查看 PNG 后填写 pending 记录，再导入：

```powershell
python scripts/design_review.py P --scene s02 --import-report review/design-review-s02-<版本>.json
```

审核至少回答：

1. 第一眼是否与 attention_order 一致？
2. declared dominant 是否真的拥有最大视觉权重？
3. 图片/数据/关系是否决定几何，而不是落进普通槽位？
4. 画面字量是否与时长匹配，是否复读旁白？
5. 留白是否有原因？
6. 与前后 scene 的 silhouette 是有意义的连续还是机械重复？

无溢出、可解码、字体加载成功都不能替代这些判断。

## 整片 sequence review

单幕 pass 不代表整条视频成立。正文 design brief 全部 ready 后运行：

```powershell
python scripts/scene_design.py P
```

默认规则：

- 连续三幕同一 `layout_signature` → error；只有明确比较/连续性用途并写 `continuity_reason` 才允许；
- 连续三幕同一 layout_family 但 silhouette 不同 → warning，提醒人工确认不是轻微变体；
- 四幕以上全部同一 intensity → warning。

这些只是机械底线。人工仍要看 contact sheet。`visual_review.py P --render` 会把每幕中点帧写成 `review/visual-*/contact-sheet.png` 并记录哈希；如果每幕都是“上方大矩形图 + 下方标题”、同一 7:5 split 或同一 rail，即使 signature 字符串写得不同，也应退回重设计。

不要为了通过节奏检查随机轮换 family。视觉变化来自内容：有时强、有时静；有时图片占满、有时一句话独立；有时数字压倒一切、有时关系图主导。

## Social card 单页与封面

当场景明确使用 social-card 种子或单页卡片时，仍可走原校验器：

```powershell
node scripts/run_design_validator.cjs P/design/s01/index.html --style=swiss --expected-pages=1 --report=P/review/validator-s01-v1.json
python scripts/design_review.py P --scene s01 --png design/s01/output.png --validator-report review/validator-s01-v1.json
```

该 validator 检查 overflow、字号、密度等静态问题，不负责判定视频 scene 的审美、观看顺序或整片节奏。WARN 不得驱使添加无意义标签、卡片或装饰。

## 视频交接

静态构图通过后，保留 `window.renderAt(t,duration)` 确定性接口再加入 reveal / beat。Motion 负责：

- 建立注意顺序；
- 展示状态变化；
- 让关系在时间上更容易理解。

Motion 不负责：

- 给空画面补热闹；
- 用飞入掩盖层级问题；
- 让固定模板看起来“变化很多”。

将 HTML、图片、字体与依赖写入项目，遵循 project.md；字幕区域及固定片尾的覆盖样式保留。播放器与导出都在场景 DOM 注入同一 caption layer。先完成视觉查看再渲染视频，不能在返回静态截图的同次调用里未检查就继续正式视频生产。

设计变更会改变新项目的 visual_content_key，因为 scene design brief 被绑定进视觉 identity；旧项目没有 design_contract_version，不被强制迁移或失效。固定片尾仍走 brand-outro.md，不参与正文构图系统。
