"""Генерация базового конфигурационного файла Telegraf для модуля."""
from __future__ import annotations


def render_telegraf_config(*, metrics_url: str = "http://127.0.0.1:8000/api/system/metrics", interval: str = "5s") -> str:
    return "\n".join(
        [
            "[agent]",
            f"  interval = \"{interval}\"",
            "  round_interval = true",
            "  flush_interval = \"5s\"",
            "",
            "[[inputs.cpu]]",
            "  percpu = false",
            "  totalcpu = true",
            "  fielddrop = [\"time_*\"]",
            "",
            "[[inputs.mem]]",
            "",
            "[[inputs.disk]]",
            "  ignore_fs = [\"tmpfs\", \"devtmpfs\", \"overlay\", \"squashfs\"]",
            "",
            "[[inputs.system]]",
            "",
            "[[outputs.http]]",
            f"  url = \"{metrics_url}\"",
            "  method = \"POST\"",
            "  data_format = \"json\"",
            "",
        ]
    )
