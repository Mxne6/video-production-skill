# 运行、TTS 与导出

## 用户旁白默认配置

新项目默认 MiniMax `speech-2.8-hd`，音色 `Chinese (Mandarin)_Sincere_Adult`（用户已确认的真诚青年），`speed:1`、`vol:1`、`pitch:0`、`text_normalization:true`。`studio init` 自动填入。未要求改动就沿用；正文和固定片尾使用同一项目音色，在完整稿件确认后按正常流程逐段合成和试听；不导入旧固定片尾录音，也不重复询问选声或默认付费生成候选试听。不添加声音效果或额外情绪参数。已有项目的明确配置不被新项目默认值覆盖。新产品读音按原稿单独核对，不能带入旧型号读音字典。此配置不等于新稿件或新生成音频已获批准，正常稿件与完整音频审核仍保留。


环境：Python 3.10+，`python -m pip install -r <技能目录>/requirements.txt`，`python -m playwright install chromium`。设计校验另需 Node.js 18+：`npm ci --prefix <技能目录>/design/guizang-social-card`，再运行 `npm --prefix <技能目录>/design/guizang-social-card exec playwright install chromium`。FFmpeg 优先环境变量 FFMPEG，再使用 imageio-ffmpeg 的固定二进制，最后才回退系统 ffmpeg；浏览器可通过 VIDEO_CHROME 指定。

以下 `studio` 表示 `python <技能目录>/scripts/studio.py`，P 表示项目路径。PowerShell 中用引号包裹含空格路径。

1. 通用视频用 `studio init P`；新义合成用 `studio init P --preset xyzchem --style swiss --theme ikb`，默认创建 `opening` 竖版模板，已明确时长时加 `--duration-mode max --seconds 30` 或 approx。首个场景可用 `--scene-template` 改选六类模板，后续场景用 `python scripts/create_video_scene.py P --scene s02 --type mechanism` 追加。一个项目只能使用一个 social-card 模式和一个官方 palette。编辑 project.json、sources 和 scenes，`studio status P` 检查缺项、估时和审批有效性。用浏览器/截图查看 HTML，先把可审核的内容做具体。
2. 用户审核稿件后：`studio approve-script P --scenes all --evidence "用户原话与消息定位"`。局部批准可用 `s01,s02`。这条命令记录已有授权，不是自动批准机制。
3. `studio voices P --prompt-key` 用不回显输入查询官方系统音色，保存音色目录但不保存密钥；也可使用进程环境 MINIMAX_API_KEY。配置已验证的 voice_id；`studio tts P --scenes s01` 只准备请求、不发送，允许未批准稿件做准备。`studio tts P --scenes s01 --send --mode audition --prompt-key` 发一次试听；正式音频使用 `--mode final`（默认）。一次只请求一个自然语义段，已批准的范围内可逐段继续，无需再次询问相同授权。未审核稿件不能发送合成。不要把密钥放进命令参数、项目、日志或报告；prompt 输入只在该进程内使用，不持久保存。
4. 不自动重试付费请求。请求失败/结果不明看 `.history/tts-*/` 中保存状态与原始响应。音频/时间戳下载失败先恢复下载，不能再调用 TTS。优先 `studio recover P --scenes s01 --attempt .history/tts-...` 恢复下载。转换失败或跨项目导入用 `studio attach P --scenes s01 --attempt <项目内原始包>` 在新目录处理副本，必须保留 request.json、transport.json、audio.mp3、timing.raw.json；模式和单位继承原记录，不能用默认 final 覆盖 audition/test。
5. 所有正式段生成后 `studio preview P` 输出实际 WAV、SHA256 和 review/index.html。此时没有字幕。展示音频让用户试听确认，再执行 `studio approve-audio P --scenes all --review-hash <输出的SHA256> --evidence "用户试听确认原话与定位"`。局部重做时可选指定场景，但必须让用户听到新版本。复用未变场景的批准。
6. `studio captions P` 验证原词、保护词、时间戳。`studio preview P --captions` 生成审核页。用 `python -m http.server 8765 --bind 127.0.0.1 --directory P` 提供项目目录，打开 http://127.0.0.1:8765/review/；不要把服务暴露到公网。支持逐句跳转、循环、速度和问题备注，localStorage 按产物哈希保存。修改后旧标记不会套到新版本。
7. `studio render P --draft` 生成可播放审核视频并自动检查字幕实际宽度、标记元素碰撞、浏览器错误、资源缺失、解码、帧数和音轨时长。耗时取决于分辨率和总帧数，按幕缓存。试听检查应在此真实画面与音轨上完成，也可用审核播放器。
8. 正式导出前各幕的静态设计审核须按 design-inheritance.md 导入。竖版视频原生模板直接准备 PNG 审核，不要求 `section.poster` validator；social card 路径保留原覆盖校验。工具重验素材、设计与稿件门槛。审核员实际听看每句后，审核页导出 caption-review.json。`studio qa-import P --report <文件>` 检查每句通过且没有未解决问题，身份绑定音频、字幕和视觉；无须另设用户字幕批准。`studio render P` 输出生产 MP4/SRT/WAV/manifest。草稿和生产的缓存区分，防止审核水印进入正片。

交付前打开 MP4，抽查首尾和切换、声音截断/爆音/异常长空白、字幕密集段。manifest 的自动结果不证明中文自然度；无法实际听声时如实标记并请用户试听，不能伪造 listened。不默认添加 BGM/SFX；用户需要时另外检查音乐授权、音量和对白清晰度。

## 项目背景音乐

用户需要背景音乐时，按 [项目音乐契约](project-music.md) 准备多条候选：先用 `music-candidates` 核对，再用 `music-audition` 逐条试听，然后由 `music-select` 随机或按 id 选定，最后走 `studio render --draft` 和混音确认。`studio render --draft`、`studio render` 均自动带当前候选，混音确认独立绑定音轨身份；不再手工拼发布音轨。旧 `mix_background.py` 仅保留历史兼容。

## 按需兼容与故障资料

首次接入、未知时间戳格式、恢复下载或用户要求换声时读 [MiniMax 兼容说明](minimax-compatibility.md)。日常已有有效配置和资产时无需重走历史接入或候选选声。
