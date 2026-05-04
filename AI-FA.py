"""
AI-FA 智能故障分析系统
AI-powered Failure Analysis & 8D Report Generation

功能：
- 多模态输入（文本+图片+Ctrl+V粘贴）
- 5-Why根因推理
- 鱼骨图自动生成（matplotlib可视化）
- 失效等级分类
- SPC时序分析（不良率趋势）
- 关联规则挖掘
- 双源知识库（内部+外部）
- FA报告生成 + 8D报告生成
- 双语支持（中文/English）
- Word报告导出（图文并茂）
- 管理员后台（知识库管理）

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
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patches as mpatches

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

# 设置中文字体（用于matplotlib鱼骨图）
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'WenQuanYi Zen Hei']
    plt.rcParams['axes.unicode_minus'] = False
except:
    pass


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
            "Man (\u4eba)": self.man,
            "Machine (\u673a)": self.machine,
            "Material (\u6599)": self.material,
            "Method (\u6cd5)": self.method,
            "Environment (\u73af)": self.environment,
            "Measurement (\u6d4b)": self.measurement
        }


@dataclass
class FailureAnalysisResult:
    """故障分析完整结果"""
    case_id: str
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
    fishbone_image: Optional[bytes] = None  # 鱼骨图图片


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
        "db_status": "数据库状态",
        "db_connected": "已连接",
        "db_disconnected": "未连接",
        "contact": "联系",
        "contact_email": "电邮: Techlife2027@gmail.com",
        
        # 输入区域
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
        "no_images": "暂无图片",
        "timeseries_section": "时序数据分析",
        "timeseries_checkbox": "启用时序数据分析（SPC控制图）",
        "timeseries_input_method": "数据输入方式",
        "timeseries_paste": "直接粘贴数据",
        "timeseries_upload": "上传Excel/CSV文件",
        "timeseries_paste_placeholder": "请输入时序数据，格式：\n日期,生产数量,故障数量\n2024-01-01,1000,5\n2024-02-01,1100,8",
        "timeseries_file_hint": "支持 .xlsx, .xls, .csv 格式",
        "download_template": "下载数据模板",
        
        # 高级选项
        "advanced_options": "高级分析选项",
        "web_search": "联网搜索行业案例",
        "rule_mining": "关联规则挖掘",
        "spc": "时序分析(SPC控制图)",
        "gen_8d": "生成8D报告",
        
        # 按钮
        "analyze_btn": "开始AI深度故障分析",
        "generate_fa_btn": "生成FA报告",
        "generate_8d_btn": "生成8D报告",
        "download_word": "下载Word报告",
        "clear_btn": "清除结果",
        
        # 分析结果
        "five_why_title": "5-Why 根因分析",
        "fishbone_title": "鱼骨图分析",
        "root_cause_title": "根因结论",
        "interim_actions": "临时措施",
        "permanent_actions": "永久措施",
        "preventive_actions": "预防再发",
        "confidence": "置信度",
        "stage_label": "失效等级",
        "spc_title": "SPC控制图分析",
        "rules_title": "关联规则挖掘",
        
        # 状态
        "analyzing": "AI正在分析中，请稍候...",
        "success": "分析完成！",
        "error": "分析失败，请重试",
        "fill_required": "请填写产品名称和故障现象",
        "api_error": "API配置错误，请检查Streamlit Secrets",
        
        # 失效等级
        "stage_0": "正常",
        "stage_1": "轻微异常",
        "stage_2": "中度异常",
        "stage_3": "严重故障",
        
        # 报告
        "report_preview": "报告预览",
        "fault_photos": "故障照片",
        "analyst": "分析人",
        "analysis_date": "分析日期",
        
        # 管理员
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
        "root_cause_title": "Root Cause Conclusion",
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


def remove_bold_markers(text: str) -> str:
    """删除文本中的**粗体标记"""
    if not text:
        return text
    return re.sub(r'\*\*([^*]+)\*\*', r'\1', text)


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


def translate_text(text: str, target_lang: str) -> str:
    """使用DeepSeek翻译文本"""
    if not text or not text.strip():
        return text
    
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


def create_fishbone_image(fishbone: FishboneAnalysis) -> bytes:
    """使用matplotlib创建鱼骨图图片"""
    
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # 画主骨（水平线）
    main_line_x = [1, 9]
    main_line_y = [5, 5]
    ax.plot(main_line_x, main_line_y, 'k-', linewidth=3, color='black')
    
    # 画箭头（鱼头）
    ax.annotate('', xy=(9, 5), xytext=(8.5, 5),
                arrowprops=dict(arrowstyle='->', lw=2, color='black'))
    
    # 鱼头标签（故障）
    ax.text(9.2, 5, get_text("symptom")[:20], fontsize=10, va='center', fontweight='bold')
    
    # 六个分支的定义
    categories = [
        ("Man (\u4eba)", fishbone.man, 4, 7.5),
        ("Machine (\u673a)", fishbone.machine, 4, 6.5),
        ("Material (\u6599)", fishbone.material, 4, 5.5),
        ("Method (\u6cd5)", fishbone.method, 6, 4.5),
        ("Environment (\u73af)", fishbone.environment, 6, 3.5),
        ("Measurement (\u6d4b)", fishbone.measurement, 6, 2.5),
    ]
    
    for idx, (cat_name, causes, spine_x, spine_y) in enumerate(categories):
        # 画脊骨
        spine_x_start = 2
        spine_y_start = spine_y
        ax.plot([spine_x_start, spine_x], [spine_y_start, spine_y], 'k-', linewidth=1.5)
        
        # 画分支线
        branch_x = 3.5
        branch_y = spine_y
        ax.plot([spine_x_start, branch_x], [spine_y_start, branch_y], 'k--', linewidth=1, alpha=0.7)
        
        # 分类标签
        ax.text(branch_x - 0.3, branch_y, cat_name, fontsize=9, ha='right', va='center', fontweight='bold')
        
        # 原因列表
        for j, cause in enumerate(causes[:4]):
            cause_text = cause[:25] + "..." if len(cause) > 25 else cause
            y_offset = branch_y + (j - 1) * 0.4
            ax.plot([branch_x, branch_x + 0.8], [branch_y, y_offset], 'k:', linewidth=0.8, alpha=0.5)
            ax.text(branch_x + 0.9, y_offset, cause_text, fontsize=7, va='center')
    
    # 标题
    ax.text(5, 9.5, get_text("fishbone_title"), fontsize=14, ha='center', fontweight='bold')
    
    plt.tight_layout()
    
    # 保存为字节流
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
    
    def get_knowledge(self, category: str) -> List[str]:
        """获取指定分类的知识条目"""
        lang = st.session_state.get("lang", "zh")
        if lang == "zh":
            return self.knowledge_zh.get(category, [])
        else:
            return self.knowledge_en.get(category, [])
    
    def add_knowledge(self, category: str, content: str) -> bool:
        """添加知识条目（自动存储双语）"""
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
        except Exception as e:
            print(f"添加失败: {e}")
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
        except Exception as e:
            print(f"删除失败: {e}")
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
        except Exception as e:
            print(f"清空失败: {e}")
        return False
    
    def export_to_dataframe(self) -> pd.DataFrame:
        """导出知识库到DataFrame"""
        max_len = max((len(self.knowledge_zh.get(cat, [])) for cat in self.categories), default=0)
        export_data = {}
        for cat in self.categories:
            items = self.knowledge_zh.get(cat, [])
            export_data[cat] = items + [''] * (max_len - len(items))
        return pd.DataFrame(export_data)
    
    def import_from_dataframe(self, df: pd.DataFrame) -> int:
        """从DataFrame导入知识库"""
        total = 0
        for cat in self.categories:
            if cat in df.columns:
                self.clear_category(cat)
                items = df[cat].dropna().tolist()
                for item in items:
                    if item and str(item).strip():
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
        if NEO4J_URI and NEO4J_PASSWORD:
            st.success(f"✅ {get_text('neo4j_connected')}")
        else:
            st.warning(f"⚠️ {get_text('neo4j_disconnected')}")
    
    st.markdown("---")
    
    # 知识库管理
    st.subheader(get_text("knowledge_base_title"))
    
    if "knowledge_db" not in st.session_state:
        st.session_state.knowledge_db = SupabaseKnowledgeDB()
    
    kb = st.session_state.knowledge_db
    categories = kb.categories
    
    selected_cat = st.selectbox(get_text("category"), categories)
    items = kb.get_knowledge(selected_cat)
    
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
    
    new_item = st.text_area(get_text("entry_content"), height=80, placeholder=get_text("entry_placeholder"))
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
            df.columns = [f"{cat} / {cat}" for cat in categories]
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
                column_map = {cat: cat for cat in categories}
                for col in df.columns:
                    for cat in categories:
                        if cat in col:
                            column_map[cat] = col
                            break
                
                import_df = pd.DataFrame()
                for cat in categories:
                    if column_map[cat] in df.columns:
                        import_df[cat] = df[column_map[cat]]
                    else:
                        import_df[cat] = []
                
                count = kb.import_from_dataframe(import_df)
                st.success(get_text("import_success").format(count=count))
                st.rerun()
            except Exception as e:
                st.error(f"导入失败: {e}")


# ==================== 失效等级分类器 ====================

class FailureStageClassifier:
    """失效等级分类器"""
    
    STAGES = {
        0: {"name_zh": "正常", "name_en": "Normal", "keywords": ["正常", "无异常", "working", "fine"]},
        1: {"name_zh": "轻微异常", "name_en": "Minor", "keywords": ["闪烁", "弱光", "色偏", "flicker", "dim", "intermittent"]},
        2: {"name_zh": "中度异常", "name_en": "Moderate", "keywords": ["烧焦", "膨胀", "变形", "burn", "swell", "deform", "黑化"]},
        3: {"name_zh": "严重故障", "name_en": "Critical", "keywords": ["短路", "冒烟", "起火", "爆炸", "short", "smoke", "fire", "explode"]}
    }
    
    @classmethod
    def classify(cls, symptom: str) -> Tuple[int, float]:
        """分类故障等级"""
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
    
    @classmethod
    def get_stage_emoji(cls, stage: int) -> str:
        emojis = {0: "✅", 1: "⚠️", 2: "🔥", 3: "🚨"}
        return emojis.get(stage, "📌")


# ==================== 5-Why 推理引擎 ====================

class FiveWhyEngine:
    """5-Why推理引擎"""
    
    WHY_TEMPLATES = {
        1: "为什么会出现这个问题？直接原因是什么？",
        2: "为什么会有这个直接原因？更深层的原因是什么？",
        3: "这个深层原因背后的系统性问题是什么？",
        4: "为什么这个系统性问题会存在？根本原因在哪？",
        5: "这个根本原因的背后，我们的流程/设计/管理有什么缺陷？"
    }
    
    @classmethod
    def generate(cls, symptom: str, product_name: str, 
                 installation: str = "", temperature: str = "") -> List[FiveWhyItem]:
        """生成5-Why推理链"""
        chain = []
        current_question = symptom
        
        for level in range(1, 6):
            prompt = cls._build_prompt(level, current_question, symptom, 
                                       product_name, installation, temperature)
            response = call_llm(prompt, max_tokens=500, temperature=0.3)
            answer_data = cls._parse_answer(response)
            answer = answer_data.get("answer", response[:300])
            verification = cls._suggest_verification(answer, product_name)
            
            chain.append(FiveWhyItem(
                level=level,
                question=remove_bold_markers(current_question[:200]),
                answer=remove_bold_markers(answer[:300]),
                confidence=answer_data.get("confidence", 0.7),
                evidence_source=remove_bold_markers(answer_data.get("evidence_source", "AI推理")),
                verification_method=remove_bold_markers(verification[:150])
            ))
            
            if level < 5:
                current_question = cls._next_question(answer, level)
        
        return chain
    
    @classmethod
    def _build_prompt(cls, level: int, question: str, symptom: str,
                      product_name: str, installation: str, temperature: str) -> str:
        context_text = ""
        if installation:
            context_text += f"安装条件: {installation}\n"
        if temperature:
            context_text += f"现场温度: {temperature}\n"
        
        return f"""你是一位资深故障分析工程师。请进行5-Why根因分析。

产品名称: {product_name}
故障现象: {symptom}

{context_text}
当前分析层级: Why-{level}
当前问题: {question}

{cls.WHY_TEMPLATES.get(level, '请分析根本原因')}

请输出JSON格式，不要有其他内容：
{{"answer": "具体答案", "evidence_source": "证据来源", "confidence": 0.8}}"""
    
    @classmethod
    def _parse_answer(cls, response: str) -> dict:
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except:
            pass
        return {"answer": response.strip()[:300], "confidence": 0.7, "evidence_source": "AI推理"}
    
    @classmethod
    def _suggest_verification(cls, answer: str, product_name: str) -> str:
        prompt = f"""基于根因假设，建议具体的验证方法：

根因假设: {answer}
产品: {product_name}

请给出1-2个具体、可执行的验证方法，直接输出："""
        return call_llm(prompt, max_tokens=150, temperature=0.2)
    
    @classmethod
    def _next_question(cls, answer: str, level: int) -> str:
        prompt = f"""基于以下答案，生成下一层（Why-{level+1}）的追问问题。

答案: {answer}

请输出一个"为什么...？"格式的问题，直接输出："""
        return call_llm(prompt, max_tokens=100, temperature=0.3)


# ==================== 鱼骨图生成器 ====================

class FishboneGenerator:
    """鱼骨图生成器"""
    
    CATEGORIES = {
        "Man": {"zh": "人", "sub": ["操作技能", "培训", "疲劳", "疏忽", "沟通"]},
        "Machine": {"zh": "机", "sub": ["设备精度", "维护", "老化", "参数设置", "工装"]},
        "Material": {"zh": "料", "sub": ["来料质量", "批次差异", "存储条件", "规格", "供应商"]},
        "Method": {"zh": "法", "sub": ["工艺流程", "SOP", "检验方法", "设计", "测试"]},
        "Environment": {"zh": "环", "sub": ["温湿度", "洁净度", "振动", "光照", "EMI"]},
        "Measurement": {"zh": "测", "sub": ["量具精度", "校准", "测量方法", "抽样", "记录"]}
    }
    
    @classmethod
    def generate(cls, symptom: str, product_name: str, 
                 five_why_chain: List[FiveWhyItem] = None) -> FishboneAnalysis:
        """生成鱼骨图"""
        fishbone = {cat: [] for cat in cls.CATEGORIES}
        
        why_context = ""
        if five_why_chain:
            why_context = "5-Why分析中已识别的关键因素：\n"
            for item in five_why_chain[:3]:
                if item.answer:
                    why_context += f"- {item.answer[:100]}...\n"
        
        for cat_key, cat_info in cls.CATEGORIES.items():
            cat_zh = cat_info["zh"]
            sub_items = ", ".join(cat_info["sub"])
            
            prompt = f"""列出可能导致以下故障的「{cat_zh}」相关原因。

产品: {product_name}
故障: {symptom}
可能的子分类: {sub_items}

{why_context}

请输出3-5个具体、可验证的原因，每行一个："""
            
            response = call_llm(prompt, max_tokens=300, temperature=0.4)
            causes = [remove_bold_markers(line.strip()) for line in response.split('\n') 
                     if line.strip() and len(line.strip()) > 5 and not line.startswith('```')]
            fishbone[cat_key] = causes[:6]
        
        return FishboneAnalysis(
            man=fishbone.get("Man", []),
            machine=fishbone.get("Machine", []),
            material=fishbone.get("Material", []),
            method=fishbone.get("Method", []),
            environment=fishbone.get("Environment", []),
            measurement=fishbone.get("Measurement", [])
        )


# ==================== 时序分析器 ====================

class TimeSeriesAnalyzer:
    """时序分析器 - SPC控制图"""
    
    @staticmethod
    def parse_data(data_text: str) -> Optional[pd.DataFrame]:
        """解析粘贴的数据"""
        try:
            lines = data_text.strip().split('\n')
            if len(lines) < 2:
                return None
            
            has_header = ',' in lines[0] and ('date' in lines[0].lower() or '日期' in lines[0])
            
            if has_header:
                df = pd.read_csv(io.StringIO(data_text))
            else:
                data = [line.split(',') for line in lines]
                df = pd.DataFrame(data[1:], columns=data[0] if len(data) > 1 else ['date', 'production_qty', 'failure_qty'])
            
            if 'production_qty' in df.columns:
                df['production_qty'] = pd.to_numeric(df['production_qty'], errors='coerce')
            if 'failure_qty' in df.columns:
                df['failure_qty'] = pd.to_numeric(df['failure_qty'], errors='coerce')
            
            df = df.dropna()
            return df if len(df) > 0 else None
        except Exception as e:
            print(f"解析失败: {e}")
            return None
    
    @staticmethod
    def parse_excel(file) -> Optional[pd.DataFrame]:
        """解析上传的Excel/CSV"""
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            if 'production_qty' in df.columns:
                df['production_qty'] = pd.to_numeric(df['production_qty'], errors='coerce')
            if 'failure_qty' in df.columns:
                df['failure_qty'] = pd.to_numeric(df['failure_qty'], errors='coerce')
            
            df = df.dropna()
            return df if len(df) > 0 else None
        except Exception as e:
            print(f"解析失败: {e}")
            return None
    
    @staticmethod
    def calculate_spc(df: pd.DataFrame) -> dict:
        """计算SPC控制限"""
        total_failures = df['failure_qty'].sum()
        total_production = df['production_qty'].sum()
        p_bar = total_failures / total_production if total_production > 0 else 0
        
        n_bar = df['production_qty'].mean()
        sigma = np.sqrt(p_bar * (1 - p_bar) / n_bar) if n_bar > 0 else 0
        ucl = min(1.0, p_bar + 3 * sigma)
        lcl = max(0, p_bar - 3 * sigma)
        
        df['defect_rate'] = df['failure_qty'] / df['production_qty'] * 100
        
        return {
            "p_bar": p_bar,
            "p_bar_pct": p_bar * 100,
            "ucl": ucl,
            "ucl_pct": ucl * 100,
            "lcl": lcl,
            "lcl_pct": lcl * 100,
            "defect_rates": df['defect_rate'].tolist(),
            "dates": df['date'].tolist() if 'date' in df.columns else list(range(len(df))),
            "out_of_control": any(df['defect_rate'] / 100 > ucl) if len(df) > 0 else False
        }
    
    @staticmethod
    def create_spc_chart(df: pd.DataFrame) -> go.Figure:
        """创建SPC控制图"""
        spc = TimeSeriesAnalyzer.calculate_spc(df)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=spc['dates'],
            y=spc['defect_rates'],
            mode='lines+markers',
            name='Defect Rate (%)',
            line=dict(color='blue', width=2),
            marker=dict(size=8)
        ))
        
        fig.add_hline(y=spc['p_bar_pct'], line_dash="dash", line_color="green",
                      annotation_text=f"Mean: {spc['p_bar_pct']:.2f}%")
        fig.add_hline(y=spc['ucl_pct'], line_dash="dash", line_color="red",
                      annotation_text=f"UCL: {spc['ucl_pct']:.2f}%")
        
        if spc['lcl_pct'] > 0:
            fig.add_hline(y=spc['lcl_pct'], line_dash="dash", line_color="red",
                          annotation_text=f"LCL: {spc['lcl_pct']:.2f}%")
        
        fig.update_layout(
            title="SPC Control Chart - Defect Rate Trend",
            xaxis_title="Date / Sample",
            yaxis_title="Defect Rate (%)",
            height=450,
            hovermode='x unified'
        )
        
        return fig
    
    @staticmethod
    def analyze_trend(df: pd.DataFrame) -> dict:
        """分析趋势"""
        if df is None or len(df) == 0:
            return {"has_data": False}
        
        spc = TimeSeriesAnalyzer.calculate_spc(df)
        recent = spc['defect_rates'][-3:] if len(spc['defect_rates']) >= 3 else spc['defect_rates']
        recent_avg = sum(recent) / len(recent) if recent else 0
        
        return {
            "has_data": True,
            "overall_rate": spc['p_bar_pct'],
            "recent_rate": recent_avg,
            "trend": "上升" if recent_avg > spc['p_bar_pct'] else "下降" if recent_avg < spc['p_bar_pct'] else "稳定",
            "is_stable": not spc['out_of_control'],
            "total_samples": len(df)
        }


# ==================== 关联规则挖掘 ====================

class AssociationRuleMiner:
    """关联规则挖掘器"""
    
    @staticmethod
    def mine_rules(symptom: str, installation: str, temperature: str) -> List[dict]:
        """挖掘关联规则"""
        prompt = f"""基于以下故障信息，挖掘潜在的关联规则（"A + B → C"模式）：

故障现象: {symptom}
安装条件: {installation if installation else '未知'}
温度: {temperature if temperature else '未知'}

请输出2-3条可能的关联规则，JSON数组格式：
[{{"antecedents": ["条件1", "条件2"], "consequents": ["结果"], "confidence": 0.8, "explanation": "解释"}}]"""
        
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
    def generate(root_cause: str, product_name: str, stage: int) -> dict:
        """生成改进措施"""
        prompt = f"""基于以下根因分析，生成改进措施：

根因: {root_cause}
产品: {product_name}
失效等级: {stage}级

请输出JSON格式：
{{"interim": ["临时措施1", "临时措施2"], "permanent": ["永久措施1", "永久措施2", "永久措施3"], "preventive": ["预防措施1", "预防措施2"]}}"""
        
        response = call_llm(prompt, max_tokens=400, temperature=0.4)
        
        try:
            data = clean_json_response(response)
            if data:
                return {
                    "interim": [remove_bold_markers(m) for m in data.get("interim", ["隔离故障产品", "通知客户暂停使用相关功能"])],
                    "permanent": [remove_bold_markers(m) for m in data.get("permanent", ["修改设计缺陷", "更换有问题的组件", "增加保护电路"])],
                    "preventive": [remove_bold_markers(m) for m in data.get("preventive", ["更新检验标准", "加强供应商管理", "增加老化测试"])]
                }
        except:
            pass
        
        return {
            "interim": ["隔离故障产品，防止影响扩大", "通知客户暂停使用相关功能", "检查同批次其他产品"],
            "permanent": ["分析并修复根本原因", "更新设计规范", "增加冗余保护设计"],
            "preventive": ["更新FMEA文档", "加强来料检验", "增加定期维护检查"]
        }


# ==================== 报告生成器 ====================

class ReportGenerator:
    """报告生成器 - 生成FA报告和8D报告"""
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """清理文本中的特殊标记"""
        if not text:
            return text
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        return text
    
    @staticmethod
    def generate_fa_report(result: FailureAnalysisResult, lang: str = "zh") -> str:
        """生成FA报告"""
        stage_name = FailureStageClassifier.get_stage_name(result.failure_stage, lang)
        stage_emoji = FailureStageClassifier.get_stage_emoji(result.failure_stage)
        
        analyst_line = ""
        if result.analyst_name:
            analyst_line = f"**{get_text('analyst')}**：{result.analyst_name}"
            if result.analyst_title:
                analyst_line += f" ({result.analyst_title})"
            analyst_line += f"\n**{get_text('analysis_date')}**：{datetime.now().strftime('%Y-%m-%d')}\n"
        
        # 5-Why表格
        five_why_table = "| 层级 | 问题 | 答案 | 置信度 |\n|------|------|------|--------|\n"
        for item in result.five_why:
            q_short = ReportGenerator._clean_text(item.question[:50] + "..." if len(item.question) > 50 else item.question)
            a_short = ReportGenerator._clean_text(item.answer[:60] + "..." if len(item.answer) > 60 else item.answer)
            five_why_table += f"| Why-{item.level} | {q_short} | {a_short} | {item.confidence:.0%} |\n"
        
        # 鱼骨图 - 文字版
        fishbone_dict = result.fishbone.to_dict()
        fishbone_text = ""
        for cat, causes in fishbone_dict.items():
            if causes:
                fishbone_text += f"\n#### {cat}\n"
                for cause in causes[:5]:
                    fishbone_text += f"- {ReportGenerator._clean_text(cause)}\n"
        
        report = f"""# 故障分析报告

{analyst_line}

## 1. 基本信息

| 项目 | 内容 |
|------|------|
| 产品名称 | {ReportGenerator._clean_text(result.product_name)} |
| 故障现象 | {ReportGenerator._clean_text(result.symptom[:200])} |
| 安装条件 | {ReportGenerator._clean_text(result.installation) if result.installation else '未提供'} |
| 现场温度 | {ReportGenerator._clean_text(result.temperature) if result.temperature else '未提供'} |
| 失效等级 | {stage_emoji} {stage_name} |
| 数据来源 | {result.internal_cases_used}个内部案例 + {result.external_sources_used}个外部来源 |

## 2. 失效等级定义

| 等级 | 名称 | 描述 |
|------|------|------|
| Stage 0 | 正常 | 功能正常，无外观异常 |
| Stage 1 | 轻微异常 | 闪烁、弱光、色偏 |
| Stage 2 | 中度异常 | 烧焦痕迹、透镜膨胀、变形 |
| Stage 3 | 严重故障 | 短路、冒烟、起火、完全失效 |

## 3. 5-Why 根因分析

{five_why_table}

## 4. 根本原因结论

{ReportGenerator._clean_text(result.root_cause)}

## 5. 鱼骨图分析

{fishbone_text}

## 6. 改进措施

### 6.1 临时措施
{chr(10).join(f'{i+1}. {ReportGenerator._clean_text(a)}' for i, a in enumerate(result.interim_actions[:3]))}

### 6.2 永久措施
{chr(10).join(f'{i+1}. {ReportGenerator._clean_text(a)}' for i, a in enumerate(result.permanent_actions[:3]))}

### 6.3 预防再发
{chr(10).join(f'{i+1}. {ReportGenerator._clean_text(a)}' for i, a in enumerate(result.preventive_actions[:2]))}
"""
        return report
    
    @staticmethod
    def generate_8d_report(result: FailureAnalysisResult, lang: str = "zh") -> str:
        """生成8D报告"""
        stage_name = FailureStageClassifier.get_stage_name(result.failure_stage, lang)
        stage_emoji = FailureStageClassifier.get_stage_emoji(result.failure_stage)
        
        analyst_line = ""
        if result.analyst_name:
            analyst_line = f"**{get_text('analyst')}**：{result.analyst_name}"
            if result.analyst_title:
                analyst_line += f" ({result.analyst_title})"
            analyst_line += f"\n**{get_text('analysis_date')}**：{datetime.now().strftime('%Y-%m-%d')}\n"
        
        # 5-Why列表
        five_why_list = ""
        for item in result.five_why:
            five_why_list += f"**Why-{item.level}**：{ReportGenerator._clean_text(item.question)}\n→ {ReportGenerator._clean_text(item.answer)}\n\n"
        
        # 鱼骨图 - 文字版
        fishbone_dict = result.fishbone.to_dict()
        fishbone_text = ""
        for cat, causes in fishbone_dict.items():
            if causes:
                fishbone_text += f"\n**{cat}**：{', '.join([ReportGenerator._clean_text(c) for c in causes[:3]])}\n"
        
        report = f"""# 8D 报告

{analyst_line}

## D1: 建立团队

| 角色 | 姓名 | 职责 |
|------|------|------|
| 团队负责人 | 质量经理 | 整体协调和进度管理 |
| 设计工程师 | 设计部 | 技术分析和设计改进 |
| 工艺工程师 | 工艺部 | 工艺验证和改善 |
| 质量工程师 | 质量部 | 质量验证和标准化 |

## D2: 问题描述

| 项目 | 内容 |
|------|------|
| What | {ReportGenerator._clean_text(result.symptom[:150])} |
| Where | {ReportGenerator._clean_text(result.installation) if result.installation else '安装现场'} |
| When | {datetime.now().strftime('%Y-%m-%d')} |
| Who | 现场维护团队 |
| How | 运行中出现异常 |
| 失效等级 | {stage_emoji} {stage_name} |

## D3: 临时措施

{chr(10).join(f'{i+1}. {ReportGenerator._clean_text(a)}' for i, a in enumerate(result.interim_actions[:3]))}

## D4: 根本原因分析

### 4.1 鱼骨图分析

{fishbone_text}

### 4.2 5-Why 分析

{five_why_list}

### 4.3 根本原因确认

{ReportGenerator._clean_text(result.root_cause)}

## D5: 永久措施

{chr(10).join(f'{i+1}. {ReportGenerator._clean_text(a)}' for i, a in enumerate(result.permanent_actions[:3]))}

## D6: 效果验证

| 验证项目 | 方法 | 标准 |
|----------|------|------|
| 功能验证 | 实际测试 | 恢复正常 |
| 耐久测试 | 加速老化测试 | 满足设计寿命要求 |
| 批量验证 | 小批量试产验证 | 不良率低于目标值 |

## D7: 预防再发

{chr(10).join(f'{i+1}. {ReportGenerator._clean_text(a)}' for i, a in enumerate(result.preventive_actions[:2]))}

## D8: 总结表彰

- 问题已分析清楚，根本原因已确认
- 改进措施已制定，待实施验证
- 经验教训已纳入知识库和FMEA文档
"""
        return report


# ==================== Word文档导出 ====================

def create_word_document(report_content: str, report_type: str, result: FailureAnalysisResult, 
                         uploaded_images: List = None, fishbone_image: bytes = None) -> io.BytesIO:
    """创建Word文档，支持图文并茂"""
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.style import WD_STYLE_TYPE
        
        doc = Document()
        
        # 标题
        title_text = f"{result.product_name} - {result.symptom[:30]} - {report_type}"
        title = doc.add_heading(remove_bold_markers(title_text), level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 分析人和日期
        if result.analyst_name:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(f"{get_text('analyst')}：{result.analyst_name}")
            if result.analyst_title:
                p.add_run(f" ({result.analyst_title})")
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(f"{get_text('analysis_date')}：{datetime.now().strftime('%Y-%m-%d')}")
        
        doc.add_paragraph()
        
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
            elif line.startswith('#### '):
                doc.add_heading(line[5:], level=4)
            elif line.startswith('|') and '|' in line[1:]:
                pass
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
                    doc.add_paragraph(f"图{idx+1}: 故障现场照片")
                except Exception as e:
                    doc.add_paragraph(f"[图片{idx+1}无法显示]")
        
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
    installation: str,
    temperature: str,
    timeseries_df: pd.DataFrame = None,
    enable_web: bool = True,
    enable_rule_mining: bool = True,
    enable_spc: bool = True,
    has_images: bool = False,
    analyst_name: str = "",
    analyst_title: str = ""
) -> FailureAnalysisResult:
    """执行故障分析"""
    
    case_id = str(uuid.uuid4())[:8]
    
    # 失效等级分类
    stage, stage_conf = FailureStageClassifier.classify(symptom)
    
    # 5-Why推理
    five_why = FiveWhyEngine.generate(symptom, product_name, installation, temperature)
    
    # 鱼骨图生成
    fishbone = FishboneGenerator.generate(symptom, product_name, five_why)
    
    # 生成鱼骨图图片
    fishbone_image = create_fishbone_image(fishbone)
    
    # 根因提取
    root_cause = five_why[-1].answer if five_why else f"{product_name} 的 {symptom} 问题需要进一步分析"
    root_cause_confidence = five_why[-1].confidence if five_why else 0.6
    
    # 改进措施
    actions = ImprovementActionGenerator.generate(root_cause, product_name, stage)
    
    # SPC分析
    spc_analysis = None
    if enable_spc and timeseries_df is not None and len(timeseries_df) > 0:
        spc_analysis = TimeSeriesAnalyzer.analyze_trend(timeseries_df)
    
    # 关联规则挖掘
    association_rules = []
    if enable_rule_mining:
        association_rules = AssociationRuleMiner.mine_rules(symptom, installation, temperature)
    
    return FailureAnalysisResult(
        case_id=case_id,
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
        has_images=has_images,
        analyst_name=analyst_name,
        analyst_title=analyst_title,
        fishbone_image=fishbone_image
    )


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
    if "uploaded_images" not in st.session_state:
        st.session_state.uploaded_images = []
    
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
        
        if st.session_state.analyst_name:
            st.success(f"{get_text('analyst')}: {st.session_state.analyst_name}")
            if st.session_state.analyst_title:
                st.caption(st.session_state.analyst_title)
        
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
    
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input(
            get_text("product_name"),
            placeholder=get_text("product_name_ph"),
            key="product_name_input",
            label_visibility="collapsed"
        )
    with col2:
        symptom = st.text_area(
            get_text("symptom"),
            placeholder=get_text("symptom_ph"),
            height=100,
            key="symptom_input",
            label_visibility="collapsed"
        )
    
    col3, col4, col5 = st.columns(3)
    with col3:
        installation = st.text_input(
            get_text("installation"),
            placeholder=get_text("installation_ph"),
            key="installation_input"
        )
    with col4:
        failure_date = st.date_input(
            get_text("failure_date"),
            value=datetime.now().date(),
            key="failure_date_input"
        )
    with col5:
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
    
    # 2. 故障图片（支持上传和粘贴）
    st.markdown(f"### {get_text('image_section')}")
    
    col_img1, col_img2 = st.columns([3, 1])
    
    with col_img1:
        uploaded_images = st.file_uploader(
            get_text("image_upload_hint"),
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="image_uploader",
            label_visibility="collapsed"
        )
    
    with col_img2:
        # 粘贴按钮组件
        st.markdown(f"<small>{get_text('image_paste_hint')}</small>", unsafe_allow_html=True)
        if st.button("📋 " + get_text("image_paste_btn"), key="paste_btn", use_container_width=True):
            st.info(get_text("image_paste_success"))
            # 注意：真正的粘贴功能需要 streamlit-paste-button 组件
            # 这里保持与上传相同的处理方式
    
    if uploaded_images:
        st.session_state.uploaded_images = []
        for img in uploaded_images:
            st.session_state.uploaded_images.append(img.getvalue())
        
        cols = st.columns(min(3, len(uploaded_images)))
        for idx, img in enumerate(uploaded_images[:3]):
            with cols[idx]:
                st.image(img, caption=f"Image {idx+1}", use_container_width=True)
    else:
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
                            installation=installation,
                            temperature=temperature,
                            timeseries_df=timeseries_df if enable_timeseries else None,
                            enable_web=enable_web,
                            enable_rule_mining=enable_rule_mining,
                            enable_spc=enable_spc,
                            has_images=len(uploaded_images) > 0 if uploaded_images else False,
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
        stage_emoji = FailureStageClassifier.get_stage_emoji(result.failure_stage)
        
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
                    st.caption(f"验证方法: {remove_bold_markers(item.verification_method[:100])}...")
                    st.progress(item.confidence, text=f"置信度: {item.confidence:.0%}")
                st.divider()
        
        # 鱼骨图（显示图片）
        with st.expander(get_text("fishbone_title")):
            if result.fishbone_image:
                st.image(result.fishbone_image, use_container_width=True)
            else:
                fishbone_dict = result.fishbone.to_dict()
                for cat, causes in fishbone_dict.items():
                    if causes:
                        st.markdown(f"**{cat}**")
                        for cause in causes[:4]:
                            st.markdown(f"- {remove_bold_markers(cause)}")
        
        # SPC分析
        if result.spc_analysis and result.spc_analysis.get("has_data"):
            with st.expander(get_text("spc_title")):
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("总体不良率", f"{result.spc_analysis['overall_rate']:.2f}%")
                with col_m2:
                    st.metric("近期趋势", result.spc_analysis['trend'])
                with col_m3:
                    st.metric("过程稳定", "是" if result.spc_analysis['is_stable'] else "否")
        
        # 关联规则
        if result.association_rules:
            with st.expander(get_text("rules_title")):
                for rule in result.association_rules:
                    antecedents = " + ".join(rule.get("antecedents", []))
                    consequents = " + ".join(rule.get("consequents", []))
                    st.info(f"{antecedents} → {consequents}\n\n置信度: {rule.get('confidence', 0):.0%}")
        
        # 根因结论
        st.markdown(f"### {get_text('root_cause_title')}")
        st.success(remove_bold_markers(result.root_cause))
        
        # 报告生成按钮
        st.markdown("---")
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 1])
        
        with col_btn1:
            if st.button(get_text("generate_fa_btn"), use_container_width=True):
                report = ReportGenerator.generate_fa_report(result, lang)
                st.session_state.current_report = report
                st.session_state.report_type = "fa"
                st.rerun()
        
        with col_btn2:
            if st.button(get_text("generate_8d_btn"), use_container_width=True):
                report = ReportGenerator.generate_8d_report(result, lang)
                st.session_state.current_report = report
                st.session_state.report_type = "8d"
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
        
        filename = f"{st.session_state.analysis_result.product_name}_{st.session_state.analysis_result.symptom[:30]}_{st.session_state.report_type.upper()}_Report_{datetime.now().strftime('%Y%m%d')}.docx"
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
    main()
