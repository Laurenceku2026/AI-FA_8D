"""Fixed 8D template profiles for AI-FA (deploy-safe standalone module)."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

MODULE_VERSION = "20260711"

# Plain filenames — no filesystem access at import time (Cloud-safe).
DEFAULT_8D_TEMPLATE_FILENAME = "默认-8D报告.xlsx"
DEFAULT_8D_TEMPLATE_FILENAME_EN = "Default-8D-Report.xlsx"
TEMPLATE1_8D_FILENAME = "模板1-8D报告.xlsx"
TEMPLATE1_8D_FILENAME_EN = "Template-1-8D-Report.xlsx"
EIGHT_D_TEMPLATE_FILENAME = DEFAULT_8D_TEMPLATE_FILENAME  # legacy alias

TEMPLATE_PROFILES: Dict[str, Dict[str, Any]] = {
    "default": {
        "filename": DEFAULT_8D_TEMPLATE_FILENAME,
        "filename_en": DEFAULT_8D_TEMPLATE_FILENAME_EN,
        "label_zh": "默认 8D 模板",
        "label_en": "Default 8D template",
    },
    "template1": {
        "filename": TEMPLATE1_8D_FILENAME,
        "filename_en": TEMPLATE1_8D_FILENAME_EN,
        "label_zh": "模板-1",
        "label_en": "Template-1",
    },
}

TEMPLATE_MODE_DEFAULT = "default"
TEMPLATE_MODE_TEMPLATE1 = "template1"
TEMPLATE_MODE_CUSTOM = "custom"


def _resolve_template_path(filename: str, app_key: str = "AI-FA") -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "templates", filename),
        os.path.join(os.environ.get("DFSS_TEMPLATE_DIR", ""), app_key, filename),
        os.path.join(
            r"C:\Users\Laurence\Technical\Project\SaaS\DFSS Report Template",
            app_key,
            filename,
        ),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    raise FileNotFoundError(f"Template not found: {filename}")


def profile_template_filename(mode: str, lang: str = "zh") -> Optional[str]:
    profile = TEMPLATE_PROFILES.get(mode)
    if not profile:
        return None
    if lang == "en":
        return str(profile.get("filename_en") or profile.get("filename") or "")
    return str(profile.get("filename") or "")


def resolve_profile_template_filename(mode: str, lang: str = "zh") -> Optional[str]:
    name = profile_template_filename(mode, lang)
    if not name:
        return None
    try:
        _resolve_template_path(name, "AI-FA")
    except FileNotFoundError:
        # Fallback to Chinese shell if English file missing on disk
        if lang == "en":
            fallback = profile_template_filename(mode, "zh")
            if fallback and fallback != name:
                try:
                    _resolve_template_path(fallback, "AI-FA")
                    return fallback
                except FileNotFoundError:
                    pass
    return name


def get_template_profile_label(mode: str, lang: str = "zh") -> str:
    if mode == TEMPLATE_MODE_CUSTOM:
        return "上传自定义模板" if lang == "zh" else "Upload custom template"
    profile = TEMPLATE_PROFILES.get(mode, {})
    key = "label_zh" if lang == "zh" else "label_en"
    return str(profile.get(key, mode))


def list_template_mode_options(lang: str = "zh") -> list[tuple[str, str]]:
    """Return (mode_id, display_label) for the template selectbox."""
    return [
        (TEMPLATE_MODE_DEFAULT, get_template_profile_label(TEMPLATE_MODE_DEFAULT, lang)),
        (TEMPLATE_MODE_TEMPLATE1, get_template_profile_label(TEMPLATE_MODE_TEMPLATE1, lang)),
        (TEMPLATE_MODE_CUSTOM, get_template_profile_label(TEMPLATE_MODE_CUSTOM, lang)),
    ]
