# Конфигурация и обслуживание NMS WebUI

Руководство по развертыванию в Production, настройке сервисов systemd, Nginx и техническому обслуживанию.

---

## 🛠️ Настройка файла конфигурации (.env)

Файл `.env` располагается в корне приложения `/opt/nms-webui/.env`:

```env
# Рабочий порт Uvicorn Backend
BACKEND_PORT=8000

# Режим авто-перезагрузки (false в prod)
RELOAD=false

# Безопасность
SECRET_KEY="your-super-secret-random-key-here"
NO_AUTH=false

# Пути
DB_PATH=/opt/nms-webui/nms.db
```

---

## 🐧 Настройка службы systemd (Production)

Для обеспечения непрерывной работы Backend под управлением Linux создайте сервис `/etc/systemd/system/nms-webui.service`:

```ini
[Unit]
Description=NMS WebUI Backend Service
After=network.target

[Service]
Type=simple
User=ttc
WorkingDirectory=/opt/nms-webui
ExecStart=/opt/nms-webui/.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
Environment=PYTHONPATH=/opt/nms-webui

[Install]
WantedBy=multi-user.target
```

**Активация службы:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nms-webui
```

---

## 🌐 Настройка Nginx Reverse Proxy

Пример конфига Nginx для проксирования веб-интерфейса и WebSocket соединений:

```nginx
server {
    listen 80;
    server_name nms.local;

    # Static Frontend
    location / {
        root /opt/nms-webui/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # WebSockets support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```
