# MiniMax 接入与恢复（按需）

此文件保存接口核对与已观察格式，历史试听仅作为兼容证据；当前生产声音默认和命令入口以 runtime.md 为准。无需每片重做选声或重发已成功请求。

## MiniMax 已核实接口（2026-09-05）

官方文档：https://platform.minimaxi.com/docs/api-reference/speech-t2a-http

当前官方示例主地址为 `https://api.minimax.cn/v1/t2a_v2`；本工具还允许已知官方地区/备用地址通过 MINIMAX_TTS_ENDPOINT 显式指定。模型固定 speech-2.8-hd，非流式，subtitle_enable=true，subtitle_type=word，output_format=hex。当前字段见官方文档，不沿用旧技能地址作为唯一地址。

完整响应保存为 response.raw.json，音频 hex 解码为 audio.mp3，data.subtitle_file 立即下载为 timing.raw.json（远程 URL 可能到期）。原始时间戳必须保持原样；words.json 是归一化副本。默认官方时间单位 ms，可用 --unit s 处理明确是秒的外部对齐，不猜单位。支持数组 `{text,start,end}`、`{text,start_time,end_time}` 和包含 words/subtitles 的对象；遇到未知结构停下检查并添加小型明确适配器。不能把句级时间戳按字数拆成词级。

CLI 的模拟响应测试只证明适配器对测试格式有效；首次 live 请求须核对实际响应结构、数据粒度、时长和听感。API 返回读音文字与原文不一致时拒绝生成字幕，保留已付费音轨并修复对齐，不重新合成掩盖问题。

试听及正式生成支持 voice_id/speed/vol/pitch/emotion、pauses、pronunciation。音色未定先选包含真实难读术语的一段完整语义试听，不能只测试“你好”。调速须同时看时长、清晰度和听感；不是越快越好。不得把 audition 引用当作 final，正式音频审核始终对应实际保存的文件。

## 2026-09-07 能力核对与接入

同段音色比较：`python scripts/audition_compare.py P --scene s01 --voice-id "已核验ID" --label "A候选" --prompt-key`。一次生成一种声音，使用已确认场景原稿和停顿；保存为 audition，不替换正式音频引用。失败后检查已保存音轨再处理，不自动重试。

用户觉得播音腔、端着或过于正式时，先按日常讲述方向选声，不继续推荐一组相近播报音色。比较时可加 `--natural-pauses`，仅在该次试听中去掉显式停顿标签，不改稿件或正式配置；不要为了“自然”擅自添加笑声、呼吸标签。最终以用户实际试听反馈为准。

已观察到真实2.8词级格式：句段内 `timestamped_words`，使用 `time_begin/time_end` 毫秒与 `word_begin/word_end` 原文位置。发音字典可让同一原文位置产生多个发音片段，适配器按相同位置合并真实时间范围；不同位置的重复字词不合并。省略的空白、标点和®™©保留原文，不为其编造时间。S01三种音色均完成文字和时间范围校验；这不证明听感或全片字幕同步通过。

核对来源：[同步合成](https://platform.minimaxi.com/docs/api-reference/speech-t2a-http)、[音色查询](https://platform.minimaxi.com/docs/api-reference/voice-management-get)、[异步合成](https://platform.minimaxi.com/docs/api-reference/speech-t2a-async-create)。同步文档也可读取同路径 `.md`。

- `pauses` 支持完整原文前缀 `after`，转换为官方停顿标签；校验长度、精度和相邻可发音内容。不要每个标点都加停顿。请求里的标签不进入旁白原文和字幕。
- `voice.text_normalization: true` 可辅助数字阅读；型号、百分比和多音字仍用 `pronunciation` 指定并实际试听。返回字幕可能使用读音替换后的文字，必须检查对齐，不能跳过原文一致性检查。
- 可选 `voice_modify` 调整音高、力度、音色或单种声音效果；默认不启用，专业产品说明优先自然清晰。语气标签、混合音色、音色复刻等虽有官方能力，本流程未为其建立原文字幕对应契约，不自动混入产品旁白。
- `emotion` 默认由模型选择；文档对 `fluent` 的适用模型描述有歧义，工具暂只接受明确的七种基础情绪，不发送 2.8 不支持的 `whisper`。
- 坚持同步非流式 `subtitle_type=word`。官方返回字段说明仍写句级，不代表真实词级结构已验证。首次请求检查原始 JSON 的粒度、单位和文字，必要时补明确适配器。异步长文本不是本片的首选。
- 新请求保存无密钥的 `transport.json`，记录模式、单位与请求地址。响应已保存但下载中断时，运行 `studio recover P --scenes s01 --attempt .history/tts-...`：只解码已有音频、GET 缺失字幕、恢复处理；不调用合成、不更改 audition/final 模式。旧请求无 transport.json 时按原 attach 流程恢复。

接口查询成功只证明密钥能查询该地区音色，不证明语音额度、合成权限、听感或真实时间戳已通过。音色名称描述来自供应商，不能替代试听。
