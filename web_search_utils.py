"""Shared bilingual web-search utilities for AI-DQA and AI-FA."""
from __future__ import annotations

import re
from typing import Callable, Dict, List


def _contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def web_search_dual(
    query: str,
    lang: str,
    translate_to_en: Callable[[str], str],
    max_results_each: int = 3,
    max_output: int = 5,
) -> str:
    """
    Dual-direction bilingual web search.
    - If query is Chinese (or lang is zh), search Chinese first.
    - Then search English as supplement (translated query when needed).
    """
    results: List[Dict[str, str]] = []

    try:
        from duckduckgo_search import DDGS

        ddgs = DDGS()
    except ImportError:
        return "（联网搜索功能需要安装 duckduckgo-search）"

    if lang == "zh" or _contains_chinese(query):
        try:
            chinese_results = list(ddgs.text(query, max_results=max_results_each))
            for item in chinese_results:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "snippet": item.get("body", "")[:300],
                        "source": "chinese",
                    }
                )
        except Exception:
            pass

    en_query = translate_to_en(query) if _contains_chinese(query) else query
    try:
        english_results = list(ddgs.text(en_query, max_results=max_results_each))
        for item in english_results:
            title = item.get("title", "")
            if not any(title == existing["title"] for existing in results):
                results.append(
                    {
                        "title": title,
                        "snippet": item.get("body", "")[:300],
                        "source": "english",
                    }
                )
    except Exception:
        pass

    if not results:
        return "（未找到相关结果）"

    formatted = [f"- {item['title']}: {item['snippet']}" for item in results[:max_output]]
    return "联网搜索结果：\n" + "\n".join(formatted)
