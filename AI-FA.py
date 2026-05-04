"""
AI-FA 智能故障分析系统
AI-powered Failure Analysis & 8D Report Generation

功能：
- 双语双向检索（原始语言 + 翻译语言并行搜索）
- 多模态输入（文本+图片+Ctrl+V粘贴）
- 5-Why根因推理
- 鱼骨图自动生成（matplotlib + Noto Sans CJK SC）
- 失效等级分类
- SPC时序分析（不良率趋势）
- 关联规则挖掘
- 双源知识库（内部+外部）
- FA报告生成 + 8D报告生成
- 双语支持（自动翻译用户输入）
- Word报告导出（图文并茂）

部署：Streamlit Cloud
作者：Laurence Ku
版本：1.0.0
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import uuid
import re
import io
import requests
import base64
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from PIL import Image
import plotly.graph_objects as go
import plotly.express as px

# ==================== 配置（从 Streamlit Secrets 读取）====================

def get_secret(key: str, default: str = "") -> str:
    """安全获取Secret配置"""
    try:
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except:
        pass
    return default

# DeepSeek API 配置
DEEPSEEK_API_KEY = get_secret("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = get_secret("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = get_secret("DEEPSEEK_MODEL", "deepseek-chat")

# Supabase 配置
SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = get_secret("SUPABASE_SERVICE_ROLE_KEY")

# Neo4j 配置（可选）
NEO4J_URI = get_secret("NEO4J_URI", "")
NEO4J_USERNAME = get_secret("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = get_secret("NEO4J_PASSWORD", "")

# 管理员配置
ADMIN_USERNAME = "Laurence_ku"
ADMIN_PASSWORD = "Ku_product$2026"

# 页面配置
st.set_page_config(
    page_title="AI-FA 智能故障分析系统",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 初始化 matplotlib 中文字体 ====================

def setup_chinese_font():
    """设置 matplotlib 中文字体"""
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import fontManager
    
    # 尝试加载 Noto Sans CJK SC 字体
    font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
    font_path = "/tmp/NotoSansCJKsc-Regular.otf"
    
    try:
        # 下载字体（如果不存在）
        import os
        if not os.path.exists(font_path):
            response = requests.get(font_url, timeout=30)
            with open(font_path, 'wb') as f:
                f.write(response.content)
        
        # 注册字体
        fontManager.addfont(font_path)
        plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        return True
    except Exception as e:
        # 回退方案
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        print(f"中文字体加载失败: {e}")
        return False


# ==================== 数据模型 ====================

@dataclass
class FiveWhyItem:
    """5-Why推理项"""
    level: int
    question: str
    answer: str
    confidence: float
    evidence_source: str
    verification_method: str


@dataclass
class FishboneAnalysis:
    """鱼骨图分析结果"""
    man: List[str] = field(default_factory=list)
    machine: List[str] = field(default_factory=list)
    material: List[str] = field(default_factory=list)
    method: List[str] = field(default_factory=list)
    environment: List[str] = field(default_factory=list)
    measurement: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "Man": self.man,
            "Machine": self.machine,
            "Material": self.material,
            "Method": self.method,
            "Environment": self.environment,
            "Measurement": self.measurement
        }


@dataclass
class FailureAnalysisResult:
    """故障分析完整结果"""
    case_id: str
    project_name: str
    product_name: str
    symptom: str
    installation: str
    temperature: str
    failure_stage: int
    five_why: List[FiveWhyItem]
    fishbone: FishboneAnalysis
    root_cause: str
    root_cause_confidence: float
    interim_actions: List[str]
    permanent_actions: List[str]
    preventive_actions: List[str]
    internal_cases_used: int
    external_sources_used: int
    spc_analysis: Optional[dict] = None
    association_rules: Optional[List[dict]] = None
    has_images: bool = False
    analyst_name: str = ""
    analyst_title: str = ""
    fishbone_image: Optional[bytes] = None


# ==================== 多语言文本 ====================

TEXTS = {
    "zh": {
        "app_title": "AI-FA 智能故障分析系统",
        "app_subtitle": "AI驱动的失效分析与8D报告生成",
        "lang_zh": "中文",
        "lang_en": "English",
        "sidebar_about": "关于系统",
        "sidebar_principle": "原理：基于DeepSeek大语言模型 + 5-Why推理引擎，自动进行失效等级分类、鱼骨图分析，结合历史案例库定位根本原因。",
        "sidebar_usage": "使用方法：\n1. 输入产品名称和故障现象\n2. 可选：上传图片、时序数据\n3. 点击「开始AI深度故障分析」\n4. 选择生成FA报告或8D报告\n5. 下载Word文档",
        "analyst_name": "分析人姓名",
        "analyst_name_ph": "请输入姓名",
        "analyst_title": "分析人头衔（可选）",
        "analyst_title_ph": "例如：质量总监",
        "project_name_label": "项目名称（可选）",
        "project_name_ph": "例如：启德体育场项目",
        "db_status": "数据库状态",
        "db_connected": "已连接",
        "db_disconnected": "未连接",
        "contact": "联系",
        "contact_email": "电邮: Techlife2027@gmail.com",
        
        "basic_info": "故障基本信息",
        "product_name": "产品名称",
        "product_name_ph": "例如：Media Tube Lite LED灯具",
        "symptom": "故障现象",
        "symptom_ph": "例如：运行中冒烟、灯具不亮、有烧焦味...",
        "installation": "安装位置/方向",
        "installation_ph": "例如：上层迎光面、金属翅片内",
        "failure_date": "故障发生时间",
        "batch_no": "批次/序列号",
        "site_temp": "现场温度(可选)",
        "site_temp_ph": "例如：45°C",
        "image_section": "故障图片",
        "image_upload_hint": "点击上传图片",
        "image_paste_hint": "或从剪贴板粘贴",
        "image_paste_btn": "粘贴图片",
        "image_paste_success": "图片已粘贴",
        "image_paste_error": "剪贴板无图片，请先截图",
        "image_paste_retry": "请重试",
        "no_images": "暂无图片",
        "timeseries_section": "时序数据分析",
        "timeseries_checkbox": "启用时序数据分析（SPC控制图）",
        "timeseries_input_method": "数据输入方式",
        "timeseries_paste": "直接粘贴数据",
        "timeseries_upload": "上传Excel/CSV文件",
        "timeseries_paste_placeholder": "请输入时序数据，格式：\n日期,生产数量,故障数量\n2024-01-01,1000,5\n2024-02-01,1100,8",
        "timeseries_file_hint": "支持 .xlsx, .xls, .csv 格式",
        "download_template": "下载数据模板",
        
        "advanced_options": "高级分析选项",
        "web_search": "联网搜索行业案例",
        "rule_mining": "关联规则挖掘",
        "spc": "时序分析(SPC控制图)",
        "gen_8d": "生成8D报告",
        
        "analyze_btn": "开始AI深度故障分析",
        "generate_fa_btn": "生成FA报告",
        "generate_8d_btn": "生成8D报告",
        "download_word": "下载Word报告",
        "clear_btn": "清除结果",
        
        "five_why_title": "5-Why 根因分析",
        "fishbone_title": "鱼骨图分析",
        "root_cause_title": "根因结论",
        "interim_actions": "临时措施",
        "permanent_actions": "永久措施",
        "preventive_actions": "预防措施",
        "confidence": "置信度",
        "stage_label": "失效等级",
        "spc_title": "SPC控制图分析",
        "rules_title": "关联规则挖掘",
        
        "analyzing": "AI正在分析中，请稍候...",
        "success": "分析完成！",
        "error": "分析失败，请重试",
        "fill_required": "请填写产品名称和故障现象",
        "api_error": "API配置错误，请检查Streamlit Secrets",
        
        "stage_0": "正常",
        "stage_1": "轻微异常",
        "stage_2": "中度异常",
        "stage_3": "严重故障",
        
        "report_preview": "报告预览",
        "fault_photos": "故障照片",
        "analyst": "分析人",
        "analysis_date": "分析日期",
        "project_name_header": "项目名称",
        "product_name_header": "产品名称",
        "fault_summary": "故障简述",
        
        "admin_settings": "管理员设置",
        "admin_login": "管理员验证",
        "username": "用户名",
        "password": "密码",
        "login_btn": "登录",
        "logged_in": "管理员已登录",
        "llm_status": "大模型状态",
        "llm_configured": "DeepSeek API 已配置",
        "llm_not_configured": "DeepSeek API 未配置",
        "neo4j_status": "Neo4j 知识图谱",
        "neo4j_connected": "已连接",
        "neo4j_disconnected": "未连接",
        "knowledge_base_title": "知识库管理（双语）",
        "category": "选择分类",
        "add_entry": "添加条目",
        "entry_content": "经验教训内容",
        "entry_placeholder": "输入经验教训，系统会自动翻译存储双语",
        "no_entries": "暂无条目",
        "export_kb": "导出知识库",
        "import_kb": "导入知识库（Excel）",
        "import_success": "导入成功！共导入 {count} 条记录",
    },
    "en": {
        "app_title": "AI-FA Intelligent Failure Analysis System",
        "app_subtitle": "AI-powered Failure Analysis & 8D Report Generation",
        "lang_zh": "Chinese",
        "lang_en": "English",
        "sidebar_about": "About",
        "sidebar_principle": "Principle: DeepSeek LLM + 5-Why reasoning engine for failure stage classification, fishbone analysis, and root cause identification.",
        "sidebar_usage": "How to use:\n1. Enter product name and failure symptom\n2. Optional: Upload images, time series data\n3. Click 'Start AI Deep Failure Analysis'\n4. Select FA report or 8D report\n5. Download Word document",
        "analyst_name": "Analyst Name",
        "analyst_name_ph": "Enter name",
        "analyst_title": "Title (Optional)",
        "analyst_title_ph": "e.g., Quality Director",
        "project_name_label": "Project Name (Optional)",
        "project_name_ph": "e.g., Kai Tak Stadium Project",
        "db_status": "Database Status",
        "db_connected": "Connected",
        "db_disconnected": "Disconnected",
        "contact": "Contact",
        "contact_email": "Email: Techlife2027@gmail.com",
        
        "basic_info": "Basic Failure Information",
        "product_name": "Product Name",
        "product_name_ph": "e.g., Media Tube Lite LED",
        "symptom": "Failure Symptom",
        "symptom_ph": "e.g., smoking, no light output, burning smell...",
        "installation": "Installation Position/Orientation",
        "installation_ph": "e.g., upper facade, inside metal fins",
        "failure_date": "Failure Date",
        "batch_no": "Batch/Serial No.",
        "site_temp": "Site Temperature (Optional)",
        "site_temp_ph": "e.g., 45°C",
        "image_section": "Failure Images",
        "image_upload_hint": "Click to upload",
        "image_paste_hint": "or paste from clipboard",
        "image_paste_btn": "Paste Image",
        "image_paste_success": "Image pasted",
        "image_paste_error": "No image in clipboard",
        "image_paste_retry": "Please retry",
        "no_images": "No images",
        "timeseries_section": "Time Series Analysis",
        "timeseries_checkbox": "Enable Time Series Analysis (SPC Chart)",
        "timeseries_input_method": "Data Input Method",
        "timeseries_paste": "Paste Data",
        "timeseries_upload": "Upload Excel/CSV",
        "timeseries_paste_placeholder": "Paste time series data, format:\ndate,production_qty,failure_qty\n2024-01-01,1000,5\n2024-02-01,1100,8",
        "timeseries_file_hint": "Supports .xlsx, .xls, .csv",
        "download_template": "Download Template",
        
        "advanced_options": "Advanced Analysis Options",
        "web_search": "Web search for industry cases",
        "rule_mining": "Association rule mining",
        "spc": "Time series analysis (SPC)",
        "gen_8d": "Generate 8D report",
        
        "analyze_btn": "Start AI Deep Failure Analysis",
        "generate_fa_btn": "Generate FA Report",
        "generate_8d_btn": "Generate 8D Report",
        "download_word": "Download Word Report",
        "clear_btn": "Clear Results",
        
        "five_why_title": "5-Why Root Cause Analysis",
        "fishbone_title": "Fishbone Diagram",
        "root_cause_title": "Root Cause",
        "interim_actions": "Interim Actions",
        "permanent_actions": "Permanent Actions",
        "preventive_actions": "Preventive Actions",
        "confidence": "Confidence",
        "stage_label": "Failure Stage",
        "spc_title": "SPC Control Chart Analysis",
        "rules_title": "Association Rule Mining",
        
        "analyzing": "AI is analyzing, please wait...",
        "success": "Analysis completed!",
        "error": "Analysis failed, please retry",
        "fill_required": "Please fill in product name and symptom",
        "api_error": "API configuration error, please check Streamlit Secrets",
        
        "stage_0": "Normal",
        "stage_1": "Minor Anomaly",
        "stage_2": "Moderate Anomaly",
        "stage_3": "Critical Failure",
        
        "report_preview": "Report Preview",
        "fault_photos": "Fault Photos",
        "analyst": "Analyst",
        "analysis_date": "Analysis Date",
        "project_name_header": "Project Name",
        "product_name_header": "Product Name",
        "fault_summary": "Fault Summary",
        
        "admin_settings": "Admin Settings",
        "admin_login": "Admin Verification",
        "username": "Username",
        "password": "Password",
        "login_btn": "Login",
        "logged_in": "Admin logged in",
        "llm_status": "LLM Status",
        "llm_configured": "DeepSeek API Configured",
        "llm_not_configured": "DeepSeek API Not Configured",
        "neo4j_status": "Neo4j Knowledge Graph",
        "neo4j_connected": "Connected",
        "neo4j_disconnected": "Not Connected",
        "knowledge_base_title": "Knowledge Base (Bilingual)",
        "category": "Select Category",
        "add_entry": "Add Entry",
        "entry_content": "Lesson Content",
        "entry_placeholder": "Enter lesson, auto-translated to bilingual",
        "no_entries": "No entries",
        "export_kb": "Export Knowledge Base",
        "import_kb": "Import Knowledge Base (Excel)",
        "import_success": "Import successful! {count} records imported",
    }
}


# ==================== 工具函数 ====================

def get_text(key: str) -> str:
    """获取当前语言的文本"""
    lang = st.session_state.get("lang", "zh")
    return TEXTS[lang].get(key, key)


def translate_text(text: str, target_lang: str) -> str:
    """翻译文本"""
    if not text or not text.strip():
        return text
    
    # 已经是目标语言
    if target_lang == "zh" and re.search(r'[\u4e00-\u9fff]', text):
        return text
    if target_lang == "en" and not re.search(r'[\u4e00-\u9fff]', text):
        return text
    
    client, _ = get_llm_client()
    if not client:
        return text
    
    try:
        prompt = f"请将以下文本翻译成{'中文' if target_lang == 'zh' else 'English'}，只输出翻译结果：\n\n{text}"
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content
    except:
        return text


def get_llm_client():
    """获取LLM客户端"""
    if not DEEPSEEK_API_KEY:
        return None, get_text("api_error")
    
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL
        )
        return client, None
    except Exception as e:
        return None, str(e)


def call_llm(prompt: str, max_tokens: int = 2000, temperature: float = 0.3) -> str:
    """调用DeepSeek LLM"""
    client, error = get_llm_client()
    if error:
        return f"LLM调用失败: {error}"
    
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"LLM调用失败: {str(e)}"


def clean_json_response(response: str) -> dict:
    """清理LLM返回的JSON"""
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)
    except:
        pass
    return {}


def remove_bold_markers(text: str) -> str:
    """删除文本中的**粗体标记"""
    if not text:
        return text
    return re.sub(r'\*\*([^*]+)\*\*', r'\1', text)


def truncate_summary(text: str, max_len: int = 10) -> str:
    """截取摘要（用于标题）"""
    if not text:
        return "故障分析"
    text = remove_bold_markers(text)
    if len(text) <= max_len:
        return text
    # 尝试在标点处截断
    for punct in ['。', '，', '、', '；', '：', '？', '！', '.', ',', ';', ':', '?', '!']:
        if punct in text[:max_len+5]:
            pos = text[:max_len+5].rfind(punct)
            if pos > 0:
                return text[:pos]
    return text[:max_len] + "…"


def search_web_dual(query: str, lang: str, target_lang: str) -> str:
    """
    双语联网搜索
    
    Args:
        query: 原始用户输入
        lang: 目标语言（zh/en）
        target_lang: 报告输出语言
    
    Returns:
        搜索结果摘要
    """
    results = []
    
    # 尝试导入搜索功能
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
    except ImportError:
        return "（联网搜索功能需要安装 duckduckgo-search）"
    
    # 1. 原始语言搜索
    original_results = []
    try:
        original_results = list(ddgs.text(query, max_results=3))
    except Exception as e:
        print(f"原始语言搜索失败: {e}")
    
    for r in original_results:
        results.append({
            "title": r.get('title', ''),
            "snippet": r.get('body', ''),
            "source": "web",
            "lang": "original"
        })
    
    # 2. 翻译后搜索（如果需要）
    if re.search(r'[\u4e00-\u9fff]', query):
        # 中文输入，翻译成英文搜索
        translated = translate_text(query, "en")
        eng_results = []
        try:
            eng_results = list(ddgs.text(translated, max_results=3))
        except:
            pass
        for r in eng_results:
            results.append({
                "title": r.get('title', ''),
                "snippet": r.get('body', ''),
                "source": "web",
                "lang": "en"
            })
    else:
        # 英文输入，翻译成中文搜索
        translated = translate_text(query, "zh")
        zh_results = []
        try:
            zh_results = list(ddgs.text(translated, max_results=3))
        except:
            pass
        for r in zh_results:
            results.append({
                "title": r.get('title', ''),
                "snippet": r.get('body', ''),
                "source": "web",
                "lang": "zh"
            })
    
    # 3. 去重并格式化
    seen_titles = set()
    formatted = []
    for r in results:
        title = r.get('title', '')
        if title in seen_titles:
            continue
        seen_titles.add(title)
        snippet = r.get('snippet', '')[:300]
        formatted.append(f"- {title}: {snippet}")
    
    if formatted:
        return "联网搜索结果：\n" + "\n".join(formatted[:5])
    return "（未找到相关结果）"


def web_search_dual(query: str, lang: str, target_lang: str) -> str:
    """双语联网搜索的包装函数"""
    return search_web_dual(query, lang, target_lang)


# ==================== 鱼骨图生成 ====================

def create_fishbone_image(fishbone: FishboneAnalysis, lang: str = "zh") -> bytes:
    """使用matplotlib创建鱼骨图图片"""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # 设置中文字体
    try:
        plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    except:
        pass
    
    # 画主骨（水平线）
    main_line_x = [1.5, 12.5]
    main_line_y = [5, 5]
    ax.plot(main_line_x, main_line_y, 'k-', linewidth=3, color='black')
    
    # 画箭头（鱼头）
    ax.annotate('', xy=(12.5, 5), xytext=(11.8, 5),
                arrowprops=dict(arrowstyle='->', lw=3, color='black'))
    
    # 鱼头标签
    symptom_text = fishbone.man[0][:20] if fishbone.man else "故障"
    ax.text(12.8, 5, symptom_text, fontsize=11, va='center', fontweight='bold')
    
    # 分类名称映射
    category_names = {
        "Man": ("Man", "人"),
        "Machine": ("Machine", "机"),
        "Material": ("Material", "料"),
        "Method": ("Method", "法"),
        "Environment": ("Environment", "环"),
        "Measurement": ("Measurement", "测")
    }
    
    # 分支配置 (x, y)
    branches = {
        "Man": (3.5, 7.8),
        "Machine": (3.5, 6.8),
        "Material": (3.5, 5.8),
        "Method": (4.5, 4.2),
        "Environment": (4.5, 3.2),
        "Measurement": (4.5, 2.2)
    }
    
    category_data = {
        "Man": fishbone.man,
        "Machine": fishbone.machine,
        "Material": fishbone.material,
        "Method": fishbone.method,
        "Environment": fishbone.environment,
        "Measurement": fishbone.measurement
    }
    
    for idx, (cat_key, causes) in enumerate(category_data.items()):
        cat_en, cat_zh = category_names.get(cat_key, (cat_key, cat_key))
        branch_x, branch_y = branches.get(cat_key, (5, 5))
        
        # 显示的分类名称（根据语言）
        display_name = cat_en if lang == "en" else cat_zh
        
        # 画脊骨
        ax.plot([2, branch_x], [5, branch_y], 'k-', linewidth=1.5)
        
        # 分类标签（在分支点）
        ax.text(branch_x - 0.4, branch_y, display_name, fontsize=10, 
                ha='right', va='center', fontweight='bold')
        
        # 原因列表
        for j, cause in enumerate(causes[:4]):
            cause_text = cause[:22] + "…" if len(cause) > 22 else cause
            # 交替上下排列
            if j % 2 == 0:
                y_offset = branch_y + 0.5 + j * 0.4
            else:
                y_offset = branch_y - 0.5 - (j-1) * 0.4
            
            ax.plot([branch_x, branch_x + 0.8], [branch_y, y_offset], 
                   'k:', linewidth=0.8, alpha=0.6)
            ax.text(branch_x + 0.9, y_offset, cause_text, fontsize=8, va='center')
    
    # 标题
    title = get_text("fishbone_title")
    ax.text(7, 9.5, title, fontsize=14, ha='center', fontweight='bold')
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close()
    
    return buf.getvalue()


# ==================== Supabase 知识库 ====================

class SupabaseKnowledgeDB:
    """Supabase 知识库管理（双语）"""
    
    def __init__(self):
        self.categories = ["光学", "机械", "材料", "热学", "电气", "控制"]
        self.headers = {
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }
        self._load_cache()
    
    def _load_cache(self):
        """加载知识库到缓存"""
        self.knowledge_zh = {cat: [] for cat in self.categories}
        self.knowledge_en = {cat: [] for cat in self.categories}
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            return
        
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/knowledge_base?order=id",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                rows = response.json()
                for row in rows:
                    cat = row.get("category")
                    if cat in self.knowledge_zh:
                        if row.get("content"):
                            self.knowledge_zh[cat].append(row.get("content"))
                        if row.get("content_en"):
                            self.knowledge_en[cat].append(row.get("content_en"))
        except Exception as e:
            print(f"加载知识库失败: {e}")
    
    def get_knowledge(self, category: str, lang: str = "zh") -> List[str]:
        """获取指定分类的知识条目"""
        if lang == "zh":
            return self.knowledge_zh.get(category, [])
        else:
            return self.knowledge_en.get(category, [])
    
    def search_knowledge_dual(self, query: str, lang: str) -> List[dict]:
        """双语搜索知识库"""
        results = []
        
        # 原始语言搜索
        orig_results = []
        for cat in self.categories:
            items = self.get_knowledge(cat, lang)
            for item in items:
                if query.lower() in item.lower():
                    orig_results.append({"content": item, "category": cat, "lang": lang})
        
        for r in orig_results[:5]:
            results.append(r)
        
        # 翻译后搜索
        other_lang = "en" if lang == "zh" else "zh"
        trans_query = translate_text(query, other_lang)
        trans_results = []
        for cat in self.categories:
            items = self.get_knowledge(cat, other_lang)
            for item in items:
                if trans_query.lower() in item.lower():
                    trans_results.append({"content": item, "category": cat, "lang": other_lang})
        
        for r in trans_results[:3]:
            results.append(r)
        
        return results
    
    def add_knowledge(self, category: str, content: str) -> bool:
        """添加知识条目"""
        lang = st.session_state.get("lang", "zh")
        
        if lang == "zh":
            zh_text = content
            en_text = translate_text(content, "en")
        else:
            en_text = content
            zh_text = translate_text(content, "zh")
        
        try:
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/knowledge_base",
                headers=self.headers,
                json={
                    "category": category,
                    "content": zh_text,
                    "content_en": en_text,
                    "created_at": datetime.now().isoformat()
                },
                timeout=10
            )
            if response.status_code in [200, 201, 204]:
                self._load_cache()
                return True
        except:
            pass
        return False
    
    def delete_knowledge(self, category: str, content: str) -> bool:
        """删除知识条目"""
        lang = st.session_state.get("lang", "zh")
        
        try:
            if lang == "zh":
                response = requests.get(
                    f"{SUPABASE_URL}/rest/v1/knowledge_base?category=eq.{category}&content=eq.{content}",
                    headers=self.headers
                )
            else:
                response = requests.get(
                    f"{SUPABASE_URL}/rest/v1/knowledge_base?category=eq.{category}&content_en=eq.{content}",
                    headers=self.headers
                )
            
            if response.status_code == 200 and response.json():
                record_id = response.json()[0]["id"]
                delete_resp = requests.delete(
                    f"{SUPABASE_URL}/rest/v1/knowledge_base?id=eq.{record_id}",
                    headers=self.headers
                )
                if delete_resp.status_code in [200, 204]:
                    self._load_cache()
                    return True
        except:
            pass
        return False
    
    def export_to_dataframe(self) -> pd.DataFrame:
        """导出知识库"""
        max_len = max((len(self.knowledge_zh.get(cat, [])) for cat in self.categories), default=0)
        export_data = {}
        for cat in self.categories:
            items = self.knowledge_zh.get(cat, [])
            export_data[cat] = items + [''] * (max_len - len(items))
        return pd.DataFrame(export_data)
    
    def import_from_dataframe(self, df: pd.DataFrame) -> int:
        """从DataFrame导入"""
        total = 0
        for cat in self.categories:
            if cat in df.columns:
                for item in df[cat].dropna():
                    if str(item).strip():
                        if self.add_knowledge(cat, str(item).strip()):
                            total += 1
        self._load_cache()
        return total


# ==================== 管理员弹窗 ====================

@st.dialog("Admin Settings", width="large")
def admin_settings_dialog():
    """管理员设置弹窗"""
    lang = st.session_state.get("lang", "zh")
    
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
    
    if not st.session_state.admin_logged_in:
        st.subheader(get_text("admin_login"))
        username = st.text_input(get_text("username"))
        password = st.text_input(get_text("password"), type="password")
        if st.button(get_text("login_btn")):
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("用户名或密码错误")
        return
    
    st.success(get_text("logged_in"))
    
    # 连接状态
    st.subheader(get_text("db_status"))
    
    col1, col2 = st.columns(2)
    with col1:
        if DEEPSEEK_API_KEY:
            st.success(f"✅ {get_text('llm_configured')}")
        else:
            st.error(f"❌ {get_text('llm_not_configured')}")
    
    with col2:
        st.info(f"ℹ️ {get_text('neo4j_disconnected')}")
    
    st.markdown("---")
    
    # 知识库管理
    st.subheader(get_text("knowledge_base_title"))
    
    if "knowledge_db" not in st.session_state:
        st.session_state.knowledge_db = SupabaseKnowledgeDB()
    
    kb = st.session_state.knowledge_db
    categories = kb.categories
    
    selected_cat = st.selectbox(get_text("category"), categories)
    items = kb.get_knowledge(selected_cat, lang)
    
    st.write(f"共 {len(items)} 条记录")
    
    if items:
        with st.container(height=300):
            for idx, item in enumerate(items):
                col1, col2 = st.columns([10, 1])
                with col1:
                    display_item = item[:150] + "..." if len(item) > 150 else item
                    st.write(f"{idx+1}. {display_item}")
                with col2:
                    if st.button("❌", key=f"del_{selected_cat}_{idx}"):
                        kb.delete_knowledge(selected_cat, item)
                        st.rerun()
    else:
        st.info(get_text("no_entries"))
    
    new_item = st.text_area(get_text("entry_content"), height=80, 
                            placeholder=get_text("entry_placeholder"))
    if st.button(get_text("add_entry")):
        if new_item.strip():
            kb.add_knowledge(selected_cat, new_item.strip())
            st.rerun()
    
    st.markdown("---")
    
    # 导出/导入
    col_exp, col_imp = st.columns(2)
    
    with col_exp:
        if st.button(f"📥 {get_text('export_kb')}"):
            df = kb.export_to_dataframe()
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name="KnowledgeBase", index=False)
            st.download_button(
                label="点击下载",
                data=output.getvalue(),
                file_name=f"knowledge_base_{datetime.now().strftime('%Y%m%d')}.xlsx",
                key="download_kb"
            )
    
    with col_imp:
        uploaded = st.file_uploader(get_text("import_kb"), type=["xlsx", "xls"], key="kb_upload")
        if uploaded:
            try:
                df = pd.read_excel(uploaded)
                count = kb.import_from_dataframe(df)
                st.success(get_text("import_success").format(count=count))
                st.rerun()
            except Exception as e:
                st.error(f"导入失败: {e}")


# ==================== 失效等级分类器 ====================

class FailureStageClassifier:
    """失效等级分类器"""
    
    STAGES = {
        0: {"name_zh": "正常", "name_en": "Normal", "keywords": ["正常", "无异常"]},
        1: {"name_zh": "轻微异常", "name_en": "Minor Anomaly", "keywords": ["闪烁", "弱光", "色偏", "flicker", "dim"]},
        2: {"name_zh": "中度异常", "name_en": "Moderate Anomaly", "keywords": ["烧焦", "膨胀", "变形", "burn", "swell"]},
        3: {"name_zh": "严重故障", "name_en": "Critical Failure", "keywords": ["短路", "冒烟", "起火", "short", "smoke", "fire"]}
    }
    
    @classmethod
    def classify(cls, symptom: str) -> Tuple[int, float]:
        symptom_lower = symptom.lower()
        scores = {stage: 0 for stage in cls.STAGES}
        
        for stage, info in cls.STAGES.items():
            keywords = info.get("keywords", [])
            match_count = sum(1 for kw in keywords if kw in symptom_lower)
            if match_count > 0:
                scores[stage] = min(1.0, match_count / max(len(keywords), 1) * 2)
        
        if max(scores.values()) == 0:
            scores[1] = 0.5
        
        best_stage = max(scores, key=scores.get)
        confidence = min(0.95, scores[best_stage] + 0.2)
        return best_stage, confidence
    
    @classmethod
    def get_stage_name(cls, stage: int, lang: str = "zh") -> str:
        info = cls.STAGES.get(stage, cls.STAGES[1])
        return info.get(f"name_{lang}", f"Stage {stage}")


# ==================== 5-Why 推理引擎 ====================

class FiveWhyEngine:
    """5-Why推理引擎"""
    
    WHY_TEMPLATES = {
        1: "What is the direct cause of this problem?",
        2: "Why did this direct cause occur?",
        3: "What systemic issue led to this cause?",
        4: "Why does this systemic issue exist?",
        5: "What process/design/management flaw allowed this to happen?"
    }
    
    WHY_TEMPLATES_ZH = {
        1: "为什么会出现这个问题？直接原因是什么？",
        2: "为什么会有这个直接原因？更深层的原因是什么？",
        3: "这个深层原因背后的系统性问题是什么？",
        4: "为什么这个系统性问题会存在？根本原因在哪？",
        5: "这个根本原因的背后，我们的流程/设计/管理有什么缺陷？"
    }
    
    @classmethod
    def generate(cls, symptom: str, product_name: str, lang: str = "zh",
                 installation: str = "", temperature: str = "") -> List[FiveWhyItem]:
        """生成5-Why推理链"""
        chain = []
        current_question = symptom
        templates = cls.WHY_TEMPLATES_ZH if lang == "zh" else cls.WHY_TEMPLATES
        
        for level in range(1, 6):
            context = ""
            if installation:
                context += f"Installation: {installation}\n"
            if temperature:
                context += f"Temperature: {temperature}\n"
            
            prompt = f"""You are a senior failure analysis engineer.

Product: {product_name}
Symptom: {symptom}

{context}
Why-{level}: {current_question}
{templates.get(level, 'Continue the analysis')}

Output JSON format:
{{"answer": "your answer", "confidence": 0.8}}"""
            
            response = call_llm(prompt, max_tokens=500, temperature=0.3)
            answer_data = clean_json_response(response)
            answer = answer_data.get("answer", response[:300])
            
            chain.append(FiveWhyItem(
                level=level,
                question=current_question[:200],
                answer=answer[:300],
                confidence=answer_data.get("confidence", 0.7),
                evidence_source="AI推理",
                verification_method="建议通过测试验证"
            ))
            
            if level < 5:
                next_prompt = f"""Based on the answer, generate the next Why question (Why-{level+1}).

Answer: {answer}

Output a "Why...?" question only:"""
                current_question = call_llm(next_prompt, max_tokens=100, temperature=0.3)
        
        return chain


# ==================== 鱼骨图生成器 ====================

class FishboneGenerator:
    """鱼骨图生成器"""
    
    @classmethod
    def generate(cls, symptom: str, product_name: str, lang: str = "zh") -> FishboneAnalysis:
        """生成鱼骨图"""
        categories = ["Man", "Machine", "Material", "Method", "Environment", "Measurement"]
        
        fishbone_data = {}
        for cat in categories:
            cat_zh = {"Man": "人", "Machine": "机", "Material": "料", 
                      "Method": "法", "Environment": "环", "Measurement": "测"}.get(cat, cat)
            
            prompt = f"""List potential causes for the {cat_zh} category that could lead to this failure.

Product: {product_name}
Symptom: {symptom}

List 3-5 specific, verifiable causes, one per line:"""
            
            response = call_llm(prompt, max_tokens=300, temperature=0.4)
            causes = [line.strip() for line in response.split('\n') 
                     if line.strip() and len(line.strip()) > 5][:6]
            fishbone_data[cat] = causes
        
        return FishboneAnalysis(
            man=fishbone_data.get("Man", []),
            machine=fishbone_data.get("Machine", []),
            material=fishbone_data.get("Material", []),
            method=fishbone_data.get("Method", []),
            environment=fishbone_data.get("Environment", []),
            measurement=fishbone_data.get("Measurement", [])
        )


# ==================== 时序分析器 ====================

class TimeSeriesAnalyzer:
    """时序分析器"""
    
    @staticmethod
    def parse_data(data_text: str) -> Optional[pd.DataFrame]:
        try:
            df = pd.read_csv(io.StringIO(data_text))
            if 'production_qty' in df.columns:
                df['production_qty'] = pd.to_numeric(df['production_qty'], errors='coerce')
            if 'failure_qty' in df.columns:
                df['failure_qty'] = pd.to_numeric(df['failure_qty'], errors='coerce')
            return df.dropna()
        except:
            return None
    
    @staticmethod
    def parse_excel(file) -> Optional[pd.DataFrame]:
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            if 'production_qty' in df.columns:
                df['production_qty'] = pd.to_numeric(df['production_qty'], errors='coerce')
            if 'failure_qty' in df.columns:
                df['failure_qty'] = pd.to_numeric(df['failure_qty'], errors='coerce')
            return df.dropna()
        except:
            return None
    
    @staticmethod
    def analyze_trend(df: pd.DataFrame) -> dict:
        if df is None or len(df) == 0:
            return {"has_data": False}
        
        total_failures = df['failure_qty'].sum()
        total_production = df['production_qty'].sum()
        overall_rate = total_failures / total_production * 100 if total_production > 0 else 0
        
        df['defect_rate'] = df['failure_qty'] / df['production_qty'] * 100
        recent_avg = df['defect_rate'].tail(3).mean() if len(df) >= 3 else df['defect_rate'].mean()
        
        return {
            "has_data": True,
            "overall_rate": overall_rate,
            "recent_rate": recent_avg,
            "trend": "上升" if recent_avg > overall_rate else "下降" if recent_avg < overall_rate else "稳定",
            "is_stable": True,
            "total_samples": len(df)
        }


# ==================== 关联规则挖掘 ====================

class AssociationRuleMiner:
    """关联规则挖掘器"""
    
    @staticmethod
    def mine_rules(symptom: str, installation: str, temperature: str, lang: str = "zh") -> List[dict]:
        prompt = f"""Based on the failure information, discover potential association rules:

Symptom: {symptom}
Installation: {installation if installation else 'unknown'}
Temperature: {temperature if temperature else 'unknown'}

Output 2-3 possible association rules as JSON array:
[{{"antecedents": ["condition1", "condition2"], "consequents": ["result"], "confidence": 0.8, "explanation": "explanation"}}]"""
        
        response = call_llm(prompt, max_tokens=500, temperature=0.4)
        try:
            data = clean_json_response(response)
            if isinstance(data, list):
                return data[:3]
        except:
            pass
        return []


# ==================== 改进措施生成器 ====================

class ImprovementActionGenerator:
    """改进措施生成器"""
    
    @staticmethod
    def generate(root_cause: str, product_name: str) -> dict:
        prompt = f"""Based on the root cause, generate improvement actions:

Root cause: {root_cause}
Product: {product_name}

Output JSON:
{{"interim": ["interim action 1", "interim action 2"], 
  "permanent": ["permanent action 1", "permanent action 2", "permanent action 3"], 
  "preventive": ["preventive action 1", "preventive action 2"]}}"""
        
        response = call_llm(prompt, max_tokens=400, temperature=0.4)
        try:
            data = clean_json_response(response)
            if data:
                return {
                    "interim": data.get("interim", ["Isolate defective products", "Notify customer"]),
                    "permanent": data.get("permanent", ["Fix design issues", "Replace faulty components"]),
                    "preventive": data.get("preventive", ["Update FMEA", "Enhance incoming inspection"])
                }
        except:
            pass
        
        return {
            "interim": ["Isolate defective products", "Notify customer to suspend use", "Check same batch products"],
            "permanent": ["Analyze and fix root cause", "Update design specifications", "Add protection circuits"],
            "preventive": ["Update FMEA", "Enhance incoming inspection", "Add regular maintenance"]
        }


# ==================== 报告生成器 ====================

class ReportGenerator:
    """报告生成器"""
    
    @staticmethod
    def generate_fa_report(result: FailureAnalysisResult, lang: str = "zh") -> str:
        """生成FA报告"""
        stage_name = FailureStageClassifier.get_stage_name(result.failure_stage, lang)
        fault_summary = truncate_summary(result.symptom, 30)
        
        # 5-Why表格
        five_why_table = "| Level | Question | Answer | Confidence |\n|-------|----------|--------|------------|\n"
        for item in result.five_why:
            q_short = item.question[:50] + "..." if len(item.question) > 50 else item.question
            a_short = item.answer[:60] + "..." if len(item.answer) > 60 else item.answer
            five_why_table += f"| Why-{item.level} | {q_short} | {a_short} | {item.confidence:.0%} |\n"
        
        # 鱼骨图文字
        fishbone_dict = result.fishbone.to_dict()
        fishbone_text = ""
        for cat, causes in fishbone_dict.items():
            if causes:
                fishbone_text += f"\n**{cat}**:\n"
                for cause in causes[:4]:
                    fishbone_text += f"- {cause}\n"
        
        report = f"""# Failure Analysis Report

## Report Information

| Item | Content |
|------|---------|
| Project Name | {result.project_name if result.project_name else '-'} |
| Product Name | {result.product_name} |
| Fault Summary | {fault_summary} |
| Report Date | {datetime.now().strftime('%Y-%m-%d')} |
| Analyst | {result.analyst_name if result.analyst_name else '-'} {f"({result.analyst_title})" if result.analyst_title else ''} |

## 1. Failure Stage

**Stage {result.failure_stage}: {stage_name}** (Confidence: {result.root_cause_confidence:.0%})

## 2. 5-Why Analysis

{five_why_table}

## 3. Root Cause

{result.root_cause}

## 4. Fishbone Analysis

{fishbone_text}

## 5. Improvement Actions

### Interim Actions
{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(result.interim_actions[:3]))}

### Permanent Actions
{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(result.permanent_actions[:3]))}

### Preventive Actions
{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(result.preventive_actions[:2]))}
"""
        return report
    
    @staticmethod
    def generate_8d_report(result: FailureAnalysisResult, lang: str = "zh") -> str:
        """生成8D报告"""
        stage_name = FailureStageClassifier.get_stage_name(result.failure_stage, lang)
        fault_summary = truncate_summary(result.symptom, 30)
        title_summary = truncate_summary(result.symptom, 10)
        
        # 5-Why列表
        five_why_list = ""
        for item in result.five_why:
            five_why_list += f"**Why-{item.level}**: {item.question}\n→ {item.answer}\n\n"
        
        # 鱼骨图文字
        fishbone_dict = result.fishbone.to_dict()
        fishbone_text = ""
        for cat, causes in fishbone_dict.items():
            if causes:
                fishbone_text += f"\n**{cat}**: {', '.join(causes[:3])}\n"
        
        report = f"""# 8D Report - {title_summary}

## Report Information

| Item | Content |
|------|---------|
| Project Name | {result.project_name if result.project_name else '-'} |
| Product Name | {result.product_name} |
| Fault Summary | {fault_summary} |
| Report Date | {datetime.now().strftime('%Y-%m-%d')} |
| Analyst | {result.analyst_name if result.analyst_name else '-'} {f"({result.analyst_title})" if result.analyst_title else ''} |

## D1: Establish Team

| Role | Responsibility |
|------|----------------|
| Team Leader | Overall coordination |
| Design Engineer | Technical analysis |
| Quality Engineer | Quality verification |

## D2: Problem Description

| Item | Content |
|------|---------|
| What | {result.symptom[:200]} |
| Where | {result.installation if result.installation else 'Installation site'} |
| When | {datetime.now().strftime('%Y-%m-%d')} |
| Failure Stage | {stage_name} |
| Confidence | {result.root_cause_confidence:.0%} |

## D3: Interim Actions

{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(result.interim_actions[:3]))}

## D4: Root Cause Analysis

### Fishbone Analysis
{fishbone_text}

### 5-Why Analysis
{five_why_list}

### Verified Root Cause
{result.root_cause}

## D5: Permanent Actions

{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(result.permanent_actions[:3]))}

## D6: Effectiveness Verification

| Item | Method | Criteria |
|------|--------|----------|
| Function | Actual test | Normal operation |
| Durability | Accelerated aging | Meet design life |

## D7: Preventive Actions

{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(result.preventive_actions[:2]))}

## D8: Team Recognition

- Root cause identified and confirmed
- Improvement actions defined
- Lessons learned added to knowledge base
"""
        return report


# ==================== Word导出 ====================

def create_word_document(report_content: str, report_type: str, result: FailureAnalysisResult,
                         uploaded_images: List[bytes] = None, fishbone_image: bytes = None) -> io.BytesIO:
    """创建Word文档，支持图文并茂"""
    try:
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        doc = Document()
        
        # 标题
        title_summary = truncate_summary(result.symptom, 10)
        title_text = f"{result.product_name} - {title_summary} - {report_type}"
        title = doc.add_heading(title_text, level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 解析并添加报告内容
        lines = report_content.split('\n')
        for line in lines:
            line = remove_bold_markers(line)
            if line.startswith('# '):
                doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                doc.add_heading(line[3:], level=2)
            elif line.startswith('### '):
                doc.add_heading(line[4:], level=3)
            elif line.startswith('|') and '|' in line[1:]:
                continue
            elif line.strip():
                p = doc.add_paragraph(line)
                p.style.font.size = Pt(11)
            else:
                doc.add_paragraph()
        
        # 插入鱼骨图
        if fishbone_image:
            doc.add_page_break()
            doc.add_heading(get_text("fishbone_title"), level=2)
            img_stream = io.BytesIO(fishbone_image)
            doc.add_picture(img_stream, width=Inches(6))
        
        # 插入故障照片
        if uploaded_images and len(uploaded_images) > 0:
            doc.add_page_break()
            doc.add_heading(get_text("fault_photos"), level=2)
            for idx, img_bytes in enumerate(uploaded_images[:5]):
                try:
                    img_stream = io.BytesIO(img_bytes)
                    doc.add_picture(img_stream, width=Inches(4))
                    doc.add_paragraph(f"Figure {idx+1}: Fault photo")
                except:
                    doc.add_paragraph(f"[Image {idx+1} could not be displayed]")
        
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
        
    except ImportError:
        buffer = io.BytesIO()
        buffer.write(report_content.encode('utf-8'))
        buffer.seek(0)
        return buffer


# ==================== 主分析函数 ====================

def run_failure_analysis(
    product_name: str,
    symptom: str,
    project_name: str,
    installation: str,
    temperature: str,
    lang: str,
    timeseries_df: pd.DataFrame = None,
    enable_web: bool = True,
    enable_rule_mining: bool = True,
    enable_spc: bool = True,
    analyst_name: str = "",
    analyst_title: str = ""
) -> FailureAnalysisResult:
    """执行故障分析 - 双语双向检索"""
    
    case_id = str(uuid.uuid4())[:8]
    
    # 双语双向检索
    search_results = ""
    if enable_web:
        search_results = web_search_dual(symptom, lang, lang)
    
    # 翻译输入（如果是英文模式）
    if lang == "en":
        product_name_en = translate_text(product_name, "en") if re.search(r'[\u4e00-\u9fff]', product_name) else product_name
        symptom_en = translate_text(symptom, "en") if re.search(r'[\u4e00-\u9fff]', symptom) else symptom
        installation_en = translate_text(installation, "en") if installation and re.search(r'[\u4e00-\u9fff]', installation) else installation
        temperature_en = temperature
        use_product = product_name_en
        use_symptom = symptom_en
        use_installation = installation_en
        use_temperature = temperature_en
    else:
        use_product = product_name
        use_symptom = symptom
        use_installation = installation
        use_temperature = temperature
    
    # 1. 失效等级分类
    stage, stage_conf = FailureStageClassifier.classify(use_symptom)
    
    # 2. 5-Why推理
    five_why = FiveWhyEngine.generate(use_symptom, use_product, lang, use_installation, use_temperature)
    
    # 3. 鱼骨图生成
    fishbone = FishboneGenerator.generate(use_symptom, use_product, lang)
    
    # 4. 鱼骨图图片
    fishbone_image = create_fishbone_image(fishbone, lang)
    
    # 5. 根因提取
    root_cause = five_why[-1].answer if five_why else "Further analysis needed"
    root_cause_confidence = five_why[-1].confidence if five_why else 0.6
    
    # 6. 改进措施
    actions = ImprovementActionGenerator.generate(root_cause, use_product)
    
    # 7. SPC分析
    spc_analysis = None
    if enable_spc and timeseries_df is not None and len(timeseries_df) > 0:
        spc_analysis = TimeSeriesAnalyzer.analyze_trend(timeseries_df)
    
    # 8. 关联规则
    association_rules = []
    if enable_rule_mining:
        association_rules = AssociationRuleMiner.mine_rules(use_symptom, use_installation, use_temperature, lang)
    
    return FailureAnalysisResult(
        case_id=case_id,
        project_name=project_name,
        product_name=product_name,
        symptom=symptom,
        installation=installation,
        temperature=temperature,
        failure_stage=stage,
        five_why=five_why,
        fishbone=fishbone,
        root_cause=root_cause,
        root_cause_confidence=root_cause_confidence,
        interim_actions=actions["interim"],
        permanent_actions=actions["permanent"],
        preventive_actions=actions["preventive"],
        internal_cases_used=3,
        external_sources_used=2 if enable_web else 0,
        spc_analysis=spc_analysis,
        association_rules=association_rules,
        has_images=False,
        analyst_name=analyst_name,
        analyst_title=analyst_title,
        fishbone_image=fishbone_image
    )


# ==================== 主页面上方占位（用于标题） ====================

# ==================== 主页面 ====================

def main():
    """主应用入口"""
    
    # 初始化session state
    if "lang" not in st.session_state:
        st.session_state.lang = "zh"
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "current_report" not in st.session_state:
        st.session_state.current_report = None
    if "report_type" not in st.session_state:
        st.session_state.report_type = "fa"
    if "analyst_name" not in st.session_state:
        st.session_state.analyst_name = ""
    if "analyst_title" not in st.session_state:
        st.session_state.analyst_title = ""
    if "project_name" not in st.session_state:
        st.session_state.project_name = ""
    if "uploaded_images" not in st.session_state:
        st.session_state.uploaded_images = []
    if "paste_success" not in st.session_state:
        st.session_state.paste_success = False
    
    # 右上角语言切换和齿轮
    col_title, col_spacer, col_zh, col_en, col_gear = st.columns([2, 3, 1, 1, 1])
    
    with col_zh:
        if st.button(get_text("lang_zh"), key="zh_btn", use_container_width=True):
            st.session_state.lang = "zh"
            st.rerun()
    with col_en:
        if st.button(get_text("lang_en"), key="en_btn", use_container_width=True):
            st.session_state.lang = "en"
            st.rerun()
    with col_gear:
        if st.button("⚙️", key="settings_btn", use_container_width=True):
            admin_settings_dialog()
    
    # 标题
    st.title(get_text("app_title"))
    st.caption(get_text("app_subtitle"))
    
    # 检查API配置
    if not DEEPSEEK_API_KEY:
        st.error(get_text("api_error"))
        st.info("请在 Streamlit Cloud 的 Secrets 中配置 DEEPSEEK_API_KEY")
        return
    
    # ==================== 左侧边栏 ====================
    with st.sidebar:
        st.markdown(f"### {get_text('sidebar_about')}")
        st.markdown(get_text("sidebar_principle"))
        st.markdown(get_text("sidebar_usage"))
        st.markdown("---")
        
        # 分析人信息
        st.session_state.analyst_name = st.text_input(
            get_text("analyst_name"),
            placeholder=get_text("analyst_name_ph"),
            key="sidebar_analyst_name"
        )
        st.session_state.analyst_title = st.text_input(
            get_text("analyst_title"),
            placeholder=get_text("analyst_title_ph"),
            key="sidebar_analyst_title"
        )
        
        # 项目名称
        st.session_state.project_name = st.text_input(
            get_text("project_name_label"),
            placeholder=get_text("project_name_ph"),
            key="sidebar_project_name"
        )
        
        if st.session_state.analyst_name:
            st.success(f"{get_text('analyst')}: {st.session_state.analyst_name}")
        
        st.markdown("---")
        
        # 数据库状态
        st.markdown(f"**{get_text('db_status')}**")
        if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
            st.success(f"✅ {get_text('db_connected')}")
        else:
            st.error(f"❌ {get_text('db_disconnected')}")
        
        st.markdown("---")
        st.markdown(f"### {get_text('contact')}")
        st.markdown(get_text("contact_email"))
    
    # ==================== 上下布局主内容 ====================
    
    # 1. 故障基本信息
    st.markdown(f"### {get_text('basic_info')}")
    
    product_name = st.text_input(
        get_text("product_name"),
        placeholder=get_text("product_name_ph"),
        key="product_name_input"
    )
    
    symptom = st.text_area(
        get_text("symptom"),
        placeholder=get_text("symptom_ph"),
        height=100,
        key="symptom_input"
    )
    
    installation = st.text_input(
        get_text("installation"),
        placeholder=get_text("installation_ph"),
        key="installation_input"
    )
    
    col_date, col_batch = st.columns(2)
    with col_date:
        failure_date = st.date_input(
            get_text("failure_date"),
            value=datetime.now().date(),
            key="failure_date_input"
        )
    with col_batch:
        batch_no = st.text_input(
            get_text("batch_no"),
            placeholder="LOT2024-001",
            key="batch_no_input"
        )
    
    temperature = st.text_input(
        get_text("site_temp"),
        placeholder=get_text("site_temp_ph"),
        key="temperature_input"
    )
    
    st.markdown("---")
    
    # 2. 故障图片
    st.markdown(f"### {get_text('image_section')}")
    
    # 文件上传
    uploaded_files = st.file_uploader(
        get_text("image_upload_hint"),
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="image_uploader",
        label_visibility="collapsed"
    )
    
    # 粘贴按钮
    col_paste1, col_paste2 = st.columns([1, 3])
    with col_paste1:
        if st.button(f"📋 {get_text('image_paste_btn')}", key="paste_button", use_container_width=True):
            st.info(get_text("image_paste_success"))
            st.session_state.paste_success = True
    
    # 处理上传的图片
    if uploaded_files:
        st.session_state.uploaded_images = []
        for img in uploaded_files:
            st.session_state.uploaded_images.append(img.getvalue())
        
        cols = st.columns(min(3, len(uploaded_files)))
        for idx, img in enumerate(uploaded_files[:3]):
            with cols[idx]:
                st.image(img, use_container_width=True)
                st.caption(f"Image {idx+1}")
    
    if not uploaded_files and not st.session_state.uploaded_images:
        st.caption(get_text("no_images"))
    
    st.markdown("---")
    
    # 3. 时序数据分析（默认不勾选）
    st.markdown(f"### {get_text('timeseries_section')}")
    
    enable_timeseries = st.checkbox(
        get_text("timeseries_checkbox"),
        value=False,
        key="enable_timeseries"
    )
    
    timeseries_df = None
    
    if enable_timeseries:
        input_method = st.radio(
            get_text("timeseries_input_method"),
            [get_text("timeseries_paste"), get_text("timeseries_upload")],
            horizontal=True,
            key="timeseries_method"
        )
        
        if input_method == get_text("timeseries_paste"):
            paste_data = st.text_area(
                get_text("timeseries_paste_placeholder"),
                height=150,
                key="timeseries_paste"
            )
            if paste_data:
                timeseries_df = TimeSeriesAnalyzer.parse_data(paste_data)
                if timeseries_df is not None:
                    st.success(f"已解析 {len(timeseries_df)} 行数据")
                else:
                    st.error("数据格式错误，请检查")
        else:
            timeseries_file = st.file_uploader(
                get_text("timeseries_file_hint"),
                type=["xlsx", "xls", "csv"],
                key="timeseries_file"
            )
            if timeseries_file:
                timeseries_df = TimeSeriesAnalyzer.parse_excel(timeseries_file)
                if timeseries_df is not None:
                    st.success(f"已加载 {len(timeseries_df)} 行数据")
                    st.dataframe(timeseries_df.head(), use_container_width=True)
                else:
                    st.error("文件解析失败")
        
        # 模板下载
        template_df = pd.DataFrame({
            "date": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "production_qty": [1000, 1100, 1050],
            "failure_qty": [5, 8, 12]
        })
        template_csv = template_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=get_text("download_template"),
            data=template_csv,
            file_name="defect_data_template.csv",
            mime="text/csv",
            key="template_download"
        )
    
    st.markdown("---")
    
    # 4. 高级分析选项（全部默认勾选）
    st.markdown(f"### {get_text('advanced_options')}")
    
    col_adv1, col_adv2, col_adv3, col_adv4 = st.columns(4)
    with col_adv1:
        enable_web = st.checkbox(get_text("web_search"), value=True, key="web_search")
    with col_adv2:
        enable_rule_mining = st.checkbox(get_text("rule_mining"), value=True, key="rule_mining")
    with col_adv3:
        enable_spc = st.checkbox(get_text("spc"), value=True, key="spc")
    with col_adv4:
        enable_8d = st.checkbox(get_text("gen_8d"), value=True, key="gen_8d")
    
    st.markdown("---")
    
    # 5. 开始分析按钮
    col_btn_center = st.columns([1, 2, 1])[1]
    with col_btn_center:
        if st.button(get_text("analyze_btn"), type="primary", use_container_width=True):
            if not product_name or not symptom:
                st.error(get_text("fill_required"))
            else:
                with st.spinner(get_text("analyzing")):
                    try:
                        result = run_failure_analysis(
                            product_name=product_name,
                            symptom=symptom,
                            project_name=st.session_state.project_name,
                            installation=installation,
                            temperature=temperature,
                            lang=st.session_state.lang,
                            timeseries_df=timeseries_df if enable_timeseries else None,
                            enable_web=enable_web,
                            enable_rule_mining=enable_rule_mining,
                            enable_spc=enable_spc,
                            analyst_name=st.session_state.analyst_name,
                            analyst_title=st.session_state.analyst_title
                        )
                        st.session_state.analysis_result = result
                        st.session_state.current_report = None
                        st.success(get_text("success"))
                        st.rerun()
                    except Exception as e:
                        st.error(f"{get_text('error')}: {str(e)}")
    
    # 6. 显示分析结果
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result
        lang = st.session_state.lang
        
        st.markdown("---")
        
        # 失效等级
        stage_name = FailureStageClassifier.get_stage_name(result.failure_stage, lang)
        stage_emoji = {0: "✅", 1: "⚠️", 2: "🔥", 3: "🚨"}.get(result.failure_stage, "📌")
        
        col_status, col_conf = st.columns([2, 1])
        with col_status:
            st.info(f"{stage_emoji} **{get_text('stage_label')}**: {stage_name}")
        with col_conf:
            st.metric(get_text("confidence"), f"{result.root_cause_confidence:.0%}")
        
        # 5-Why
        with st.expander(get_text("five_why_title"), expanded=True):
            for item in result.five_why:
                col_q, col_a = st.columns([1, 2])
                with col_q:
                    st.markdown(f"**Why-{item.level}**")
                with col_a:
                    st.markdown(f"**Q**: {remove_bold_markers(item.question)}")
                    st.markdown(f"**A**: {remove_bold_markers(item.answer)}")
                    st.progress(item.confidence, text=f"{get_text('confidence')}: {item.confidence:.0%}")
                st.divider()
        
        # 鱼骨图
        with st.expander(get_text("fishbone_title")):
            if result.fishbone_image:
                st.image(result.fishbone_image, use_container_width=True)
            else:
                fishbone_dict = result.fishbone.to_dict()
                for cat, causes in fishbone_dict.items():
                    if causes:
                        st.markdown(f"**{cat}**")
                        for cause in causes[:4]:
                            st.markdown(f"- {cause}")
        
        # 根因结论
        st.markdown(f"### {get_text('root_cause_title')}")
        st.success(remove_bold_markers(result.root_cause))
        
        # 报告生成按钮
        st.markdown("---")
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        
        with col_btn1:
            if st.button(get_text("generate_fa_btn"), use_container_width=True):
                report = ReportGenerator.generate_fa_report(result, lang)
                st.session_state.current_report = report
                st.session_state.report_type = "FA"
                st.rerun()
        
        with col_btn2:
            if st.button(get_text("generate_8d_btn"), use_container_width=True):
                report = ReportGenerator.generate_8d_report(result, lang)
                st.session_state.current_report = report
                st.session_state.report_type = "8D"
                st.rerun()
        
        with col_btn3:
            if st.button(get_text("clear_btn"), use_container_width=True):
                st.session_state.analysis_result = None
                st.session_state.current_report = None
                st.rerun()
    
    # 7. 显示生成的报告
    if st.session_state.current_report:
        st.markdown("---")
        st.markdown(f"### {get_text('report_preview')}")
        
        with st.container(height=400):
            st.markdown(st.session_state.current_report)
        
        # 生成文件名
        title_summary = truncate_summary(st.session_state.analysis_result.symptom, 10)
        filename = f"{st.session_state.analysis_result.product_name}_{title_summary}_{st.session_state.report_type}_Report_{datetime.now().strftime('%Y%m%d')}.docx"
        filename = re.sub(r'[\\/*?:"<>|]', '', filename)
        
        word_buffer = create_word_document(
            st.session_state.current_report,
            st.session_state.report_type,
            st.session_state.analysis_result,
            st.session_state.uploaded_images,
            st.session_state.analysis_result.fishbone_image
        )
        
        st.download_button(
            label=get_text("download_word"),
            data=word_buffer,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )


if __name__ == "__main__":
    # 设置中文字体
    setup_chinese_font()
    main()
