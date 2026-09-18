# 语言版本

默认目标语言是 `zh-CN`，英语使用 `en`，法国法语使用 `fr-FR`。地区英语在真实音色、口音和试听结果明确前不建立别名状态。每个目标语言使用独立项目目录，不能复制中文项目的 `state.json`、`.history` 或审批。

## 独立本地化，不是页面翻译

中英法共用的是生产引擎、字体、主题、六个结构模板和固定片尾工具；不共用最终稿件、分幕、scene HTML、页面文字、语言相关图片、音频或审核。默认任务“做英文版”表示从原始资料制作一部英语视频，不表示把已完成的中文视频逐句翻译并替换页面文字。

制作任意目标语言前先查 [生产记录](production-registry.md)，确认同一产品的该语言是否已经正式导出；完成后把语言、项目路径和导出文件写回同一张表。

英语和法语项目按以下顺序执行：

1. 优先使用官方英语资料；只有中文资料时，以原始条款、数字、单位和条件为依据写英语稿件，不把中文成片文案当唯一来源。
2. 新建 `*-en` 项目，不复制中文项目目录，也不导入中文 `state.json`、`.history`、scene 文件或审批。
3. 英语旁白按英语观众独立成稿，保持事实一致，不要求逐句对应中文，不新增资料没有的结论。
4. 根据英语稿件重新决定幕数、顺序、信息重点和时长，再选择模板；即使沿用相同模板或 scene ID，也必须通过 `create_video_scene.py` 新建并填写内容。
5. 禁止复制中文 scene HTML 后替换文字。可以复用与语言无关的产品图、Logo 和示意图；含中文文字、中文标注或中文排版的图片必须重新制作或换成英语版本。
6. 英文画面文字、旁白和字幕使用同一语言，之后独立完成静态查看、稿件确认、TTS、试听、字幕和导出。

只有用户明确要求“中文视频的翻译版本”时才可把中文成片或页面作为翻译参考；仍须新建英语项目，并从模板重建 scene HTML，不能在中文项目上原地替换文字。

## 建项

```powershell
python -X utf8 video-production/scripts/studio.py init projects/my-video-en --language en
python -X utf8 video-production/scripts/studio.py init projects/my-xyzchem-en --language en --preset xyzchem --duration-mode max --seconds 30
```

`--language` 和 `--voice-id` 只用于 `init`。之后命令从 `project.json` 读取语言。英语默认 `English_expressive_narrator` 是官方目录候选，未表示已试听或已批准；MiniMax 请求使用 `language_boost: English`。

## 英语与法语制作

资料事实、型号、数字、单位和性能条件先核对，再写英语稿件；翻译不能新增结论。画面文字、旁白和字幕使用同一语言。英语估时按 WPM 加停顿和尾部留白，只用于预算；TTS 实测音轨仍是最终依据。

英语和法语字幕必须逐字重建 `narration`，保留空格、标点、缩写、连字符词、数字小数和数字+单位。法语的重音字符、撇号缩合（如 `l’`、`d’`）和连字符词不能被切断。只在完整词和真实 provider 时间戳边界切分，不能按字符平均分配时间；`caption_language.py` 提供安全切点。

英语与中文共用一套主题、字体和结构模板，但英语内容、分幕和场景文件独立生成。新义合成竖版项目从六个视频原生模板重新创建，根据英语稿选择模板和排布，不把中文页面翻成英文，也不另造一套字体体系；Social card 继续用于封面和单页卡片。模板选择、静态 PNG 与设计证据按 [设计交接](design-inheritance.md) 执行。先独立渲染、查看 PNG，再导入设计审核，最后才启动视频预览或导出。

## 英文固定片尾

`--preset xyzchem --language en` 使用 `xyzchem-fixed-outro-en-v1`，版式沿用固定片尾结构，英文公司名依据官网 `https://www.xyzchem.com/en/`。候选固定旁白是：`This product is brought to you by Nanjing Xinyi Synthesis Technology Co., Ltd.`；仍需用户确认。确认后把固定旁白纳入完整英语稿件，与正文使用同一项目音色逐段生成和试听；不得接中文片尾录音或复用其他项目的固定录音。

```powershell
python -X utf8 video-production/scripts/create_brand_outro.py projects/my-xyzchem-en --language en --product "XYZCHEM® S7000" --product-brand "XYZCHEM®" --product-model "S7000" --kicker "LIQUID C-S-H SEEDING" --category "Liquid C-S-H Seed for Early Strength" --theme-html scenes/s01/index.html --output design/company-outro-en-v2
python -X utf8 video-production/scripts/attach_brand_outro.py projects/my-xyzchem-en --design design/company-outro-en-v2 --claim-ids company-source-claim
```

`create_brand_outro.py` 直接生成固定 `index.html / output.png / plan.json`，只截取品牌卡片并校验 1080×1440；不另外手工截图或追加局部样式。产品品牌和型号需要明确分层时使用 `--product-brand / --product-model`。英语片尾不维护固定录音。没有稿件确认或生成后的英语音频试听时，记录 `waiting`，不伪称 MP4 已完成。
