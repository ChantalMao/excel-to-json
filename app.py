import streamlit as st
import pandas as pd
import io
import zipfile

# 设置网页标题
st.set_page_config(page_title="Excel 转 JSON 工具", layout="centered")

st.title("📊 Excel 多 Sheet 转 JSON 工具")
st.markdown("上传 Excel 文件，自动将每个 Sheet 转换为单独的 JSON 文件并打包下载。")

# --- 侧边栏：设置命名规则 ---
st.sidebar.header("⚙️ 命名规则设置")
prefix = st.sidebar.text_input("文件名前缀", value="", placeholder="例如：data_")
suffix = st.sidebar.text_input("文件名后缀", value="", placeholder="例如：_v1")
name_source = st.sidebar.radio(
    "文件名来源",
    ("使用 Sheet 名称", "使用 Sheet 索引 (1, 2, 3...)")
)

# --- 主界面：文件上传 ---
uploaded_file = st.file_uploader("请上传 Excel 文件 (.xlsx)", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # 读取 Excel
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names
        
        st.success(f"✅ 成功读取文件！包含 {len(sheet_names)} 个 Sheet：{', '.join(sheet_names)}")

        # 创建一个内存中的 ZIP 文件
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # 遍历每个 Sheet
            for index, sheet_name in enumerate(sheet_names):
                # 读取数据
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                # --- 处理命名逻辑 ---
                if name_source == "使用 Sheet 名称":
                    base_name = sheet_name
                else:
                    base_name = str(index + 1)
                
                # 拼接最终文件名
                json_filename = f"{prefix}{base_name}{suffix}.json"
                
                # 转换为 JSON 字符串
                json_str = df.to_json(orient='records', force_ascii=False, indent=4)
                
                # 写入 ZIP 包
                zip_file.writestr(json_filename, json_str)

        # 准备下载按钮
        st.divider()
        st.subheader("🎉 转换完成")
        
        # 重新定位指针到文件开头
        zip_buffer.seek(0)
        
        st.download_button(
            label="⬇️ 点击下载所有 JSON (ZIP压缩包)",
            data=zip_buffer,
            file_name="converted_json_files.zip",
            mime="application/zip"
        )
        
    except Exception as e:
        st.error(f"❌ 发生错误: {e}")

else:
    st.info("请在上方上传文件开始使用。")