"""Анализ MPEG-TS потока через TSDuck (tsp). PAT/PMT, битрейт, сервисы."""
from __future__ import annotations

import subprocess
from typing import Optional

from backend.utils import find_executable


def _is_http(url: str) -> bool:
    return isinstance(url, str) and (
        url.startswith("http://") or url.startswith("https://")
    )


class TsAnalyzer:
    """
    Запуск tsp для анализа потока (HTTP или UDP).
    Вывод: PAT, PMT, битрейт, сервисы (SDT) и т.д.
    """

    def __init__(self, tsp_bin: str = "tsp"):
        self.tsp_bin = find_executable(tsp_bin) or tsp_bin

    @classmethod
    def available(cls, tsp_bin: str = "tsp") -> bool:
        return find_executable(tsp_bin) is not None

    def analyze(
        self,
        url: str,
        *,
        timeout_sec: float = 8.0,
        max_packets: Optional[int] = 50_000,
    ) -> tuple[bool, str]:
        """
        Запустить tsp -I ... -P analyze -O drop.
        :return: (success, output_text)
        """
        if not self.available(self.tsp_bin):
            return False, "TSDuck (tsp) не найден. Установите: sudo ./scripts/install-stream-tools.sh"
        if not url or not url.strip():
            return False, "URL не задан"
        # HTTP/HTTPS → -I http; иначе считаем UDP → -I ip
        if _is_http(url):
            input_spec = ["-I", "http", url]
        else:
            input_spec = ["-I", "ip", url]
        # Ограничение по времени (мс) и/или по пакетам, чтобы не висеть
        args = [
            self.tsp_bin,
            *input_spec,
            "--timeout", str(int(timeout_sec * 1000)),
        ]
        if max_packets is not None:
            args.extend(["--max-input-packets", str(max_packets)])
        args.extend(["-P", "analyze", "-O", "drop"])
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                timeout=timeout_sec + 2,
                text=True,
                errors="replace",
            )
            out = (proc.stdout or "").strip() + "\n" + (proc.stderr or "").strip()
            out = out.strip()
            if not out:
                out = "(нет вывода)"
            return proc.returncode == 0, out
        except subprocess.TimeoutExpired:
            return False, "Таймаут анализа потока."
        except FileNotFoundError:
            return False, "tsp не найден (установите TSDuck)."
        except Exception as e:
            return False, str(e)
