import streamlit as st
import pandas as pd
import google.generativeai as genai
import tempfile
import time
import os

# --- 1. 配置区域 ---
st.set_page_config(page_title="GMV 全链路分析 (严格版)", layout="wide")

# (A) API Key 配置
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.error("❌ 未找到 API Key，请在 Streamlit Secrets 中配置。")
    st.stop()

genai.configure(api_key=api_key)

# (B) System Instruction (Prompt)
# ⚠️ 注意：保留首尾的三个引号
GEM_SYSTEM_INSTRUCTION = """
你是一位资深的电商广告投放分析专家。
你的任务是基于用户上传的“完整数据包”（Excel数据 + 封面图 + 视频）进行深度归因分析。

【分析逻辑】
1. **数据诊断**：根据 Excel (JSON) 数据，指出消耗、GMV、ROI 的关键表现和波动。
2. **素材归因**：
   - 结合视频的前3秒内容、BGM、节奏，分析为什么这个视频在这个数据表现下是好/坏的。
   - 结合封面图，分析点击率 (CTR) 与封面的关系。
3. **结论与建议**：不要模棱两可，直接给出“继续放量”、“暂停”、“修改开头”等具体指令。

输出风格：专业、直接、行动导向。
"""

st.title("🚀 GMV 全链路分析 (数据+图+视)")

# --- 2. 侧边栏：上传区 (全必填) ---
with st.sidebar:
    st.header("📂 资料上传 (全部必填)")
    
    uploaded_excel = st.file_uploader("1. Excel 报表", type=["xlsx", "xls"])
    uploaded_image = st.file_uploader("2. 广告封面图", type=["png", "jpg", "jpeg", "webp"])
    uploaded_video = st.file_uploader("3. 广告视频", type=["mp4", "mov", "avi"])
    
    st.divider()
    analyze_btn = st.button("🚀 开始联合分析", type="primary")

# --- 3. 功能函数 ---
def process_excel_data(file):
    """提取 Excel 中的关键 Sheet 并转 JSON"""
    try:
        xls = pd.ExcelFile(file)
        data_bundle = {}
        
        target_sheets = {
            "分时段数据": "分时段表现",
            "商品-gmv max": "商品GMV明细",
            "素材-gmv max": "素材GMV明细"
        }
        
        found = False
        for sheet_name in xls.sheet_names:
            clean_name = sheet_name.strip()
            for key, alias in target_sheets.items():
                if key in clean_name:
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    data_bundle[alias] = df.to_dict(orient='records')
                    found = True
        
        return str(data_bundle) if found else None
    except Exception as e:
        return None

def upload_media(file, mime_type):
    """上传媒体文件到 Gemini"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.name.split('.')[-1]}") as tmp:
            tmp.write(file.getvalue())
            tmp_path = tmp.name
        
        g_file = genai.upload_file(tmp_path, mime_type=mime_type)
        return g_file
    except Exception as e:
        st.error(f"上传文件失败: {e}")
        return None

def wait_for_video(file_obj):
    """等待视频处理完成"""
    if not file_obj: return False
    with st.spinner(f"正在转码视频: {file_obj.name}..."):
        while file_obj.state.name == "PROCESSING":
            time.sleep(2)
            file_obj = genai.get_file(file_obj.name)
        if file_obj.state.name != "ACTIVE":
            st.error("视频处理失败，请重试。")
            return False
    return True

# --- 4. 主程序 ---
if analyze_btn:
    # ❌ 严格校验：缺一不可
    if not (uploaded_excel and uploaded_image and uploaded_video):
        st.error("⚠️ 资料不
