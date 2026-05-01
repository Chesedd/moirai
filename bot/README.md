# moirai-bot

Telegram-бот Moirai на aiogram 3.x. Принимает сообщения через long
polling от пользователей из whitelist (`TELEGRAM_ALLOWED_USER_IDS`).

Пока это каркас Фазы 3: `/start` и эхо-ответ на текст. Запись в
`inbox.md` на Google Drive и команды `/done`, `/plan` появятся в
следующих подзадачах роадмапа.

## Сборка

```
docker build -t moirai-bot bot/
```

## Локальный запуск

Переменные окружения берутся из `.env` в корне репо (см.
`.env.example` рядом с этим репо). Запуск стека целиком — через
`infra/docker-compose.yml`, см. корневой [README](../README.md).
