import os
import shlex


VFS_NAME = "vfs"


def parse_command(line):
    """Разбирает строку на команду и аргументы."""
    expanded_line = os.path.expandvars(line)

    try:
        parts = shlex.split(expanded_line)
    except ValueError as error:
        raise ValueError(f"invalid syntax: {error}") from error

    if not parts:
        return None, []

    return parts[0], parts[1:]


def execute_command(command, args):
    """Выполняет команду и возвращает True, если нужно продолжить."""
    if command == "exit":
        if args:
            print("Error: exit does not accept arguments")
            return True

        return False

    if command == "ls":
        print(f"ls {args}")
        return True

    if command == "cd":
        print(f"cd {args}")
        return True

    print(f"Error: unknown command: {command}")
    return True


def run_cli():
    """Запускает интерактивный режим эмулятора."""
    while True:
        try:
            line = input(f"{VFS_NAME}> ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue

        try:
            command, args = parse_command(line)
        except ValueError as error:
            print(f"Error: {error}")
            continue

        if command is None:
            continue

        if not execute_command(command, args):
            break


def main():
    """Точка входа в программу."""
    run_cli()


if __name__ == "__main__":
    main()

