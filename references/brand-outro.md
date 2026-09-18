# 固定公司片尾组件（唯一入口）

新义合成 / XYZCHEM 产品视频从首次分镜起，将固定片尾作为 scenes[] 的正常最后一幕。正文正常创作；片尾直接套用组件，不再另起最后一页设计任务，也不在正文成片后另行补做。其他公司的视频不套用此身份。

## 画面

固定模板按语言存放：中文为 `assets/brand/outro/zh-CN/template.html`，英文为 `assets/brand/outro/en/template.html`。中英文使用同一组件结构：透明 Logo、可选技术 kicker、产品品牌、蓝色等宽型号、产品类别、公司页脚。默认不含电话、官网、二维码、咨询入口、访问引导或其他 CTA，避免被平台判为引流；无重复页脚，无完整旁白常驻文字，不添加 TDS 宣言或“由谁提供”标题，不硬编码产品族或技术主张。配色从正文 HTML 读取，Logo 保持原色。语言目录只保存各自公司信息和模板，不复制正文场景。

如果某个发布渠道明确要求商业联系方式，单独制作并审核商业版，不修改默认中性组件。

正文主题确定后运行：

```powershell
python scripts/create_brand_outro.py P --product "新一砼® S7046" --category "粉末晶种早强剂" --theme-html design/s01/index.html --output design/company-outro-fixed-v2
```

英文示例：

```powershell
python scripts/create_brand_outro.py P --language en --product "XYZCHEM® S7000" --product-brand "XYZCHEM®" --product-model "S7000" --kicker "LIQUID C-S-H SEEDING" --category "Liquid C-S-H Seed for Early Strength" --theme-html scenes/s01/index.html --output design/company-outro-en-v2
```

需要拆开产品层级时显式传入 `--product-brand "XYZCHEM" --product-model "S7000"`；未传时脚本只在空格后的末段像型号且含数字时自动拆分，否则整段作为品牌。`--kicker` 可省略。此工具只填固定模板并输出 `index.html / output.png / plan.json`，不调用图像模型、不创作新布局、不发送 TTS，不写用户审批。P 为项目路径，命令使用 Skill 脚本路径；输出目录已存在时换新版本。需要项目 assets/fonts/ 内的 Inter.ttf、NotoSansSC.ttf、IBMPlexMono.ttf，当前布局支持 1080×1440。其他画幅、超长产品名或深色主题须实际核对可读性，不自动拉伸或添加内容。

复制原图 `assets/brand/logo/xyzchem-logo-user.png` 到项目引用，不依赖桌面；透明留白用 CSS 安排，不重绘标志。工具等待字体和图片就绪后，只截取 `#company-card`，输出固定 1080×1440 PNG；不截整页，不把模板 body 的深色背景或 padding 带入成片，也不手工追加页内样式。静态页生成后查看 PNG，再原样接入视频层；上游模板快照不改，已确认历史视频不覆盖。

## 旁白：固定文案，随整稿生成

中文配置以 `assets/brand/outro/zh-CN/component.json` 为准，固定文案为：

> 本期产品由南京新义合成科技有限公司提供。

产品名称仅更新画面，不改这句旁白，不再为每个型号生成不同收束文案。项目 scenes[].narration 从组件复制这句固定文案，纳入首次整片稿件，不保存另一份产品专属片尾稿。项目仍记录公司关系的来源证据。

固定文案必须纳入完整稿件确认；确认后，片尾与其他正文使用同一项目音色，在正常流程中逐段生成、试听、生成字幕并参与整片预览。组件不保存固定 voice/model 配置；不要导入旧固定录音，也不要在项目之间复用片尾音频。

生成工具已渲染对应目录 `output.png`，单独查看 PNG 后运行：

```powershell
python scripts/attach_brand_outro.py P --design design/company-outro-fixed-v2 --claim-ids company-source-claim
```

claim ID 必须已存在并支持公司关系。命令复制固定 PNG 到新场景版本、追加唯一最后一幕、设置字幕 bottom:13%，不写入新的稿件、音频或 attempt 记录；其他场景已有记录原样保留。它不生成稿件或设计批准，不导入音频，不发送 TTS。新幕仍须纳入整稿确认并按 design-inheritance.md 记录实际静态查看。重复片尾或画幅不匹配会阻断。`create_brand_outro.py` 负责固定组件和最终 PNG，`attach_brand_outro.py` 只负责把已确认的固定版本装配到项目。

## 时间线与导出

片尾属于正常最后场景（role 为 brand-outro，visual_plan 使用现有工具支持的 medium，如 typography），不增加第二个静音片尾或重复持留页。末尾留白默认 tail_seconds=1.5。所有时间以本次生成的片尾 WAV 和真实词边界为准，不再维护固定音频的前导偏移。

字幕来自本次生成音频的真实时间戳，视频层添加于底部留白（bottom:13%），不写进静态模板。背景音乐按包含该片尾的完整旁白轨避让，最后淡出。整片试听检查正文到片尾的音色、响度、字幕和停顿。

只有用户明确修补旧视频才处理历史补尾，复用未改内容；不再保留新视频的“独立生成最后一页＋另写片尾旁白”常规流程。
