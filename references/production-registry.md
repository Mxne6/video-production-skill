# 产品视频生产记录

Skill 维护一份跨项目记录，用来回答“某产品的中文版/英文版是否已经做过”，避免重复建项和重复制作：

- 事实源：`records/production-registry.json`
- 查表文件：`records/production-registry.md`

记录以产品名不区分大小写归一，语言固定为 `zh-CN` 和 `en`，状态为 `not_started / planned / in_progress / done`。`done` 必须绑定真实存在的导出文件；草稿、试听和未导出的项目不能登记为完成。

## 开工前

新视频确定产品名和目标语言后，先查完整记录，再决定是否建项：

```powershell
python scripts/production_registry.py check --product "S7000"
python scripts/production_registry.py check --product "S7000" --language en
```

如果 `en` 已是 `done`，不要直接重复制作；先核对导出文件、项目路径和用户是否明确要求新版本。中文未制作、英文已完成时，正常单独制作中文版。`check` 返回 `not_started` 才能直接开工。

## 制作中

开始制作时登记一次，后续新会话可据此恢复：

```powershell
python scripts/production_registry.py record --product "S7000" --language zh-CN --status in_progress --project P --note "中文版制作中"
```

## 完工后

正式导出成功后登记。`--export` 相对项目根目录；不传时从项目 `state.json.export.path` 读取。工具会确认导出文件真实存在，不存在则不写完成记录：

```powershell
python scripts/production_registry.py record --product "S7000" --language zh-CN --status done --project P --note "中文正式版"
python scripts/production_registry.py record --product "S7000" --language en --status done --project P-en --note "英文正式版"
```

同一产品同一语言已经是 `done` 时默认阻断；只有用户明确要求新版本时才加 `--force`。记录完成后，`records/production-registry.md` 会生成一张产品 × 语言表，直接回答“中文做了没有、英文做了没有”。
