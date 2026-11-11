"""調査レポート（report.md）生成."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .utils import now_jst_iso


def generate_report(
    *,
    output_path: Path,
    seed_keyword: str,
    raw_rows: list[dict[str, str]],
    clean_rows: list[dict[str, str]],
    priority_rows: list[dict[str, str]],
    errors: list[dict[str, str]],
) -> None:
    source_counter = Counter()
    for row in raw_rows:
        source_counter[row.get("source", "unknown")] += 1

    category_counter = Counter(row.get("category", "その他") for row in clean_rows)

    volume_confirmed = sum(
        1 for row in clean_rows if row.get("search_volume_status") == "取得済み"
    )
    volume_unknown = len(clean_rows) - volume_confirmed
    example_count = sum(1 for row in clean_rows if row.get("is_example_data") == "yes")
    real_count = len(clean_rows) - example_count

    # テーマ候補: カテゴリごとに代表キーワードを抽出（実データのみ）
    theme_candidates: list[str] = []
    by_cat: dict[str, list[str]] = {}
    for row in clean_rows:
        if row.get("is_example_data") == "yes":
            continue
        by_cat.setdefault(row["category"], []).append(row["keyword"])

    preferred_order = [
        "副業の種類・おすすめ",
        "単発勤務・ダブルワーク",
        "在宅勤務",
        "収入・時給",
        "法律・就業規則",
        "税金・確定申告",
        "スキル活用・個人事業",
        "その他",
    ]
    for cat in preferred_order:
        kws = by_cat.get(cat, [])
        if not kws:
            continue
        sample = " / ".join(kws[:3])
        theme_candidates.append(f"- {cat}: {sample}")

    main_intents = []
    for cat, count in category_counter.most_common():
        if cat == "その他":
            continue
        main_intents.append(f"- {cat}（{count}件）")
    if not main_intents:
        main_intents.append("- 十分な分類結果なし（取得件数が少ない、またはその他のみ）")

    missing_info = []
    if volume_unknown == len(clean_rows):
        missing_info.append(
            "- 検索ボリューム（月間検索数）は未取得です。キーワードプランナーやラッコキーワードのCSV投入が必要です。"
        )
    elif volume_unknown:
        missing_info.append(
            f"- 検索ボリューム未確認のキーワードが {volume_unknown} 件あります。"
        )
    if source_counter.get("rakko_csv", 0) == 0:
        missing_info.append("- ラッコキーワードCSVは今回取り込みなし。")
    if source_counter.get("keyword_planner_csv", 0) == 0:
        missing_info.append("- GoogleキーワードプランナーCSVは今回取り込みなし。")
    if errors:
        missing_info.append(f"- 取得エラーが {len(errors)} 件記録されています（errors.log 参照）。")
    if not missing_info:
        missing_info.append("- 特になし（ただし競合動画分析などは未実施）。")

    next_steps = [
        "- GoogleキーワードプランナーまたはラッコキーワードからCSVをエクスポートし、`data/input/` に置いて再実行する。",
        "- 検索ボリューム取得後に `keywords_priority.csv` の順位を確認する。",
        "- YouTube上の競合動画（再生数・タイトル）を別途調査し、需要と供給のギャップを見る。",
        "- 本レポートのテーマ候補から、発信者が話せる範囲と照合して初期動画10本を選定する。",
    ]

    lines = [
        "# 薬剤師副業キーワード調査レポート",
        "",
        f"- 作成日時: {now_jst_iso()}（Asia/Tokyo）",
        f"- メインキーワード: {seed_keyword}",
        "",
        "## 実際に取得できたキーワード数",
        "",
        f"- 生データ行数（ソース別の延べ）: {len(raw_rows)} 件",
        f"- 重複整理後のユニークキーワード: {len(clean_rows)} 件",
        f"- 実データ: {real_count} 件",
        f"- 例示データ: {example_count} 件（今回の収集結果に例示を混在させていません）",
        "",
        "## 情報源別の取得件数（生データ）",
        "",
    ]

    if source_counter:
        for source, count in sorted(source_counter.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- {source}: {count} 件")
    else:
        lines.append("- 取得なし")

    lines.extend(
        [
            "",
            "## カテゴリ別の件数（整理後）",
            "",
        ]
    )
    if category_counter:
        for cat, count in sorted(category_counter.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- {cat}: {count} 件")
    else:
        lines.append("- 分類対象なし")

    lines.extend(
        [
            "",
            "## 主な検索意図",
            "",
            *main_intents,
            "",
            "## 検索ボリュームの状況",
            "",
            f"- 取得済み: {volume_confirmed} 件",
            f"- 未確認: {volume_unknown} 件",
            "- 注意: サジェストに出ることと、月間検索数が多いことは別です。",
            "- 検索ボリュームを推測で埋めていません。未取得は「未確認」「評価保留」としています。",
            "",
            "## 取得できなかった情報",
            "",
            *missing_info,
            "",
            "## 次に必要な調査",
            "",
            *next_steps,
            "",
            "## YouTube動画企画に使えそうなテーマ候補",
            "",
        ]
    )

    if theme_candidates:
        lines.extend(theme_candidates)
        lines.append("")
        lines.append(
            "※ 上記は今回取得できた実キーワードの分類に基づく候補です。"
            "最終的な動画10本の決定は、検索ボリュームと競合状況を見て別途行います。"
        )
    else:
        lines.append("- 今回はテーマ候補を提示できる実データが不足しています。")

    lines.extend(
        [
            "",
            "## 評価用データの扱い",
            "",
            f"- `keywords_priority.csv` 行数: {len(priority_rows)} 件",
            "- 検索ボリューム未取得のキーワードは需要順位を付けず「評価保留」としています。",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
