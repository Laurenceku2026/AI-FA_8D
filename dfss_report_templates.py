"""Fill client 8D Excel templates for AI-FA exports."""
from __future__ import annotations

import os
import re
from datetime import datetime
from io import BytesIO
from typing import List, Tuple

import xlrd
from xlutils.copy import copy as xl_copy

TEMPLATE_EXTENSIONS = (".xlsx", ".xls", ".docx")
EIGHT_D_TEMPLATE_FILENAME = "FM--QEOP-244 8D报告 A0.xls"


def list_report_templates(app_key: str = "AI-FA") -> List[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    folders = [
        os.path.join(here, "templates"),
        os.path.join(os.environ.get("DFSS_TEMPLATE_DIR", ""), app_key),
        os.path.join(r"C:\Users\Laurence\Technical\Project\SaaS\DFSS Report Template", app_key),
    ]
    found: List[str] = []
    for folder in folders:
        if not folder or not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            if name.startswith("~$"):
                continue
            if os.path.splitext(name)[1].lower() in TEMPLATE_EXTENSIONS:
                if name not in found:
                    found.append(name)
    return sorted(found)


def template_mime_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".xls":
        return "application/vnd.ms-excel"
    if ext == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def export_report_template(
    template_filename: str,
    result,
    lang: str = "zh",
    analyst_name: str = "",
) -> Tuple[BytesIO, str]:
    """Fill a selected report template. Fixed client templates use rule mapping (no LLM)."""
    lower_name = template_filename.lower()
    if lower_name.endswith(".xls") or lower_name.endswith(".xlsx"):
        if "8d" in lower_name or "qeop-244" in lower_name:
            data = fill_8d_template(
                result=result,
                lang=lang,
                analyst_name=analyst_name,
                template_filename=template_filename,
            )
            return data, template_mime_type(template_filename)
    raise ValueError(
        "当前模板暂未配置自动填表规则。"
        if lang == "zh"
        else "Automatic fill rules are not configured for this template yet."
    )


def resolve_template_path(filename: str, app_key: str = "AI-FA") -> str:
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
    raise FileNotFoundError(f"8D template not found: {filename}")


def _clean_text(text: str) -> str:
    return re.sub(r"\*\*", "", text or "").strip()


def _join_lines(items: List[str], lang: str) -> str:
    cleaned = [_clean_text(x) for x in items if _clean_text(x)]
    if cleaned:
        return "\n".join(f"{i + 1}. {line}" for i, line in enumerate(cleaned))
    return "待补充" if lang == "zh" else "Pending"


def _build_cause_analysis(result, lang: str) -> str:
    root = _clean_text(result.root_cause_zh if lang == "zh" else result.root_cause_en)
    parts = [f"根本原因：{root}" if lang == "zh" else f"Root cause: {root}"]

    for item in result.five_why:
        q = _clean_text(item.question_zh if lang == "zh" else item.question_en)
        a = _clean_text(item.answer_zh if lang == "zh" else item.answer_en)
        if q or a:
            parts.append(f"Why-{item.level}: {q}\n→ {a}")

    fishbone_dict = result.fishbone.to_dict(lang)
    cat_names_zh = {
        "Man": "人",
        "Machine": "机",
        "Material": "料",
        "Method": "法",
        "Environment": "环",
        "Measurement": "测",
    }
    for cat, causes in fishbone_dict.items():
        if not causes:
            continue
        cat_label = cat_names_zh.get(cat, cat) if lang == "zh" else cat
        cause_text = "；".join(_clean_text(c) for c in causes[:3])
        parts.append(f"{cat_label}: {cause_text}")

    return "\n\n".join(parts)


def fill_8d_template(
    result,
    lang: str = "zh",
    analyst_name: str = "",
    template_filename: str = EIGHT_D_TEMPLATE_FILENAME,
) -> BytesIO:
    """Fill the client 8D .xls template and return an in-memory workbook."""
    template_path = resolve_template_path(template_filename, "AI-FA")
    rb = xlrd.open_workbook(template_path, formatting_info=True)
    wb = xl_copy(rb)
    ws = wb.get_sheet(0)

    product_name = _clean_text(result.product_name)
    symptom = _clean_text(result.symptom if lang == "zh" else result.symptom_en)
    installation = _clean_text(result.installation if lang == "zh" else result.installation_en)
    today = datetime.now().strftime("%Y-%m-%d")

    team_text = analyst_name or ("AI-FA 跨职能小组" if lang == "zh" else "AI-FA cross-functional team")
    interim = result.interim_actions_zh if lang == "zh" else result.interim_actions_en
    permanent = result.permanent_actions_zh if lang == "zh" else result.permanent_actions_en
    preventive = result.preventive_actions_zh if lang == "zh" else result.preventive_actions_en

    # Header
    ws.write(5, 6, product_name)  # R6 部件名称
    ws.write(5, 3, _clean_text(result.project_name) or "-")  # R6 部件编号
    ws.write(6, 6, today)  # R7 日期

    # D1-D8 content areas in the client template
    ws.write(8, 0, team_text)  # D1
    problem = symptom
    if installation:
        problem = f"{problem}\n\n安装环境：{installation}" if lang == "zh" else f"{problem}\n\nInstallation: {installation}"
    ws.write(11, 0, problem)  # D2
    ws.write(14, 0, _join_lines(interim, lang))  # D3
    ws.write(18, 0, _build_cause_analysis(result, lang))  # D4
    ws.write(22, 0, _join_lines(permanent, lang))  # D5
    ws.write(25, 0, _join_lines(
        [
            "功能/可靠性验证通过" if lang == "zh" else "Function/reliability verification passed",
            f"失效等级：{result.failure_stage}" if lang == "zh" else f"Failure stage: {result.failure_stage}",
        ],
        lang,
    ))  # D6
    ws.write(28, 0, _join_lines(preventive, lang))  # D7

    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out
