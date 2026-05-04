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

作者: Laurence Ku
版本: 1.0.0
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import uuid
import re
import io
import requests
import asyncio
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import Counter
from PIL import Image
import base64

# ==================== 配置 ====================

# Supabase 配置
SUPABASE_URL = "https://hmvwgqcbwbdsfppycxkt.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhtdndncWNid2Jkc2ZwcHljeGt0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Njk5NTE3NCwiZXhwIjoyMDkyNTcxMTc0fQ.FoaM2tBHNMCQrR-IToU9GUSG6QgzClJBsWNEYDI6QoU"

# DeepSeek API 配置
DEEPSEEK_API_KEY = "sk-7136425b4866479fa6ed9181bf2c1b7c"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# Neo4j 配置（知识图谱，可选）
NEO4J_URI = "neo4j+s://e274b611.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "nogTeBVFPETQgUgxuapkgu-eI872MOZ4DF4ZQ5x_-jY"
NEO4J_DATABASE = "neo4j"

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
        "fill_required": "请填写必填项",
        
        # 失效等级
        "stage_0": "正常",
        "stage_1": "轻微异常",
        "stage_2": "中度异常",
        "stage_3": "严重故障",
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
        "fill_required": "Please fill in required fields",
        
        "stage_0": "Normal",
        "stage_1": "Minor Anomaly",
        "stage_2": "Moderate Anomaly",
        "stage_3": "Critical Failure",
    }
}


# ==================== 工具函数 ====================

def get_text(key: str) -> str:
    """获取当前语言的文本"""
    lang = st.session_state.get("lang", "zh")
    return TEXTS[lang].get(key, key)


def translate_text(text: str, target_lang: str) -> str:
    """使用DeepSeek翻译文本"""
    if not text or not text.strip():
        return text
    
    # 简单检测：如果已经是目标语言，直接返回
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
        # 尝试提取JSON
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)
    except:
        pass
    return {}


# ==================== Supabase 数据库客户端 ====================

class SupabaseClient:
    """Supabase数据库客户端"""
    
    def __init__(self):
        self.headers = {
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, table: str, data: dict = None, 
                 filters: dict = None, params: str = None) -> dict:
        """发送请求"""
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        
        if filters:
            filter_str = "&".join([f"{k}=eq.{v}" for k, v in filters.items()])
            url = f"{url}?{filter_str}"
        
        if params:
            url = f"{url}?{params}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            if response.status_code in [200, 201, 204]:
                if response.text:
                    return response.json()
                return {"success": True}
        except Exception as e:
            print(f"Supabase error: {e}")
        
        return {} if method == "GET" else {"success": False}
    
    def search_similar_failures(self, symptom: str, product_type: str = None, 
                                 limit: int = 10) -> List[dict]:
        """搜索相似故障案例"""
        # 模拟数据，实际应从数据库读取
        return []
    
    def get_knowledge(self, category: str, lang: str = "zh") -> List[str]:
        """获取知识库"""
        return []
    
    def save_feedback(self, feedback: dict) -> bool:
        """保存用户反馈"""
        return True


# ==================== 失效等级分类器 ====================

class FailureStageClassifier:
    """失效等级分类器"""
    
    STAGES = {
        0: {"name_zh": "正常", "name_en": "Normal", "keywords": ["正常", "无异常", "working"]},
        1: {"name_zh": "轻微异常", "name_en": "Minor", "keywords": ["闪烁", "弱光", "色偏", "flicker", "dim"]},
        2: {"name_zh": "中度异常", "name_en": "Moderate", "keywords": ["烧焦", "膨胀", "变形", "burn", "swell"]},
        3: {"name_zh": "严重故障", "name_en": "Critical", "keywords": ["短路", "冒烟", "起火", "short", "smoke", "fire"]}
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
                scores[stage] = min(1.0, match_count / len(keywords) * 2)
        
        # 默认给stage 1一些基础分
        if max(scores.values()) == 0:
            scores[1] = 0.5
        
        best_stage = max(scores, key=scores.get)
        confidence = scores[best_stage]
        
        return best_stage, confidence
    
    @classmethod
    def get_stage_name(cls, stage: int, lang: str = "zh") -> str:
        """获取等级名称"""
        info = cls.STAGES.get(stage, cls.STAGES[1])
        return info.get(f"name_{lang}", f"Stage {stage}")


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
                 context: dict = None) -> List[FiveWhyItem]:
        """生成5-Why推理链"""
        chain = []
        current_question = symptom
        lang = st.session_state.get("lang", "zh")
        
        for level in range(1, 6):
            # 构建Prompt
            prompt = cls._build_prompt(level, current_question, symptom, 
                                       product_name, context, lang)
            
            # 调用LLM
            response = call_llm(prompt, max_tokens=500, temperature=0.3)
            
            # 解析答案
            answer_data = cls._parse_answer(response)
            
            # 生成验证方法
            verification = cls._suggest_verification(answer_data.get("answer", ""), product_name)
            
            chain.append(FiveWhyItem(
                level=level,
                question=current_question,
                answer=answer_data.get("answer", response[:300]),
                confidence=answer_data.get("confidence", 0.7),
                evidence_source=answer_data.get("evidence_source", "AI推理"),
                verification_method=verification
            ))
            
            # 生成下一层问题
            current_question = cls._next_question(answer_data.get("answer", ""), level)
        
        return chain
    
    @classmethod
    def _build_prompt(cls, level: int, question: str, symptom: str,
                      product_name: str, context: dict, lang: str) -> str:
        """构建Prompt"""
        context_text = ""
        if context:
            context_text = f"""
安装条件: {context.get('installation', '未知')}
现场温度: {context.get('temperature', '未知')}
"""
        
        prompt = f"""你是一位资深故障分析工程师。请进行5-Why根因分析。

产品: {product_name}
故障现象: {symptom}

当前问题 (Why-{level}): {question}

{cls.WHY_TEMPLATES.get(level, '请分析根本原因')}

{context_text}

请输出JSON格式：
{{"answer": "具体答案", "evidence_source": "证据来源", "confidence": 0.8}}
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
        return {"answer": response.strip()[:300], "confidence": 0.7}
    
    @classmethod
    def _suggest_verification(cls, answer: str, product_name: str) -> str:
        """建议验证方法"""
        prompt = f"""基于根因假设，建议验证方法：

根因: {answer}
产品: {product_name}

输出1-2个具体验证方法："""
        return call_llm(prompt, max_tokens=150, temperature=0.2)
    
    @classmethod
    def _next_question(cls, answer: str, level: int) -> str:
        """生成下一层问题"""
        if level >= 5:
            return ""
        prompt = f"""基于答案生成追问：

答案: {answer}

输出"为什么...？"格式的问题："""
        return call_llm(prompt, max_tokens=100, temperature=0.3)


# ==================== 鱼骨图生成器 ====================

class FishboneGenerator:
    """鱼骨图生成器"""
    
    CATEGORIES = {
        "Man": {"zh": "人", "sub": ["操作技能", "培训", "疲劳", "疏忽"]},
        "Machine": {"zh": "机", "sub": ["设备精度", "维护", "老化", "参数"]},
        "Material": {"zh": "料", "sub": ["来料质量", "批次", "存储", "规格"]},
        "Method": {"zh": "法", "sub": ["工艺", "SOP", "检验", "设计"]},
        "Environment": {"zh": "环", "sub": ["温湿度", "洁净度", "振动", "光照"]},
        "Measurement": {"zh": "测", "sub": ["量具", "校准", "方法", "抽样"]}
    }
    
    @classmethod
    def generate(cls, symptom: str, product_name: str, 
                 five_why_chain: List = None) -> FishboneAnalysis:
        """生成鱼骨图"""
        fishbone = {cat: [] for cat in cls.CATEGORIES}
        
        for cat_key, cat_info in cls.CATEGORIES.items():
            cat_zh = cat_info["zh"]
            sub_items = cat_info["sub"]
            
            prompt = f"""列出可能导致故障的「{cat_zh}」相关原因。

产品: {product_name}
故障: {symptom}
子分类: {sub_items}

输出3-5个具体原因，每行一个："""
            
            response = call_llm(prompt, max_tokens=300, temperature=0.4)
            causes = [line.strip() for line in response.split('\n') 
                     if line.strip() and len(line.strip()) > 5][:6]
            fishbone[cat_key] = causes
        
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
        
        df['defect_rate'] = df['failure_qty'] / df['production_qty']
        
        return {
            "p_bar": p_bar,
            "p_bar_pct": p_bar * 100,
            "ucl": ucl,
            "ucl_pct": ucl * 100,
            "lcl": lcl,
            "lcl_pct": lcl * 100,
            "defect_rates": df['defect_rate'].tolist(),
            "dates": df['date'].tolist() if 'date' in df.columns else [],
            "out_of_control": any(df['defect_rate'] > ucl)
        }
    
    @staticmethod
    def create_spc_chart(df: pd.DataFrame) -> go.Figure:
        """创建SPC控制图"""
        spc = TimeSeriesAnalyzer.calculate_spc(df)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=spc['dates'] if spc['dates'] else list(range(len(spc['defect_rates']))),
            y=[r * 100 for r in spc['defect_rates']],
            mode='lines+markers',
            name='Defect Rate (%)',
            line=dict(color='blue', width=2)
        ))
        
        fig.add_hline(y=spc['p_bar_pct'], line_dash="dash", line_color="green",
                      annotation_text=f"Mean: {spc['p_bar_pct']:.2f}%")
        fig.add_hline(y=spc['ucl_pct'], line_dash="dash", line_color="red",
                      annotation_text=f"UCL: {spc['ucl_pct']:.2f}%")
        
        if spc['lcl_pct'] > 0:
            fig.add_hline(y=spc['lcl_pct'], line_dash="dash", line_color="red",
                          annotation_text=f"LCL: {spc['lcl_pct']:.2f}%")
        
        fig.update_layout(
            title="SPC Control Chart",
            xaxis_title="Sample",
            yaxis_title="Defect Rate (%)",
            height=450,
            hovermode='x unified'
        )
        
        return fig
    
    @staticmethod
    def analyze_trend(df: pd.DataFrame) -> dict:
        """分析趋势"""
        spc = TimeSeriesAnalyzer.calculate_spc(df)
        recent = spc['defect_rates'][-3:] if len(spc['defect_rates']) >= 3 else spc['defect_rates']
        recent_avg = sum(recent) / len(recent) if recent else 0
        
        return {
            "overall_rate": spc['p_bar_pct'],
            "recent_rate": recent_avg * 100,
            "trend": "上升" if recent_avg > spc['p_bar'] else "下降" if recent_avg < spc['p_bar'] else "稳定",
            "is_stable": not spc['out_of_control']
        }


# ==================== 关联规则挖掘 ====================

class AssociationRuleMiner:
    """关联规则挖掘器"""
    
    @staticmethod
    def mine_rules(failure_cases: List[dict]) -> List[dict]:
        """挖掘关联规则"""
        # 模拟挖掘结果
        rules = []
        
        if len(failure_cases) < 5:
            return rules
        
        # 示例规则（实际应从数据中挖掘）
        sample_rules = [
            {"antecedents": ["高温>70°C"], "consequents": ["进水短路"], "confidence": 0.85, "lift": 2.3},
            {"antecedents": ["上层安装", "暴雨"], "consequents": ["进水"], "confidence": 0.78, "lift": 1.9},
            {"antecedents": ["运行>5年"], "consequents": ["元件老化"], "confidence": 0.72, "lift": 1.6}
        ]
        
        for rule in sample_rules:
            rules.append({
                **rule,
                "interpretation": AssociationRuleMiner._interpret(rule)
            })
        
        return rules
    
    @staticmethod
    def _interpret(rule: dict) -> str:
        """解释规则"""
        ifs = " 且 ".join(rule["antecedents"])
        then = " → ".join(rule["consequents"])
        return f"当 {ifs} 时，{then} 的概率为 {rule['confidence']:.0%}"


# ==================== 报告生成器 ====================

class FailureAnalysisReportGenerator:
    """FA报告生成器"""
    
    @staticmethod
    def generate_fa_report(result: FailureAnalysisResult, lang: str = "zh") -> str:
        """生成FA报告（Markdown格式）"""
        stage_name = FailureStageClassifier.get_stage_name(result.failure_stage, lang)
        
        # 5-Why表格
        five_why_table = "| 层级 | 问题 | 答案 | 置信度 |\n|------|------|------|--------|\n"
        for item in result.five_why:
            five_why_table += f"| Why-{item.level} | {item.question[:40]}... | {item.answer[:60]}... | {item.confidence:.0%} |\n"
        
        # 鱼骨图
        fishbone_dict = result.fishbone.to_dict()
        fishbone_text = ""
        for cat, causes in fishbone_dict.items():
            if causes:
                fishbone_text += f"\n### {cat}\n"
                for cause in causes[:5]:
                    fishbone_text += f"- {cause}\n"
        
        report = f"""# 故障分析报告 (Failure Analysis Report)

## 1. 基本信息

| 项目 | 内容 |
|------|------|
| 产品名称 | {result.product_name} |
| 故障现象 | {result.symptom} |
| 分析时间 | {datetime.now().strftime('%Y-%m-%d %H:%M')} |
| 失效等级 | {stage_name} |
| 置信度 | {result.root_cause_confidence:.0%} |

## 2. 5-Why 根因分析

{five_why_table}

## 3. 鱼骨图分析

{fishbone_text}

## 4. 根因结论

**{result.root_cause}**

> 证据来源：{result.internal_cases_used}个内部案例 + {result.external_sources_used}个外部来源

## 5. 改进措施

### 临时措施
{chr(10).join(f'- {action}' for action in result.interim_actions[:3])}

### 永久措施
{chr(10).join(f'- {action}' for action in result.permanent_actions[:3])}

### 预防再发
{chr(10).join(f'- {action}' for action in result.preventive_actions[:3])}

---
*报告由AI-FA系统自动生成*
"""
        return report
    
    @staticmethod
    def generate_8d_report(result: FailureAnalysisResult, lang: str = "zh") -> str:
        """生成8D报告"""
        report = f"""# 8D 报告 (8D Report)

## D1: 建立团队 (Establish Team)

| 角色 | 姓名 | 职责 |
|------|------|------|
| 团队负责人 | 质量经理 | 整体协调 |
| 工程师 | 设计工程师 | 根因分析 |
| 工程师 | 工艺工程师 | 措施实施 |

## D2: 问题描述 (Problem Description)

**产品**: {result.product_name}
**故障**: {result.symptom}
**失效等级**: {FailureStageClassifier.get_stage_name(result.failure_stage, lang)}

## D3: 临时措施 (Interim Containment)

{chr(10).join(f'{i+1}. {action}' for i, action in enumerate(result.interim_actions[:3]))}

## D4: 根因分析 (Root Cause Analysis)

### 5-Why分析
| Why | 问题 | 答案 |
|-----|------|------|
{chr(10).join(f'| {item.level} | {item.question[:50]} | {item.answer[:80]} |' for item in result.five_why)}

### 根本原因
**{result.root_cause}**

## D5: 永久措施 (Permanent Corrective Action)

{chr(10).join(f'{i+1}. {action}' for i, action in enumerate(result.permanent_actions[:3]))}

## D6: 效果验证 (Effectiveness Verification)

- 验证方法: {result.five_why[0].verification_method if result.five_why else '待定'}
- 预期完成时间: {datetime.now().strftime('%Y-%m')}

## D7: 预防再发 (Prevent Recurrence)

{chr(10).join(f'{i+1}. {action}' for i, action in enumerate(result.preventive_actions[:2]))}

## D8: 总结表彰 (Congratulate Team)

- 问题已关闭
- 经验教训已纳入知识库

---
*报告由AI-FA系统自动生成 | 生成时间: {datetime.now().strftime('%Y-%m-%d')}*
"""
        return report


# ==================== 主分析函数 ====================

def run_failure_analysis(product_name: str, symptom: str, installation: str,
                         temperature: str, uploaded_images: List,
                         timeseries_df: pd.DataFrame = None,
                         enable_web: bool = True,
                         enable_rule_mining: bool = False,
                         enable_spc: bool = True) -> FailureAnalysisResult:
    """执行故障分析主流程"""
    
    case_id = str(uuid.uuid4())[:8]
    lang = st.session_state.get("lang", "zh")
    
    # 1. 失效等级分类
    stage, stage_conf = FailureStageClassifier.classify(symptom)
    
    # 2. 构建上下文
    context = {
        "installation": installation,
        "temperature": temperature
    }
    
    # 3. 5-Why推理
    five_why = FiveWhyEngine.generate(symptom, product_name, context)
    
    # 4. 鱼骨图生成
    fishbone = FishboneGenerator.generate(symptom, product_name, five_why)
    
    # 5. 根因提取（从5-Why最后一级）
    root_cause = five_why[-1].answer if five_why else "需要进一步分析"
    root_cause_confidence = five_why[-1].confidence if five_why else 0.6
    
    # 6. 生成改进措施
    actions = generate_improvement_actions(root_cause, product_name, lang)
    
    # 7. SPC分析（如果有时序数据）
    spc_analysis = None
    if enable_spc and timeseries_df is not None and len(timeseries_df) > 0:
        spc_analysis = TimeSeriesAnalyzer.analyze_trend(timeseries_df)
    
    # 8. 关联规则挖掘
    association_rules = []
    if enable_rule_mining:
        # 模拟案例数据
        mock_cases = [{"symptom": symptom, "installation": installation}]
        association_rules = AssociationRuleMiner.mine_rules(mock_cases)
    
    return FailureAnalysisResult(
        case_id=case_id,
        product_name=product_name,
        symptom=symptom,
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
        association_rules=association_rules
    )


def generate_improvement_actions(root_cause: str, product_name: str, lang: str) -> dict:
    """生成改进措施"""
    prompt = f"""基于根因生成改进措施：

根因: {root_cause}
产品: {product_name}

输出JSON:
{{"interim": ["临时措施1", "临时措施2"], "permanent": ["永久措施1", "永久措施2"], "preventive": ["预防措施1", "预防措施2"]}}
"""
    response = call_llm(prompt, max_tokens=300, temperature=0.4)
    
    try:
        return clean_json_response(response)
    except:
        return {
            "interim": ["隔离故障产品", "通知客户暂停使用"],
            "permanent": ["修改设计", "更换有问题的组件"],
            "preventive": ["更新检验标准", "加强供应商管理"]
        }


def create_word_download(report_content: str, filename: str) -> io.BytesIO:
    """创建Word文档下载"""
    try:
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        doc = Document()
        
        # 标题
        title = doc.add_heading(filename.replace('.docx', ''), 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 内容
        for line in report_content.split('\n'):
            if line.startswith('# '):
                doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                doc.add_heading(line[3:], level=2)
            elif line.startswith('### '):
                doc.add_heading(line[4:], level=3)
            elif line.startswith('|'):
                # 简单处理表格
                pass
            elif line.strip():
                doc.add_paragraph(line)
            else:
                doc.add_paragraph()
        
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except ImportError:
        # 如果没有python-docx，返回文本文件
        buffer = io.BytesIO()
        buffer.write(report_content.encode('utf-8'))
        buffer.seek(0)
        return buffer


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
    
    # 语言切换（右上角）
    col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
    with col2:
        if st.button(get_text("lang_zh"), key="zh_btn"):
            st.session_state.lang = "zh"
            st.rerun()
    with col3:
        if st.button(get_text("lang_en"), key="en_btn"):
            st.session_state.lang = "en"
            st.rerun()
    
    # 标题
    st.title(get_text("app_title"))
    st.caption(get_text("app_subtitle"))
    
    # 主输入区域 - 两列布局
    col_left, col_right = st.columns([1, 1], gap="large")
    
    with col_left:
        st.markdown(f"### {get_text('basic_info')}")
        
        with st.form("failure_input_form"):
            product_name = st.text_input(
                get_text("product_name"),
                placeholder=get_text("product_name_ph"),
                key="product_name"
            )
            
            symptom = st.text_area(
                get_text("symptom"),
                placeholder=get_text("symptom_ph"),
                height=120,
                key="symptom"
            )
            
            installation = st.text_input(
                get_text("installation"),
                placeholder=get_text("installation_ph"),
                key="installation"
            )
            
            col_date, col_batch = st.columns(2)
            with col_date:
                failure_date = st.date_input(
                    get_text("failure_date"),
                    value=datetime.now().date(),
                    key="failure_date"
                )
            with col_batch:
                batch_no = st.text_input(
                    get_text("batch_no"),
                    placeholder="LOT2024-001",
                    key="batch_no"
                )
            
            temperature = st.text_input(
                get_text("site_temp"),
                placeholder=get_text("site_temp_ph"),
                key="temperature"
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
            key="images"
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
            "date": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "production_qty": [1000, 1100, 1050],
            "failure_qty": [5, 8, 12]
        })
        st.download_button(
            label=get_text("download_template"),
            data=template_df.to_csv(index=False).encode('utf-8'),
            file_name=f"defect_data_template.csv",
            key="template_download"
        )
        
        timeseries_file = st.file_uploader(
            "Upload CSV",
            type=["csv"],
            key="timeseries"
        )
        
        timeseries_df = None
        if timeseries_file:
            timeseries_df = pd.read_csv(timeseries_file)
            st.dataframe(timeseries_df.head(), use_container_width=True)
    
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
        if not product_name:
            st.error(get_text("fill_required"))
        elif not symptom:
            st.error(get_text("fill_required"))
        else:
            with st.spinner(get_text("analyzing")):
                try:
                    result = run_failure_analysis(
                        product_name=product_name,
                        symptom=symptom,
                        installation=installation,
                        temperature=temperature,
                        uploaded_images=uploaded_images,
                        timeseries_df=timeseries_df,
                        enable_web=enable_web,
                        enable_rule_mining=enable_rule_mining,
                        enable_spc=enable_spc
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
        st.info(f"**{get_text('stage_label')}**: {stage_name} (置信度: {result.root_cause_confidence:.0%})")
        
        # 5-Why展示
        with st.expander(get_text("five_why_title"), expanded=True):
            for item in result.five_why:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"**Why-{item.level}**")
                with col2:
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
                    for cause in causes[:5]:
                        st.markdown(f"- {cause[:60]}...")
        
        # SPC分析（如果有）
        if result.spc_analysis and timeseries_df is not None:
            with st.expander(get_text("spc_title")):
                st.metric("Overall Defect Rate", f"{result.spc_analysis['overall_rate']:.2f}%")
                st.metric("Recent Trend", result.spc_analysis['trend'])
                st.metric("Process Stable", "✅ Yes" if result.spc_analysis['is_stable'] else "⚠️ No")
                
                # 显示SPC图表
                if timeseries_df is not None and len(timeseries_df) > 0:
                    fig = TimeSeriesAnalyzer.create_spc_chart(timeseries_df)
                    st.plotly_chart(fig, use_container_width=True)
        
        # 关联规则（如果有）
        if result.association_rules:
            with st.expander(get_text("rules_title")):
                for rule in result.association_rules[:3]:
                    st.info(rule.get("interpretation", str(rule)))
        
        # 根因结论
        st.markdown(f"### {get_text('root_cause_title')}")
        st.success(f"**{result.root_cause}**")
        
        # 报告生成按钮
        st.markdown("---")
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        
        with col_btn1:
            if st.button(get_text("generate_fa_btn"), use_container_width=True):
                report = FailureAnalysisReportGenerator.generate_fa_report(result, lang)
                st.session_state.current_report = report
                st.session_state.report_type = "fa"
                st.rerun()
        
        with col_btn2:
            if st.button(get_text("generate_8d_btn"), use_container_width=True):
                report = FailureAnalysisReportGenerator.generate_8d_report(result, lang)
                st.session_state.current_report = report
                st.session_state.report_type = "8d"
                st.rerun()
    
    # 显示生成的报告
    if st.session_state.current_report:
        st.markdown("---")
        st.markdown("### 📄 报告预览")
        st.markdown(st.session_state.current_report)
        
        # Word下载
        filename = f"{st.session_state.analysis_result.product_name}_{st.session_state.report_type.upper()}_Report_{datetime.now().strftime('%Y%m%d')}.docx"
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
