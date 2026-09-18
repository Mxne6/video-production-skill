# 按产品名称查资料

本机公司知识库：`D:\CMS产品知识库`，当前以 SQLite 数据库 `D:\CMS产品知识库\database\product_knowledge_base.sqlite3` 为检索入口。用户只给型号（例如 SRA-8711）或产品名称即可启动查询。该路径是用户本机资料位置，不是 Skill 自带文件；其他机器不可访问时明确说明并请求资料路径。旧 `D:\新建文件夹 (3)\公司产品库` 路径和旧 `scripts/search_knowledge_base.py` 已不存在，不要继续调用。

## 只读检索

先读取 `D:\CMS产品知识库` 适用的 AGENTS.md（如有），再查询数据库。可用 Python 的 `sqlite3` 读取 products、aliases、documents、product_documents、specifications、document_chunks 等表；先按精确型号查 products.name 和 product_code，再查 aliases。示例：

```powershell
```powershell
python -X utf8 -c "import sqlite3; p=r'D:\CMS产品知识库\database\product_knowledge_base.sqlite3'; con=sqlite3.connect(p); print(con.execute('select id,name,product_code from products where upper(name) like ? or upper(coalesce(product_code,\'\')) like ?', ('%SRA-8711%','%SRA-8711%')).fetchall())"
```
```

替换示例为用户给出的型号或名称。先查原始名称，再按必要的大小写、空格、连字符变体核对，不把不同型号合并。搜索命中只是定位线索，不能将检索排名当作型号已确认或性能证据。

## 读取与归档

- 以结果返回的 `documents.local_path` 或 `product_documents` 关联定位 PDF；结果可能为相对路径或 source_files 哈希路径，不假定所有版本字段一致。
- 优先读数据库 `documents.content` 或 `document_chunks.content`；需要核对版式、单位或表格时打开 `documents.local_path` 指向的原 PDF。
- 文本缺失、提取错乱、表格单位/布局影响含义时查看原 PDF；原 PDF 是权威来源。
- 核对产品型号、中文名称、公司、用途和资料版本。存在多个不同产品匹配、资料矛盾且影响表述时，给出具体候选再询问用户。
- 确定资料后复制相关 PDF 到新视频项目 sources/，记录原路径、SHA256、页码与证据。仅复制实际用到的资料，不修改知识库。
- 产品名不能代替稿件批准：找到资料后按正常流程联合准备正文、固定公司片尾与画面，再进行整片稿件审核。

查无结果时说明已经查过的名称和缺项，再请用户提供完整型号或资料；不编造产品事实，也不默认改用网络上同名的其他公司产品。
