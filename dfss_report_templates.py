"""Fill client 8D Excel templates for AI-FA exports."""
from __future__ import annotations

import os
import re
from datetime import datetime
from io import BytesIO
from typing import List, Optional, Tuple

import xlrd
from xlutils.copy import copy as xl_copy

from fa_template_profiles import (
    TEMPLATE_MODE_CUSTOM,
    TEMPLATE_MODE_DEFAULT,
    resolve_profile_template_filename,
)

TEMPLATE_EXTENSIONS = (".xlsx", ".xls", ".docx")
DEFAULT_8D_TEMPLATE_FILENAME = resolve_profile_template_filename(TEMPLATE_MODE_DEFAULT) or "默认-8D报告.xls"
TEMPLATE1_8D_FILENAME = resolve_profile_template_filename("template1") or "模板1-8D报告.xls"

# 8D 内容区（0-based row/col），两套模板结构一致
EIGHT_D_CONTENT_ROWS = {
    "d1": 8,
    "d2": 11,
    "d3": 14,
    "d4": 18,
    "d5": 22,
    "d6": 25,
    "d7": 28,
    "d8": 31,
}


def list_report_templates(app_key: str = "AI-FA") -> List[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    folders = [
        os.path.join(here, "templates"),
        os.path.join(os.environ.get("DFSS_TEMPLATE_DIR", ""), app_key),
        os.path.join(r"C:\Users\Laurence\Technical\Project\SaaS\DFSS Report Template", app_key),
    ]
    found: List[str] = []
    for preferred in (DEFAULT_8D_TEMPLATE_FILENAME, TEMPLATE1_8D_FILENAME):
        try:
            resolve_template_path(preferred, app_key)
            if preferred not in found:
                found.append(preferred)
        except FileNotFoundError:
            continue
    for folder in folders:
        if not folder or not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            if name.startswith("~$"):
                continue
            if os.path.splitext(name)[1].lower() in TEMPLATE_EXTENSIONS:
                if "8d" in name.lower() and name not in found:
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
    result,
    lang: str = "zh",
    analyst_name: str = "",
    template_mode: str = TEMPLATE_MODE_DEFAULT,
    template_filename: str = "",
    template_bytes: Optional[bytes] = None,
) -> Tuple[BytesIO, str]:
    """Fill a selected 8D report template using rule mapping (no LLM)."""
    if template_mode == TEMPLATE_MODE_CUSTOM:
        if not template_bytes:
            raise ValueError(
                "请先上传自定义 8D 模板。" if lang == "zh" else "Please upload a custom 8D template first."
            )
        name = template_filename or "custom_8d.xls"
        data = fill_8d_template(
            result=result,
            lang=lang,
            analyst_name=analyst_name,
            template_bytes=template_bytes,
            template_filename=name,
        )
        return data, template_mime_type(name)

    filename = template_filename or resolve_profile_template_filename(template_mode) or DEFAULT_8D_TEMPLATE_FILENAME
    lower_name = filename.lower()
    if lower_name.endswith(".xls") or lower_name.endswith(".xlsx"):
        if "8d" in lower_name:
            data = fill_8d_template(
                result=result,
                lang=lang,
                analyst_name=analyst_name,
                template_filename=filename,
            )
            return data, template_mime_type(filename)
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


def _stage_name(stage: int, lang: str) -> str:
    stages_zh = {0: "正常", 1: "轻微异常", 2: "中度异常", 3: "严重故障"}
    stages_en = {0: "Normal", 1: "Minor anomaly", 2: "Moderate anomaly", 3: "Critical failure"}
    mapping = stages_zh if lang == "zh" else stages_en
    return mapping.get(stage, str(stage))


def _build_d1_team(result, analyst_name: str, lang: str) -> str:
    leader = analyst_name or ("组长" if lang == "zh" else "Team leader")
    if lang == "zh":
        lines = [
            f"1. 组长：{leader}（统筹8D流程与跨部门协调）",
            "2. 设计工程师：负责根因分析、设计变更与长期对策",
            "3. 质量工程师：负责围堵措施、验证试验与标准化",
        ]
        if result.analyst_title:
            lines[0] = f"1. 组长：{leader}（{result.analyst_title}）"
    else:
        lines = [
            f"1. Team leader: {leader} (8D coordination)",
            "2. Design engineer: root cause analysis and permanent actions",
            "3. Quality engineer: containment, verification, and standardization",
        ]
    return "\n".join(lines)


def _build_d2_problem(result, lang: str) -> str:
    symptom = _clean_text(result.symptom if lang == "zh" else result.symptom_en)
    installation = _clean_text(result.installation if lang == "zh" else result.installation_en)
    stage = _stage_name(result.failure_stage, lang)
    today = datetime.now().strftime("%Y-%m-%d")
    if lang == "zh":
        parts = [
            f"What（什么）：{symptom}",
            f"Where（何处）：{installation or '安装/使用现场'}",
            f"When（何时）：{today}",
            "Who（何人）：现场维护/质量团队",
            "Why（为何）：待根因确认",
            "How（如何发现）：运行或检验过程中发现异常",
            f"How many/How bad（程度）：{stage}（置信度 {result.root_cause_confidence:.0%}）",
        ]
    else:
        parts = [
            f"What: {symptom}",
            f"Where: {installation or 'Installation site'}",
            f"When: {today}",
            "Who: Field maintenance / quality team",
            "Why: Root cause under investigation",
            "How: Detected during operation or inspection",
            f"Severity: {stage} (confidence {result.root_cause_confidence:.0%})",
        ]
    return "\n".join(parts)


def _build_cause_analysis(result, lang: str) -> str:
    root = _clean_text(result.root_cause_zh if lang == "zh" else result.root_cause_en)
    parts = [f"根本原因：{root}" if lang == "zh" else f"Root cause: {root}"]

    if result.five_why:
        parts.append("5-Why 分析：" if lang == "zh" else "5-Why analysis:")
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
    parts.append("鱼骨图（6M）摘要：" if lang == "zh" else "Fishbone (6M) summary:")
    for cat, causes in fishbone_dict.items():
        if not causes:
            continue
        cat_label = cat_names_zh.get(cat, cat) if lang == "zh" else cat
        cause_text = "；".join(_clean_text(c) for c in causes[:5])
        parts.append(f"{cat_label}: {cause_text}")

    return "\n\n".join(parts)


def _build_d6_verification(result, lang: str) -> str:
    stage = _stage_name(result.failure_stage, lang)
    if lang == "zh":
        lines = [
            "验证项目：功能测试、可靠性/耐久测试、现场回归确认",
            "验证方法：按产品标准进行型式试验，并跟踪现场批次",
            "判定准则：故障现象不再复现，关键性能指标满足规格",
            f"验证结果：功能/可靠性验证通过；失效等级：{stage}",
        ]
    else:
        lines = [
            "Items: functional test, reliability/durability test, field confirmation",
            "Method: type tests per product standard with batch follow-up",
            "Criteria: failure no longer reproduced; KPIs within specification",
            f"Result: verification passed; failure stage: {stage}",
        ]
    if result.spc_analysis:
        lines.append(
            f"SPC：{str(result.spc_analysis.get('summary', '已进行时序数据分析'))[:120]}"
            if lang == "zh"
            else f"SPC: {str(result.spc_analysis.get('summary', 'Time-series reviewed'))[:120]}"
        )
    return "\n".join(lines)


def _build_d8_recognition(lang: str) -> str:
    if lang == "zh":
        return _join_lines(
            [
                "根本原因已确认并形成闭环",
                "改进措施已定义并进入标准化",
                "经验教训已纳入知识库与流程",
            ],
            lang,
        )
    return _join_lines(
        [
            "Root cause confirmed and closed",
            "Improvement actions defined and standardized",
            "Lessons learned added to knowledge base",
        ],
        lang,
    )


def _estimate_row_height(text: str, base: int = 480, per_line: int = 280, chars_per_line: int = 42) -> int:
    content = str(text or "")
    line_count = content.count("\n") + 1
    wrapped = sum(max(1, (len(line) + chars_per_line - 1) // chars_per_line) for line in content.splitlines() or [""])
    total_lines = max(line_count, wrapped)
    return min(12000, base + total_lines * per_line)


def _write_cell_with_height(ws, row: int, col: int, text: str) -> None:
    ws.write(row, col, text)
    height = _estimate_row_height(text)
    row_obj = ws.row(row)
    row_obj.height = height
    row_obj.height_mismatch = True


def fill_8d_template(
    result,
    lang: str = "zh",
    analyst_name: str = "",
    template_filename: str = DEFAULT_8D_TEMPLATE_FILENAME,
    template_bytes: Optional[bytes] = None,
) -> BytesIO:
    """Fill the client 8D .xls template and return an in-memory workbook."""
    if template_bytes:
        rb = xlrd.open_workbook(file_contents=template_bytes, formatting_info=True)
    else:
        template_path = resolve_template_path(template_filename, "AI-FA")
        rb = xlrd.open_workbook(template_path, formatting_info=True)
    wb = xl_copy(rb)
    ws = wb.get_sheet(0)

    product_name = _clean_text(result.product_name)
    project_name = _clean_text(result.project_name) or product_name
    symptom = _clean_text(result.symptom if lang == "zh" else result.symptom_en)
    installation = _clean_text(result.installation if lang == "zh" else result.installation_en)
    today = datetime.now().strftime("%Y-%m-%d")
    stage = _stage_name(result.failure_stage, lang)

    interim = result.interim_actions_zh if lang == "zh" else result.interim_actions_en
    permanent = result.permanent_actions_zh if lang == "zh" else result.permanent_actions_en
    preventive = result.preventive_actions_zh if lang == "zh" else result.preventive_actions_en

    # Header fields
    ws.write(5, 1, project_name)  # 客户名称
    ws.write(5, 3, project_name)  # 部件编号
    ws.write(5, 6, product_name)  # 部件名称
    ws.write(6, 1, analyst_name or "-")  # 客户代码
    ws.write(6, 3, stage)  # 失效率/严重度
    ws.write(6, 6, today)  # 日期

    d1 = _build_d1_team(result, analyst_name, lang)
    d2 = _build_d2_problem(result, lang)
    d3 = _join_lines(interim, lang)
    d4 = _build_cause_analysis(result, lang)
    d5 = _join_lines(permanent, lang)
    d6 = _build_d6_verification(result, lang)
    d7 = _join_lines(preventive, lang)
    d8 = _build_d8_recognition(lang)

    sections = {
        "d1": d1,
        "d2": d2,
        "d3": d3,
        "d4": d4,
        "d5": d5,
        "d6": d6,
        "d7": d7,
        "d8": d8,
    }
    for key, content in sections.items():
        _write_cell_with_height(ws, EIGHT_D_CONTENT_ROWS[key], 0, content)

    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out
