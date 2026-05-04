"""
AI-FA 智能故障分析系统
AI-powered Failure Analysis & 8D Report Generation

版本: 2.0.0
功能:
- 双语双向检索（中文/英文并行搜索）
- Supabase 知识库管理（六分类）
- 时序数据分析 + SPC图表
- 关联规则挖掘
- 联网搜索
- 5-Why推理 + 鱼骨图
- FA报告 + 8D报告
- Word导出（图文并茂）

修复内容:
- 中英文输出完全分离
- 用户输入自动翻译
- 报告信息表格完整显示
- 5-Why 表格+列表双格式
- D2 5W2H 格式
- 鱼骨图放大到12英寸
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import uuid
import re
import io
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from PIL import Image
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
from matplotlib.font_manager import fontManager

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


# ==================== 数据模型 ====================

@dataclass
class FiveWhyItem:
    """5-Why推理项"""
    level: int
    question: str
    answer: str
    confidence: float
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
    symptom_en: str
    installation: str
    installation_en: str
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
        "product_name_ph": "例如：Allegro Dot L RGBW",
        "symptom": "故障现象",
        "symptom_ph": "例如：暴雨后灯具闪烁、不亮、有烧焦痕迹...",
        "installation": "安装位置/方向",
        "installation_ph": "例如：上层迎光面、黑色金属表面",
        "failure_date": "故障发生时间",
        "batch_no": "批次/序列号",
        "site_temp": "现场温度(可选)",
        "site_temp_ph": "例如：70°C",
        "image_section": "故障图片",
        "image_upload_hint": "点击上传图片",
        "image_paste_hint": "或从剪贴板粘贴",
        "image_paste_btn": "粘贴图片",
        "image_paste_success": "图片已粘贴",
        "image_paste_error": "剪贴板无图片，请先截图",
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
        "report_info": "报告信息",
        "report_date": "报告日期",
        
        "what": "故障现象",
        "where": "发现位置",
        "when": "发生时间",
        "who": "发现人",
        "why": "初步判断",
        "how": "发生过程",
        "how_many": "影响数量",
        
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
        
        "establish_team": "建立团队",
        "problem_description": "问题描述",
        "root_cause_analysis": "根本原因分析",
        "effectiveness_verification": "效果验证",
        "team_recognition": "总结表彰",
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
        "product_name_ph": "e.g., Allegro Dot L RGBW",
        "symptom": "Failure Symptom",
        "symptom_ph": "e.g., flickering, no light output, burning marks after heavy rain...",
        "installation": "Installation Position/Orientation",
        "installation_ph": "e.g., upper facade, black metal surface",
        "failure_date": "Failure Date",
        "batch_no": "Batch/Serial No.",
        "site_temp": "Site Temperature (Optional)",
        "site_temp_ph": "e.g., 70°C",
        "image_section": "Failure Images",
        "image_upload_hint": "Click to upload",
        "image_paste_hint": "or paste from clipboard",
        "image_paste_btn": "Paste Image",
        "image_paste_success": "Image pasted",
        "image_paste_error": "No image in clipboard",
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
        "report_info": "Report Information",
        "report_date": "Report Date",
        
        "what": "What",
        "where": "Where",
        "when": "When",
        "who": "Who",
        "why": "Why (Preliminary)",
        "how": "How",
        "how_many": "How Many",
        
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
        
        "establish_team": "Establish Team",
        "problem_description": "Problem Description",
        "root_cause_analysis": "Root Cause Analysis",
        "effectiveness_verification": "Effectiveness Verification",
        "team_recognition": "Team Recognition",
    }
}


def get_text(key: str) -> str:
    """获取当前语言的文本"""
    lang = st.session_state.get("lang", "zh")
    return TEXTS[lang].get(key, key)


# ==================== 工具函数 ====================

def is_chinese(text: str) -> bool:
    """判断是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def translate_to_en(text: str) -> str:
    """翻译为英文（保留专有名词）"""
    if not text or not is_chinese(text):
        return text
    
    client = get_llm_client()
    if not client:
        return text
    
    prompt = f"""请将以下文本翻译成英文。注意：LED、PCB、DMX、IP、UL、RGBW、PCBA、SMD、COB、PWM、EMI、ESD等专业术语保持原样不翻译。

文本：{text}

只输出翻译结果，不要其他内容："""
    
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except:
        return text


def translate_to_zh(text: str) -> str:
    """翻译为中文（保留专有名词）"""
    if not text or not is_chinese(text):
        return text
    
    client = get_llm_client()
    if not client:
        return text
    
    prompt = f"""请将以下文本翻译成中文。注意：LED、PCB、DMX、IP、UL、RGBW、PCBA、SMD、COB、PWM、EMI、ESD等专业术语保持原样不翻译。

文本：{text}

只输出翻译结果，不要其他内容："""
    
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except:
        return text


def get_llm_client():
    """获取LLM客户端"""
    if not DEEPSEEK_API_KEY:
        return None
    
    try:
        from openai import OpenAI
        return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    except:
        return None


def call_llm(prompt: str, max_tokens: int = 2000, temperature: float = 0.3) -> str:
    """调用DeepSeek LLM"""
    client = get_llm_client()
    if not client:
        return "LLM配置错误"
    
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"调用失败: {str(e)}"


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
    return text[:max_len] + "…"


# ==================== 联网搜索（双语双向）====================

def web_search_dual(query: str, lang: str) -> str:
    """双语双向联网搜索"""
    results = []
    
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
    except ImportError:
        return "（联网搜索功能需要安装 duckduckgo-search）"
    
    # 原始语言搜索
    try:
        orig_results = list(ddgs.text(query, max_results=3))
        for r in orig_results:
            results.append({
                "title": r.get('title', ''),
                "snippet": r.get('body', '')[:300],
                "source": "original"
            })
    except:
        pass
    
    # 翻译后搜索
    if is_chinese(query):
        translated = translate_to_en(query)
    else:
        translated = translate_to_zh(query)
    
    try:
        trans_results = list(ddgs.text(translated, max_results=3))
        for r in trans_results:
            title = r.get('title', '')
            if not any(title == existing['title'] for existing in results):
                results.append({
                    "title": title,
                    "snippet": r.get('body', '')[:300],
                    "source": "translated"
                })
    except:
        pass
    
    if not results:
        return "（未找到相关结果）"
    
    formatted = []
    for r in results[:5]:
        formatted.append(f"- {r['title']}: {r['snippet']}")
    
    return "联网搜索结果：\n" + "\n".join(formatted)


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
    
    def search_knowledge_dual(self, query: str, lang: str) -> List[str]:
        """双语搜索知识库"""
        results = []
        
        # 原始语言搜索
        for cat in self.categories:
            items = self.get_knowledge(cat, lang)
            for item in items:
                if query.lower() in item.lower():
                    results.append(item)
        
        # 翻译后搜索
        other_lang = "en" if lang == "zh" else "zh"
        trans_query = translate_to_en(query) if lang == "zh" else translate_to_zh(query)
        for cat in self.categories:
            items = self.get_knowledge(cat, other_lang)
            for item in items:
                if trans_query.lower() in item.lower():
                    if item not in results:
                        results.append(item)
        
        return results[:10]
    
    def add_knowledge(self, category: str, content: str) -> bool:
        """添加知识条目"""
        lang = st.session_state.get("lang", "zh")
        
        if lang == "zh":
            zh_text = content
            en_text = translate_to_en(content)
        else:
            en_text = content
            zh_text = translate_to_zh(content)
        
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
    
    def clear_category(self, category: str) -> bool:
        """清空分类"""
        try:
            response = requests.delete(
                f"{SUPABASE_URL}/rest/v1/knowledge_base?category=eq.{category}",
                headers=self.headers
            )
            if response.status_code in [200, 204]:
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
                self.clear_category(cat)
                for item in df[cat].dropna():
                    if str(item).strip():
                        if self.add_knowledge(cat, str(item).strip()):
                            total += 1
        self._load_cache()
        return total


# ==================== 默认知识库数据 ====================

DEFAULT_KNOWLEDGE = {
    "光学": [
        "LED光衰过快通常与结温过高有关，建议优化散热设计",
        "色偏问题可能由不同批次LED芯片的色温差异导致",
        "透镜发黄/老化是由于长时间高温导致的材料降解",
        "光斑不均匀可能是光学设计或LED排列问题",
        "防水结构失效导致水汽进入光学腔体，引起透光率下降"
    ],
    "机械": [
        "外壳开裂通常与材料选型、应力集中或安装过紧有关",
        "密封圈老化失效是进水故障的常见原因，建议定期更换",
        "螺丝松动可能导致电气接触不良或防水失效",
        "振动环境下的连接器需要增加锁紧机构或点胶固定",
        "热膨胀系数不匹配导致不同材料间产生间隙"
    ],
    "材料": [
        "PCBA碳化是短路后的典型现象，会导致电阻下降形成正反馈",
        "灌封胶与外壳的附着力不足是水汽侵入的薄弱环节",
        "PVC线材在高温环境下会加速老化变脆",
        "PMMA透镜的耐温等级通常为80°C，超过会变形",
        "PA66材料具有较好的阻燃性（V0等级）"
    ],
    "热学": [
        "结温每升高10°C，LED寿命约减少50%",
        "黑色表面在阳光直射下温度可达70-80°C",
        "散热不良是导致电子元器件加速老化的主要原因",
        "热胀冷缩效应会破坏密封结构，建议使用柔性密封材料",
        "建议在高温环境应用中使用主动散热或增大散热面积"
    ],
    "电气": [
        "浪涌保护不足是电源损坏的常见原因",
        "短路发生后持续供电会导致PCB碳化起火",
        "建议在电源输出端加装保险丝或断路器",
        "湿气侵入会导致绝缘电阻下降，引发漏电或短路",
        "长时间过载运行会加速电解电容老化"
    ],
    "控制": [
        "单片机的死机可能是电源纹波过大或EMI干扰导致",
        "通信异常常由接线松动、线缆过长或终端电阻配置错误引起",
        "固件bug可能导致异常状态无法恢复",
        "建议增加看门狗定时器防止系统死锁",
        "DMX信号链中的终端电阻匹配很重要"
    ]
}


# ==================== 管理员弹窗 ====================

@st.dialog("管理员设置", width="large")
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
        if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
            st.success(f"✅ {get_text('db_connected')}")
        else:
            st.error(f"❌ {get_text('db_disconnected')}")
    
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
        st.markdown(f"**{get_text('export_kb')}**")
        if st.button("📥 " + get_text("export_kb"), key="export_btn"):
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
        st.markdown(f"**{get_text('import_kb')}**")
        uploaded = st.file_uploader("选择Excel文件", type=["xlsx", "xls"], key="kb_upload")
        if uploaded:
            try:
                df = pd.read_excel(uploaded)
                count = kb.import_from_dataframe(df)
                st.success(get_text("import_success").format(count=count))
                st.rerun()
            except Exception as e:
                st.error(f"导入失败: {e}")


# ==================== 鱼骨图生成（放大版）====================

def setup_chinese_font():
    """设置中文字体（从网络加载）"""
    try:
        font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
        font_path = "/tmp/NotoSansCJKsc-Regular.otf"
        
        import os
        if not os.path.exists(font_path):
            response = requests.get(font_url, timeout=30)
            with open(font_path, 'wb') as f:
                f.write(response.content)
        
        fontManager.addfont(font_path)
        plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        return True
    except:
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
        return False


def create_fishbone_image(fishbone: FishboneAnalysis, lang: str = "zh") -> bytes:
    """生成鱼骨图图片（放大版 16x10 英寸）"""
    setup_chinese_font()
    
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    # 主骨
    ax.plot([2, 14], [6, 6], 'k-', linewidth=3)
    
    # 箭头
    ax.annotate('', xy=(14, 6), xytext=(13.2, 6),
                arrowprops=dict(arrowstyle='->', lw=3, color='black'))
    
    # 鱼头标签
    ax.text(14.5, 6, get_text("symptom")[:25] if lang == "zh" else "Failure", 
            fontsize=12, va='center', fontweight='bold')
    
    cat_names_zh = {"Man": "人", "Machine": "机", "Material": "料",
                    "Method": "法", "Environment": "环", "Measurement": "测"}
    
    categories = [
        ("Man", fishbone.man, 4, 9.5),
        ("Machine", fishbone.machine, 4, 8.2),
        ("Material", fishbone.material, 4, 6.9),
        ("Method", fishbone.method, 5, 5.1),
        ("Environment", fishbone.environment, 5, 3.8),
        ("Measurement", fishbone.measurement, 5, 2.5)
    ]
    
    for cat_key, causes, spine_x, spine_y in categories:
        display_name = cat_names_zh.get(cat_key, cat_key) if lang == "zh" else cat_key
        
        ax.plot([2.5, spine_x], [6, spine_y], 'k-', linewidth=1.5)
        ax.text(spine_x - 0.5, spine_y, display_name, fontsize=11,
                ha='right', va='center', fontweight='bold')
        
        for j, cause in enumerate(causes[:4]):
            cause_text = cause[:25] + "…" if len(cause) > 25 else cause
            y_offset = spine_y + 0.6 + j * 0.45 if j % 2 == 0 else spine_y - 0.6 - (j-1) * 0.45
            ax.plot([spine_x, spine_x + 0.8], [spine_y, y_offset], 'k:', linewidth=0.8, alpha=0.6)
            ax.text(spine_x + 0.9, y_offset, cause_text, fontsize=8, va='center')
    
    ax.text(8, 11.2, get_text("fishbone_title"), fontsize=16, ha='center', fontweight='bold')
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close()
    
    return buf.getvalue()


# ==================== 失效等级分类 ====================

STAGES = {
    0: {"zh": "正常", "en": "Normal"},
    1: {"zh": "轻微异常", "en": "Minor Anomaly"},
    2: {"zh": "中度异常", "en": "Moderate Anomaly"},
    3: {"zh": "严重故障", "en": "Critical Failure"}
}


def classify_stage(symptom: str) -> Tuple[int, float]:
    """分类故障等级"""
    symptom_lower = symptom.lower()
    
    keywords = {
        1: ["闪烁", "弱光", "色偏", "flicker", "dim", "intermittent"],
        2: ["烧焦", "膨胀", "变形", "burn", "swell", "deform", "黑化"],
        3: ["短路", "冒烟", "起火", "爆炸", "short", "smoke", "fire", "explode"]
    }
    
    scores = {0: 0, 1: 0, 2: 0, 3: 0}
    
    for stage, kw_list in keywords.items():
        for kw in kw_list:
            if kw in symptom_lower:
                scores[stage] += 1
    
    if max(scores.values()) == 0:
        return 1, 0.6
    
    best = max(scores, key=scores.get)
    confidence = min(0.95, 0.5 + scores[best] * 0.1)
    return best, confidence


def get_stage_name(stage: int, lang: str) -> str:
    return STAGES.get(stage, STAGES[1])[lang]


# ==================== 5-Why 推理 ====================

def generate_five_why(symptom: str, product_name: str, lang: str,
                      installation: str = "", temperature: str = "") -> List[FiveWhyItem]:
    """生成5-Why推理链（双语支持）"""
    chain = []
    current_question = symptom
    
    templates_zh = {
        1: "为什么会出现这个问题？直接原因是什么？",
        2: "为什么会有这个直接原因？",
        3: "这个原因背后的系统性问题是什么？",
        4: "为什么这个系统性问题会存在？",
        5: "流程/设计/管理上有什么缺陷？"
    }
    
    templates_en = {
        1: "What is the direct cause of this problem?",
        2: "Why did this direct cause occur?",
        3: "What systemic issue led to this?",
        4: "Why does this systemic issue exist?",
        5: "What process/design/management flaw allowed this?"
    }
    
    templates = templates_zh if lang == "zh" else templates_en
    
    for level in range(1, 6):
        context = ""
        if installation:
            context += f"Installation: {installation}\n"
        if temperature:
            context += f"Temperature: {temperature}\n"
        
        prompt = f"""You are a failure analysis engineer.

Product: {product_name}
Symptom: {symptom}

{context}
Level {level}: {current_question}
{template}

Output JSON: {{"answer": "your answer", "confidence": 0.8}}"""
        
        response = call_llm(prompt, max_tokens=500, temperature=0.3)
        
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1:
                data = json.loads(response[start:end])
                answer = data.get("answer", response[:300])
                conf = data.get("confidence", 0.7)
            else:
                answer = response[:300]
                conf = 0.7
        except:
            answer = response[:300]
            conf = 0.7
        
        chain.append(FiveWhyItem(
            level=level,
            question=current_question[:200],
            answer=answer[:300],
            confidence=conf,
            verification_method="建议通过测试验证"
        ))
        
        if level < 5:
            next_prompt = f"""Based on the answer, generate the next Why question (Why-{level+1}).

Answer: {answer}

Output only the question in "Why...?" format:"""
            current_question = call_llm(next_prompt, max_tokens=100, temperature=0.3)
    
    return chain


# ==================== 鱼骨图生成 ====================

def generate_fishbone(symptom: str, product_name: str, lang: str) -> FishboneAnalysis:
    """生成鱼骨图"""
    categories = ["Man", "Machine", "Material", "Method", "Environment", "Measurement"]
    cat_zh = {"Man": "人", "Machine": "机", "Material": "料",
              "Method": "法", "Environment": "环", "Measurement": "测"}
    
    result = {}
    
    for cat in categories:
        display = cat_zh.get(cat, cat) if lang == "zh" else cat
        
        prompt = f"""List potential causes for {display} category that could lead to this failure.

Product: {product_name}
Symptom: {symptom}

List 3-5 specific causes, one per line:"""
        
        response = call_llm(prompt, max_tokens=300, temperature=0.4)
        causes = [line.strip() for line in response.split('\n') 
                 if line.strip() and len(line.strip()) > 5][:5]
        result[cat] = causes
    
    return FishboneAnalysis(
        man=result.get("Man", []),
        machine=result.get("Machine", []),
        material=result.get("Material", []),
        method=result.get("Method", []),
        environment=result.get("Environment", []),
        measurement=result.get("Measurement", [])
    )


# ==================== 改进措施 ====================

def generate_actions(root_cause: str, product_name: str, lang: str) -> dict:
    """生成改进措施"""
    prompt = f"""Based on the root cause, generate improvement actions.

Root cause: {root_cause}
Product: {product_name}

Output JSON:
{{"interim": ["action 1", "action 2"], 
  "permanent": ["action 1", "action 2", "action 3"], 
  "preventive": ["action 1", "action 2"]}}"""
    
    response = call_llm(prompt, max_tokens=400, temperature=0.4)
    
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1:
            data = json.loads(response[start:end])
            return {
                "interim": data.get("interim", ["隔离故障产品", "通知客户"]),
                "permanent": data.get("permanent", ["修复设计缺陷", "更换组件"]),
                "preventive": data.get("preventive", ["更新FMEA", "加强检验"])
            }
    except:
        pass
    
    return {
        "interim": ["隔离故障产品", "通知客户暂停使用", "检查同批次产品"],
        "permanent": ["修复根本原因", "更新设计规范", "增加保护电路"],
        "preventive": ["更新FMEA文档", "加强来料检验", "增加定期维护"]
    }


# ==================== 时序分析器 ====================

class TimeSeriesAnalyzer:
    """时序分析器 - SPC控制图"""
    
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
    
    @staticmethod
    def create_spc_chart(df: pd.DataFrame) -> go.Figure:
        total_failures = df['failure_qty'].sum()
        total_production = df['production_qty'].sum()
        p_bar = total_failures / total_production if total_production > 0 else 0
        
        df['defect_rate'] = df['failure_qty'] / df['production_qty'] * 100
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['defect_rate'],
            mode='lines+markers',
            name='Defect Rate (%)'
        ))
        fig.add_hline(y=p_bar * 100, line_dash="dash", line_color="green",
                      annotation_text=f"Mean: {p_bar*100:.2f}%")
        
        fig.update_layout(
            title="SPC Control Chart",
            xaxis_title="Sample",
            yaxis_title="Defect Rate (%)",
            height=450
        )
        return fig


# ==================== 关联规则挖掘 ====================

def mine_association_rules(symptom: str, installation: str, temperature: str, lang: str) -> List[dict]:
    """挖掘关联规则"""
    prompt = f"""Based on the failure information, discover potential association rules:

Symptom: {symptom}
Installation: {installation if installation else 'unknown'}
Temperature: {temperature if temperature else 'unknown'}

Output 2-3 possible association rules as JSON array:
[{{"antecedents": ["condition1", "condition2"], "consequents": ["result"], "confidence": 0.8, "explanation": "explanation"}}]"""
    
    response = call_llm(prompt, max_tokens=500, temperature=0.4)
    try:
        start = response.find('[')
        end = response.rfind(']') + 1
        if start != -1:
            return json.loads(response[start:end])[:3]
    except:
        pass
    return []


# ==================== 报告生成器 ====================

def generate_fa_report(result: FailureAnalysisResult, lang: str) -> str:
    """生成FA报告"""
    stage_name = get_stage_name(result.failure_stage, lang)
    stage_emoji = {0: "✅", 1: "⚠️", 2: "🔥", 3: "🚨"}.get(result.failure_stage, "📌")
    
    symptom_text = result.symptom if lang == "zh" else result.symptom_en
    if not symptom_text and lang == "en":
        symptom_text = translate_to_en(result.symptom)
    
    fault_summary = symptom_text[:30] + "..." if len(symptom_text) > 30 else symptom_text
    title_summary = symptom_text[:12] + "..." if len(symptom_text) > 12 else symptom_text
    
    # 信息表格
    info_table = f"""
## {get_text('report_info')}

| {get_text('project_name_header')} | {result.project_name if result.project_name else '-'} |
| {get_text('product_name_header')} | {result.product_name} |
| {get_text('fault_summary')} | {fault_summary} |
| {get_text('report_date')} | {datetime.now().strftime('%Y-%m-%d')} |
| {get_text('analyst')} | {result.analyst_name if result.analyst_name else '-'} {f"({result.analyst_title})" if result.analyst_title else ''} |

"""
    
    # 失效等级
    stage_section = f"""
## {get_text('stage_label')}

{stage_emoji} **{stage_name}** ({get_text('confidence')}: {result.root_cause_confidence:.0%})

"""
    
    # 5-Why - 表格形式
    five_why_table = "| Level | Question | Answer | Confidence |\n|-------|----------|--------|------------|\n"
    for item in result.five_why:
        q_short = item.question[:45] + "..." if len(item.question) > 45 else item.question
        a_short = item.answer[:55] + "..." if len(item.answer) > 55 else item.answer
        five_why_table += f"| Why-{item.level} | {q_short} | {a_short} | {item.confidence:.0%} |\n"
    
    # 5-Why - 列表形式
    five_why_list = ""
    for item in result.five_why:
        five_why_list += f"\n**Why-{item.level}**: {item.question}\n→ {item.answer}\n*{get_text('confidence')}: {item.confidence:.0%}*\n"
    
    five_why_section = f"""
## {get_text('five_why_title')}

### 表格形式

{five_why_table}

### 详细说明

{five_why_list}
"""
    
    # 根因
    root_cause_section = f"""
## {get_text('root_cause_title')}

{result.root_cause}

"""
    
    # 鱼骨图文字版
    fishbone_dict = result.fishbone.to_dict()
    fishbone_text = ""
    for cat, causes in fishbone_dict.items():
        if causes:
            fishbone_text += f"\n**{cat}**:\n" + "\n".join([f"- {c}" for c in causes[:4]]) + "\n"
    
    fishbone_section = f"""
## {get_text('fishbone_title')}

{fishbone_text}
"""
    
    # 改进措施
    actions_text = f"""
### {get_text('interim_actions')}
{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(result.interim_actions[:3]))}

### {get_text('permanent_actions')}
{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(result.permanent_actions[:3]))}

### {get_text('preventive_actions')}
{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(result.preventive_actions[:2]))}
"""
    
    return info_table + stage_section + five_why_section + root_cause_section + fishbone_section + actions_text


def generate_8d_report(result: FailureAnalysisResult, lang: str) -> str:
    """生成8D报告"""
    stage_name = get_stage_name(result.failure_stage, lang)
    stage_emoji = {0: "✅", 1: "⚠️", 2: "🔥", 3: "🚨"}.get(result.failure_stage, "📌")
    
    symptom_text = result.symptom if lang == "zh" else result.symptom_en
    if not symptom_text and lang == "en":
        symptom_text = translate_to_en(result.symptom)
    
    fault_summary = symptom_text[:30] + "..." if len(symptom_text) > 30 else symptom_text
    title_summary = symptom_text[:12] + "..." if len(symptom_text) > 12 else symptom_text
    
    # 信息表格
    info_table = f"""
## {get_text('report_info')}

| {get_text('project_name_header')} | {result.project_name if result.project_name else '-'} |
| {get_text('product_name_header')} | {result.product_name} |
| {get_text('fault_summary')} | {fault_summary} |
| {get_text('report_date')} | {datetime.now().strftime('%Y-%m-%d')} |
| {get_text('analyst')} | {result.analyst_name if result.analyst_name else '-'} {f"({result.analyst_title})" if result.analyst_title else ''} |

"""
    
    # D1
    d1 = f"""
## D1: {get_text('establish_team')}

| Role | Responsibility |
|------|----------------|
| Team Leader | Overall coordination |
| Design Engineer | Technical analysis |
| Quality Engineer | Quality verification |

"""
    
    # D2 5W2H
    d2 = f"""
## D2: {get_text('problem_description')}

| {get_text('what')} | {symptom_text[:200]} |
| {get_text('where')} | {result.installation if result.installation else 'Installation site'} |
| {get_text('when')} | {datetime.now().strftime('%Y-%m-%d')} |
| {get_text('who')} | Field maintenance team |
| {get_text('why')} | Under investigation |
| {get_text('how')} | Failure occurred during operation |
| {get_text('how_many')} | Stage {result.failure_stage} - {stage_name} |

"""
    
    # D3
    d3 = f"""
## D3: {get_text('interim_actions')}

{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(result.interim_actions[:3]))}

"""
    
    # D4 5-Why
    five_why_list = ""
    for item in result.five_why:
        five_why_list += f"\n**Why-{item.level}**: {item.question}\n→ {item.answer}\n"
    
    fishbone_dict = result.fishbone.to_dict()
    fishbone_text = ""
    for cat, causes in fishbone_dict.items():
        if causes:
            fishbone_text += f"\n**{cat}**: {', '.join(causes[:3])}\n"
    
    d4 = f"""
## D4: {get_text('root_cause_analysis')}

### Fishbone Analysis
{fishbone_text}

### 5-Why Analysis
{five_why_list}

### Verified Root Cause
{result.root_cause}

"""
    
    # D5
    d5 = f"""
## D5: {get_text('permanent_actions')}

{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(result.permanent_actions[:3]))}

"""
    
    # D6
    d6 = f"""
## D6: {get_text('effectiveness_verification')}

| Item | Method | Criteria |
|------|--------|----------|
| Function | Actual test | Normal operation |
| Durability | Accelerated aging | Meet design life |

"""
    
    # D7
    d7 = f"""
## D7: {get_text('preventive_actions')}

{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(result.preventive_actions[:2]))}

"""
    
    # D8
    d8 = f"""
## D8: {get_text('team_recognition')}

- Root cause identified and confirmed
- Improvement actions defined
- Lessons learned added to knowledge base

"""
    
    return info_table + d1 + d2 + d3 + d4 + d5 + d6 + d7 + d8


def create_word_document(report_content: str, result: FailureAnalysisResult,
                         uploaded_images: List[bytes] = None,
                         fishbone_image: bytes = None) -> io.BytesIO:
    """创建Word文档"""
    try:
        from docx import Document
        from docx.shared import Inches, Pt
        
        doc = Document()
        
        # 标题
        title_summary = truncate_summary(result.symptom, 12)
        title = doc.add_heading(f"{result.product_name} - {title_summary}", level=1)
        
        # 添加报告内容
        lines = report_content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('# '):
                doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                doc.add_heading(line[3:], level=2)
            elif line.startswith('### '):
                doc.add_heading(line[4:], level=3)
            elif line.startswith('|') and '|' in line[1:]:
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    table_lines.append(lines[i].strip())
                    i += 1
                
                if len(table_lines) >= 2:
                    header_cells = [c.strip() for c in table_lines[0].split('|')[1:-1]]
                    if '---' in table_lines[1]:
                        data_lines = table_lines[2:]
                    else:
                        data_lines = table_lines[1:]
                    
                    if header_cells and data_lines:
                        table = doc.add_table(rows=1+len(data_lines), cols=len(header_cells))
                        table.style = 'Table Grid'
                        for col, cell_text in enumerate(header_cells):
                            table.cell(0, col).text = cell_text
                        
                        for row_idx, data_line in enumerate(data_lines):
                            cells = [c.strip() for c in data_line.split('|')[1:-1]]
                            for col_idx, cell_text in enumerate(cells):
                                if col_idx < len(header_cells):
                                    table.cell(row_idx+1, col_idx).text = cell_text
                        doc.add_paragraph()
                continue
            elif line:
                doc.add_paragraph(line)
            else:
                doc.add_paragraph()
            
            i += 1
        
        # 插入鱼骨图
        if fishbone_image:
            doc.add_page_break()
            doc.add_heading(get_text("fishbone_title"), level=2)
            img_stream = io.BytesIO(fishbone_image)
            doc.add_picture(img_stream, width=Inches(12))
        
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

def run_analysis(product_name: str, symptom: str, project_name: str,
                 installation: str, temperature: str, lang: str,
                 timeseries_df: pd.DataFrame = None,
                 enable_web: bool = True,
                 enable_rules: bool = True,
                 analyst_name: str = "", analyst_title: str = "") -> FailureAnalysisResult:
    """执行故障分析"""
    
    # 根据目标语言翻译输入
    if lang == "en" and is_chinese(symptom):
        symptom_en = translate_to_en(symptom)
        product_name_en = translate_to_en(product_name) if is_chinese(product_name) else product_name
        installation_en = translate_to_en(installation) if installation and is_chinese(installation) else installation
    else:
        symptom_en = symptom
        product_name_en = product_name
        installation_en = installation
    
    use_symptom = symptom_en if lang == "en" else symptom
    use_product = product_name_en if lang == "en" else product_name
    use_installation = installation_en if lang == "en" else installation
    
    # 联网搜索
    web_results = ""
    if enable_web:
        web_results = web_search_dual(use_symptom, lang)
    
    # 知识库检索
    kb = SupabaseKnowledgeDB()
    kb_results = kb.search_knowledge_dual(use_symptom, lang)
    
    # 分类等级
    stage, _ = classify_stage(use_symptom)
    
    # 生成5-Why
    five_why = generate_five_why(use_symptom, use_product, lang, use_installation, temperature)
    
    # 生成鱼骨图
    fishbone = generate_fishbone(use_symptom, use_product, lang)
    
    # 生成鱼骨图图片
    fishbone_image = create_fishbone_image(fishbone, lang)
    
    # 根因
    root_cause = five_why[-1].answer if five_why else "Further analysis needed"
    root_cause_confidence = five_why[-1].confidence if five_why else 0.6
    
    # 改进措施
    actions = generate_actions(root_cause, use_product, lang)
    
    # SPC分析
    spc_analysis = None
    if timeseries_df is not None and len(timeseries_df) > 0:
        spc_analysis = TimeSeriesAnalyzer.analyze_trend(timeseries_df)
    
    # 关联规则
    association_rules = []
    if enable_rules:
        association_rules = mine_association_rules(use_symptom, use_installation, temperature, lang)
    
    return FailureAnalysisResult(
        case_id=str(uuid.uuid4())[:8],
        project_name=project_name,
        product_name=product_name,
        symptom=symptom,
        symptom_en=symptom_en,
        installation=installation,
        installation_en=installation_en,
        temperature=temperature,
        failure_stage=stage,
        five_why=five_why,
        fishbone=fishbone,
        root_cause=root_cause,
        root_cause_confidence=root_cause_confidence,
        interim_actions=actions["interim"],
        permanent_actions=actions["permanent"],
        preventive_actions=actions["preventive"],
        internal_cases_used=len(kb_results),
        external_sources_used=1 if web_results else 0,
        spc_analysis=spc_analysis,
        association_rules=association_rules,
        analyst_name=analyst_name,
        analyst_title=analyst_title,
        fishbone_image=fishbone_image
    )


# ==================== 主页面 ====================

def main():
    """主应用入口"""
    
    # 初始化
    if "lang" not in st.session_state:
        st.session_state.lang = "zh"
    if "result" not in st.session_state:
        st.session_state.result = None
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
    
    # 右上角语言切换和齿轮
    col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
    with col3:
        if st.button(get_text("lang_zh"), key="zh_btn"):
            st.session_state.lang = "zh"
            st.rerun()
    with col4:
        if st.button(get_text("lang_en"), key="en_btn"):
            st.session_state.lang = "en"
            st.rerun()
    with col5:
        if st.button("⚙️", key="settings_btn"):
            admin_settings_dialog()
    
    st.title(get_text("app_title"))
    st.caption(get_text("app_subtitle"))
    
    if not DEEPSEEK_API_KEY:
        st.error(get_text("api_error"))
        return
    
    # 侧边栏
    with st.sidebar:
        st.markdown(f"### {get_text('sidebar_about')}")
        st.markdown(get_text("sidebar_principle"))
        st.markdown(get_text("sidebar_usage"))
        st.markdown("---")
        
        st.session_state.analyst_name = st.text_input(get_text("analyst_name"), placeholder=get_text("analyst_name_ph"))
        st.session_state.analyst_title = st.text_input(get_text("analyst_title"), placeholder=get_text("analyst_title_ph"))
        st.session_state.project_name = st.text_input(get_text("project_name_label"), placeholder=get_text("project_name_ph"))
        
        if st.session_state.analyst_name:
            st.success(f"{get_text('analyst')}: {st.session_state.analyst_name}")
        
        st.markdown("---")
        st.markdown(f"**{get_text('db_status')}**")
        if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
            st.success(f"✅ {get_text('db_connected')}")
        else:
            st.error(f"❌ {get_text('db_disconnected')}")
        
        st.markdown("---")
        st.markdown(f"### {get_text('contact')}")
        st.markdown(get_text("contact_email"))
    
    # 主表单 - 上下布局
    st.markdown(f"### {get_text('basic_info')}")
    
    product_name = st.text_input(get_text("product_name"), placeholder=get_text("product_name_ph"))
    symptom = st.text_area(get_text("symptom"), height=120, placeholder=get_text("symptom_ph"))
    installation = st.text_input(get_text("installation"), placeholder=get_text("installation_ph"))
    
    col_date, col_batch = st.columns(2)
    with col_date:
        st.date_input(get_text("failure_date"), value=datetime.now().date())
    with col_batch:
        st.text_input(get_text("batch_no"), placeholder="LOT2024-001")
    
    temperature = st.text_input(get_text("site_temp"), placeholder=get_text("site_temp_ph"))
    
    st.markdown("---")
    st.markdown(f"### {get_text('image_section')}")
    
    uploaded_files = st.file_uploader(get_text("image_upload_hint"), type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    if uploaded_files:
        st.session_state.uploaded_images = [img.getvalue() for img in uploaded_files]
        cols = st.columns(min(3, len(uploaded_files)))
        for idx, img in enumerate(uploaded_files[:3]):
            with cols[idx]:
                st.image(img, use_container_width=True)
    else:
        st.caption(get_text("no_images"))
    
    st.markdown("---")
    st.markdown(f"### {get_text('timeseries_section')}")
    
    enable_timeseries = st.checkbox(get_text("timeseries_checkbox"), value=False)
    timeseries_df = None
    
    if enable_timeseries:
        input_method = st.radio(get_text("timeseries_input_method"), [get_text("timeseries_paste"), get_text("timeseries_upload")], horizontal=True)
        
        if input_method == get_text("timeseries_paste"):
            paste_data = st.text_area(get_text("timeseries_paste_placeholder"), height=150)
            if paste_data:
                timeseries_df = TimeSeriesAnalyzer.parse_data(paste_data)
        else:
            timeseries_file = st.file_uploader(get_text("timeseries_file_hint"), type=["xlsx", "xls", "csv"])
            if timeseries_file:
                timeseries_df = TimeSeriesAnalyzer.parse_excel(timeseries_file)
                if timeseries_df is not None:
                    st.dataframe(timeseries_df.head(), use_container_width=True)
        
        template_df = pd.DataFrame({"date": ["2024-01-01", "2024-02-01"], "production_qty": [1000, 1100], "failure_qty": [5, 8]})
        st.download_button(get_text("download_template"), template_df.to_csv(index=False).encode(), "template.csv")
    
    st.markdown("---")
    st.markdown(f"### {get_text('advanced_options')}")
    
    col_adv1, col_adv2, col_adv3, col_adv4 = st.columns(4)
    with col_adv1:
        enable_web = st.checkbox(get_text("web_search"), value=True)
    with col_adv2:
        enable_rules = st.checkbox(get_text("rule_mining"), value=True)
    with col_adv3:
        enable_spc = st.checkbox(get_text("spc"), value=True)
    with col_adv4:
        enable_8d = st.checkbox(get_text("gen_8d"), value=True)
    
    st.markdown("---")
    
    if st.button(get_text("analyze_btn"), type="primary", use_container_width=True):
        if not product_name or not symptom:
            st.error(get_text("fill_required"))
        else:
            with st.spinner(get_text("analyzing")):
                try:
                    result = run_analysis(
                        product_name=product_name,
                        symptom=symptom,
                        project_name=st.session_state.project_name,
                        installation=installation,
                        temperature=temperature,
                        lang=st.session_state.lang,
                        timeseries_df=timeseries_df if enable_timeseries else None,
                        enable_web=enable_web,
                        enable_rules=enable_rules,
                        analyst_name=st.session_state.analyst_name,
                        analyst_title=st.session_state.analyst_title
                    )
                    st.session_state.result = result
                    st.session_state.current_report = None
                    st.success(get_text("success"))
                    st.rerun()
                except Exception as e:
                    st.error(f"{get_text('error')}: {str(e)}")
    
    # 显示结果
    if st.session_state.result:
        result = st.session_state.result
        lang = st.session_state.lang
        stage_name = get_stage_name(result.failure_stage, lang)
        
        st.markdown("---")
        st.info(f"**{get_text('stage_label')}**: {stage_name} ({get_text('confidence')}: {result.root_cause_confidence:.0%})")
        
        with st.expander(get_text("five_why_title"), expanded=True):
            for item in result.five_why:
                st.markdown(f"**Why-{item.level}**: {item.question}")
                st.markdown(f"→ {item.answer}")
                st.progress(item.confidence, text=f"{get_text('confidence')}: {item.confidence:.0%}")
                st.divider()
        
        with st.expander(get_text("fishbone_title")):
            if result.fishbone_image:
                st.image(result.fishbone_image, use_container_width=True)
            else:
                fishbone_dict = result.fishbone.to_dict()
                for cat, causes in fishbone_dict.items():
                    if causes:
                        st.markdown(f"**{cat}**")
                        for c in causes[:4]:
                            st.markdown(f"- {c}")
        
        if result.spc_analysis and result.spc_analysis.get("has_data"):
            with st.expander(get_text("spc_title")):
                st.metric("Overall Rate", f"{result.spc_analysis['overall_rate']:.2f}%")
                st.metric("Trend", result.spc_analysis['trend'])
        
        if result.association_rules:
            with st.expander(get_text("rules_title")):
                for rule in result.association_rules:
                    antecedents = " + ".join(rule.get("antecedents", []))
                    consequents = " + ".join(rule.get("consequents", []))
                    st.info(f"{antecedents} → {consequents} (Confidence: {rule.get('confidence', 0):.0%})")
        
        st.markdown(f"### {get_text('root_cause_title')}")
        st.success(result.root_cause)
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button(get_text("generate_fa_btn"), use_container_width=True):
                report = generate_fa_report(result, lang)
                st.session_state.current_report = report
                st.session_state.report_type = "FA"
                st.rerun()
        with col_btn2:
            if st.button(get_text("generate_8d_btn"), use_container_width=True):
                report = generate_8d_report(result, lang)
                st.session_state.current_report = report
                st.session_state.report_type = "8D"
                st.rerun()
        with col_btn3:
            if st.button(get_text("clear_btn"), use_container_width=True):
                st.session_state.result = None
                st.session_state.current_report = None
                st.rerun()
    
    # 显示报告
    if st.session_state.current_report:
        st.markdown("---")
        st.markdown(f"### {get_text('report_preview')}")
        with st.container(height=500):
            st.markdown(st.session_state.current_report)
        
        title_summary = truncate_summary(st.session_state.result.symptom, 12)
        filename = f"{st.session_state.result.product_name}_{title_summary}_{st.session_state.report_type}_Report_{datetime.now().strftime('%Y%m%d')}.docx"
        filename = re.sub(r'[\\/*?:"<>|]', '', filename)
        
        word_buffer = create_word_document(
            st.session_state.current_report,
            st.session_state.result,
            st.session_state.uploaded_images,
            st.session_state.result.fishbone_image
        )
        
        st.download_button(
            label=get_text("download_word"),
            data=word_buffer,
            file_name=filename,
            use_container_width=True
        )


if __name__ == "__main__":
    setup_chinese_font()
    main()
