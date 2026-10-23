import argparse
import csv
import hashlib
import json
import os
import shlex
import sys
from pathlib import Path

VFS_NAME = "vfs"
HEAD_LINES = 10


def parse_command(line):
    """Разбирает команду и раскрывает переменные окружения ОС."""
    try:
        parts = shlex.split(os.path.expandvars(line))
    except ValueError as error:
        raise ValueError(f"invalid syntax: {error}") from error
    return (parts[0], parts[1:]) if parts else (None, [])


class VirtualFileSystem:
    """Файловая система в памяти, загружаемая из CSV."""

    def __init__(self, csv_path):
        """Загружает записи виртуальной файловой системы из CSV."""
        self.name = Path(csv_path).stem
        self.entries = {}
        self.cwd = "/"
        self.history = []
        raw_data = Path(csv_path).read_bytes()
        self.sha256 = hashlib.sha256(raw_data).hexdigest()
        self._load_entries(raw_data)

    def _load_entries(self, raw_data):
        """Разбирает CSV и проверяет структуру виртуальной файловой системы."""
        try:
            text = raw_data.decode("utf-8-sig")
            rows = csv.DictReader(text.splitlines())
            required = {"path", "type", "content"}
            if not required.issubset(rows.fieldnames or []):
                raise ValueError(
                    "CSV must have path,type,content columns"
                )
            for row in rows:
                self._add_entry(row)
            self.entries.setdefault(
                "/", {"type": "dir", "content": ""}
            )
            self._validate_entries()
        except (UnicodeDecodeError, csv.Error) as error:
            raise ValueError(f"invalid VFS CSV: {error}") from error

    def _add_entry(self, row):
        """Добавляет одну запись CSV после проверки её полей."""
        path = self.normalize(row["path"])
        kind = row["type"].strip()
        if not path or kind not in ("file", "dir"):
            raise ValueError(f"invalid VFS entry: {row}")
        if path in self.entries:
            raise ValueError(f"duplicate path: {path}")
        self.entries[path] = {
            "type": kind,
            "content": row.get("content", ""),
        }

    def _validate_entries(self):
        """Проверяет наличие родительских каталогов и их тип."""
        for path in list(self.entries):
            if path == "/":
                continue
            parent = str(Path(path).parent)
            if parent == ".":
                parent = "/"
            if parent not in self.entries:
                raise ValueError(f"parent directory missing: {parent}")
            if self.entries[parent]["type"] != "dir":
                raise ValueError(f"parent is not a directory: {parent}")

    @staticmethod
    def normalize(path):
        """Приводит путь к форме от корня виртуальной файловой системы."""
        return "/" + str(Path("/" + path.lstrip("/"))).lstrip("./")

    def resolve(self, path):
        """Возвращает абсолютный путь внутри виртуальной файловой системы."""
        if not path:
            return self.cwd
        if path.startswith("/"):
            candidate = os.path.normpath(path)
        else:
            candidate = os.path.normpath(os.path.join(self.cwd, path))
        return "/" + candidate.lstrip("/")

    def exists(self, path):
        """Проверяет, существует ли путь."""
        return self.resolve(path) in self.entries

    def children(self, path):
        """Возвращает отсортированные имена непосредственных потомков."""
        directory = self.resolve(path)
        prefix = directory.rstrip("/") + "/"
        result = []
        for name in self.entries:
            if name == directory or not name.startswith(prefix):
                continue
            rest = name[len(prefix):]
            if rest and "/" not in rest:
                suffix = "/" if self.entries[name]["type"] == "dir" else ""
                result.append(rest + suffix)
        return sorted(result)

    def list_dir(self, path="."):
        """Возвращает содержимое каталога или имя файла."""
        target = self.resolve(path)
        if target not in self.entries:
            raise ValueError(f"no such file or directory: {path}")
        entry = self.entries[target]
        if entry["type"] == "file":
            return [Path(target).name]
        return self.children(target)

    def read_file(self, path):
        """Возвращает содержимое файла."""
        target = self.resolve(path)
        entry = self.entries.get(target)
        if not entry or entry["type"] != "file":
            raise ValueError(f"not a file: {path}")
        return entry["content"]

    def remove_dir(self, path):
        """Удаляет пустой каталог, кроме корневого."""
        target = self.resolve(path)
        if target == "/" or target not in self.entries:
            raise ValueError(
                f"directory not found or cannot remove root: {path}"
            )
        if self.entries[target]["type"] != "dir":
            raise ValueError(f"not a directory: {path}")
        if self.children(target):
            raise ValueError(f"directory is not empty: {path}")
        del self.entries[target]

    def _copy_destination(self, src, destination):
        """Вычисляет и проверяет путь назначения для копирования."""
        dst = self.resolve(destination)
        if dst in self.entries and self.entries[dst]["type"] == "dir":
            dst = dst.rstrip("/") + "/" + Path(src).name
        if dst == src or dst.startswith(src.rstrip("/") + "/"):
            raise ValueError("cannot copy a directory into itself")
        if dst in self.entries:
            raise ValueError(f"destination already exists: {dst}")
        parent = str(Path(dst).parent)
        if parent == ".":
            parent = "/"
        if (
            parent not in self.entries
            or self.entries[parent]["type"] != "dir"
        ):
            raise ValueError(
                f"destination directory does not exist: {parent}"
            )
        return dst

    def copy(self, source, destination):
        """Копирует файл или каталог внутри виртуальной файловой системы."""
        src = self.resolve(source)
        if src not in self.entries:
            raise ValueError(f"source not found: {source}")
        dst = self._copy_destination(src, destination)
        prefix = src.rstrip("/") + "/"
        to_copy = [
            path for path in self.entries
            if path == src or path.startswith(prefix)
        ]
        copies = {
            dst + path[len(src):]: self.entries[path].copy()
            for path in to_copy
        }
        self.entries.update(copies)


def _require_arg_count(args, expected, usage):
    """Проверяет количество аргументов команды."""
    if len(args) != expected:
        raise ValueError(f"usage: {usage}")


def _cmd_vfs_info(args, vfs):
    """Печатает имя виртуальной файловой системы и её SHA-256."""
    _require_arg_count(args, 0, "vfs-info")
    if vfs is None:
        raise ValueError("VFS is not loaded")
    print(f"Name: {vfs.name}")
    print(f"SHA-256: {vfs.sha256}")


def _cmd_ls(args, vfs):
    """Выводит содержимое каталога."""
    if len(args) > 1:
        raise ValueError("usage: ls [path]")
    for item in vfs.list_dir(args[0] if args else "."):
        print(item)


def _cmd_cd(args, vfs):
    """Меняет текущий каталог виртуальной файловой системы."""
    if len(args) > 1:
        raise ValueError("usage: cd [path]")
    target = vfs.resolve(args[0] if args else "/")
    if target not in vfs.entries or vfs.entries[target]["type"] != "dir":
        invalid_path = args[0] if args else target
        raise ValueError(f"not a directory: {invalid_path}")
    vfs.cwd = target


def _cmd_history(args, vfs):
    """Печатает историю команд."""
    _require_arg_count(args, 0, "history")
    for number, line in enumerate(vfs.history, 1):
        print(f"{number} {line}")


def _cmd_rev(args, vfs):
    """Выводит перевёрнутое содержимое файла или последней команды."""
    if len(args) > 1:
        raise ValueError("usage: rev [file]")
    if args:
        result = vfs.read_file(args[0])[::-1]
    else:
        last_command = vfs.history[-1] if vfs.history else ""
        result = last_command[::-1]
    print(result)


def _cmd_rmdir(args, vfs):
    """Удаляет пустой каталог."""
    _require_arg_count(args, 1, "rmdir directory")
    vfs.remove_dir(args[0])
    print(f"Removed directory: {args[0]}")


def _cmd_cp(args, vfs):
    """Копирует файл или каталог."""
    _require_arg_count(args, 2, "cp source destination")
    vfs.copy(args[0], args[1])
    print(f"Copied {args[0]} to {args[1]}")


def _cmd_cat(args, vfs):
    """Печатает содержимое файла."""
    _require_arg_count(args, 1, "cat file")
    print(vfs.read_file(args[0]), end="")


def _cmd_head(args, vfs):
    """Печатает первые строки файла."""
    _require_arg_count(args, 1, "head file")
    content = vfs.read_file(args[0])
    print("\n".join(content.splitlines()[:HEAD_LINES]))


COMMANDS = {
    "vfs-info": _cmd_vfs_info,
    "ls": _cmd_ls,
    "cd": _cmd_cd,
    "history": _cmd_history,
    "rev": _cmd_rev,
    "rmdir": _cmd_rmdir,
    "cp": _cmd_cp,
    "cat": _cmd_cat,
    "head": _cmd_head,
}


def execute_command(command, args, vfs=None):
    """Выполняет команду. Возвращает False для выхода."""
    if command == "exit":
        if args:
            print("Error: exit does not accept arguments")
            return True
        return False
    if command in ("ls", "cd") and vfs is None:
        print(f"{command} {args}")
        return True
    try:
        handler = COMMANDS.get(command)
        if handler is None:
            print(f"Error: unknown command: {command}")
            return True
        handler(args, vfs)
    except (ValueError, KeyError) as error:
        print(f"Error: {error}")
    return True


def load_config(config_path):
    """Загружает конфигурацию из JSON-объекта."""
    try:
        with open(config_path, encoding="utf-8") as file:
            config = json.load(file)
        if not isinstance(config, dict):
            raise ValueError("configuration must be a JSON object")
        return config
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"cannot read configuration: {error}") from error


def _run_line(line, vfs):
    """Разбирает и выполняет одну строку скрипта или командной строки."""
    try:
        command, args = parse_command(line)
    except ValueError as error:
        print(f"Error: {error}")
        return True
    if command is None:
        return True
    if vfs is not None and command != "history":
        vfs.history.append(line)
    return execute_command(command, args, vfs)


def run_cli(vfs=None):
    """Запускает интерактивный цикл команд."""
    while True:
        prompt_name = vfs.name if vfs else VFS_NAME
        prompt_path = vfs.cwd if vfs else ""
        try:
            line = input(f"{prompt_name}:{prompt_path}> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line.strip():
            continue
        if not _run_line(line, vfs):
            break


def run_script(script_path, vfs):
    """Выполняет команды из стартового скрипта."""
    try:
        with open(script_path, encoding="utf-8") as file:
            for raw_line in file:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                prompt_name = vfs.name if vfs else VFS_NAME
                print(f"{prompt_name}> {line}")
                if not _run_line(line, vfs):
                    break
    except OSError as error:
        print(f"Error: cannot run startup script: {error}")


def main():
    """Запускает эмулятор."""
    """Параметры JSON имеют приоритет над аргументами CLI."""
    parser = argparse.ArgumentParser(
        description="Shell emulator with an in-memory VFS"
    )
    parser.add_argument("--vfs", help="path to VFS CSV")
    parser.add_argument("--script", help="path to startup script")
    parser.add_argument("--config", help="path to JSON configuration")
    args = parser.parse_args()

    options = {"vfs": args.vfs, "script": args.script}
    if args.config:
        try:
            options.update(load_config(args.config))
        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)

    print(f"Configuration: {options}")
    vfs = None
    if options.get("vfs"):
        try:
            vfs = VirtualFileSystem(options["vfs"])
            motd = vfs.entries.get("/motd")
            if motd and motd["type"] == "file":
                print(motd["content"])
        except (OSError, ValueError) as error:
            print(f"Error loading VFS: {error}", file=sys.stderr)
            sys.exit(1)

    if options.get("script"):
        run_script(options["script"], vfs)
    else:
        run_cli(vfs)


if __name__ == "__main__":
    main()
