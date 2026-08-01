# Резервное копирование и обслуживание БД (SQLite WAL)

Платформа **NMS WebUI** использует для хранения пользователей, настроек модулей, аудита и кэшей единую базу данных **SQLite** (`nms.db`), работающую в оптимизированном режиме **WAL (Write-Ahead Logging)**.

---

## 💾 Способы резервного копирования

### 1. Скачивание через Веб-интерфейс / REST API
Администраторы с разрешением `system.admin` могут скачать полную актуальную резервную копию базы данных:
- **UI**: Вкладка *"Администрирование"* → *"Служебные утилиты"* → Кнопка *"Скачать бэкап БД"*.
- **REST API**: `GET /api/system/backup` (требует `Authorization: Bearer <token>`).

Каждая загрузка фиксируется в системе аудита с меткой времени и имени файла (`nms-backup-YYYYMMDD-HHMMSS.db`).

---

### 2. Резервное копирование на сервере (Cron / Bash)
В режиме **WAL** SQLite позволяет делать горячие снимки базы без остановки веб-сервера.

Официальная команда создания корректного снимка через `sqlite3`:
```bash
sqlite3 /opt/nms-webui/nms.db ".backup '/opt/nms-webui/data/backups/nms-backup-$(date +%Y%m%d-%H%M%S).db'"
```

> ⚠️ **Важно**: Не используйте простой `cp nms.db ...`, если идут активные транзакции записи! В режиме WAL часть неизмененных страниц может находиться в файле `nms.db-wal`. Команда `.backup` корректно сбрасывает WAL во время снимка.

Пример скрипта ротации бэкапов (сохранять 30 дней):
```bash
#!/usr/bin/env bash
BACKUP_DIR="/opt/nms-webui/data/backups"
mkdir -p "$BACKUP_DIR"
NOW=$(date +%Y%m%d-%H%M%S)

# Создаем сброс с WAL
sqlite3 /opt/nms-webui/nms.db ".backup '$BACKUP_DIR/nms-$NOW.db'"

# Удаляем бэкапы старше 30 дней
find "$BACKUP_DIR" -type f -name "nms-*.db" -mtime +30 -delete
```

---

## 🛠️ Обслуживание и Оптимизация (Maintenance)

### 1. Режим WAL и PRAGMA wal_checkpoint
При интенсивной записи размер `nms.db-wal` может расти. Backend при старте и периодически выполняет сброс WAL-журнала в основной файл:
```sql
PRAGMA wal_checkpoint(PASSIVE);
```

### 2. Сжатие и дефрагментация (VACUUM)
После удаления устаревших журналов аудита или временных данных полезно освобождать неиспользуемые страницы базы данных:
```bash
sqlite3 /opt/nms-webui/nms.db "VACUUM;"
```

### 3. Проверка целостности (Integrity Check)
Для проверки отсутствия повреждений файлов БД используйте:
```bash
sqlite3 /opt/nms-webui/nms.db "PRAGMA integrity_check;"
# Вывод должен быть: ok
```

---

## 🔄 Восстановление из бэкапа

1. Остановите службу WebUI:
   ```bash
   sudo systemctl stop nms-webui
   ```
2. Подмените файл `nms.db` бэкапом и удалите старые WAL-файлы при их наличии:
   ```bash
   cp /opt/nms-webui/data/backups/nms-20260801-120000.db /opt/nms-webui/nms.db
   rm -f /opt/nms-webui/nms.db-wal /opt/nms-webui/nms.db-shm
   ```
3. Запустите службу WebUI:
   ```bash
   sudo systemctl start nms-webui
   ```
