import streamlit as st
import pandas as pd
import google.generativeai as genai
import tempfile
import time
import os
from datetime import datetime

# --- 1. 配置区域 ---
st.set_page_config(page_title="GMV 智能分析工作台", layout="wide")

# (A) API Key 配置
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.error("❌ 请在 Secrets 中配置 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=api_key)

# (B) System Instruction (Prompt)
GEM_SYSTEM_INSTRUCTION = """
你是一位资深的电商广告投放分析专家。
你的任务是基于用户上传的“完整数据包”（Excel数据 + 封面图 + 视频）进行深度归因分析。

【分析逻辑】
1. **数据诊断**：根据 Excel (JSON) 数据，指出消耗、GMV、ROI 的关键表现和波动。
2. **素材归因**：结合视频内容和封面图，分析素材与数据的关系。
3. **结论与建议**：给出明确的优化动作。

输出风格：专业、直接、行动导向。
"""

# --- 2. Session State 初始化 (核心数据结构) ---
if "sessions" not in st.session_state:
    # 存储所有会话：Key=任务ID (0116-01), Value={chat_session: 对象, title: 标题}
    st.session_state.sessions = {} 
if "current_task_id" not in st.session_state:
    st.session_state.current_task_id = None  # None 代表正在新建任务界面

# --- 3. 辅助函数 ---

def generate_task_id():
    """生成唯一任务ID: MMDD-NN (如 0116-01)"""
    today_str = datetime.now().strftime('%m%d')
    # 找出今天已有的任务数量
    count = 1
    for task_id in st.session_state.sessions.keys():
        if task_id.startswith(today_str):
            try:
                # 解析后缀数字
                suffix = int(task_id.split('-')[1])
                if suffix >= count:
                    count = suffix + 1
            except:
                pass
    return f"{today_str}-{count:02d}"

def process_excel_data(file):
    """提取 Excel 转 JSON"""
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
    except: return None

def upload_media(file, mime_type):
    """上传文件到 Gemini"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.name.split('.')[-1]}") as tmp:
            tmp.write(file.getvalue())
            tmp_path = tmp.name
        g_file = genai.upload_file(tmp_path, mime_type=mime_type)
        return g_file
    except: return None

def wait_for_video(file_obj):
    """等待视频处理"""
    if not file_obj: return False
    with st.spinner(f"正在后台处理视频数据..."):
        while file_obj.state.name == "PROCESSING":
            time.sleep(2)
            file_obj = genai.get_file(file_obj.name)
        if file_obj.state.name != "ACTIVE": return False
    return True

# --- 4. 侧边栏：任务导航 ---
with st.sidebar:
    st.title("🗂️ 任务列表")
    
    # "新建任务" 按钮
    if st.button("➕ 新建分析任务", use_container_width=True, type="primary"):
        st.session_state.current_task_id = None # 切换到新建界面
        st.rerun()

    st.divider()

    # 历史任务列表
    # 按时间倒序排列（最新的在上面）
    task_list = sorted(list(st.session_state.sessions.keys()), reverse=True)
    
    if not task_list:
        st.caption("暂无历史任务")
    else:
        # 使用 Radio 组件模拟列表选择，虽然样式不同，但状态管理最稳定
        selected_task = st.radio(
            "历史记录", 
            task_list, 
            index=0 if st.session_state.current_task_id is None else None,
            key="nav_radio"
        )
        
        # 如果用户点击了列表中的某一项，切换过去
        # 注意：这里需要判断一下，避免 Radio 默认选中第一个导致无法切回“新建”
        if st.session_state.current_task_id != selected_task:
            # 这里加个按钮来确认切换，或者直接用 Radio 驱动
            # 为了体验更像 Gemini，我们直接用按钮列表生成
            pass

    # 更加像 Gemini 的 Sidebar UI 实现方式：使用按钮循环
    # 为了避免与 Radio 冲突，上面 Radio 代码只是逻辑示例，下面是实际 UI
    # 我们清空上面的 Radio，用纯按钮实现
    
with st.sidebar:
    # 重新清空一下，用更纯粹的 UI
    pass 

# 重写侧边栏逻辑 (为了更好的交互体验)
sidebar_placeholder = st.sidebar.empty()
with sidebar_placeholder.container():
    st.header("🗂️ 工作台")
    if st.button("➕ 新建分析任务", key="new_task_btn", type="primary", use_container_width=True):
        st.session_state.current_task_id = None
        st.rerun()
    
    st.markdown("---")
    st.subheader("历史记录")
    
    # 倒序遍历显示任务
    tasks = sorted(list(st.session_
