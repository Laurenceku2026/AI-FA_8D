"""Shared Supabase knowledge base utilities for AI-DQA and AI-FA."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Callable, Dict, List, Optional

import pandas as pd
import requests

KNOWLEDGE_CATEGORIES = ["光学", "机械", "材料", "热学", "电气", "控制"]


def is_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


class SupabaseKnowledgeDB:
    """Supabase knowledge base with bilingual dual-direction search."""

    def __init__(
        self,
        supabase_url: str,
        service_role_key: str,
        translate_to_en: Callable[[str], str],
        translate_to_zh: Callable[[str], str],
        ui_lang_getter: Callable[[], str] = lambda: "zh",
    ):
        self.supabase_url = supabase_url
        self.service_role_key = service_role_key
        self._translate_to_en = translate_to_en
        self._translate_to_zh = translate_to_zh
        self._ui_lang_getter = ui_lang_getter
        self.categories = list(KNOWLEDGE_CATEGORIES)
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
        }
        self.knowledge_zh: Dict[str, List[str]] = {cat: [] for cat in self.categories}
        self.knowledge_en: Dict[str, List[str]] = {cat: [] for cat in self.categories}
        self._load_cache()

    def _load_cache(self) -> None:
        self.knowledge_zh = {cat: [] for cat in self.categories}
        self.knowledge_en = {cat: [] for cat in self.categories}
        if not self.supabase_url or not self.service_role_key:
            return
        try:
            response = requests.get(
                f"{self.supabase_url}/rest/v1/knowledge_base?order=id",
                headers=self.headers,
                timeout=10,
            )
            if response.status_code == 200:
                for row in response.json():
                    cat = row.get("category")
                    if cat in self.knowledge_zh:
                        if row.get("content"):
                            self.knowledge_zh[cat].append(row.get("content"))
                        if row.get("content_en"):
                            self.knowledge_en[cat].append(row.get("content_en"))
        except Exception as exc:
            print(f"加载知识库失败: {exc}")

    def get_knowledge(self, category: str, lang: str = "zh") -> List[str]:
        if lang == "zh":
            return self.knowledge_zh.get(category, [])
        return self.knowledge_en.get(category, [])

    def get_knowledge_by_category(self, category: str) -> List[str]:
        return self.get_knowledge(category, self._ui_lang_getter())

    def search_knowledge_dual(self, query: str, lang: str) -> List[str]:
        """
        Dual-direction bilingual search for one query language.
        - lang='en': search English corpus first, then translate query to Chinese and search Chinese corpus.
        - lang='zh': search Chinese corpus first, then translate query to English and search English corpus.
        """
        if not query or not query.strip():
            return []

        results: List[str] = []
        query_lower = query.lower()

        for cat in self.categories:
            for item in self.get_knowledge(cat, lang):
                if query_lower in item.lower() and item not in results:
                    results.append(item)

        other_lang = "en" if lang == "zh" else "zh"
        trans_query = (
            self._translate_to_en(query) if lang == "zh" else self._translate_to_zh(query)
        )
        trans_lower = (trans_query or "").lower()
        if trans_lower:
            for cat in self.categories:
                for item in self.get_knowledge(cat, other_lang):
                    if trans_lower in item.lower() and item not in results:
                        results.append(item)

        return results[:10]

    def search_knowledge(self, keywords: str, limit: int = 10) -> List[str]:
        query_lang = "zh" if is_chinese(keywords) else "en"
        return self.search_knowledge_dual(keywords, query_lang)[:limit]

    def search_knowledge_full(self, query: str, limit: int = 10) -> List[str]:
        """Full bidirectional retrieval used by AI-DQA and AI-FA analysis flows."""
        if not query or not query.strip():
            return []

        primary_lang = "zh" if is_chinese(query) else "en"
        other_lang = "en" if primary_lang == "zh" else "zh"
        translated = (
            self._translate_to_en(query) if primary_lang == "zh" else self._translate_to_zh(query)
        )

        merged: List[str] = []
        for item in self.search_knowledge_dual(query, primary_lang):
            if item not in merged:
                merged.append(item)
        for item in self.search_knowledge_dual(translated, other_lang):
            if item not in merged:
                merged.append(item)
        return merged[:limit]

    def add_knowledge(self, category: str, content: str) -> bool:
        lang = self._ui_lang_getter()
        if lang == "zh":
            zh_text, en_text = content, self._translate_to_en(content)
        else:
            en_text, zh_text = content, self._translate_to_zh(content)

        try:
            response = requests.post(
                f"{self.supabase_url}/rest/v1/knowledge_base",
                headers=self.headers,
                json={
                    "category": category,
                    "content": zh_text,
                    "content_en": en_text,
                    "created_at": datetime.now().isoformat(),
                },
                timeout=10,
            )
            if response.status_code in (200, 201, 204):
                self._load_cache()
                return True
        except Exception as exc:
            print(f"添加知识库失败: {exc}")
        return False

    def delete_knowledge(self, category: str, content: str) -> bool:
        lang = self._ui_lang_getter()
        try:
            if lang == "zh":
                url = (
                    f"{self.supabase_url}/rest/v1/knowledge_base"
                    f"?category=eq.{category}&content=eq.{content}"
                )
            else:
                url = (
                    f"{self.supabase_url}/rest/v1/knowledge_base"
                    f"?category=eq.{category}&content_en=eq.{content}"
                )
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200 and response.json():
                record_id = response.json()[0]["id"]
                delete_resp = requests.delete(
                    f"{self.supabase_url}/rest/v1/knowledge_base?id=eq.{record_id}",
                    headers=self.headers,
                    timeout=10,
                )
                if delete_resp.status_code in (200, 204):
                    self._load_cache()
                    return True
        except Exception as exc:
            print(f"删除知识库失败: {exc}")
        return False

    def clear_category(self, category: str) -> bool:
        try:
            response = requests.delete(
                f"{self.supabase_url}/rest/v1/knowledge_base?category=eq.{category}",
                headers=self.headers,
                timeout=10,
            )
            if response.status_code in (200, 204):
                self._load_cache()
                return True
        except Exception as exc:
            print(f"清空分类失败: {exc}")
        return False

    def clear_knowledge_category(self, category: str) -> bool:
        return self.clear_category(category)

    def get_all_knowledge(self) -> Dict[str, List[str]]:
        if self._ui_lang_getter() == "zh":
            return self.knowledge_zh
        return self.knowledge_en

    def export_to_dataframe(self) -> pd.DataFrame:
        max_len = max((len(self.knowledge_zh.get(cat, [])) for cat in self.categories), default=0)
        export_data = {}
        for cat in self.categories:
            items = self.knowledge_zh.get(cat, [])
            export_data[cat] = items + [""] * (max_len - len(items))
        return pd.DataFrame(export_data)

    def import_from_dataframe(self, df: pd.DataFrame) -> int:
        total = 0
        for cat in self.categories:
            if cat in df.columns:
                self.clear_category(cat)
                for item in df[cat].dropna():
                    text = str(item).strip()
                    if text and self.add_knowledge(cat, text):
                        total += 1
        self._load_cache()
        return total
