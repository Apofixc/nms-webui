# Безопасность, 2FA/MFA и Управление сессиями

Полный справочник по подсистеме безопасности NMS WebUI: двухфакторная аутентификация (TOTP), валидация и сброс сессий, и журнал аудита.

---

## 🔐 1. Двухфакторная аутентификация (MFA / TOTP)

Система содержит встроенный Pure Python генератор и валидатор одноразовых паролей TOTP (RFC 6238) без сторонних C-зависимостей (`backend/core/mfa.py`).

### Поддерживаемые приложения:
- Google Authenticator
- Яндекс.Ключ
- YubiKey Authenticator
- 2FA приложения на базе iOS / Android

### Основные функции `backend/core/mfa.py`:

```python
from backend.core.mfa import (
    generate_totp_secret,
    get_totp_uri,
    generate_qr_svg,
    verify_totp_code
)

# 1. Генерация 160-битного Base32 секрета
secret = generate_totp_secret()

# 2. Формирование стандартизированного URI (otpauth://)
uri = get_totp_uri(username="admin", secret=secret, issuer="NMS-WebUI")

# 3. Динамическая генерация SVG QR-кода в формате data:image/svg+xml
qr_svg_base64 = generate_qr_svg(uri)

# 4. Валидация 6-значного кода с учётом рассинхронизации часов (окно 30 сек)
is_valid = verify_totp_code(secret=secret, code="123456")
```

---

## 🎫 2. Управление активными сессиями (JWT & Active Sessions)

Для предотвращения компрометации токенов NMS WebUI отслеживает уникальный идентификатор токена `JTI` (JWT ID) в таблице `active_sessions`.

### Сброс сторонних сессий (Terminate Sessions):

Администратор может инвалидировать все выданные ранее токены пользователей через эндпоинт:

```http
POST /api/system/sessions/terminate-all?keep_current=true
Authorization: Bearer <token>
```

**Логика работы:**
1. При отметке `keep_current=true` текущий `JTI` остается действительным.
2. В базе `active_sessions` все остальное записи помечаются `is_revoked = 1`.
3. Учетные записи обновляют метку `token_valid_after = <current_timestamp>`.

---

## 📝 3. Журналирование безопасности и Аудит (Audit Log)

Любое критическое изменение (вход в систему, сброс сессий, сфера прав, изменение настроек модуля) обязано логироваться с помощью функции `log_audit_event`:

```python
from backend.core.audit import log_audit_event

log_audit_event(
    user_id=user.id,
    username=user.username,
    action="MFA_ENABLED",
    resource="user_profile",
    details="Включена двухфакторная аутентификация TOTP",
    ip_address=request.client.host
)
```

Таблица `audit_logs` защищена от внешнего редактирования и доступна для просмотра в разделе **Безопасность и Журнал событий** системными администраторами.
