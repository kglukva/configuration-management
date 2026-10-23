# Shell Emulator — Configuration Management

Эмулятор командной оболочки UNIX-подобной ОС на Python 3. Команды выполняются над виртуальной файловой системой в памяти, загружаемой из CSV.

## Реализованные этапы

- **Этап 1 — REPL:** интерактивный CLI, раскрытие переменных окружения, `ls`, `cd`, `exit`, обработка ошибок.
- **Этап 2 — Конфигурация:** аргументы `--vfs`, `--script`, `--config`, JSON-конфигурация, стартовые скрипты и отображение параметров.
- **Этап 3 — VFS:** загрузка CSV, проверка ошибок, служебная команда `vfs-info` с SHA-256, сообщение `motd`.
- **Этап 4 — Основные команды:** `ls`, `cd`, `history`, `rev`; также доступны `cat` и `head`.
- **Этап 5 — Дополнительные команды:** `rmdir` и `cp`, изменения выполняются в памяти.

## Структура проекта

- `src/main.py` — реализация эмулятора.
- `tests/test_main.py` — автоматические тесты.
- `vfs.csv` — виртуальная файловая система.
- `config.json` — конфигурация.
- `scripts/` — сценарии проверки этапов.
- `run.sh` — запуск программы.

## Запуск

Требуется Python 3. Для базовой работы внешние библиотеки не нужны.

```bash
./run.sh --vfs vfs.csv
```

Запуск стартового скрипта:

```bash
./run.sh --vfs vfs.csv --script scripts/stage3.sh
```

Запуск через конфигурацию:

```bash
./run.sh --config config-script.json
```

Значения из JSON имеют приоритет над аргументами командной строки.

## Тестирование

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile src/main.py
```

## Примеры команд

```text
vfs:/> vfs-info
vfs:/> ls /
vfs:/> cd docs
vfs:/docs> ls
vfs:/docs> cat readme.txt
vfs:/docs> history
vfs:/docs> rev readme.txt
vfs:/docs> cp readme.txt copy.txt
vfs:/docs> exit
```

## Ограничения

Изменения `cp` и `rmdir` выполняются только в памяти и не сохраняются обратно в исходный CSV. Команда `rmdir` удаляет только пустые каталоги.

