# 项目背景音乐与调音

背景音乐先准备候选，再随机选定一条或由用户指定。随机只决定用哪条，不代替最终混音的听感确认。候选可以是项目素材，也可以是可复用的音乐库；每个候选必须有自己的 `id`、源文件和完整授权记录。不得因为候选是用户提供就跳过授权字段，也不得自动选定后直接发布。

## 候选库

项目在 `project.json` 保存候选：

```json
"music": {
  "candidates": [
    {
      "id": "calm-tech",
      "source": "music/calm-tech.mp3",
      "license": "music/calm-tech.license.json",
      "loop": false
    },
    {
      "id": "clean-pulse",
      "source": "music/clean-pulse.mp3",
      "license": "music/clean-pulse.license.json",
      "loop": true
    }
  ],
  "selected": "calm-tech",
  "gap_db": 24,
  "offset_db": 0
}
```

- `id` 使用稳定、可读的短标识；候选增删不覆盖已选版本。
- `source` 和 `license` 都是项目根目录下的相对路径。授权记录字段仍为 title、artist、source_url、license、attribution，保留真实授权状态，不把用户提供等同于公开授权已核实。
- `loop:true` 只在素材短于旁白时循环该素材；仍须检查循环点、尾部和淡出。长素材默认不循环。
- `selected` 缺省指向第一条候选，便于旧项目兼容；用户确认后必须写成明确的候选 id。
- `gap_db` 是基础避让（6–36 dB），`offset_db` 是用户试听调整（−18–8 dB）。没有配置或 `enabled:false` 时输出纯旁白。不要把当前样片的强音乐档位当作所有视频的默认值。

## 多条制作与选择流程

1. 准备候选：把每条音乐的源文件和独立授权记录复制进项目，先用 `music-candidates` 核对列表、当前选择和素材哈希。

```powershell
python scripts/studio.py music-candidates P
```

2. 逐条试听：为每条候选生成音量匹配后的 WAV 预览和 manifest；预览不改变项目中的当前选择。

```powershell
python scripts/studio.py music-audition P --output review/music-audition-v1
```

3. 实际听完每条预览后，按两种方式之一选定当前曲目：用户不指定时随机选一条；用户指定时按 id 选择。随机选择必须记录实际结果和种子，指定选择必须记录用户原话。两者都只写当前候选，不跳过最终混音试听。

```powershell
# 不指定时随机选择
python scripts/studio.py music-select P --evidence "用户不指定，随机选择"

# 用户指定候选
python scripts/studio.py music-select P --candidate-id clean-pulse --evidence "用户明确选择 clean-pulse"
```

4. 选择完成后，`studio render P --draft` 自动混音并生成同目录 `mixer.html`。音乐与旁白同一音频时钟；视频只做画面跟随，漂移超过 80 ms 时校正。切后台自动暂停。页面先加载本地视频和两条音轨，适用于短视频；大体积视频会增加内存占用。
5. 滑杆针对真正的零偏移音乐床，仅应用一次增益，保留与导出相同的余量限制。用户给出数值后写回 `music.offset_db`，再导出对应审核视频。页面调节本身不会修改项目配置。
6. `studio status P` 显示音乐 identity。对当前混音取得真实确认后运行 `studio approve-music P --review-hash <music identity> --evidence "用户原话与对应试听产物"`。已确认声音与新混音哈希完全相同时可复用原确认，不额外试听。不把纯旁白确认或候选试听确认当混音确认。
7. `studio render P` 自动包含音乐，并在 `state.json` 与导出 manifest 记录最终 identity、候选 id、素材/授权/旁白/音量依赖和音轨哈希；带音乐时同时输出 `soundtrack.wav`。改音乐、选择或音量只重混音、复用画面缓存。改字幕或画面保留音乐缓存与音乐确认，但重新核对对应画面 QA。改旁白或时长使音乐与音乐确认失效。循环开关也属于音乐身份的一部分。

旧 `mix_background.py` 保留给历史项目，不再作为新项目正式交付入口。旧 mixer.html 不原地覆盖；使用新导出目录的页面。最终审核仍对应完整 MP4，实时调音页不能替代字幕逐句审核。

历史发布文件不可覆盖。`status` 依据当前依赖识别音乐过期，导出是带独立 manifest 的不可变版本。
