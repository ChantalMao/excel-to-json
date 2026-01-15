import streamlit as st
import pandas as pd
import google.generativeai as genai
import tempfile
import time
import os

# --- 1. 配置区域 ---
st.set_page_config(page_title="广告分析 Gem (API版)", layout="wide")

# (A) API Key 配置
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.error("❌ 未找到 API Key，请在 Streamlit Secrets 中配置。")
    st.stop()

genai.configure(api_key=api_key)

# (B) 【关键】在这里粘贴你 Gem 的指令！
# 注意：一定要保留首尾的三个引号，不要误删！
GEM_SYSTEM_INSTRUCTION = """
你是一位资深的广告投放分析专家。
请根据用户上传的 Excel 数据（JSON格式）和广告素材（图片/视频），进行深度归因分析。
分析数据趋势，结合素材内容，给出具体的优化建议。
"""

st.title("🚀 广告分析 Gem (API集成版)")

# --- 2. 侧边栏：上传区 ---
with st.sidebar:
    st.header("📂 素材与数据上传")
    uploaded_excel = st.file_uploader("1. 上传 Excel 报表", type=["xlsx", "xls"])
    uploaded_image = st.file_uploader("2. 上传广告封面/截图 (可选)", type=["png", "jpg", "jpeg"])
    uploaded_video = st.file_uploader("3. 上传广告视频 (可选)", type=["mp4", "mov"])
    
    analyze_btn = st.button("开始分析", type="primary")

# --- 3. 功能函数 ---
def process_excel_data(file):
    """提取 Excel 中的关键 Sheet 并转 JSON"""
    try:
        xls = pd.ExcelFile(file)
        data_bundle = {}
        
        # 定义你要提取的 Sheet 关键词映射
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
                    # 转换为 JSON 对象
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
    if not file_obj:
        return False
        
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
    if not uploaded_excel:
        st.warning("⚠️ 请先上传 Excel 文件！")
    else:
        # 1. 处理数据
        json_data = process_excel_data(uploaded_excel)
        
        if not json_data:
            st.error("❌ Excel 中未找到指定的数据 Sheet (分时段/商品/素材)。")
        else:
            col1, col2 = st.columns([1, 1])
            
            # 2. 准备 Prompt 内容
            user_content = [f"这是今天的投放数据(JSON版)：\n{json_data}\n\n请结合附带的素材进行分析。"]
            
            # 3. 处理素材
            with col1:
                st.subheader("📊 数据与素材")
                st.success("Excel 数据已解析")
                
                if uploaded_image:
                    img_file = upload_media(uploaded_image, "image/jpeg")
                    if img_file:
                        user_content.append(img_file)
                        st.image(uploaded_image, caption="图片素材", use_column_width=True)
                    
                if uploaded_video:
                    vid_file = upload_media(uploaded_video, "video/mp4")
                    if vid_file and wait_for_video(vid_file):
                        user_content.append(vid_file)
                        st.video(uploaded_video)

            # 4. 调用 AI
            with col2:
                st.subheader("💡 智能分析结果")
                try:
                    model = genai.GenerativeModel(
                        model_name="gemini-1.5-flash",
                        system_instruction=GEM_SYSTEM_INSTRUCTION
                    )
                    
                    with st.spinner("Gemini 正在分析数据与视频细节..."):
                        response = model.generate_content(user_content)
                        st.markdown(response.text)
                        
                except Exception as e:
                    st.error(f"分析出错: {e}")
