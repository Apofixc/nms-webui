"""Тесты безопасности Этапа 1 (Критичная безопасность)."""
from backend.core.app import create_app
from backend.core.auth import create_access_token, decode_access_token
from backend.core.config import Settings, get_or_create_secret_key
from backend.core.crypto import PREFIX, decrypt_secret, encrypt_secret, mask_secret
from fastapi.testclient import TestClient


def test_secret_key_generation_and_persistence(tmp_path, monkeypatch):
    """Проверка генерации и сохранения secret_key в data/.secret_key."""
    fake_data_dir = tmp_path / "data"
    monkeypatch.setattr("backend.core.config.DATA_DIR", fake_data_dir)
    
    # 1. Сброс текущей глобальной настройки
    import backend.core.config as cfg
    cfg._settings = Settings(secret_key="")

    # 2. Получение ключа (должен автоматически сгенерироваться и сохраниться)
    key1 = get_or_create_secret_key()
    assert len(key1) >= 32
    secret_file = fake_data_dir / ".secret_key"
    assert secret_file.exists()
    assert secret_file.read_text(encoding="utf-8").strip() == key1

    # 3. Повторный вызов в новом сеансе читает из файла
    cfg._settings = Settings(secret_key="")
    key2 = get_or_create_secret_key()
    assert key2 == key1


def test_aes_gcm_encryption_decryption():
    """Проверка AES-256-GCM шифрования, расшифровки и поддержания старых данных."""
    plaintext = "super_secret_mfa_token_12345"

    # Шифрование
    encrypted = encrypt_secret(plaintext)
    assert encrypted.startswith(PREFIX)
    assert encrypted != plaintext

    # Расшифровка
    decrypted = decrypt_secret(encrypted)
    assert decrypted == plaintext

    # Проверка бесшовной миграции (незашифрованный открытый текст читается как есть)
    legacy_text = "old_unencrypted_secret"
    assert decrypt_secret(legacy_text) == legacy_text

    # Маскирование
    assert mask_secret(plaintext) == "***"
    assert mask_secret(None) is None


def test_jwt_token_flow_with_dynamic_key(monkeypatch):
    """Проверка выпуска токена и его недействительности при смене ключа."""
    import backend.core.config as cfg
    cfg._settings = Settings(secret_key="initial-test-secret-key-12345")

    token = create_access_token(user_id="usr-1", username="testuser")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "usr-1"
    assert payload["username"] == "testuser"

    # Изменение ключа приводит к отказу декодирования
    cfg._settings = Settings(secret_key="changed-different-secret-key-67890")
    payload_invalid = decode_access_token(token)
    assert payload_invalid is None


def test_security_headers_and_cors():
    """Проверка работы Middleware заголовков безопасности и CORS."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_masked_secrets_in_api():
    """Проверка маскирования чувствительных полей при вызове утилит маскирования."""
    assert mask_secret("api_token_super_secret") == "***"
    assert mask_secret("telegram_bot_token_98765") == "***"
    assert mask_secret("") == ""
    assert mask_secret(None) is None

