# 🚀 Code-Snippet: 你的代码片段管家

**Code-Snippet** 是一个为开发者设计的轻量级命令行工具，旨在帮助你快速存储、检索和管理常用的代码片段。基于 Python 开发，拥有舒适的终端交互体验。

## ✨ 核心特性

- 📦 **全局召唤**：安装后在任何目录下输入 `snip` 即可快速使用。
- 🎨 **颜值拉满**：使用 Rich 驱动，提供彩色表格视图和代码语法高亮。
- ⌨️ **多行录入**：完美支持一键粘贴多行代码，输入 `END` 即可保存。
- ⚙️ **高度自定义**：支持用户自定义本地数据库的存储路径。
- 🔎 **更好检索**：支持语言、备注、内容搜索、导入导出和编辑已有片段。
- 🧩 **脚本友好**：支持参数、文件和标准输入录入，也支持纯代码输出。

## 🛠️ 快速开始

### 下载与安装

```bash
git clone https://github.com/Alechino-chaos/Code-Snippet.git
cd Code-Snippet
pip install -e .
```

### 📖 使用指南

安装完成后，你可以在终端的任何位置直接敲击 `snip` 以及搭配对应的参数来使用！

查看帮助和版本：

```bash
snip --help
snip --version
```

➕ 1. **录入代码**

```bash
snip add
snip add demo
snip add demo --lang python --note "常用打印示例"
snip add demo --code "print('hello')"
snip add demo --file demo.py
Get-Content demo.py | snip add demo --stdin
```

不传 `--code`、`--file` 或 `--stdin` 时，会进入交互式多行录入，单独输入一行 `END` 保存。三种非交互录入方式不能同时使用。如果标签已存在，会询问是否覆盖，默认不覆盖。

📋 2. **查看库存**

```bash
snip list
snip list --lang python
snip list --sort tag
snip list --sort updated --reverse
```

支持按 `tag`、`language`、`updated` 排序，默认按 `updated` 排序。

🔍 3. **查找片段**

```bash
snip find
snip find demo
snip find demo --plain
snip find demo --no-line-numbers
```

`snip find` 会根据片段保存的 `language` 字段进行语法高亮。`--plain` 只输出代码内容，适合复制、重定向或脚本调用。

🔎 4. **搜索片段**

```bash
snip search demo
snip search requests
snip search requests --lang python
```

搜索范围包括标签、备注和代码内容，也可以用 `--lang` 限定语言。

✏️ 5. **编辑片段**

```bash
snip edit demo
snip edit demo --lang javascript --note "浏览器调试版本"
```

编辑时会重新录入代码内容，并更新 `updated_at`。

🏷️ 6. **重命名片段**

```bash
snip rename old-tag new-tag
snip rename old-tag new-tag --overwrite
```

默认不会覆盖已有的新标签；加上 `--overwrite` 才会覆盖。

🗑️ 7. **删除片段**

```bash
snip delete
snip delete demo
```

⚙️ 8. **查看和自定义存储路径**

```bash
snip path
snip config
snip config D:\data\mysnips.json
```

📤 9. **导入导出**

```bash
snip export D:\backup\snips.json
snip import D:\backup\snips.json
snip import D:\backup\snips.json --overwrite
```

导入时如果遇到重复标签，默认跳过；加上 `--overwrite` 才会覆盖已有片段。

## 🗃️ 数据存储

- 默认数据库路径：`~/.snip_data.json`
- 配置文件路径：`~/.snip_config.json`
- 旧版数据格式 `{ "标签": "代码内容" }` 仍可读取。
- 新版数据会保存为 v2 结构：

```json
{
  "__schema_version": 2,
  "snippets": {
    "demo": {
      "code": "print('hi')",
      "language": "python",
      "note": "optional note",
      "created_at": "2026-07-08T18:00:00",
      "updated_at": "2026-07-08T18:00:00"
    }
  }
}
```

- 旧版数据在新增、编辑、删除、导入等写入操作后会自动保存为 v2。
- 保存时会使用临时文件和原子替换，降低异常中断导致文件损坏的风险。

## 💾 备份与恢复

备份：

```bash
snip export D:\backup\snips.json
```

恢复：

```bash
snip import D:\backup\snips.json
```

如果希望恢复文件覆盖当前同名标签：

```bash
snip import D:\backup\snips.json --overwrite
```

## 🧯 常见提示

- 如果提示“数据文件不是有效的 JSON”，说明数据库文件内容已损坏，需要手动修复 JSON 格式。
- 如果提示“文件夹不存在”，请先创建目标文件夹，再执行 `snip config <path>`。
- 标签不能为空；重复标签保存时需要确认覆盖。
- 如果导入后数量少于文件中的片段数量，通常是因为重复标签被默认跳过了。
