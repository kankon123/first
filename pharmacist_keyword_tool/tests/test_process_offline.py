"""ネットワーク不要のオフライン検証."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.csv_importer import import_all_csv, merge_volume_onto_keywords
from src.process import build_clean_rows, build_priority_rows, categorize_keyword
from src.utils import normalize_keyword, write_csv_utf8_bom


CATEGORIES = [
    {"name": "在宅勤務", "keywords": ["在宅"]},
    {"name": "税金・確定申告", "keywords": ["確定申告"]},
    {"name": "法律・就業規則", "keywords": ["バレ"]},
    {"name": "副業の種類・おすすめ", "keywords": ["おすすめ"]},
    {"name": "その他", "keywords": []},
]


class ProcessOfflineTest(unittest.TestCase):
    def test_normalize_and_category(self) -> None:
        self.assertEqual(normalize_keyword("  薬剤師　副業  "), "薬剤師 副業")
        self.assertEqual(
            categorize_keyword("薬剤師 副業 在宅", CATEGORIES),
            "在宅勤務",
        )

    def test_dedupe_and_priority_hold(self) -> None:
        raw = [
            {
                "keyword": "薬剤師 副業 在宅",
                "source": "google_suggest",
                "probe_query": "薬剤師 副業 ざ",
                "fetched_at": "2026-01-01 00:00:00 +0900",
                "search_volume": "",
                "search_volume_status": "未確認",
                "is_example_data": "no",
                "notes": "",
            },
            {
                "keyword": "薬剤師  副業 在宅",
                "source": "youtube_suggest",
                "probe_query": "薬剤師 副業 ざ",
                "fetched_at": "2026-01-01 00:00:01 +0900",
                "search_volume": "",
                "search_volume_status": "未確認",
                "is_example_data": "no",
                "notes": "",
            },
        ]
        clean = build_clean_rows(raw, CATEGORIES)
        self.assertEqual(len(clean), 1)
        self.assertEqual(clean[0]["category"], "在宅勤務")
        priority = build_priority_rows(clean)
        self.assertEqual(priority[0]["evaluation_status"], "評価保留")
        self.assertEqual(priority[0]["priority_rank"], "")

    def test_missing_input_dir_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rows = import_all_csv(
                input_dir=Path(tmp) / "no_such_dir",
                rakko_glob="rakko*.csv",
                planner_glob="planner*.csv",
                keyword_planner_glob="*planner*.csv",
            )
            self.assertEqual(rows, [])

    def test_volume_merge(self) -> None:
        base = [
            {
                "keyword": "薬剤師 副業",
                "source": "google_suggest",
                "probe_query": "",
                "fetched_at": "2026-01-01 00:00:00 +0900",
                "search_volume": "",
                "search_volume_status": "未確認",
                "is_example_data": "no",
                "notes": "",
            }
        ]
        volume_rows = [
            {
                "keyword": "薬剤師 副業",
                "source": "keyword_planner_csv",
                "probe_query": "",
                "fetched_at": "2026-01-01 00:00:00 +0900",
                "search_volume": "1000",
                "search_volume_status": "取得済み",
                "is_example_data": "no",
                "notes": "",
            }
        ]
        merged = merge_volume_onto_keywords(base, volume_rows)
        self.assertEqual(merged[0]["search_volume"], "1000")
        self.assertEqual(merged[0]["search_volume_status"], "取得済み")

    def test_csv_roundtrip_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            write_csv_utf8_bom(
                path,
                ["keyword", "search_volume"],
                [{"keyword": "薬剤師 副業", "search_volume": "未確認"}],
            )
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
