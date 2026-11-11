"""重複削除・表記統一・カテゴリ分類・優先度整理."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .utils import normalize_keyword


def categorize_keyword(keyword: str, categories: list[dict[str, Any]]) -> str:
    text = keyword.casefold()
    compact = text.replace(" ", "").replace("\u3000", "")
    for cat in categories:
        name = cat.get("name", "その他")
        if name == "その他":
            continue
        for tip in cat.get("keywords", []):
            tip_l = tip.casefold()
            tip_c = tip_l.replace(" ", "").replace("\u3000", "")
            if tip_l in text or tip_c in compact:
                return name
    return "その他"


def build_clean_rows(
    raw_rows: list[dict[str, str]],
    categories: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """同一正規化キーの重複をまとめ、表記を統一する."""
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in raw_rows:
        key = normalize_keyword(row.get("keyword", ""))
        if not key:
            continue
        groups[key].append(row)

    clean: list[dict[str, str]] = []
    for key, items in groups.items():
        # 最も短い表記、同長なら先に出現したものを代表にする
        representative = sorted(items, key=lambda r: (len(r["keyword"]), items.index(r)))[0]
        keyword = representative["keyword"].strip()
        sources = sorted({i.get("source", "") for i in items if i.get("source")})
        fetched_ats = [i.get("fetched_at", "") for i in items if i.get("fetched_at")]
        volumes = [
            i.get("search_volume", "").strip()
            for i in items
            if i.get("search_volume_status") == "取得済み" and i.get("search_volume", "").strip()
        ]
        example_flags = {i.get("is_example_data", "no") for i in items}

        if volumes:
            # 複数ある場合は数値として比較できるもの優先、できなければ先頭
            numeric = []
            for v in volumes:
                try:
                    numeric.append((int(str(v).replace(",", "")), v))
                except ValueError:
                    continue
            search_volume = str(max(numeric)[1]) if numeric else volumes[0]
            search_volume_status = "取得済み"
        else:
            search_volume = ""
            search_volume_status = "未確認"

        clean.append(
            {
                "keyword": keyword,
                "normalized_keyword": key,
                "category": categorize_keyword(keyword, categories),
                "sources": "|".join(sources),
                "source_count": str(len(sources)),
                "first_fetched_at": min(fetched_ats) if fetched_ats else "",
                "last_fetched_at": max(fetched_ats) if fetched_ats else "",
                "search_volume": search_volume,
                "search_volume_status": search_volume_status,
                "occurrence_count": str(len(items)),
                "is_example_data": "yes" if "yes" in example_flags else "no",
                "notes": "deduplicated",
            }
        )

    clean.sort(key=lambda r: (r["category"], r["keyword"]))
    return clean


def build_priority_rows(clean_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """
    検索ボリュームと企画関連性の整理。
    検索ボリューム未取得の場合は需要順位を付けず「評価保留」。
    サジェスト存在 ≠ 月間検索数が多い、を明示する。
    """
    with_volume: list[dict[str, str]] = []
    without_volume: list[dict[str, str]] = []

    for row in clean_rows:
        item = {
            "keyword": row["keyword"],
            "category": row["category"],
            "search_intent": row["category"],
            "sources": row["sources"],
            "search_volume": row["search_volume"],
            "search_volume_status": row["search_volume_status"],
            "suggest_presence": "あり（サジェスト取得済み）"
            if "suggest" in row["sources"] or "google_suggest" in row["sources"] or "youtube_suggest" in row["sources"]
            else ("あり（CSV取込）" if row["sources"] else "不明"),
            "volume_vs_suggest_note": (
                "サジェストに出ることと月間検索数が多いことは別です。"
                "検索ボリュームが未確認のため需要順位は付けません。"
            ),
            "video_relevance": _estimate_video_relevance(row["category"]),
            "priority_rank": "",
            "evaluation_status": "",
            "planning_note": "",
        }
        if row["search_volume_status"] == "取得済み" and row["search_volume"]:
            with_volume.append(item)
        else:
            item["priority_rank"] = ""
            item["evaluation_status"] = "評価保留"
            item["planning_note"] = "検索ボリューム未確認のため需要順位付け不可"
            without_volume.append(item)

    # ボリューム取得済みのみ数値順で順位付け
    def volume_key(item: dict[str, str]) -> int:
        try:
            return int(str(item["search_volume"]).replace(",", "").replace("〜", "-").split("-")[0])
        except ValueError:
            return -1

    with_volume.sort(key=volume_key, reverse=True)
    for idx, item in enumerate(with_volume, start=1):
        item["priority_rank"] = str(idx)
        item["evaluation_status"] = "ボリューム基準で暫定順位付与"
        item["volume_vs_suggest_note"] = (
            "検索ボリュームに基づく暫定順位です。"
            "サジェスト存在の有無とは別指標です。"
        )
        item["planning_note"] = "キーワードプランナー等の実測値に基づく"

    return with_volume + without_volume


def _estimate_video_relevance(category: str) -> str:
    mapping = {
        "副業の種類・おすすめ": "高（入門・一覧系動画向き）",
        "単発勤務・ダブルワーク": "高（実務・始め方動画向き）",
        "在宅勤務": "高（働き方関心が強い）",
        "収入・時給": "高（収益系の関心）",
        "税金・確定申告": "中〜高（不安解消系）",
        "法律・就業規則": "高（リスク・不安系）",
        "スキル活用・個人事業": "中（差別化・応用）",
        "その他": "要確認",
    }
    return mapping.get(category, "要確認")
