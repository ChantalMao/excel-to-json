import streamlit as st
import pandas as pd
import io
import zipfile

# 设置网页标题
st.set_page_config(page_title="Excel 转 JSON 工具 (手动后缀版)", layout="centered")

st.title("📊 Excel 转 JSON 工具")
st.markdown("自动识别 Sheet 类型并重命名，后缀手动指定。")

# --- 侧边栏：设置 ---
st.sidebar.header("⚙️ 命名设置")

# 这里改为手动输入文本
user_suffix = st.sidebar.text_input(
    "请输入文件后缀", 
    value="1501", 
    help="这个后缀会自动加在文件名后面，例如输入 1501，文件名变成：分日数据_1501.json"
)

st.sidebar.info(f"当前预览：\n\nxxx_{user_suffix}.json")

# --- 主界面：文件上传 ---
uploaded_file = st.file_uploader("请上传 Excel 文件 (.xlsx)", type=["xlsx", "xls"])

# --- 核心逻辑：Sheet 改名映射 ---
def get_new_name(original_name):
    """
    根据用户规则重命名 Sheet
    """
    clean_name = original_name.strip()
    
    # 模糊匹配：只要 Sheet 名包含关键词，就改名
    if "分时段数据" in clean_name:
        return "分日数据"
    elif "商品-gmv max" in clean_name:
        return "商品明细数据"
    elif "素材-gmv max" in clean_name:
        return "素材明细数据"
    else:
        # 其他不认识的 Sheet，保持原名
        return clean_name

if uploaded_file is not None:
    try:
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names
        
        st.success(f"✅ 读取成功！检测到 Sheet: {sheet_names}")

        # 创建内存 ZIP
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            count = 0
            for sheet_name in sheet_names:
                # 读取数据
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                # 1. 映射新名字
                base_name = get_new_name(sheet_name)
                
                # 2. 拼接文件名：名字 + 下划线 + 你输入的后缀
                # 如果你不想要中间的下划线，可以把下面这行改成: f"{base_name}{user_suffix}.json"
                json_filename = f"{base_name}_{user_suffix}.json"
                
                # 转换为 JSON
                json_str = df.to_json(orient='records', force_ascii=False, indent=4)
                
                # 写入 ZIP
                zip_file.writestr(json_filename, json_str)
                count += 1
                st.write(f"🔹 转换: `{sheet_name}` -> `{json_filename}`")

        # 下载按钮
        st.divider()
        zip_buffer.seek(0)
        
        st.download_button(
            label="⬇️ 下载 JSON 压缩包",
            data=zip_buffer,
            file_name=f"json_output_{user_suffix}.zip",
            mime="application/zip"
        )
        
    except Exception as e:
        st.error(f"❌ 发生错误: {e}")
