"""Log Provider System — абстракции и реестр источников системных и удаленных логов."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

NMS_ROOT = Path(__file__).resolve().parent.parent.parent


def matches_log_level(line_str: str, target_level: str) -> bool:
    """Точная проверка уровня лога с учетом стандартов (INFO, WARN/WARNING, ERROR, DEBUG)."""
    if not target_level or target_level == "ALL":
        return True

    target = target_level.upper().strip()
    target_norm = "WARN" if target in ("WARN", "WARNING") else target
    line_upper = line_str.upper()

    # 1. Поиск структурированной метки уровня
    m = re.search(r'(?:\||\[|\b)(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)(?:\s*\||\]|:|\b)', line_upper)
    if m:
        extracted = m.group(1)
        extracted_norm = "WARN" if extracted in ("WARN", "WARNING") else extracted
        return extracted_norm == target_norm

    # 2. Фолбэк для неструктурированных строк
    return bool(re.search(r'\b' + re.escape(target_norm) + r'\b', line_upper)) or (
        target_norm == "WARN" and bool(re.search(r'\bWARNING\b', line_upper))
    )


def clean_ansi(text: str) -> str:
    """Очистка текста от управления терминалом ANSI escape-кодами."""
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)


class BaseLogProvider(ABC):
    """Абстрактный провайдер логов."""

    def __init__(self, provider_id: str, name: str, category: str = "system"):
        self.id = provider_id
        self.name = name
        self.category = category  # "system", "module", "remote"

    @abstractmethod
    async def get_logs(self, lines: int = 200, level: str = "ALL", search: str = "") -> Dict[str, Any]:
        """Получить массив строк лога с фильтрацией."""
        pass

    @abstractmethod
    async def download_log(self) -> Tuple[bytes, str, str]:
        """Скачать лог-файл целиком. Возвращает (bytes, filename, media_type)."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Проверить доступность источника логов."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация свойств провайдера для API."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
        }


class LocalFileLogProvider(BaseLogProvider):
    """Провайдер для чтения локальных лог-файлов на сервере."""

    def __init__(self, provider_id: str, name: str, file_path: Path, category: str = "system"):
        super().__init__(provider_id, name, category)
        self.file_path = file_path

    async def is_available(self) -> bool:
        return self.file_path.exists()

    async def get_logs(self, lines: int = 200, level: str = "ALL", search: str = "") -> Dict[str, Any]:
        if not self.file_path.exists():
            return {"id": self.id, "name": self.name, "content": [], "total_lines": 0, "matched_lines": 0}

        with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()

        filtered = []
        search_lower = search.lower().strip()
        level_upper = level.upper().strip()

        for line in all_lines:
            line_str = clean_ansi(line.rstrip("\r\n"))
            if search_lower and search_lower not in line_str.lower():
                continue
            if not matches_log_level(line_str, level_upper):
                continue
            filtered.append(line_str)

        result_lines = filtered[-max(1, min(lines, 2000)):]

        return {
            "id": self.id,
            "name": self.name,
            "content": result_lines,
            "total_lines": len(all_lines),
            "matched_lines": len(filtered),
        }

    async def download_log(self) -> Tuple[bytes, str, str]:
        if not self.file_path.exists():
            content = b""
        else:
            with open(self.file_path, "rb") as f:
                content = f.read()
        filename = self.file_path.name
        return content, filename, "text/plain; charset=utf-8"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        exists = self.file_path.exists()
        data["exists"] = exists
        data["size_bytes"] = self.file_path.stat().st_size if exists else 0
        return data


class RemoteHTTPLogProvider(BaseLogProvider):
    """Провайдер для получения логов с удаленного сервера/узла по HTTP API."""

    def __init__(self, provider_id: str, name: str, url: str, headers: Optional[Dict[str, str]] = None, category: str = "remote"):
        super().__init__(provider_id, name, category)
        self.url = url
        self.headers = headers or {}

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(self.url, headers=self.headers)
                return res.status_code == 200
        except Exception:
            return False

    async def get_logs(self, lines: int = 200, level: str = "ALL", search: str = "") -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(
                    self.url,
                    params={"lines": lines, "level": level, "search": search},
                    headers=self.headers,
                )
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, dict):
                        data["id"] = self.id
                        data["name"] = self.name
                        return data
                    if isinstance(data, list):
                        return {
                            "id": self.id,
                            "name": self.name,
                            "content": data,
                            "total_lines": len(data),
                            "matched_lines": len(data),
                        }
        except Exception as exc:
            return {
                "id": self.id,
                "name": self.name,
                "content": [f"[ERROR] Failed to load remote log / Не удалось загрузить удаленный лог: {exc}"],
                "total_lines": 1,
                "matched_lines": 1,
            }

        return {"id": self.id, "name": self.name, "content": [], "total_lines": 0, "matched_lines": 0}

    async def download_log(self) -> Tuple[bytes, str, str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{self.url}/download", headers=self.headers)
                if res.status_code == 200:
                    return res.content, f"{self.id}.log", "text/plain; charset=utf-8"
        except Exception as exc:
            return f"Error downloading remote log / Ошибка скачивания удаленного лога: {exc}".encode("utf-8"), f"{self.id}.log", "text/plain"

        return b"", f"{self.id}.log", "text/plain"


class LogProviderRegistry:
    """Глобальный менеджер провайдеров логов."""

    def __init__(self):
        self._providers: Dict[str, BaseLogProvider] = {}

    def register(self, provider: BaseLogProvider) -> None:
        self._providers[provider.id] = provider

    def unregister(self, provider_id: str) -> None:
        self._providers.pop(provider_id, None)

    def get(self, provider_id: str) -> Optional[BaseLogProvider]:
        if provider_id in self._providers:
            return self._providers[provider_id]
        for p in self._providers.values():
            if p.name == provider_id:
                return p
        return None

    async def list_all(self) -> List[Dict[str, Any]]:
        result = []
        for provider in self._providers.values():
            result.append(provider.to_dict())
        return result


# Глобальный экземпляр реестра
log_provider_registry = LogProviderRegistry()

# Регистрация системного лог-провайдера по умолчанию
log_provider_registry.register(
    LocalFileLogProvider(
        provider_id="backend.log",
        name="backend.log",
        file_path=NMS_ROOT / "backend.log",
        category="system",
    )
)


def load_remote_sources_from_db() -> None:
    """Загрузить и зарегистрировать сохраненные в БД удаленные источники логов."""
    try:
        from backend.core.database import get_db_connection
        conn = get_db_connection()
        rows = conn.execute("SELECT id, name, url, api_token FROM remote_log_sources").fetchall()
        conn.close()
        for r in rows:
            headers = {}
            if r["api_token"]:
                headers["Authorization"] = f"Bearer {r['api_token']}"
            provider = RemoteHTTPLogProvider(
                provider_id=r["id"],
                name=r["name"],
                url=r["url"],
                headers=headers,
                category="remote",
            )
            log_provider_registry.register(provider)
    except Exception:
        pass

