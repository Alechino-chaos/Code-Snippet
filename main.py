import sys
import json
import os
import json

from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax

console = Console()

DEFAULT_DB_PATH = os.path.join(os.path.expanduser("~"), ".snip_data.json")
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".snip_config.json")

def get_db_path():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get("db_path", DEFAULT_DB_PATH)
    return DEFAULT_DB_PATH

FILE_NAME = get_db_path()

def load_data():
    if not os.path.exists(FILE_NAME):
        return {}
    
    with open(FILE_NAME, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}
        
def save_data(data):
    with open(FILE_NAME, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def config_path():
    new_path = input("Please enter the complete path (For example: D:\\data\\mysnips.json): ")

    dir_name = os.path.dirname(new_path)
    if dir_name and not os.path.exists(dir_name):
        print(f"❌ Error: The folder {dir_name} does not exist. Please create it first.")
        return

    with open(CONFIG_FILE, 'w') as f:
        json.dump({"db_path": new_path}, f)
    
    print(f"✅ Setup completed! From now on, the code will be saved at: {new_path}")

def add_snippet():
    tag = input("Please enter the label of the code snippet: ")
    print("Please enter the code (type 'END' on a new line to save):")

    lines = []
    while True:
        line = input()
        if line == 'END':
            break
        lines.append(line)
    code = '\n'.join(lines)
    data = load_data()
    data[tag] = code
    save_data(data)
    print(f"✅ The code snippet labeled as [{tag}] has been successfully saved! ")

def find_snippet():
    tag = input("Please enter the label you want to find: ")
    data = load_data()

    if tag in data:
        console.print(f"\n[bold green]🔍 Find the code for the tag [{tag}]: [/bold green]")
        syntax = Syntax(data[tag], "python", theme="monokai", line_numbers=True)
        console.print(syntax)
        print()
    else:
        console.print(f"[bold red]❌ Sorry, no code snippet labeled as [{tag}] was found.[/bold red]")

def list_snippet():
    data = load_data()

    if not data:
        console.print("📭 There are no code snippets saved yet.")
        return

    table = Table(title="📦 Code snippets", show_header=True, header_style="bold magenta")
    table.add_column("Number", style="dim", width=6, justify="center")
    table.add_column("Tag", style="cyan")
    table.add_column("Preview", style="green")
    
    for index, (tag, code) in enumerate(data.items(), 1):
        first_line = code.split('\n')[0]
        preview = first_line[:40] + '...' if len(first_line) > 40 else first_line
        table.add_row(str(index), tag, preview)
        
    console.print(table)

def delete_snippet():
    tag = input("Please enter the label you want to delete: ")
    data = load_data()

    if tag in data:
        del data[tag]
        save_data(data)
        print(f"🗑️ The code snippet labeled as [{tag}] has been successfully deleted!")

    else:
        print(f"❌ Sorry, the label [{tag}] does not exist.")

def main():
    if len(sys.argv) < 2:
        print("💡 Welcome to use Code Spippet V1.0")
        print("The usage method:")
        print("  python main.py add   ->  add new code")
        print("  python main.py find  ->  search for existing code")
        return
    
    command = sys.argv[1]

    if command == 'config':
        config_path()
    elif command == 'add':
        add_snippet()
    elif command == 'find':
        find_snippet()
    elif command == 'list':
        list_snippet()
    elif command == 'delete':
        delete_snippet()
    else:
        print(f"⚠️ Unknown command: {command}")

if __name__ == "__main__":
    main()