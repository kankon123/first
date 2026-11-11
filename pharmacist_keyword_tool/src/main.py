"""薬剤師副業キーワード調査ツール エントリポイント."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from .collectors import collect_suggestions
from .csv_importer import import_all_csv, merge_volume_onto_keywords
from .process import build_clean_rows, build_priority_rows
from .report import generate_report
from .utils import read_csv_flexible, setup_logger, write_csv_utf8_bom


ROOT = Path(__file__).resolve().parents[1]


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="薬剤師向け「副業」関連キーワードを収集・整理するツール",
    )
    parser.add_argument(
        "--config",
        default=str(ROOT / "config.yaml"),
        help="設定ファイルパス（既定: config.yaml）",
    )
    parser.add_argument(
        "--skip-suggest",
        action="store_true",
        help="Google/YouTubeサジェスト取得をスキップ（CSVのみ処理）",
    )
    parser.add_argument(
        "--reprocess-raw",
        action="store_true",
        help="既存の keywords_raw.csv を読み直し、整理・レポートだけ再生成する",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="出力先ディレクトリ（省略時は設定ファイルの paths.output_dir）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = (Path.cwd() / config_path).resolve()
    if not config_path.exists():
        print(f"設定ファイルが見つかりません: {config_path}", file=sys.stderr)
        return 1

    config = load_config(config_path)
    project_root = config_path.parent

    input_dir = project_root / config["paths"]["input_dir"]
    output_dir = Path(args.output_dir) if args.output_dir else project_root / config["paths"]["output_dir"]
    if not output_dir.is_absolute():
        output_dir = (project_root / output_dir).resolve()
    error_log = output_dir / Path(config["paths"]["error_log"]).name

    output_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logger(error_log)
    logger.info("調査開始: seed=%s", config.get("seed_keyword"))

    raw_rows: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    # 1) サジェスト収集 or 既存rawの再処理
    if args.reprocess_raw:
        raw_path = output_dir / "keywords_raw.csv"
        if raw_path.exists():
            raw_rows.extend(read_csv_flexible(raw_path))
            logger.info("既存rawを読み込み: %s 件 (%s)", len(raw_rows), raw_path)
        else:
            logger.warning("再処理対象の raw がありません: %s", raw_path)
    elif not args.skip_suggest:
        try:
            suggest_rows, suggest_errors = collect_suggestions(
                seed_keyword=config["seed_keyword"],
                probe_suffixes=config.get("probe_suffixes", [""]),
                second_pass_suffixes=config.get("second_pass_suffixes", [""]),
                max_second_pass_seeds=int(config.get("max_second_pass_seeds", 12)),
                interval_seconds=float(config.get("request_interval_seconds", 0.25)),
                timeout_seconds=float(config.get("request_timeout_seconds", 10)),
                logger=logger,
            )
            raw_rows.extend(suggest_rows)
            errors.extend(suggest_errors)
            logger.info(
                "サジェスト取得行数: %s / エラー: %s",
                len(suggest_rows),
                len(suggest_errors),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("サジェスト収集で例外: %s", exc)
            errors.append(
                {
                    "source": "suggest_collector",
                    "query": config.get("seed_keyword", ""),
                    "message": str(exc),
                    "fetched_at": "",
                }
            )
    else:
        logger.info("サジェスト取得をスキップしました")

    # 2) CSV取り込み（無くても継続）
    try:
        csv_rows = import_all_csv(
            input_dir=input_dir,
            rakko_glob=config["paths"].get("rakko_glob", "rakko*.csv"),
            planner_glob=config["paths"].get("planner_glob", "planner*.csv"),
            keyword_planner_glob=config["paths"].get(
                "keyword_planner_glob", "*keyword*planner*.csv"
            ),
            logger=logger,
        )
        raw_rows.extend(csv_rows)
        logger.info("CSV取込行数: %s", len(csv_rows))
    except Exception as exc:  # noqa: BLE001
        logger.warning("CSV取り込みで例外（処理は継続）: %s", exc)
        csv_rows = []
        errors.append(
            {
                "source": "csv_importer",
                "query": str(input_dir),
                "message": str(exc),
                "fetched_at": "",
            }
        )

    # 3) 後から入れたボリュームCSVを既存キーワードへ照合
    volume_sources = [
        r for r in csv_rows if r.get("search_volume_status") == "取得済み"
    ]
    if volume_sources:
        raw_rows = merge_volume_onto_keywords(raw_rows, volume_sources)

    # 4) 整理
    clean_rows = build_clean_rows(raw_rows, config.get("categories", []))
    priority_rows = build_priority_rows(clean_rows)

    # 5) 出力
    raw_fields = [
        "keyword",
        "source",
        "probe_query",
        "fetched_at",
        "search_volume",
        "search_volume_status",
        "is_example_data",
        "notes",
    ]
    clean_fields = [
        "keyword",
        "normalized_keyword",
        "category",
        "sources",
        "source_count",
        "first_fetched_at",
        "last_fetched_at",
        "search_volume",
        "search_volume_status",
        "occurrence_count",
        "is_example_data",
        "notes",
    ]
    priority_fields = [
        "keyword",
        "category",
        "search_intent",
        "sources",
        "search_volume",
        "search_volume_status",
        "suggest_presence",
        "volume_vs_suggest_note",
        "video_relevance",
        "priority_rank",
        "evaluation_status",
        "planning_note",
    ]

    write_csv_utf8_bom(output_dir / "keywords_raw.csv", raw_fields, raw_rows)
    write_csv_utf8_bom(output_dir / "keywords_clean.csv", clean_fields, clean_rows)
    write_csv_utf8_bom(
        output_dir / "keywords_priority.csv", priority_fields, priority_rows
    )

    errors_csv = output_dir / "errors.csv"
    if errors:
        write_csv_utf8_bom(
            errors_csv,
            ["source", "query", "message", "fetched_at"],
            errors,
        )
    elif errors_csv.exists():
        # 前回エラーが残らないよう、成功時は空ファイルに更新
        write_csv_utf8_bom(
            errors_csv,
            ["source", "query", "message", "fetched_at"],
            [],
        )

    generate_report(
        output_path=output_dir / "report.md",
        seed_keyword=config.get("seed_keyword", ""),
        raw_rows=raw_rows,
        clean_rows=clean_rows,
        priority_rows=priority_rows,
        errors=errors,
    )

    summary = {
        "raw_count": len(raw_rows),
        "clean_count": len(clean_rows),
        "priority_count": len(priority_rows),
        "error_count": len(errors),
        "volume_confirmed": sum(
            1 for r in clean_rows if r.get("search_volume_status") == "取得済み"
        ),
        "output_dir": str(output_dir),
    }
    (output_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    logger.info(
        "完了: unique=%s raw=%s errors=%s output=%s",
        summary["clean_count"],
        summary["raw_count"],
        summary["error_count"],
        output_dir,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
