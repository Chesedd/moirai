# Роадмап

Этапы реализации Moirai. Галочками отмечается готовность.
Оркестратор-чат держит этот файл в актуальном состоянии:
из него берётся следующая подзадача для сессии Claude Code.

## Фаза 1 — Инфраструктура

- [ ] VPS на Hetzner (CX11, Ubuntu 24.04, 1 публичный IPv4)
- [ ] Базовая настройка: пользователь, ssh-ключи, `ufw`, автообновления
- [ ] Docker Engine + Compose plugin
- [ ] Клонирование репо в `/opt/moirai`
- [ ] Шаблон `.env` заполнен на сервере (токены, ID папки)
- [ ] `infra/docker-compose.yml` поднимается, Caddy отдаёт `/health`
- [ ] Systemd-юнит `planner-bot.service` автозапускает стек

## Фаза 2 — Google Cloud

- [ ] Проект в Google Cloud Console
- [ ] Включён Google Drive API
- [ ] Service account, скачан JSON-ключ, положен в `/opt/moirai/secrets/`
- [ ] Создана папка `/TelegramPlanner/` в Google Drive владельца
- [ ] Папка расшарена на email service account'а с правом Editor
- [ ] Подключён Google Drive коннектор в Claude (от имени пользователя)

## Фаза 3 — MVP бота

- [x] Приём сообщений из Telegram (long polling, aiogram 3.x)
- [x] Whitelist по `user_id` из `.env`
- [x] Дозапись входящих в `inbox.md` на Drive с таймстампом и типом
- [x] Команды `/start`, `/help`
- [x] Команда `/undo` (откат последней записи в `inbox.md`)
- [x] State-файл `state/undo_log.json`
- [ ] Поллинг `outputs/` раз в `OUTPUTS_POLL_INTERVAL_SEC`
- [ ] Отправка новых артефактов в чат (пересылка `*_short.md`)
- [ ] State-файл `state/last_sent.json`
- [ ] Reply keyboard: план на день / все задачи / команды
- [ ] Команды `/done N`, `/plan` (реальная нумерация по `daily_plan.md`)

## Фаза 4 — Routines

- [ ] Промпт `daily_plan` (ежедневно 08:00)
- [ ] Промпт `priorities` (ежедневно 21:00)
- [ ] Промпт `weekly_review` (воскресенье 20:00, включая чистку inbox в archive)
- [ ] Настройка routines в Claude Code с соответствующим расписанием
- [ ] Проверка: inbox не растёт бесконечно, архив наполняется, форматы
  артефактов совпадают с [DATA_FORMATS.md](DATA_FORMATS.md)

## Фаза 5 — Расширения

- [ ] Промпт `schedule_refresh` и routine (ежечасно 09:00–22:00)
- [ ] Таймер напоминаний в боте (проверка `schedule.md` раз в минуту)
- [ ] Команда `/remind N` (настройка `lead_time`, сохранение в state)
- [ ] Дефолты: `REMIND_LEAD_EVENT_MIN=15`, `REMIND_LEAD_SLOT_MIN=5`
- [ ] Команды `/skip N`, `/now`
- [ ] Eisenhower-матрица в `weekly_review.md`
- [ ] Счётчик переносов (`²`, `³`) и флаг вечно висящих задач

## Фаза 6 — На потом

- [ ] Голосовые сообщения + транскрибация (Whisper)
- [ ] Мультипользователь: подпапки `users/{user_id}/` на Drive
- [ ] HTTPS через Caddy (для будущих webhook-сценариев)
- [ ] CI/CD через GitHub Actions (автодеплой по push в `main`)
- [ ] Ruff/pytest в pre-commit и CI
