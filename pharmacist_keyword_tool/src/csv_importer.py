"""ラッコキーワード / Googleキーワードプランナー CSV の取り込み."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import find_column, now_jst_iso, read_csv_flexible


RAKKO_KEYWORD_COLUMNS = [
    "キーワード",
    "keyword",
    "Keyword",
    "検索キーワード",
]
RAKKO_VOLUME_COLUMNS = [
    "月間検索数",
    "検索ボリューム",
    "ボリューム",
    "volume",
    "Search Volume",
    "avg_monthly_searches",
]

PLANNER_KEYWORD_COLUMNS = [
    "キーワード",
    "Keyword",
    "keyword",
    "検索キーワード",
]
PLANNER_VOLUME_COLUMNS = [
    "平均月間検索ボリューム",
    "Avg. monthly searches",
    "Avg monthly searches",
    "月間検索数",
    "検索ボリューム",
    "Search volume",
    "volume",
]


def _import_generic(
    path: Path,
    *,
    source_name: str,
    keyword_columns: list[str],
    volume_columns: list[str],
    logger: Any = None,
) -> list[dict[str, str]]:
    try:
        rows = read_csv_flexible(path)
    except Exception as exc:  # noqa: BLE001 - 入力欠落や壊れたCSVでも継続
        if logger:
            logger.warning("CSV読み込み失敗: %s (%s)", path, exc)
        return []

    if not rows:
        if logger:
            logger.info("CSVが空、またはヘッダーのみ: %s", path)
        return []

    out: list[dict[str, str]] = []
    fetched_at = now_jst_iso()
    for row in rows:
        kw_col = find_column(row, keyword_columns)
        if not kw_col:
            continue
        keyword = row[kw_col].strip()
        if not keyword:
            continue

        vol_col = find_column(row, volume_columns)
        if vol_col and row.get(vol_col, "").strip() not in ("", "-", "—", "－"):
            volume = row[vol_col].strip().replace(",", "")
            volume_status = "取得済み"
        else:
            volume = ""
            volume_status = "未確認"

        out.append(
            {
                "keyword": keyword,
                "source": source_name,
                "probe_query": "",
                "fetched_at": fetched_at,
                "search_volume": volume,
                "search_volume_status": volume_status,
                "is_example_data": "no",
                "notes": f"imported_from:{path.name}",
            }
        )
    return out


def discover_input_files(input_dir: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    if not input_dir.exists():
        return files
    for pattern in patterns:
        files.extend(sorted(input_dir.glob(pattern)))
    # 重複排除しつつ順序維持
    seen = set()
    unique: list[Path] = []
    for f in files:
        if f.resolve() in seen:
            continue
        seen.add(f.resolve())
        unique.append(f)
    return unique


def import_all_csv(
    *,
    input_dir: Path,
    rakko_glob: str,
    planner_glob: str,
    keyword_planner_glob: str,
    logger: Any = None,
) -> list[dict[str, str]]:
    """入力CSVが無くても空リストを返し、異常終了しない."""
    results: list[dict[str, str]] = []

    if not input_dir.exists():
        if logger:
            logger.info("入力ディレクトリが無いためCSV取り込みをスキップ: %s", input_dir)
        return results

    rakko_files = discover_input_files(input_dir, [rakko_glob])
    planner_files = discover_input_files(
        input_dir,
        [planner_glob, keyword_planner_glob, "*planner*.csv", "*キーワードプランナー*.csv"],
    )

    for path in rakko_files:
        if logger:
            logger.info("ラッコキーワードCSVを取り込み: %s", path.name)
        results.extend(
            _import_generic(
                path,
                source_name="rakko_csv",
                keyword_columns=RAKKO_KEYWORD_COLUMNS,
                volume_columns=RAKKO_VOLUME_COLUMNS,
                logger=logger,
            )
        )

    for path in planner_files:
        # ラッコと二重取り込みしない
        if path in rakko_files:
            continue
        if logger:
            logger.info("キーワードプランナーCSVを取り込み: %s", path.name)
        results.extend(
            _import_generic(
                path,
                source_name="keyword_planner_csv",
                keyword_columns=PLANNER_KEYWORD_COLUMNS,
                volume_columns=PLANNER_VOLUME_COLUMNS,
                logger=logger,
            )
        )

    # その他のCSV（汎用）もキーワード列があれば取り込む
    known = set(rakko_files) | set(planner_files)
    for path in sorted(input_dir.glob("*.csv")):
        if path in known:
            continue
        if logger:
            logger.info("汎用CSVを取り込み試行: %s", path.name)
        imported = _import_generic(
            path,
            source_name="csv_import",
            keyword_columns=RAKKO_KEYWORD_COLUMNS + PLANNER_KEYWORD_COLUMNS,
            volume_columns=RAKKO_VOLUME_COLUMNS + PLANNER_VOLUME_COLUMNS,
            logger=logger,
        )
        results.extend(imported)

    return results


def merge_volume_onto_keywords(
    keywords: list[dict[str, str]],
    volume_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """収集済みキーワードへ、後から読み込んだ検索ボリュームを照合する."""
    from .utils import normalize_keyword

    volume_map: dict[str, str] = {}
    for row in volume_rows:
        if row.get("search_volume_status") != "取得済み":
            continue
        key = normalize_keyword(row.get("keyword", ""))
        vol = row.get("search_volume", "").strip()
        if key and vol:
            volume_map[key] = vol

    merged: list[dict[str, str]] = []
    for row in keywords:
        item = dict(row)
        key = normalize_keyword(item.get("keyword", ""))
        if key in volume_map:
            item["search_volume"] = volume_map[key]
            item["search_volume_status"] = "取得済み"
            note = item.get("notes", "")
            extra = "volume_matched_from_csv"
            item["notes"] = f"{note};{extra}" if note else extra
        merged.append(item)
    return merged
