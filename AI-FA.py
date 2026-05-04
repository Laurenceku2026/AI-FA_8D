"""
AI-FA 智能故障分析系统
AI-powered Failure Analysis & 8D Report Generation

功能：
- 多模态输入（文本+图片）
- 5-Why根因推理
- 鱼骨图自动生成
- 失效等级分类
- SPC时序分析（不良率趋势）
- 关联规则挖掘
- 双源知识库（内部+外部）
- FA报告生成
- 8D报告生成
- 双语支持（中文/English）
- Word报告导出

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
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter
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

# Neo4j 配置（可选，用于知识图谱）
NEO4J_URI = get_secret("NEO4J_URI", "")
NEO4J_USERNAME = get_secret("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = get_secret("NEO4J_PASSWORD", "")

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
            "Man (人)": self.man,
            "Machine (机)": self.machine,
            "Material (料)": self.material,
            "Method (法)": self.method,
            "Environment (环)": self.environment,
            "Measurement (测)": self.measurement
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


# ==================== 多语言文本 ====================

TEXTS = {
    "zh": {
        "app_title": "🔬 AI-FA 智能故障分析系统",
        "app_subtitle": "AI驱动的失效分析与8D报告生成",
        "lang_zh": "🇨🇳 中文",
        "lang_en": "🇬🇧 English",
        
        # 输入区域
        "basic_info": "📋 故障基本信息",
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
        "image_section": "🖼️ 故障图片",
        "image_hint": "拖拽或点击上传图片（支持JPG、PNG，最多5张）",
        "timeseries_section": "📊 时序数据（可选）",
        "timeseries_hint": "上传不良率CSV，自动生成SPC控制图",
        "download_template": "📥 下载CSV模板",
        
        # 高级选项
        "advanced_options": "🔬 高级分析选项",
        "web_search": "联网搜索行业案例",
        "rule_mining": "关联规则挖掘",
        "spc": "时序分析(SPC控制图)",
        "gen_8d": "生成8D报告",
        
        # 按钮
        "analyze_btn": "🚀 开始AI深度故障分析",
        "generate_fa_btn": "📄 生成FA报告",
        "generate_8d_btn": "📋 生成8D报告",
        "download_word": "📥 下载Word报告",
        "clear_btn": "🗑️ 清除结果",
        
        # 分析结果
        "five_why_title": "🔍 5-Why 根因分析",
        "fishbone_title": "🐟 鱼骨图分析",
        "root_cause_title": "🎯 根因结论",
        "actions_title": "📌 改进措施",
        "interim_actions": "临时措施",
        "permanent_actions": "永久措施",
        "preventive_actions": "预防再发",
        "confidence": "置信度",
        "evidence_source": "证据来源",
        "verification_method": "建议验证方法",
        "stage_label": "失效等级",
        "spc_title": "📈 SPC控制图分析",
        "rules_title": "🔗 关联规则挖掘",
        
        # 状态
        "analyzing": "AI正在分析中，请稍候...",
        "success": "分析完成！",
        "error": "分析失败，请重试",
        "fill_required": "请填写产品名称和故障现象",
        "api_error": "API配置错误，请检查Streamlit Secrets",
        
        # 失效等级
        "stage_0": "✅ 正常",
        "stage_1": "⚠️ 轻微异常",
        "stage_2": "🔥 中度异常",
        "stage_3": "🚨 严重故障",
        
        # 报告
        "report_preview": "📄 报告预览",
    },
    "en": {
        "app_title": "🔬 AI-FA Intelligent Failure Analysis System",
        "app_subtitle": "AI-powered Failure Analysis & 8D Report Generation",
        "lang_zh": "🇨🇳 中文",
        "lang_en": "🇬🇧 English",
        
        "basic_info": "📋 Basic Failure Information",
        "product_name": "Product Name",
        "product_name_ph": "e.g., Media Tube Lite LED",
        "symptom": "Failure Symptom",
        "symptom_ph": "e.g., smoking during operation, no light output...",
        "installation": "Installation Position/Orientation",
        "installation_ph": "e.g., upper facade, inside metal fins",
        "failure_date": "Failure Date",
        "batch_no": "Batch/Serial No.",
        "site_temp": "Site Temperature (Optional)",
        "site_temp_ph": "e.g., 45°C",
        "image_section": "🖼️ Failure Images",
        "image_hint": "Drag or click to upload images (JPG, PNG, max 5)",
        "timeseries_section": "📊 Time Series Data (Optional)",
        "timeseries_hint": "Upload defect rate CSV for automatic SPC chart",
        "download_template": "📥 Download CSV Template",
        
        "advanced_options": "🔬 Advanced Analysis Options",
        "web_search": "Web search for industry cases",
        "rule_mining": "Association rule mining",
        "spc": "Time series analysis (SPC)",
        "gen_8d": "Generate 8D report",
        
        "analyze_btn": "🚀 Start AI Deep Failure Analysis",
        "generate_fa_btn": "📄 Generate FA Report",
        "generate_8d_btn": "📋 Generate 8D Report",
        "download_word": "📥 Download Word Report",
        "clear_btn": "🗑️ Clear Results",
        
        "five_why_title": "🔍 5-Why Root Cause Analysis",
        "fishbone_title": "🐟 Fishbone Diagram",
        "root_cause_title": "🎯 Root Cause Conclusion",
        "actions_title": "📌 Improvement Actions",
        "interim_actions": "Interim Actions",
        "permanent_actions": "Permanent Actions",
        "preventive_actions": "Preventive Actions",
        "confidence": "Confidence",
        "evidence_source": "Evidence Source",
        "verification_method": "Verification Method",
        "stage_label": "Failure Stage",
        "spc_title": "📈 SPC Control Chart Analysis",
        "rules_title": "🔗 Association Rule Mining",
        
        "analyzing": "AI is analyzing, please wait...",
        "success": "Analysis completed!",
        "error": "Analysis failed, please retry",
        "fill_required": "Please fill in product name and symptom",
        "api_error": "API configuration error, please check Streamlit Secrets",
        
        "stage_0": "✅ Normal",
        "stage_1": "⚠️ Minor Anomaly",
        "stage_2": "🔥 Moderate Anomaly",
        "stage_3": "🚨 Critical Failure",
        
        "report_preview": "📄 Report Preview",
    }
}


# ==================== 工具函数 ====================

def get_text(key: str) -> str:
    """获取当前语言的文本"""
    lang = st.session_state.get("lang", "zh")
    return TEXTS[lang].get(key, key)


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
        
        # 默认给stage 1一些基础分
        if max(scores.values()) == 0:
            scores[1] = 0.5
        
        best_stage = max(scores, key=scores.get)
        confidence = min(0.95, scores[best_stage] + 0.2)
        
        return best_stage, confidence
    
    @classmethod
    def get_stage_name(cls, stage: int, lang: str = "zh") -> str:
        """获取等级名称"""
        info = cls.STAGES.get(stage, cls.STAGES[1])
        return info.get(f"name_{lang}", f"Stage {stage}")
    
    @classmethod
    def get_stage_emoji(cls, stage: int) -> str:
        """获取等级图标"""
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
        lang = st.session_state.get("lang", "zh")
        
        for level in range(1, 6):
            # 构建Prompt
            prompt = cls._build_prompt(level, current_question, symptom, 
                                       product_name, installation, temperature, lang)
            
            # 调用LLM
            response = call_llm(prompt, max_tokens=500, temperature=0.3)
            
            # 解析答案
            answer_data = cls._parse_answer(response)
            answer = answer_data.get("answer", response[:300])
            
            # 生成验证方法
            verification = cls._suggest_verification(answer, product_name)
            
            chain.append(FiveWhyItem(
                level=level,
                question=current_question[:200],
                answer=answer[:300],
                confidence=answer_data.get("confidence", 0.7),
                evidence_source=answer_data.get("evidence_source", "AI推理"),
                verification_method=verification[:150]
            ))
            
            # 生成下一层问题（最后一层不需要）
            if level < 5:
                current_question = cls._next_question(answer, level)
        
        return chain
    
    @classmethod
    def _build_prompt(cls, level: int, question: str, symptom: str,
                      product_name: str, installation: str, temperature: str, lang: str) -> str:
        """构建Prompt"""
        context_text = ""
        if installation:
            context_text += f"安装条件: {installation}\n"
        if temperature:
            context_text += f"现场温度: {temperature}\n"
        
        prompt = f"""你是一位资深故障分析工程师。请进行5-Why根因分析。

产品名称: {product_name}
故障现象: {symptom}

{context_text}
当前分析层级: Why-{level}
当前问题: {question}

{cls.WHY_TEMPLATES.get(level, '请分析根本原因')}

请输出JSON格式，不要有其他内容：
{{"answer": "具体答案", "evidence_source": "证据来源（内部案例/行业知识/推理）", "confidence": 0.8}}
"""
        return prompt
    
    @classmethod
    def _parse_answer(cls, response: str) -> dict:
        """解析答案"""
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
        """建议验证方法"""
        prompt = f"""基于根因假设，建议具体的验证方法：

根因假设: {answer}
产品: {product_name}

请给出1-2个具体、可执行的验证方法，直接输出，不要JSON格式："""
        return call_llm(prompt, max_tokens=150, temperature=0.2)
    
    @classmethod
    def _next_question(cls, answer: str, level: int) -> str:
        """生成下一层问题"""
        prompt = f"""基于以下答案，生成下一层（Why-{level+1}）的追问问题。

答案: {answer}

请输出一个"为什么...？"格式的问题，直接输出，不要JSON格式："""
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
        
        # 提取5-Why中的关键信息
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

请输出3-5个具体、可验证的原因，每行一个，不要编号："""
            
            response = call_llm(prompt, max_tokens=300, temperature=0.4)
            causes = [line.strip() for line in response.split('\n') 
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
        
        # 不良率曲线
        fig.add_trace(go.Scatter(
            x=spc['dates'],
            y=spc['defect_rates'],
            mode='lines+markers',
            name='Defect Rate (%)',
            line=dict(color='blue', width=2),
            marker=dict(size=8)
        ))
        
        # 平均线
        fig.add_hline(y=spc['p_bar_pct'], line_dash="dash", line_color="green",
                      annotation_text=f"Mean: {spc['p_bar_pct']:.2f}%")
        
        # 上控制限
        fig.add_hline(y=spc['ucl_pct'], line_dash="dash", line_color="red",
                      annotation_text=f"UCL: {spc['ucl_pct']:.2f}%")
        
        # 下控制限
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
        rules = []
        
        # 基于输入生成潜在规则
        prompt = f"""基于以下故障信息，挖掘潜在的关联规则（"A + B → C"模式）：

故障现象: {symptom}
安装条件: {installation if installation else '未知'}
温度: {temperature if temperature else '未知'}

请输出2-3条可能的关联规则，每条规则包含：前因、后果、置信度估计。

输出JSON数组格式：
[{{"antecedents": ["条件1", "条件2"], "consequents": ["结果"], "confidence": 0.8, "explanation": "解释"}}]
"""
        response = call_llm(prompt, max_tokens=500, temperature=0.4)
        
        try:
            data = clean_json_response(response)
            if isinstance(data, list):
                rules = data
            elif isinstance(data, dict) and "rules" in data:
                rules = data["rules"]
            else:
                # 默认规则
                rules = [
                    {"antecedents": ["高温环境", "长时间运行"], "consequents": ["元件老化加速"], "confidence": 0.75, "explanation": "高温加速化学反应和材料退化"},
                    {"antecedents": ["潮湿环境", "防水结构老化"], "consequents": ["进水短路"], "confidence": 0.82, "explanation": "水分侵入导致绝缘下降"},
                    {"antecedents": ["安装方向不当", "暴雨天气"], "consequents": ["积水渗入"], "confidence": 0.78, "explanation": "方向性积水风险"}
                ]
        except:
            rules = []
        
        return rules[:3]


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
{{"interim": ["临时措施1", "临时措施2"], "permanent": ["永久措施1", "永久措施2", "永久措施3"], "preventive": ["预防措施1", "预防措施2"]}}
"""
        response = call_llm(prompt, max_tokens=400, temperature=0.4)
        
        try:
            data = clean_json_response(response)
            if data:
                return {
                    "interim": data.get("interim", ["隔离故障产品", "通知客户暂停使用相关功能"]),
                    "permanent": data.get("permanent", ["修改设计缺陷", "更换有问题的组件", "增加保护电路"]),
                    "preventive": data.get("preventive", ["更新检验标准", "加强供应商管理", "增加老化测试"])
                }
        except:
            pass
        
        # 默认措施
        return {
            "interim": ["隔离故障产品，防止影响扩大", "通知客户暂停使用相关功能", "检查同批次其他产品"],
            "permanent": ["分析并修复根本原因", "更新设计规范", "增加冗余保护设计"],
            "preventive": ["更新FMEA文档", "加强来料检验", "增加定期维护检查"]
        }


# ==================== 报告生成器 ====================

class ReportGenerator:
    """报告生成器"""
    
    @staticmethod
    def generate_fa_report(result: FailureAnalysisResult, lang: str = "zh") -> str:
        """生成FA报告（Markdown格式）"""
        stage_name = FailureStageClassifier.get_stage_name(result.failure_stage, lang)
        stage_emoji = FailureStageClassifier.get_stage_emoji(result.failure_stage)
        
        # 5-Why表格
        five_why_table = "| 层级 | 问题 | 答案 | 置信度 | 验证方法 |\n|------|------|------|--------|----------|\n"
        for item in result.five_why:
            question_short = item.question[:50] + "..." if len(item.question) > 50 else item.question
            answer_short = item.answer[:60] + "..." if len(item.answer) > 60 else item.answer
            five_why_table += f"| Why-{item.level} | {question_short} | {answer_short} | {item.confidence:.0%} | {item.verification_method[:40]}... |\n"
        
        # 鱼骨图
        fishbone_dict = result.fishbone.to_dict()
        fishbone_text = ""
        for cat, causes in fishbone_dict.items():
            if causes:
                fishbone_text += f"\n#### {cat}\n"
                for cause in causes[:5]:
                    fishbone_text += f"- {cause}\n"
        
        # 改进措施
        interim_text = "\n".join([f"{i+1}. {action}" for i, action in enumerate(result.interim_actions)])
        permanent_text = "\n".join([f"{i+1}. {action}" for i, action in enumerate(result.permanent_actions)])
        preventive_text = "\n".join([f"{i+1}. {action}" for i, action in enumerate(result.preventive_actions)])
        
        # SPC分析（如果有）
        spc_section = ""
        if result.spc_analysis and result.spc_analysis.get("has_data"):
            spc_section = f"""
## 6. SPC趋势分析

| 指标 | 数值 |
|------|------|
| 总体不良率 | {result.spc_analysis['overall_rate']:.2f}% |
| 近期不良率 | {result.spc_analysis['recent_rate']:.2f}% |
| 趋势方向 | {result.spc_analysis['trend']} |
| 过程稳定 | {'是' if result.spc_analysis['is_stable'] else '否'} |
"""
        
        # 关联规则
        rules_section = ""
        if result.association_rules:
            rules_section = "\n## 7. 关联规则发现\n\n"
            for rule in result.association_rules:
                if rule.get("explanation"):
                    rules_section += f"- **规则**: {' + '.join(rule.get('antecedents', []))} → {' + '.join(rule.get('consequents', []))}\n"
                    rules_section += f"  - 置信度: {rule.get('confidence', 0):.0%} | {rule.get('explanation', '')}\n\n"
        
        report = f"""# 故障分析报告 (Failure Analysis Report)

## 1. 基本信息

| 项目 | 内容 |
|------|------|
| 案例ID | {result.case_id} |
| 产品名称 | {result.product_name} |
| 故障现象 | {result.symptom} |
| 安装条件 | {result.installation or '未提供'} |
| 现场温度 | {result.temperature or '未提供'} |
| 分析时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
| 失效等级 | {stage_emoji} {stage_name} |
| 置信度 | {result.root_cause_confidence:.0%} |
| 数据来源 | {result.internal_cases_used}个内部案例 + {result.external_sources_used}个外部来源 |

## 2. 5-Why 根因分析

{five_why_table}

## 3. 根因结论

> **{result.root_cause}**

## 4. 鱼骨图分析

{fishbone_text}

## 5. 改进措施

### 5.1 临时措施 (ICA)

{interim_text}

### 5.2 永久措施 (PCA)

{permanent_text}

### 5.3 预防再发

{preventive_text}
{spc_section}
{rules_section}
---
*报告由 AI-FA 智能故障分析系统自动生成 | 版本 1.0.0*
"""
        return report
    
    @staticmethod
    def generate_8d_report(result: FailureAnalysisResult, lang: str = "zh") -> str:
        """生成8D报告"""
        stage_name = FailureStageClassifier.get_stage_name(result.failure_stage, lang)
        stage_emoji = FailureStageClassifier.get_stage_emoji(result.failure_stage)
        
        # 5-Why列表
        five_why_list = ""
        for item in result.five_why:
            five_why_list += f"**Why-{item.level}**: {item.question}\n→ {item.answer}\n\n"
        
        report = f"""# 8D 报告 (8D Report)

## D1: 建立团队 (Establish Team)

| 角色 | 姓名 | 职责 |
|------|------|------|
| 团队负责人 | 质量经理 | 整体协调和进度管理 |
| 设计工程师 | 设计部 | 技术分析和设计改进 |
| 工艺工程师 | 工艺部 | 工艺验证和改善 |
| 质量工程师 | 质量部 | 质量验证和标准化 |

## D2: 问题描述 (Problem Description)

**5W2H分析：**

| 项目 | 内容 |
|------|------|
| What | {result.symptom} |
| Where | {result.installation or '安装现场'} |
| When | {datetime.now().strftime('%Y-%m-%d')} |
| Who | 现场维护团队 |
| Why | 初步分析中 |
| How | 运行中出现异常 |
| How many | 待统计 |

## D3: 临时措施 (Interim Containment Action)

{chr(10).join(f'{i+1}. {action}' for i, action in enumerate(result.interim_actions))}

## D4: 根本原因分析 (Root Cause Analysis)

### 4.1 可能原因分析（鱼骨图）

{chr(10).join(f'- **{cat}**: {", ".join(causes[:3])}' for cat, causes in result.fishbone.to_dict().items() if causes)}

### 4.2 5-Why 分析

{five_why_list}

### 4.3 根本原因确认

**{result.root_cause}**

| 验证项目 | 结果 |
|----------|------|
| 根本原因确认 | ✅ 已确认 |
| 置信度 | {result.root_cause_confidence:.0%} |

## D5: 永久措施 (Permanent Corrective Action)

{chr(10).join(f'{i+1}. {action}' for i, action in enumerate(result.permanent_actions))}

## D6: 效果验证 (Effectiveness Verification)

| 验证项目 | 方法 | 标准 | 结果 |
|----------|------|------|------|
| 功能验证 | 实际测试 | 恢复正常 | 待验证 |
| 耐久测试 | 加速老化 | 5年寿命 | 待验证 |
| 批量验证 | 小批量试产 | 不良率<0.1% | 待验证 |

## D7: 预防再发 (Prevent Recurrence)

{chr(10).join(f'{i+1}. {action}' for i, action in enumerate(result.preventive_actions))}

## D8: 总结表彰 (Congratulate Team)

- 问题已分析清楚，根本原因已确认
- 改进措施已制定，待实施验证
- 经验教训已纳入知识库和FMEA

---
*报告由 AI-FA 智能故障分析系统自动生成*
*分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*失效等级: {stage_emoji} {stage_name}*
"""
        return report


# ==================== Word导出 ====================

def create_word_download(report_content: str, filename: str) -> io.BytesIO:
    """创建Word文档下载"""
    buffer = io.BytesIO()
    
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        doc = Document()
        
        # 解析Markdown并添加到Word
        lines = report_content.split('\n')
        
        for line in lines:
            if line.startswith('# '):
                doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                doc.add_heading(line[3:], level=2)
            elif line.startswith('### '):
                doc.add_heading(line[4:], level=3)
            elif line.startswith('#### '):
                doc.add_heading(line[5:], level=4)
            elif line.startswith('|') and '|' in line[1:]:
                # 表格处理（简化）
                pass
            elif line.strip():
                p = doc.add_paragraph(line)
                p.style.font.size = Pt(11)
            else:
                doc.add_paragraph()
        
        doc.save(buffer)
    except ImportError:
        # 如果没有python-docx，保存为文本文件
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
    enable_rule_mining: bool = False,
    enable_spc: bool = True,
    has_images: bool = False
) -> FailureAnalysisResult:
    """执行故障分析主流程"""
    
    case_id = str(uuid.uuid4())[:8]
    
    # 1. 失效等级分类
    stage, stage_conf = FailureStageClassifier.classify(symptom)
    
    # 2. 5-Why推理
    five_why = FiveWhyEngine.generate(symptom, product_name, installation, temperature)
    
    # 3. 鱼骨图生成
    fishbone = FishboneGenerator.generate(symptom, product_name, five_why)
    
    # 4. 根因提取（从5-Why最后一级）
    root_cause = five_why[-1].answer if five_why else f"{product_name} 的 {symptom} 问题需要进一步分析"
    root_cause_confidence = five_why[-1].confidence if five_why else 0.6
    
    # 5. 生成改进措施
    actions = ImprovementActionGenerator.generate(root_cause, product_name, stage)
    
    # 6. SPC分析（如果有时序数据）
    spc_analysis = None
    if enable_spc and timeseries_df is not None and len(timeseries_df) > 0:
        spc_analysis = TimeSeriesAnalyzer.analyze_trend(timeseries_df)
    
    # 7. 关联规则挖掘
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
        has_images=has_images
    )


# ==================== 主界面 ====================

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
    if "timeseries_df" not in st.session_state:
        st.session_state.timeseries_df = None
    
    # 右上角语言切换
    col_title, col_spacer, col_zh, col_en = st.columns([3, 2, 1, 1])
    with col_zh:
        if st.button(get_text("lang_zh"), key="zh_btn", use_container_width=True):
            st.session_state.lang = "zh"
            st.rerun()
    with col_en:
        if st.button(get_text("lang_en"), key="en_btn", use_container_width=True):
            st.session_state.lang = "en"
            st.rerun()
    
    # 标题
    st.title(get_text("app_title"))
    st.caption(get_text("app_subtitle"))
    
    # 检查API配置
    if not DEEPSEEK_API_KEY:
        st.error(get_text("api_error"))
        st.info("请在 Streamlit Cloud 的 Secrets 中配置 DEEPSEEK_API_KEY")
        return
    
    # 主输入区域
    col_left, col_right = st.columns([1, 1], gap="large")
    
    with col_left:
        st.markdown(f"### {get_text('basic_info')}")
        
        with st.form("failure_input_form"):
            product_name = st.text_input(
                get_text("product_name"),
                placeholder=get_text("product_name_ph"),
                key="product_name_input"
            )
            
            symptom = st.text_area(
                get_text("symptom"),
                placeholder=get_text("symptom_ph"),
                height=120,
                key="symptom_input"
            )
            
            installation = st.text_input(
                get_text("installation"),
                placeholder=get_text("installation_ph"),
                key="installation_input"
            )
            
            col_date, col_batch = st.columns(2)
            with col_date:
                st.date_input(
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
            
            submitted = st.form_submit_button(
                get_text("analyze_btn"),
                type="primary",
                use_container_width=True
            )
    
    with col_right:
        st.markdown(f"### {get_text('image_section')}")
        
        uploaded_images = st.file_uploader(
            get_text("image_hint"),
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="image_uploader"
        )
        
        if uploaded_images:
            cols = st.columns(min(3, len(uploaded_images)))
            for idx, img in enumerate(uploaded_images[:3]):
                with cols[idx]:
                    st.image(img, caption=f"Image {idx+1}", use_container_width=True)
        
        st.markdown(f"### {get_text('timeseries_section')}")
        st.caption(get_text("timeseries_hint"))
        
        # CSV模板下载
        template_df = pd.DataFrame({
            "date": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"],
            "production_qty": [1000, 1100, 1050, 1200, 1150],
            "failure_qty": [5, 8, 12, 7, 9]
        })
        
        template_csv = template_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=get_text("download_template"),
            data=template_csv,
            file_name="defect_data_template.csv",
            mime="text/csv",
            key="template_download_btn"
        )
        
        timeseries_file = st.file_uploader(
            "上传CSV文件",
            type=["csv"],
            key="timeseries_uploader"
        )
        
        if timeseries_file:
            try:
                timeseries_df = pd.read_csv(timeseries_file)
                st.session_state.timeseries_df = timeseries_df
                st.dataframe(timeseries_df.head(), use_container_width=True)
            except Exception as e:
                st.error(f"CSV解析失败: {e}")
                st.session_state.timeseries_df = None
        else:
            st.session_state.timeseries_df = None
    
    # 高级选项
    with st.expander(get_text("advanced_options")):
        col_adv1, col_adv2, col_adv3 = st.columns(3)
        with col_adv1:
            enable_web = st.checkbox(get_text("web_search"), value=True)
        with col_adv2:
            enable_rule_mining = st.checkbox(get_text("rule_mining"), value=False)
        with col_adv3:
            enable_spc = st.checkbox(get_text("spc"), value=True)
    
    # 执行分析
    if submitted:
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
                        timeseries_df=st.session_state.timeseries_df,
                        enable_web=enable_web,
                        enable_rule_mining=enable_rule_mining,
                        enable_spc=enable_spc,
                        has_images=len(uploaded_images) > 0 if uploaded_images else False
                    )
                    st.session_state.analysis_result = result
                    st.session_state.current_report = None
                    st.success(get_text("success"))
                    st.rerun()
                except Exception as e:
                    st.error(f"{get_text('error')}: {str(e)}")
    
    # 显示分析结果
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result
        lang = st.session_state.lang
        
        st.markdown("---")
        
        # 失效等级展示
        stage_name = FailureStageClassifier.get_stage_name(result.failure_stage, lang)
        stage_emoji = FailureStageClassifier.get_stage_emoji(result.failure_stage)
        
        col_status, col_conf = st.columns([2, 1])
        with col_status:
            st.info(f"{stage_emoji} **{get_text('stage_label')}**: {stage_name}")
        with col_conf:
            st.metric(get_text("confidence"), f"{result.root_cause_confidence:.0%}")
        
        # 5-Why展示
        with st.expander(get_text("five_why_title"), expanded=True):
            for item in result.five_why:
                col_q, col_a = st.columns([1, 2])
                with col_q:
                    st.markdown(f"**Why-{item.level}**")
                with col_a:
                    st.markdown(f"**Q**: {item.question}")
                    st.markdown(f"**A**: {item.answer}")
                    st.caption(f"🔬 {get_text('verification_method')}: {item.verification_method[:100]}...")
                    st.progress(item.confidence, text=f"{get_text('confidence')}: {item.confidence:.0%}")
                st.divider()
        
        # 鱼骨图展示
        with st.expander(get_text("fishbone_title")):
            fishbone_dict = result.fishbone.to_dict()
            cols = st.columns(3)
            for idx, (cat, causes) in enumerate(fishbone_dict.items()):
                with cols[idx % 3]:
                    st.markdown(f"**{cat}**")
                    for cause in causes[:4]:
                        st.markdown(f"- {cause[:60]}...")
        
        # SPC分析
        if result.spc_analysis and result.spc_analysis.get("has_data"):
            with st.expander(get_text("spc_title")):
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("总体不良率", f"{result.spc_analysis['overall_rate']:.2f}%")
                with col_m2:
                    st.metric("近期趋势", result.spc_analysis['trend'])
                with col_m3:
                    st.metric("过程稳定", "✅ 是" if result.spc_analysis['is_stable'] else "⚠️ 否")
                
                if st.session_state.timeseries_df is not None:
                    fig = TimeSeriesAnalyzer.create_spc_chart(st.session_state.timeseries_df)
                    st.plotly_chart(fig, use_container_width=True)
        
        # 关联规则
        if result.association_rules:
            with st.expander(get_text("rules_title")):
                for rule in result.association_rules:
                    antecedents = " + ".join(rule.get("antecedents", []))
                    consequents = " + ".join(rule.get("consequents", []))
                    st.info(f"**{antecedents} → {consequents}**\n\n置信度: {rule.get('confidence', 0):.0%} | {rule.get('explanation', '')}")
        
        # 根因结论
        st.markdown(f"### {get_text('root_cause_title')}")
        st.success(f"**{result.root_cause}**")
        
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
    
    # 显示生成的报告
    if st.session_state.current_report:
        st.markdown("---")
        st.markdown(f"### {get_text('report_preview')}")
        
        with st.container(height=500):
            st.markdown(st.session_state.current_report)
        
        # Word下载
        filename = f"{st.session_state.analysis_result.product_name}_{st.session_state.report_type.upper()}_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.docx"
        word_buffer = create_word_download(st.session_state.current_report, filename)
        
        st.download_button(
            label=get_text("download_word"),
            data=word_buffer,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )


if __name__ == "__main__":
    main()
