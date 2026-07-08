import argparse
import copy
import json
import os
import sys
import uuid
from datetime import datetime

from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table


VERSION = "1.1.0"
SCHEMA_VERSION = 2
DEFAULT_LANGUAGE = "python"
DEFAULT_DB_PATH = os.path.join(os.path.expanduser("~"), ".snip_data.json")
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".snip_config.json")

console = Console()


class SnipError(Exception):
    """Raised for user-facing snip command errors."""


def get_db_path(config_file=None):
    config_file = config_file or CONFIG_FILE
    if not os.path.exists(config_file):
        return DEFAULT_DB_PATH

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as exc:
        raise SnipError(f"配置文件不是有效的 JSON: {config_file}") from exc

    return config.get("db_path") or DEFAULT_DB_PATH


def now_iso():
    return datetime.now().replace(microsecond=0).isoformat()


def empty_data():
    return {"__schema_version": SCHEMA_VERSION, "snippets": {}}


def normalize_snippet(value, timestamp=None):
    timestamp = timestamp or now_iso()
    if isinstance(value, str):
        return {
            "code": value,
            "language": DEFAULT_LANGUAGE,
            "note": "",
            "created_at": timestamp,
            "updated_at": timestamp,
        }

    if not isinstance(value, dict):
        raise SnipError("代码片段格式错误，应为字符串或对象。")

    code = value.get("code")
    if not isinstance(code, str):
        raise SnipError("代码片段缺少有效的 code 字段。")

    language = value.get("language") or DEFAULT_LANGUAGE
    note = value.get("note") or ""
    created_at = value.get("created_at") or timestamp
    updated_at = value.get("updated_at") or created_at

    if not all(isinstance(item, str) for item in [language, note, created_at, updated_at]):
        raise SnipError("代码片段元信息格式错误。")

    return {
        "code": code,
        "language": language,
        "note": note,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def normalize_data(raw_data):
    if raw_data == {}:
        return empty_data()

    if not isinstance(raw_data, dict):
        raise SnipError("数据文件格式错误，应为 JSON 对象。")

    if raw_data.get("__schema_version") == SCHEMA_VERSION:
        snippets = raw_data.get("snippets")
        if not isinstance(snippets, dict):
            raise SnipError("v2 数据文件缺少有效的 snippets 字段。")

        normalized = empty_data()
        for tag, snippet in snippets.items():
            normalized["snippets"][validate_tag(tag)] = normalize_snippet(snippet)
        return normalized

    if "__schema_version" in raw_data or "snippets" in raw_data:
        raise SnipError("数据文件结构不受支持。")

    normalized = empty_data()
    timestamp = now_iso()
    for tag, code in raw_data.items():
        normalized["snippets"][validate_tag(tag)] = normalize_snippet(code, timestamp)
    return normalized


def read_json_file(path, missing_ok=False):
    if not os.path.exists(path):
        if missing_ok:
            return {}
        raise SnipError(f"文件不存在: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise SnipError(f"文件不是有效的 JSON: {path}") from exc


def load_data(db_path=None):
    db_path = db_path or get_db_path()
    return normalize_data(read_json_file(db_path, missing_ok=True))


def save_json_atomic(path, data):
    dir_name = os.path.dirname(path) or "."
    os.makedirs(dir_name, exist_ok=True)

    temp_path = os.path.join(dir_name, f"snip_{uuid.uuid4().hex}.tmp")
    content = json.dumps(data, indent=4, ensure_ascii=False) + "\n"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, path)
    except PermissionError:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        try:
            os.remove(temp_path)
        except OSError:
            pass
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def save_data(data, db_path=None):
    save_json_atomic(db_path or get_db_path(), data)


def validate_tag(tag):
    tag = (tag or "").strip()
    if not tag:
        raise SnipError("标签不能为空。")
    return tag


def prompt_tag(message):
    return validate_tag(input(message).strip())


def read_multiline_code():
    console.print("请输入代码内容，单独输入一行 END 保存：")
    lines = []
    while True:
        line = input()
        if line == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def should_overwrite(tag):
    answer = input(f"标签「{tag}」已存在，是否覆盖？[y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def get_snippets(data):
    return data["snippets"]


def make_snippet(code, language=DEFAULT_LANGUAGE, note="", timestamp=None):
    timestamp = timestamp or now_iso()
    return {
        "code": code,
        "language": language or DEFAULT_LANGUAGE,
        "note": note or "",
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def preview_text(text, max_length=40):
    first_line = str(text).split("\n")[0]
    return first_line[:max_length] + "..." if len(first_line) > max_length else first_line


def config_path(path=None):
    new_path = (path or input("请输入完整的数据文件路径，例如 D:\\data\\mysnips.json: ")).strip()
    if not new_path:
        raise SnipError("数据文件路径不能为空。")

    dir_name = os.path.dirname(new_path)
    if dir_name and not os.path.exists(dir_name):
        raise SnipError(f"文件夹不存在，请先创建: {dir_name}")

    save_json_atomic(CONFIG_FILE, {"db_path": new_path})
    console.print(f"配置完成，以后代码片段会保存到: {new_path}")


def add_snippet(tag=None, language=DEFAULT_LANGUAGE, note=""):
    tag = validate_tag(tag) if tag is not None else prompt_tag("请输入代码片段标签: ")
    code = read_multiline_code()
    data = load_data()
    snippets = get_snippets(data)

    if tag in snippets and not should_overwrite(tag):
        console.print(f"已取消保存，标签「{tag}」保持不变。")
        return

    snippets[tag] = make_snippet(code, language, note)
    save_data(data)
    console.print(f"代码片段「{tag}」已保存。")


def edit_snippet(tag=None, language=None, note=None):
    tag = validate_tag(tag) if tag is not None else prompt_tag("请输入要编辑的标签: ")
    data = load_data()
    snippets = get_snippets(data)

    if tag not in snippets:
        raise SnipError(f"标签「{tag}」不存在。")

    current = snippets[tag]
    code = read_multiline_code()
    updated = copy.deepcopy(current)
    updated["code"] = code
    if language is not None:
        updated["language"] = language or DEFAULT_LANGUAGE
    if note is not None:
        updated["note"] = note
    updated["updated_at"] = now_iso()
    snippets[tag] = normalize_snippet(updated)
    save_data(data)
    console.print(f"代码片段「{tag}」已更新。")


def find_snippet(tag=None):
    tag = validate_tag(tag) if tag is not None else prompt_tag("请输入要查找的标签: ")
    data = load_data()
    snippets = get_snippets(data)

    if tag in snippets:
        snippet = snippets[tag]
        console.print(f"\n[bold green]找到标签「{tag}」的代码：[/bold green]")
        print_code(snippet["code"], snippet["language"])
        if snippet["note"]:
            console.print(f"备注: {snippet['note']}")
        return

    console.print(f"[bold red]没有找到标签「{tag}」。[/bold red]")


def print_code(code, language):
    try:
        syntax = Syntax(
            code,
            language or DEFAULT_LANGUAGE,
            theme="monokai",
            line_numbers=True,
        )
        console.print(syntax)
    except Exception:
        console.print(code)


def add_snippet_row(table, index, tag, snippet):
    table.add_row(
        str(index),
        tag,
        snippet["language"],
        preview_text(snippet["note"], 24),
        preview_text(snippet["code"]),
        snippet["updated_at"],
    )


def list_snippet(language=None):
    data = load_data()
    snippets = get_snippets(data)

    if language:
        snippets = {
            tag: snippet
            for tag, snippet in snippets.items()
            if snippet["language"] == language
        }

    if not snippets:
        console.print("还没有保存任何代码片段。")
        return

    table = Table(title="代码片段", show_header=True, header_style="bold magenta")
    table.add_column("序号", style="dim", width=6, justify="center")
    table.add_column("标签", style="cyan")
    table.add_column("语言", style="yellow")
    table.add_column("备注", style="blue")
    table.add_column("预览", style="green")
    table.add_column("更新时间", style="magenta")

    for index, (tag, snippet) in enumerate(snippets.items(), 1):
        add_snippet_row(table, index, tag, snippet)

    console.print(table)


def search_snippet(keyword):
    keyword = (keyword or "").strip()
    if not keyword:
        raise SnipError("搜索关键字不能为空。")

    data = load_data()
    matched = []
    lowered = keyword.lower()
    for tag, snippet in get_snippets(data).items():
        haystack = "\n".join([tag, snippet["note"], snippet["code"]]).lower()
        if lowered in haystack:
            matched.append((tag, snippet))

    if not matched:
        console.print(f"没有找到包含「{keyword}」的代码片段。")
        return

    table = Table(title=f"搜索结果: {keyword}", show_header=True, header_style="bold magenta")
    table.add_column("序号", style="dim", width=6, justify="center")
    table.add_column("标签", style="cyan")
    table.add_column("语言", style="yellow")
    table.add_column("备注", style="blue")
    table.add_column("预览", style="green")
    table.add_column("更新时间", style="magenta")

    for index, (tag, snippet) in enumerate(matched, 1):
        add_snippet_row(table, index, tag, snippet)

    console.print(table)


def delete_snippet(tag=None):
    tag = validate_tag(tag) if tag is not None else prompt_tag("请输入要删除的标签: ")
    data = load_data()
    snippets = get_snippets(data)

    if tag not in snippets:
        console.print(f"[bold red]标签「{tag}」不存在。[/bold red]")
        return

    del snippets[tag]
    save_data(data)
    console.print(f"代码片段「{tag}」已删除。")


def export_snippets(path):
    path = (path or "").strip()
    if not path:
        raise SnipError("导出路径不能为空。")
    data = load_data()
    save_json_atomic(path, data)
    console.print(f"已导出到: {path}")


def import_snippets(path, overwrite=False):
    path = (path or "").strip()
    if not path:
        raise SnipError("导入路径不能为空。")

    incoming = normalize_data(read_json_file(path))
    data = load_data()
    snippets = get_snippets(data)

    imported = 0
    skipped = 0
    for tag, snippet in get_snippets(incoming).items():
        if tag in snippets and not overwrite:
            skipped += 1
            continue
        snippets[tag] = snippet
        imported += 1

    save_data(data)
    console.print(f"导入完成: 新增或覆盖 {imported} 个，跳过 {skipped} 个。")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="snip",
        description="Code-Snippet: 轻量级本地代码片段管理工具。",
    )
    parser.add_argument("--version", action="version", version=f"Code-Snippet {VERSION}")

    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="录入新的代码片段")
    add_parser.add_argument("tag", nargs="?", help="代码片段标签")
    add_parser.add_argument("--lang", default=DEFAULT_LANGUAGE, help="代码语言，默认 python")
    add_parser.add_argument("--note", default="", help="备注")

    list_parser = subparsers.add_parser("list", help="查看所有代码片段")
    list_parser.add_argument("--lang", help="只显示指定语言的代码片段")

    find_parser = subparsers.add_parser("find", help="按标签查找代码片段")
    find_parser.add_argument("tag", nargs="?", help="要查找的标签")

    edit_parser = subparsers.add_parser("edit", help="编辑已有代码片段")
    edit_parser.add_argument("tag", nargs="?", help="要编辑的标签")
    edit_parser.add_argument("--lang", help="更新代码语言")
    edit_parser.add_argument("--note", help="更新备注")

    search_parser = subparsers.add_parser("search", help="搜索标签、备注和代码内容")
    search_parser.add_argument("keyword", help="搜索关键字")

    delete_parser = subparsers.add_parser("delete", help="按标签删除代码片段")
    delete_parser.add_argument("tag", nargs="?", help="要删除的标签")

    config_parser = subparsers.add_parser("config", help="设置本地数据库保存路径")
    config_parser.add_argument("path", nargs="?", help="JSON 数据文件路径")

    export_parser = subparsers.add_parser("export", help="导出数据库为 JSON")
    export_parser.add_argument("path", help="导出文件路径")

    import_parser = subparsers.add_parser("import", help="从 JSON 导入代码片段")
    import_parser.add_argument("path", help="导入文件路径")
    import_parser.add_argument("--overwrite", action="store_true", help="覆盖重复标签")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "config":
            config_path(args.path)
        elif args.command == "add":
            add_snippet(args.tag, args.lang, args.note)
        elif args.command == "find":
            find_snippet(args.tag)
        elif args.command == "edit":
            edit_snippet(args.tag, args.lang, args.note)
        elif args.command == "search":
            search_snippet(args.keyword)
        elif args.command == "list":
            list_snippet(args.lang)
        elif args.command == "delete":
            delete_snippet(args.tag)
        elif args.command == "export":
            export_snippets(args.path)
        elif args.command == "import":
            import_snippets(args.path, args.overwrite)
    except SnipError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
