import streamlit as st
import pandas as pd
import sys
import os
import ast

# --- SETUP PATHS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from db_utils import (
    get_connection, execute_query, 
    get_all_subjects, 
    add_question, add_edge
)

st.set_page_config(page_title="Admin Import Data", page_icon="📥", layout="wide")

# --- AUTH CHECK ---
if "authentication_status" not in st.session_state or st.session_state["authentication_status"] is None:
    st.warning("🔒 Vui lòng đăng nhập."); st.stop()

if st.session_state.get('role') != 'admin':
    st.error("⛔ Bạn không có quyền truy cập trang này."); st.stop()

st.title("📥 Nhập Liệu Môn Học (Admin)")
st.caption("Công cụ hỗ trợ giáo viên/admin import cấu trúc môn học và ngân hàng câu hỏi từ file CSV/Excel.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Hướng dẫn")
    st.info("""
    1. Chuẩn bị file CSV theo mẫu.
    2. Chọn môn học cần import.
    3. Upload file Cấu trúc (Structure) trước để tạo khung.
    4. Upload file Câu hỏi (Questions) sau.
    5. Kiểm tra log để xem kết quả.
    """)
    
    with open("import_templates/structure_template.csv", "rb") as f:
        st.download_button("Tải mẫu Cấu trúc (CSV)", f, "structure_template.csv", "text/csv")
        
    with open("import_templates/questions_template.csv", "rb") as f2:
        st.download_button("Tải mẫu Câu hỏi (CSV)", f2, "questions_template.csv", "text/csv")

# --- MAIN UI ---

# 1. Chọn Môn học
all_subs = get_all_subjects()
if not all_subs:
    st.error("Chưa có môn học nào trong CSDL. Vui lòng tạo môn học trước.")
    st.stop()

sub_names = [s[1] for s in all_subs]
sub_ids = [s[0] for s in all_subs]
selected_sub_name = st.selectbox("📚 Chọn Môn học để nhập liệu:", sub_names)
selected_subject_id = sub_ids[sub_names.index(selected_sub_name)]

st.divider()

tab_struct, tab_quest = st.tabs(["1️⃣ Cấu trúc (Graph)", "2️⃣ Câu hỏi (Bank)"])

# --- TAB 1: STRUCTURE IMPORT ---
with tab_struct:
    st.subheader("Nhập cấu trúc cây tri thức (Knowledge Graph)")
    uploaded_struct = st.file_uploader("Upload file CSV Cấu trúc", type=['csv', 'xlsx'], key="up_struct")
    
    if uploaded_struct:
        try:
            if uploaded_struct.name.endswith('.csv'):
                df_struct = pd.read_csv(uploaded_struct)
            else:
                df_struct = pd.read_excel(uploaded_struct)
            
            st.dataframe(df_struct.head())
            
            if st.button("🚀 Thực hiện Import Cấu trúc"):
                count_ok = 0
                count_err = 0
                log_box = st.empty()
                logs = []
                
                # Normalize columns
                df_struct.columns = df_struct.columns.str.lower().str.strip()
                
                # Validation basic
                req_cols = ['node_id', 'source_node_id']
                if not all(c in df_struct.columns for c in req_cols):
                    st.error(f"File thiếu cột bắt buộc: {req_cols}")
                else:
                    progress_bar = st.progress(0)
                    total = len(df_struct)
                    
                    conn = get_connection() # Use single connection for batch
                    if not conn: st.error("Lỗi kết nối DB"); st.stop()
                    
                    for idx, row in df_struct.iterrows():
                        target = str(row['node_id']).strip()
                        source = str(row['source_node_id']).strip()
                        
                        if source.upper() == 'ROOT': 
                            # Root node logic defines the starting point, 
                            # But our graph table needs pairs. 
                            # If ROOT, maybe we don't insert edge or insert special ROOT edge?
                            # Current logic: knowledge_structure stores Edges.
                            # So we only insert if Source is a real node.
                            # Skip ROOT definition line if it just declares the node exist.
                            pass 
                        else:
                            # Add Edge
                            # Check exist?
                            try:
                                # We treat 'source' column as Parent, 'Node_ID' as Child (Target)
                                execute_query(conn, 
                                    "INSERT INTO knowledge_structure (source, target, subject_id) VALUES (%s, %s, %s)",
                                    (source, target, selected_subject_id))
                                count_ok += 1
                            except Exception as e:
                                logs.append(f"Row {idx}: Lỗi {e}")
                                count_err += 1
                        
                        progress_bar.progress((idx + 1) / total)
                    
                    conn.commit()
                    conn.close()
                    
                    st.success(f"✅ Đã import {count_ok} cạnh. Lỗi: {count_err}")
                    if logs:
                        with st.expander("Chi tiết lỗi"):
                            st.write(logs)
                            
        except Exception as e:
            st.error(f"Lỗi đọc file: {e}")

# --- TAB 2: QUESTIONS IMPORT ---
with tab_quest:
    st.subheader("Nhập ngân hàng câu hỏi")
    uploaded_quest = st.file_uploader("Upload file CSV Câu hỏi", type=['csv', 'xlsx'], key="up_quest")
    
    if uploaded_quest:
        try:
            if uploaded_quest.name.endswith('.csv'):
                df_quest = pd.read_csv(uploaded_quest)
            else:
                df_quest = pd.read_excel(uploaded_quest)
            
            st.dataframe(df_quest.head())
            
            if st.button("🚀 Thực hiện Import Câu hỏi"):
                count_ok = 0
                count_err = 0
                logs = []
                
                # Normalize columns
                df_quest.columns = df_quest.columns.str.lower().str.strip()
                
                # Validation
                req_cols = ['question_id', 'skill_id_list', 'content', 'options', 'answer']
                if not all(c in df_quest.columns for c in req_cols):
                    st.error(f"File thiếu cột bắt buộc: {req_cols}")
                else:
                    progress_bar = st.progress(0)
                    total = len(df_quest)
                    
                    conn = get_connection()
                    if not conn: st.error("Lỗi kết nối DB"); st.stop()
                    
                    for idx, row in df_quest.iterrows():
                        try:
                            # Prepare Data
                            q_id = str(row['question_id']).strip()
                            skill = str(row['skill_id_list']).strip()
                            content = str(row['content']).strip()
                            options_raw = str(row['options']).strip()
                            ans = str(row['answer']).strip()
                            
                            # Optional cols
                            diff = str(row.get('difficulty', 'Medium')).strip()
                            exp = str(row.get('explanation', '')).strip()
                            
                            # Validate Options format (List string)
                            try:
                                dummy = ast.literal_eval(options_raw)
                                if not isinstance(dummy, list): raise ValueError("Options not a list")
                            except:
                                logs.append(f"Row {idx} (QID: {q_id}): Format Options sai. Phải là list ['A...', 'B...'].")
                                count_err += 1
                                continue
                            
                            # Insert/Update
                            # First delete if exist to update
                            execute_query(conn, "DELETE FROM questions WHERE question_id = %s", (q_id,))
                            
                            execute_query(conn, 
                                '''INSERT INTO questions (question_id, skill_id_list, content, options, answer, difficulty, explanation, subject_id)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''', 
                                (q_id, skill, content, options_raw, ans, diff, exp, selected_subject_id))
                            
                            count_ok += 1
                            
                        except Exception as e:
                            logs.append(f"Row {idx}: Lỗi {e}")
                            count_err += 1
                        
                        progress_bar.progress((idx + 1) / total)
                    
                    conn.commit()
                    conn.close()
                    
                    st.success(f"✅ Đã import {count_ok} câu hỏi. Lỗi: {count_err}")
                    if logs:
                        with st.expander("Chi tiết lỗi"):
                            for l in logs: st.write(l)

        except Exception as e:
            st.error(f"Lỗi đọc file: {e}")
