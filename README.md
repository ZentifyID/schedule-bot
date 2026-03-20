# schedule-bot

Telegram-бот, который:
- берет базовое расписание группы (числитель/знаменатель)
- ищет на публичном Яндекс Диске `.docx` по дате
- парсит замены и выдает итоговое расписание

## Файлы
- `main.py` - точка входа CLI
- `schedule_bot/cli.py` - команды CLI
- `schedule_bot/schedule_service.py` - парсер docx, merge базового расписания и замен, CSV->JSON
- `schedule_bot/yandex_disk.py` - работа с публичной ссылкой Яндекс Диска
- `schedule_bot/telegram_bot.py` - Telegram long polling и команды бота
- `schedule.base.csv` - удобный шаблон базового расписания для заполнения
- `schedule.base.json` - итоговый файл, который читает бот

## Как заполнять оригинальное расписание (рекомендуется)
1. Открой `schedule.base.csv` в Excel/Google Sheets.
2. Заполни строки по всем парам для Пн-Пт отдельно для `числитель` и `знаменатель`.
3. Сконвертируй в JSON:
```powershell
python main.py csv-to-json --csv schedule.base.csv --out schedule.base.json --group "31 ИС"
```

Колонки CSV:
- `week_type`: `числитель` или `знаменатель`
- `weekday`: `понедельник|вторник|среда|четверг|пятница`
- `pair`: `I..VII`
- `subject`, `teacher`, `room`

## Проверка на локальном файле замен
```powershell
python main.py check-docx --docx "C:\Users\zgami\Downloads\23.03.2026.docx" --base schedule.base.json --group "31 ИС"
```

## Запуск Telegram-бота
Переменные окружения:
- `TELEGRAM_BOT_TOKEN` - токен бота
- `YANDEX_PUBLIC_URL` - публичная ссылка на папку/файл замен
- `TARGET_GROUP` - например `31 ИС` (опционально)
- `BOT_TIMEZONE` - например `Europe/Saratov` (опционально)
- `WEEK1_START_DATE` - `YYYY-MM-DD` (опционально, если не найден файл замен)

Запуск:
```powershell
python main.py run-bot --base schedule.base.json --group "31 ИС" --yandex-public-url "https://disk.yandex.ru/d/F_GFm6_Qi9GYAQ"
```

Команды в Telegram:
- `/today`
- `/tomorrow`
- `/date YYYY-MM-DD` (также `YYYY.MM.DD` и `DD.MM.YYYY`)
