"""Приём и хранение системных метрик от Telegraf."""
from __future__ import annotations

import re
from typing import Any

_snapshot: dict[str, Any] = {}


def update_from_telegraf_json(body: list[dict] | dict) -> None:
    global _snapshot
    if isinstance(body, dict):
        body = body.get("metrics", body.get("data", [body]))
    if not isinstance(body, list):
        return
    out: dict[str, Any] = {"available": True}
    for m in body:
        if not isinstance(m, dict):
            continue
        name = m.get("name") or m.get("measurement")
        fields = m.get("fields") or {}
        if name == "cpu" and fields:
            idle = _float(fields.get("usage_idle"))
            if idle is not None:
                out["cpu_usage_percent"] = round(100.0 - idle, 1)
            else:
                out["cpu_usage_percent"] = _float(fields.get("usage_user")) or 0
        elif name == "mem" and fields:
            out["mem_used_percent"] = _float(fields.get("used_percent"))
            out["mem_total_kb"] = _float(fields.get("total"))
            out["mem_used_kb"] = _float(fields.get("used"))
        elif name == "disk" and fields:
            out["disk_used_percent"] = _float(fields.get("used_percent"))
            out["disk_total_kb"] = _float(fields.get("total"))
            out["disk_used_kb"] = _float(fields.get("used"))
        elif name == "system" and fields:
            out["load1"] = _float(fields.get("load1"))
            out["load5"] = _float(fields.get("load5"))
            out["load15"] = _float(fields.get("load15"))
    if len(out) > 1:
        _snapshot = out


def update_from_influx_line(text: str) -> None:
    global _snapshot
    out: dict[str, Any] = {"available": True}
    for line in text.strip().split("\n"):
        if " " not in line:
            continue
        part, rest = line.split(" ", 1)
        name = part.split(",")[0]
        parts = rest.strip().split()
        fields_part = parts[0] if parts else rest
        fields = {}
        for kv in re.split(r",(?=[a-zA-Z_][a-zA-Z0-9_]*=)", fields_part):
            if "=" in kv:
                k, v = kv.split("=", 1)
                if v.endswith("i"):
                    v = v[:-1]
                fields[k] = v
        if name == "cpu":
            idle = _float(fields.get("usage_idle"))
            if idle is not None:
                out["cpu_usage_percent"] = round(100.0 - idle, 1)
        elif name == "mem":
            out["mem_used_percent"] = _float(fields.get("used_percent"))
            out["mem_total_kb"] = _float(fields.get("total"))
            out["mem_used_kb"] = _float(fields.get("used"))
        elif name == "disk":
            out["disk_used_percent"] = _float(fields.get("used_percent"))
            out["disk_total_kb"] = _float(fields.get("total"))
            out["disk_used_kb"] = _float(fields.get("used"))
        elif name == "system":
            out["load1"] = _float(fields.get("load1"))
            out["load5"] = _float(fields.get("load5"))
            out["load15"] = _float(fields.get("load15"))
    if len(out) > 1:
        _snapshot = out


def _float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def get_snapshot() -> dict[str, Any]:
    if not _snapshot or _snapshot.get("available") is not True:
        return {"available": False}
    return dict(_snapshot)
