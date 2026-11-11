"""Google / YouTube サジェスト収集（公開オートコンプリートAPI）."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import quote

import requests

from .utils import now_jst_iso


GOOGLE_SUGGEST_URL = (
    "https://suggestqueries.google.com/complete/search"
    "?client=firefox&hl=ja&q={query}"
)
YOUTUBE_SUGGEST_URL = (
    "https://suggestqueries.google.com/complete/search"
    "?client=firefox&ds=yt&hl=ja&q={query}"
)


class SuggestCollector:
    def __init__(
        self,
        *,
        interval_seconds: float = 0.35,
        timeout_seconds: float = 10,
        logger: Any = None,
        session: requests.Session | None = None,
    ) -> None:
        self.interval_seconds = interval_seconds
        self.timeout_seconds = timeout_seconds
        self.logger = logger
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "PharmacistKeywordTool/0.1 "
                    "(research; educational; contact: local)"
                ),
                "Accept": "application/json,text/javascript,*/*",
                "Accept-Language": "ja,en;q=0.8",
            }
        )
        self.errors: list[dict[str, str]] = []

    def _log_error(self, source: str, query: str, message: str) -> None:
        record = {
            "source": source,
            "query": query,
            "message": message,
            "fetched_at": now_jst_iso(),
        }
        self.errors.append(record)
        if self.logger:
            self.logger.warning("[%s] query=%r error=%s", source, query, message)

    def fetch_suggestions(self, source: str, query: str) -> list[str]:
        if source == "google_suggest":
            url = GOOGLE_SUGGEST_URL.format(query=quote(query))
        elif source == "youtube_suggest":
            url = YOUTUBE_SUGGEST_URL.format(query=quote(query))
        else:
            raise ValueError(f"unknown source: {source}")

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.session.get(url, timeout=self.timeout_seconds)
                if response.status_code == 403:
                    # レート制限の可能性があるため待機して再試行（迂回はしない）
                    wait = self.interval_seconds * (2 ** attempt)
                    if self.logger:
                        self.logger.warning(
                            "[%s] 403 for %r (attempt %s/%s). wait=%.1fs",
                            source,
                            query,
                            attempt,
                            max_attempts,
                            wait,
                        )
                    time.sleep(wait)
                    if attempt == max_attempts:
                        self._log_error(source, query, "403 Client Error after retries")
                        return []
                    continue
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, list) or len(data) < 2:
                    self._log_error(source, query, f"unexpected payload: {data!r}")
                    return []
                suggestions = data[1]
                if not isinstance(suggestions, list):
                    self._log_error(
                        source, query, f"suggestions not list: {suggestions!r}"
                    )
                    return []
                results = []
                for item in suggestions:
                    if isinstance(item, str) and item.strip():
                        results.append(item.strip())
                    elif isinstance(item, list) and item and isinstance(item[0], str):
                        results.append(item[0].strip())
                return results
            except (requests.RequestException, json.JSONDecodeError, ValueError) as exc:
                self._log_error(source, query, str(exc))
                return []
            finally:
                time.sleep(self.interval_seconds)
        return []

    def collect_for_seed(
        self,
        *,
        seed: str,
        suffixes: list[str],
        sources: list[str],
        must_contain: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """プローブクエリでサジェストを取得し、返ってきた候補だけを記録する."""
        rows: list[dict[str, str]] = []
        seen_local: set[tuple[str, str]] = set()
        required = [p for p in (must_contain or []) if p]

        for source in sources:
            for suffix in suffixes:
                probe = f"{seed}{suffix}"
                suggestions = self.fetch_suggestions(source, probe)
                fetched_at = now_jst_iso()
                for kw in suggestions:
                    key = (source, kw)
                    if key in seen_local:
                        continue
                    # メインテーマ語を含まないノイズは除外
                    if required and not all(p in kw for p in required):
                        continue
                    seen_local.add(key)
                    rows.append(
                        {
                            "keyword": kw,
                            "source": source,
                            "probe_query": probe,
                            "fetched_at": fetched_at,
                            "search_volume": "",
                            "search_volume_status": "未確認",
                            "is_example_data": "no",
                            "notes": "autocomplete_suggest",
                        }
                    )
        return rows


def collect_suggestions(
    *,
    seed_keyword: str,
    probe_suffixes: list[str],
    second_pass_suffixes: list[str],
    max_second_pass_seeds: int,
    interval_seconds: float,
    timeout_seconds: float,
    logger: Any = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    collector = SuggestCollector(
        interval_seconds=interval_seconds,
        timeout_seconds=timeout_seconds,
        logger=logger,
    )
    theme_parts = [p for p in seed_keyword.split() if p]

    first = collector.collect_for_seed(
        seed=seed_keyword,
        suffixes=probe_suffixes,
        sources=["google_suggest", "youtube_suggest"],
        must_contain=theme_parts,
    )

    # 1段階目で得たキーワードを種にして拡張（件数を抑えつつ関連語を増やす）
    unique_keywords: list[str] = []
    seen = set()
    for row in first:
        kw = row["keyword"]
        if kw == seed_keyword:
            continue
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    second: list[dict[str, str]] = []
    for kw in unique_keywords[:max_second_pass_seeds]:
        more = collector.collect_for_seed(
            seed=kw,
            suffixes=second_pass_suffixes,
            sources=["google_suggest", "youtube_suggest"],
            must_contain=theme_parts,
        )
        second.extend(more)

    all_rows = first + second
    return all_rows, collector.errors
