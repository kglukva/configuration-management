
import argparse
import csv
import hashlib
import json
import os
import shlex
import sys
from pathlib import Path


VFS_NAME = "vfs"


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
        self.name = Path(csv_path).stem
        self.entries = {}
        self.cwd = "/"
        self.history = []
        raw_data = Path(csv_path).read_bytes()
        self.sha256 = hashlib.sha256(raw_data).hexdigest()

        try:
            text = raw_data.decode("utf-8-sig")
            rows = csv.DictReader(text.splitlines())
            if not {"path", "type", "content"}.issubset(rows.fieldnames or []):
                raise ValueError("CSV must have path,type,content columns")

            for row in rows:
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

            self.entries.setdefault("/", {"type": "dir", "content": ""})
            for path in list(self.entries):
                parent = str(Path(path).parent)
                if parent == ".":
                    parent = "/"
                if path != "/" and parent not in self.entries:
                    raise ValueError(f"parent directory missing: {parent}")
                if path != "/" and self.entries[parent]["type"] != "dir":
                    raise ValueError(f"parent is not a directory: {parent}")

        except (UnicodeDecodeError, csv.Error) as error:
            raise ValueError(f"invalid VFS CSV: {error}") from error

    @staticmethod
    def normalize(path):
        return "/" + str(Path("/" + path.lstrip("/"))).lstrip("./")

    def resolve(self, path):
        if not path:
            return self.cwd
        if path.startswith("/"):
            candidate = os.path.normpath(path)
        else:
            candidate = os.path.normpath(os.path.join(self.cwd, path))
        return "/" + candidate.lstrip("/")

    def exists(self, path):
        return self.resolve(path) in self.entries

    def children(self, path):
        directory = self.resolve(path)
        prefix = directory.rstrip("/") + "/"
        result = []
        for name in self.entries:
            if name == directory:
                continue
            if name.startswith(prefix):
                rest = name[len(prefix):]
                if rest and "/" not in rest:
                    result.append(rest + ("/" if self.entries[name]["type"] == "dir" else ""))
        return sorted(result)

    def list_dir(self, path="."):
        target = self.resolve(path)
        if target not in self.entries:
            raise ValueError(f"no such file or directory: {path}")
        entry = self.entries[target]
        if entry["type"] == "file":
            return [Path(target).name]
        return self.children(target)

    def read_file(self, path):
        target = self.resolve(path)
        entry = self.entries.get(target)
        if not entry or entry["type"] != "file":
            raise ValueError(f"not a file: {path}")
        return entry["content"]

    def remove_dir(self, path):
        target = self.resolve(path)
        if target == "/" or target not in self.entries:
            raise ValueError(f"directory not found or cannot remove root: {path}")
        if self.entries[target]["type"] != "dir":
            raise ValueError(f"not a directory: {path}")
        if self.children(target):
            raise ValueError(f"directory is not empty: {path}")
        del self.entries[target]

    def copy(self, source, destination):
        src = self.resolve(source)
        dst = self.resolve(destination)
        if src not in self.entries:
            raise ValueError(f"source not found: {source}")
        if dst in self.entries and self.entries[dst]["type"] == "dir":
            dst = dst.rstrip("/") + "/" + Path(src).name
        if dst == src or dst.startswith(src.rstrip("/") + "/"):
            raise ValueError("cannot copy a directory into itself")
        if dst in self.entries:
            raise ValueError(f"destination already exists: {dst}")

        parent = str(Path(dst).parent)
        if parent == ".":
            parent = "/"
        if parent not in self.entries or self.entries[parent]["type"] != "dir":
            raise ValueError(f"destination directory does not exist: {parent}")

        to_copy = [p for p in self.entries if p == src or p.startswith(src.rstrip("/") + "/")]
        for old in to_copy:
            suffix = old[len(src):]
            self.entries[dst + suffix] = self.entries[old].copy()


def execute_command(command, args, vfs=None):
    """Выполняет команду. Возвращает False для выхода."""
    if command == "exit":
        if args:
            print("Error: exit does not accept arguments")
            return True
        return False

    if command == "ls" and vfs is None:
        print(f"ls {args}")
        return True
    if command == "cd" and vfs is None:
        print(f"cd {args}")
        return True

    try:
        if command == "vfs-info":
            if args:
                raise ValueError("vfs-info does not accept arguments")
            if vfs is None:
                raise ValueError("VFS is not loaded")
            print(f"Name: {vfs.name}")
            print(f"SHA-256: {vfs.sha256}")

        elif command == "ls":
            if len(args) > 1:
                raise ValueError("usage: ls [path]")
            for item in vfs.list_dir(args[0] if args else "."):
                print(item)

        elif command == "cd":
            if len(args) > 1:
                raise ValueError("usage: cd [path]")
            target = vfs.resolve(args[0] if args else "/")
            if target not in vfs.entries or vfs.entries[target]["type"] != "dir":
                raise ValueError(f"not a directory: {args[0] if args else target}")
            vfs.cwd = target

        elif command == "history":
            if args:
                raise ValueError("usage: history")
            for number, line in enumerate(vfs.history, 1):
                print(f"{number} {line}")

        elif command == "rev":
            if len(args) > 1:
                raise ValueError("usage: rev [file]")
            if args:
                print(vfs.read_file(args[0])[::-1])
            else:
                print(" ".join(vfs.history[-1:])[::-1] if vfs.history else "")

        elif command == "rmdir":
            if len(args) != 1:
                raise ValueError("usage: rmdir directory")
            vfs.remove_dir(args[0])
            print(f"Removed directory: {args[0]}")

        elif command == "cp":
            if len(args) != 2:
                raise ValueError("usage: cp source destination")
            vfs.copy(args[0], args[1])
            print(f"Copied {args[0]} to {args[1]}")

        elif command == "cat":
            if len(args) != 1:
                raise ValueError("usage: cat file")
            print(vfs.read_file(args[0]), end="")

        elif command == "head":
            if len(args) != 1:
                raise ValueError("usage: head file")
            print("\n".join(vfs.read_file(args[0]).splitlines()[:10]))

        else:
            print(f"Error: unknown command: {command}")

    except (ValueError, KeyError) as error:
        print(f"Error: {error}")

    return True


def load_config(config_path):
    try:
        with open(config_path, encoding="utf-8") as file:
            config = json.load(file)
        if not isinstance(config, dict):
            raise ValueError("configuration must be a JSON object")
        return config
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"cannot read configuration: {error}") from error


def run_cli(vfs=None):
    while True:
        try:
            line = input(f"{vfs.name if vfs else VFS_NAME}:{vfs.cwd if vfs else ''}> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        try:
            command, args = parse_command(line)
        except ValueError as error:
            print(f"Error: {error}")
            continue

        if command is None:
            continue

        if vfs is not None and command != "history":
            vfs.history.append(line)

        if not execute_command(command, args, vfs):
            break


def run_script(script_path, vfs):
    try:
        with open(script_path, encoding="utf-8") as file:
            for raw_line in file:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                print(f"{vfs.name if vfs else VFS_NAME}> {line}")
                try:
                    command, args = parse_command(line)
                except ValueError as error:
                    print(f"Error: {error}")
                    return
                if command is None:
                    continue
                if vfs is not None and command != "history":
                    vfs.history.append(line)
                if not execute_command(command, args, vfs):
                    break
    except OSError as error:
        print(f"Error: cannot run startup script: {error}")


def main():
    parser = argparse.ArgumentParser(description="Shell emulator with an in-memory VFS")
    parser.add_argument("--vfs", help="path to VFS CSV")
    parser.add_argument("--script", help="path to startup script")
    parser.add_argument("--config", help="path to JSON configuration")
    args = parser.parse_args()

    options = {"vfs": args.vfs, "script": args.script}
    if args.config:
        try:
            # Variant 9: values in the configuration file override CLI values.
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

