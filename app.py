import streamlit as st
import pandas as pd
import io
import zipfile

# 设置网页标题
st.set_page_config(page_title="Excel 转 JSON 工具 (过滤版)", layout="centered")

st.title("📊 Excel 转 JSON 工具")
st.markdown("仅转换指定 Sheet (分时段/商品/素材)，自动忽略其他无关 Sheet。")

# --- 侧边栏：设置 ---
st.sidebar.header("⚙️ 命名设置")

user_suffix = st.sidebar.text_input(
    "请输入文件后缀", 
    value="1501", 
    help="例如输入 1501，文件名变成：分日数据_1501.json"
)

st.sidebar.info(f"当前预览：\n\nxxx_{user_suffix}.json")

# --- 主界面：文件上传 ---
uploaded_file = st.file_uploader("请上传 Excel 文件 (.xlsx)", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names
        
        st.success(f"✅ 文件读取成功，正在筛选目标 Sheet...")

        # 创建内存 ZIP
        zip_buffer = io.BytesIO()
        converted_count = 0

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for sheet_name in sheet_names:
                clean_name = sheet_name.strip()
                base_name = None

                # --- 筛选与重命名逻辑 ---
                # 只有匹配到以下关键词才处理，否则跳过
                if "分时段数据" in clean_name:
                    base_name = "分日数据"
                elif "商品-gmv max" in clean_name:
                    base_name = "商品明细数据"
                elif "素材-gmv max" in clean_name:
                    base_name = "素材明细数据"
                else:
                    # 如果不是这三个，直接跳过
                    continue

                # --- 开始转换 ---
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                # 拼接文件名
                json_filename = f"{base_name}_{user_suffix}.json"
                
                # 转换为 JSON
                json_str = df.to_json(orient='records', force_ascii=False, indent=4)
                
                # 写入 ZIP
                zip_file.writestr(json_filename, json_str)
                converted_count += 1
                st.write(f"🔹 已转换: `{sheet_name}` -> `{json_filename}`")

        # --- 结果处理 ---
        if converted_count == 0:
            st.warning("⚠️ 未找到指定的 Sheet (
