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

# --- 2. Session State 初始化 ---
if "sessions" not in st.session_state:
    st.session_state.sessions = {} 
if "current_task_id" not in st.session_state:
    st.session_state.current_task_id = None

# --- 3. 辅助函数 ---

def generate_task_id():
    """生成唯一任务ID: MMDD-NN"""
    today_str = datetime.now().strftime('%m%d')
    count = 1
    for task_id in st.session_state.sessions.keys():
        if task_id.startswith(today_str):
            try:
                suffix = int(task_id.split('-')[1])
                if suffix >= count:
                    count = suffix + 1
            except:
                pass
    return f"{today_str}-{count:02d}"

def process_excel_data(file):
    """Excel 转 JSON"""
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

# --- 4. 侧边栏：任务导航 (已修复报错) ---
with st.sidebar:
    st.title("🗂️ 工作台")
    
    # 新建任务按钮
    if st.button("➕ 新建分析任务", key="new_task_main", type="primary", use_container_width=True):
        st.session_state.current_task_id = None
        st.rerun()
    
    st.divider()
    st.subheader("历史记录")
    
    # 获取任务列表并排序
    # 修复点：确保这里是一行完整的代码
    tasks = sorted(list(st.session_state.sessions.keys()), reverse=True)
    
    if not tasks:
        st.caption("暂无历史任务")
    
    for t_id in tasks:
        # 判断是否是当前选中的任务
        label = f"📂 {t_id}"
        if t_id == st.session_state.current_task_id:
            label = f"🟢 {t_id} (当前)"
            
        # 生成按钮
        if st.button(label, key=f"btn_{t_id}", use_container_width=True):
            st.session_state.current_task_id = t_id
            st.rerun()

# --- 5. 主界面逻辑 ---

# SCENE 1: 新建任务界面
if st.session_state.current_task_id is None:
    st.title("🚀 新建分析任务")
    st.caption("上传素材后，系统将自动创建新会话")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        uploaded_excel = st.file_uploader("1. Excel 报表 (必填)", type=["xlsx", "xls"])
        uploaded_image = st.file_uploader("2. 广告封面图 (必填)", type=["png", "jpg", "jpeg", "webp"])
        uploaded_video = st.file_uploader("3. 广告视频 (必填)", type=["mp4", "mov", "avi"])

    with col2:
        st.info("💡 提示：")
        st.markdown("""
        - 点击 **开始分析** 后，系统会自动生成任务 ID (如 0116-01)。
        - 图片和视频将**不再预览**，直接在后台处理。
        - 你可以随时在左侧栏切换回历史任务。
        """)
        
        start_btn = st.button("🚀 开始分析", type="primary", use_container_width=True)

    if start_btn:
        if not (uploaded_excel and uploaded_image and uploaded_video):
            st.error("⚠️ 资料不全！请必须同时上传：Excel、图片 和 视频。")
        else:
            with st.spinner("🔄 正在解析数据并上传素材 (无需预览)..."):
                # 1. 解析 Excel
                json_data = process_excel_data(uploaded_excel)
                if not json_data:
                    st.error("❌ Excel 解析失败，未找到指定 Sheet。")
                    st.stop()

                # 2. 上传素材
                img_file = upload_media(uploaded_image, "image/jpeg")
                vid_file = upload_media(uploaded_video, "video/mp4")
                
                if not (img_file and vid_file and wait_for_video(vid_file)):
                    st.error("❌ 素材上传或处理失败，请重试。")
                    st.stop()

                # 3. 初始化 Gemini
                try:
                    model = genai.GenerativeModel(
                        model_name="gemini-1.5-flash",
                        system_instruction=GEM_SYSTEM_INSTRUCTION
                    )
                    chat = model.start_chat(history=[])
                    
                    # 4. 发送初始内容
                    initial_content = [
                        f"这是投放数据(JSON)：\n{json_data}\n\n请结合图片和视频进行分析。",
                        img_file,
                        vid_file
                    ]
                    
                    response = chat.send_message(initial_content)
                    
                    # 5. 创建并保存任务
                    new_task_id = generate_task_id()
                    st.session_state.sessions[new_task_id] = {
                        "chat": chat,
                        "history": [
                            {"role": "user", "content": "【系统指令】分析数据与素材"},
                            {"role": "model", "content": response.text}
                        ]
                    }
                    
                    st.session_state.current_task_id = new_task_id
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"分析出错: {e}")

# SCENE 2: 历史任务详情页
else:
    task_id = st.session_state.current_task_id
    
    # 容错校验
    if task_id not in st.session_state.sessions:
        st.session_state.current_task_id = None
        st.rerun()
        
    session_data = st.session_state.sessions[task_id]
    chat_session = session_data["chat"]
    history = session_data["history"]
    
    st.title(f"📂 任务详情: {task_id}")
    
    # 1. 显示历史
    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # 2. 对话输入
    if prompt := st.chat_input("输入修正指令..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        history.append({"role": "user", "content": prompt})
        
        try:
            with st.spinner("Gemini 正在思考..."):
                response = chat_session.send_message(prompt)
                with st.chat_message("model"):
                    st.markdown(response.text)
                history.append({"role": "model", "content": response.text})
                # 强制保存
                st.session_state.sessions[task_id]["history"] = history
        except Exception as e:
            st.error(f"回复出错: {e}")
