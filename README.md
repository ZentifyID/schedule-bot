# schedule-bot

Telegram-бот для учебного расписания группы с учетом:
- базового расписания (числитель/знаменатель),
- ежедневных замен из `.docx` по публичной ссылке Яндекс Диска,
- форматированного ответа по парам и времени.

## Возможности
- Читает замены из Яндекс Диска по дате (`dd.mm.yyyy` в названии файла).
- Находит только нужную группу (по умолчанию `31 ИС`).
- Накладывает замены на базовое расписание.
- Если файл замен не найден:
  - показывает базовое расписание,
  - добавляет предупреждение.
- Поддерживает темы (Topics) в Telegram-группах:
  - отвечает в той же теме, откуда пришла команда,
  - можно зафиксировать конкретную тему через `TELEGRAM_THREAD_ID`.

## Формат ответа
Пример:

`Расписание на среду 25 марта (числитель) для 31 ИС`

`3) 11:20-12:50`  
`Физическая культура (Харитонова) - Спорт.зал / ЗАМЕНА`

`4) 13:20-14:50`  
`МДК 06.04 (Филатова) - 111 / ЗАМЕНА`

## Структура проекта
- `main.py` - точка входа CLI
- `schedule_bot/cli.py` - аргументы и команды CLI
- `schedule_bot/schedule_service.py` - парсинг docx, merge расписания, форматирование, CSV->JSON
- `schedule_bot/yandex_disk.py` - интеграция с публичным API Яндекс Диска
- `schedule_bot/telegram_bot.py` - long polling, обработка команд Telegram
- `schedule_bot/constants.py` - константы
- `schedule.base.csv` - редактируемый шаблон базового расписания
- `schedule.base.json` - итоговый файл базового расписания для бота

## Требования
- Python 3.11+
- Telegram Bot Token
- Публичная ссылка Яндекс Диска с файлами замен

## Быстрый старт (локально)
```powershell
python -m venv .venv
.venv\Scripts\activate
python main.py run-bot --base schedule.base.json --group "31 ИС" --yandex-public-url "https://disk.yandex.ru/d/F_GFm6_Qi9GYAQ"
```

Перед запуском задайте переменные окружения:
- `TELEGRAM_BOT_TOKEN`
- `YANDEX_PUBLIC_URL` (если не передаете флагом)

## Переменные окружения
- `TELEGRAM_BOT_TOKEN` - токен Telegram-бота
- `YANDEX_PUBLIC_URL` - публичная ссылка Яндекс Диска
- `TARGET_GROUP` - группа (по умолчанию `31 ИС`)
- `BOT_TIMEZONE` - таймзона (по умолчанию `Europe/Saratov`)
- `WEEK1_START_DATE` - дата начала недели-числителя (`YYYY-MM-DD`) для fallback-режима
- `TELEGRAM_THREAD_ID` - фиксированная тема в группе (опционально)

## Команды в Telegram
- `/today` - расписание на сегодня
- `/tomorrow` - расписание на завтра
- `/date YYYY-MM-DD` - расписание на указанную дату

Также поддерживаются:
- `/date YYYY.MM.DD`
- `/date DD.MM.YYYY`

## Работа с базовым расписанием
Рекомендуемый путь:
1. Редактировать `schedule.base.csv` (удобно в Excel/Google Sheets).
2. Сконвертировать в JSON:

```powershell
python main.py csv-to-json --csv schedule.base.csv --out schedule.base.json --group "31 ИС"
```

## Проверка на локальном файле замен
```powershell
python main.py check-docx --docx "C:\Users\...\24.03.2026.docx" --base schedule.base.json --group "31 ИС"
```

## Запуск на Ubuntu через systemd (рекомендуется)
1. Клонировать проект на сервер.
2. Создать `.env` c переменными.
3. Запустить как сервис `systemd` с `Restart=always`.

Пример `ExecStart`:
```bash
/opt/schedule-bot/.venv/bin/python /opt/schedule-bot/main.py run-bot --base /opt/schedule-bot/schedule.base.json --group "31 ИС"
```

Полезные команды:
```bash
sudo systemctl restart schedule-bot
sudo systemctl status schedule-bot
sudo journalctl -u schedule-bot -f
```

## Безопасность
- Не храните токен бота в репозитории.
- Используйте `.env` и переменные окружения.
- Если токен утек, перевыпустите его через `@BotFather`.

## Лицензия
Добавьте лицензию (`MIT`, `Apache-2.0` и т.д.) при публикации репозитория.
