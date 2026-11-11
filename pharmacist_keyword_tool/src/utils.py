"""共通ユーティリティ."""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable

JST = timezone(timedelta(hours=9))


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_iso() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S %z")


def setup_logger(error_log_path: Path) -> logging.Logger:
    error_log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("pharmacist_keyword_tool")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(error_log_path, encoding="utf-8")
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def normalize_keyword(text: str) -> str:
    """表記ゆれを抑える簡易正規化（結果保存用の統一キー）."""
    if text is None:
        return ""
    s = str(text).strip()
    s = s.replace("\u3000", " ")
    while "  " in s:
        s = s.replace("  ", " ")
    # 全角英数を半角へ
    translated = []
    for ch in s:
        code = ord(ch)
        if 0xFF01 <= code <= 0xFF5E:
            translated.append(chr(code - 0xFEE0))
        else:
            translated.append(ch)
    s = "".join(translated)
    return s.casefold()


def write_csv_utf8_bom(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    """Excelで文字化けしにくい UTF-8 BOM CSV を出力する."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def read_csv_flexible(path: Path) -> list[dict[str, str]]:
    """BOM付き/無し、区切り推定付きのCSV読み込み."""
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    rows: list[dict[str, str]] = []
    for row in reader:
        cleaned = {}
        for k, v in row.items():
            key = (k or "").strip()
            cleaned[key] = "" if v is None else str(v).strip()
        rows.append(cleaned)
    return rows


def find_column(row: dict[str, str], candidates: list[str]) -> str | None:
    lowered = {k.casefold(): k for k in row.keys()}
    for cand in candidates:
        key = lowered.get(cand.casefold())
        if key is not None and row.get(key, "") != "":
            return key
    # 部分一致
    for cand in candidates:
        for actual_lower, actual in lowered.items():
            if cand.casefold() in actual_lower and row.get(actual, "") != "":
                return actual
    return None
