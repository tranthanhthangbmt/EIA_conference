import streamlit as st
import pandas as pd
import sys
import os
import time

# --- SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import các hàm từ db_utils
# Đã thêm 'import_content_from_docx' vào danh sách import
from db_utils import (
    get_all_questions, add_question, delete_question, 
    get_graph_structure, add_edge, delete_edge, 
    save_resource, get_resource,
    import_knowledge_structure, import_questions_bank, 
    import_lectures_data, clear_table_data,
    import_content_from_docx,  # <--- MỚI THÊM
    generate_test_packet, # <--- TEST PACKET
    import_content_from_docx,  # <--- MỚI THÊM
    generate_test_packet, # <--- TEST PACKET
    get_all_subjects, create_subject, delete_subject_content # <--- SUBJECT MANAGEMENT
)

st.set_page_config(page_title="Quản trị Nội dung", page_icon="🛠️", layout="wide")

# 1. KIỂM TRA QUYỀN (Chỉ Teacher trở lên)
if "authentication_status" not in st.session_state or not st.session_state["authentication_status"]:
    st.warning("🔒 Vui lòng đăng nhập."); st.stop()

role = st.session_state.get("role", "student")
if role not in ["admin", "teacher", "manager"]:
    st.error("⛔ Bạn không có quyền truy cập trang này."); st.stop()

st.title("🛠️ Hệ thống Quản trị Nội dung (CMS)")

# --- GLOBAL SUBJECT SELECTION ---
st.markdown("### 📌 Chọn Môn học làm việc")
all_subjects = get_all_subjects() # Returns list of tuples (id, name)

# Self-healing: If no subjects found, try clearing cache once (in case of stale cache after creation)
if not all_subjects and "subject_retry" not in st.session_state:
    st.session_state["subject_retry"] = True
    st.cache_data.clear()
    st.rerun()

subject_options = [s[0] for s in all_subjects]
subject_map = {s[0]: s[1] for s in all_subjects}

col_sub, col_create = st.columns([2, 1])
with col_sub:
    selected_subject_id = st.selectbox("Đang làm việc với môn:", subject_options, format_func=lambda x: f"{x} - {subject_map.get(x, '')}")
    selected_subject = selected_subject_id # Alias for compatibility

with col_create:
    with st.expander("➕ Tạo Môn Mới"):
        with st.form("create_subject_form"):
            new_sub_id = st.text_input("Mã (VD: LyThuyetDoThi)").strip()
            new_sub_name = st.text_input("Tên (VD: Lý Thuyết Đồ Thị)").strip()
            new_sub_desc = st.text_area("Mô tả").strip()
            
            if st.form_submit_button("Tạo"):
                if new_sub_id and new_sub_name:
                    success, msg = create_subject(new_sub_id, new_sub_name, new_sub_desc)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Thiếu thông tin.")

# --- CACHE CONTROL ---
col_cache, _ = st.columns([1, 5])
with col_cache:
    if st.button("🔄 Xóa Cache Hệ thống", type="secondary", help="Xóa bộ nhớ đệm để cập nhật dữ liệu mới nhất từ Database"):
        st.cache_data.clear()
        st.toast("Đã xóa cache thành công!", icon="🧹")

# --- TABS GIAO DIỆN ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📥 Import Dữ liệu", 
    "❓ Ngân hàng Câu hỏi", 
    "🕸️ Cấu trúc Đồ thị", 
    "📚 Tài nguyên Bài giảng",
    "🚀 Tối ưu hóa"
])

# ============================================================
# TAB 1: IMPORT DỮ LIỆU (ĐÃ CẬP NHẬT TÍNH NĂNG MỚI)
# ============================================================
with tab1:
    st.header("📥 Nhập dữ liệu từ file CSV & DOCX")
    st.info("Chức năng này giúp khởi tạo nhanh dữ liệu cho hệ thống.")

    st.info(f"Đang nhập liệu cho môn: **{selected_subject}**")
    
    st.divider()

    col_a, col_b, col_c = st.columns(3)

    # --- 1. IMPORT CẤU TRÚC CÂY (K-GRAPH) ---
    with col_a:
        st.subheader("1. Cấu trúc Cây (Graph)")
        st.caption("File: k-graph.csv (Cột: source, target)")
        file_k = st.file_uploader("Upload k-graph.csv", type=["csv"], key="upl_k")
        
        if file_k:
            if st.button("🚀 Nhập Cấu trúc", key="btn_k"):
                try:
                    df = pd.read_csv(file_k)
                    df.columns = df.columns.str.strip().str.lower()
                    
                    # Kiểm tra cột
                    if 'source' in df.columns and 'target' in df.columns:
                        success, msg = import_knowledge_structure(df, selected_subject)
                        if success: 
                            st.cache_data.clear() # Clear cache to show new data
                            st.success(msg)
                        else: st.error(msg)
                    else:
                        st.error("File CSV thiếu cột 'source' hoặc 'target'.")
                except Exception as e: st.error(f"Lỗi đọc file: {e}")
        
        with st.expander("🗑️ Xóa dữ liệu cũ"):
            if st.button("Xóa toàn bộ Cấu trúc", type="primary"):
                clear_table_data("knowledge_structure")
                st.warning("Đã xóa sạch bảng cấu trúc!")

    # --- 2. IMPORT CÂU HỎI (Q-MATRIX) ---
    with col_b:
        st.subheader("2. Ngân hàng Câu hỏi")
        st.caption("File: q-matrix.csv (Cột: question_id, content, ...)")
        file_q = st.file_uploader("Upload q-matrix.csv", type=["csv"], key="upl_q")
        
        if file_q:
            if st.button("🚀 Nhập Câu hỏi", key="btn_q"):
                try:
                    df = pd.read_csv(file_q)
                    # Normalize columns
                    df.columns = df.columns.str.strip().str.lower()
                    
                    # Check sơ bộ
                    if 'question_id' in df.columns:
                        success, msg = import_questions_bank(df, selected_subject)
                        if success: 
                            st.cache_data.clear() # Clear cache to show new data
                            st.success(msg)
                        else: st.error(msg)
                    else: st.error("File thiếu cột 'question_id'")
                except Exception as e: st.error(f"Lỗi: {e}")

        with st.expander("🗑️ Xóa dữ liệu cũ"):
            if st.button("Xóa toàn bộ Câu hỏi", type="primary"):
                clear_table_data("questions")
                st.warning("Đã xóa sạch bảng câu hỏi!")

    # --- 3. IMPORT BÀI GIẢNG (LECTURES) ---
    with col_c:
        st.subheader("3. Tài nguyên Bài giảng")
        st.caption("File: lectures.csv (Cột: node_id, title, content_url...)")
        file_l = st.file_uploader("Upload lectures.csv", type=["csv"], key="upl_l")
        
        if file_l:
            if st.button("🚀 Nhập Bài giảng", key="btn_l"):
                try:
                    # 1. Đọc file và chuẩn hóa tên cột
                    df = pd.read_csv(file_l, encoding='utf-8-sig')
                    df.columns = df.columns.str.strip().str.lower()
                    
                    # 2. MAPPING CỘT (Tự động đổi tên cho khớp Database)
                    column_map = {
                        'id': 'node_id',          # id -> node_id
                        'url': 'content_url',     # url -> content_url
                        'link': 'content_url',    # link -> content_url
                        'desc': 'description',    # desc -> description
                        'type': 'content_type'    # type -> content_type
                    }
                    df.rename(columns=column_map, inplace=True)

                    # 3. Kiểm tra cột bắt buộc (node_id)
                    if 'node_id' in df.columns:
                        # Gọi hàm import từ db_utils
                        success, msg = import_lectures_data(df)
                        
                        if success: 
                            st.success(f"✅ {msg}")
                            with st.expander("Xem dữ liệu đã nhận diện:"):
                                st.dataframe(df.head(3))
                        else: 
                            st.error(msg)
                    else:
                        st.error(f"❌ Không tìm thấy cột ID bài học.")
                        st.caption(f"Các cột hệ thống tìm thấy: {list(df.columns)}")
                        
                except Exception as e: 
                    st.error(f"Lỗi xử lý file: {e}")

    # --- 4. IMPORT NỘI DUNG CHI TIẾT (TỪ WORD) - TÍNH NĂNG MỚI ---
    st.markdown("---")
    st.subheader("4. 📑 Nhập nội dung bài học từ File Word")
    st.info("Hệ thống sẽ tự động cắt file Word theo Heading (1.1, 1.2...) và điền vào nội dung bài học tương ứng.")
    
    file_docx = st.file_uploader("Upload tài liệu (.docx)", type=["docx"], key="upl_docx")
    
    if file_docx:
        if st.button("🚀 Phân tách & Nhập nội dung", type="primary"):
            with st.spinner("Đang đọc và phân tích file Word..."):
                # Gọi hàm xử lý Word từ db_utils
                success, log_msg = import_content_from_docx(file_docx)
                if success:
                    st.success("Đã xử lý xong!")
                    with st.expander("Xem chi tiết nhật ký nhập liệu"):
                        st.text(log_msg)
                else:
                    st.error(log_msg)

# ============================================================
# TAB 2: QUẢN LÝ CÂU HỎI (GIỮ NGUYÊN)
# ============================================================
with tab2:
    st.subheader(f"Danh sách câu hỏi hiện tại ({selected_subject})")
    df_q = get_all_questions(selected_subject)
    st.dataframe(df_q, use_container_width=True)
    
    with st.expander("➕ Thêm câu hỏi thủ công"):
        with st.form("add_q_form"):
            c1, c2 = st.columns([1, 2])
            q_id = c1.text_input("ID Câu hỏi (VD: Q100)")
            skill = c2.text_input("Thuộc Skill ID (VD: 1.2_TaiSao_ML)")
            content = st.text_area("Nội dung câu hỏi")
            options = st.text_input("Lựa chọn (List Python)", value="['A. ...', 'B. ...', 'C. ...', 'D. ...']")
            c3, c4, c5 = st.columns(3)
            ans = c3.text_input("Đáp án (VD: A)")
            diff = c4.selectbox("Độ khó", ["easy", "medium", "hard"])
            exp = c5.text_input("Giải thích")
            if st.form_submit_button("Lưu"):
                success, msg = add_question(q_id, skill, content, options, ans, diff, exp, selected_subject)
                if success: st.success(msg); st.rerun()
                else: st.error(msg)
    
    with st.expander("❌ Xóa câu hỏi"):
        if not df_q.empty:
            q_to_del = st.selectbox("Chọn ID xóa", df_q['question_id'].unique())
            if st.button("Xóa câu hỏi này"):
                delete_question(q_to_del); st.success("Đã xóa!"); st.rerun()

# ============================================================
# TAB 3: QUẢN LÝ ĐỒ THỊ (GIỮ NGUYÊN)
# ============================================================
with tab3:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader(f"Cấu trúc cây tri thức ({selected_subject})")
        df_k = get_graph_structure(selected_subject)
        st.dataframe(df_k, use_container_width=True, height=400)
    with c2:
        st.subheader("Thêm/Xóa mối quan hệ")
        with st.form("add_edge"):
            src = st.text_input("Node Cha")
            tgt = st.text_input("Node Con")
            if st.form_submit_button("Thêm liên kết"):
                success, msg = add_edge(src, tgt, selected_subject)
                if success: st.success(msg); st.rerun()
                else: st.error(msg)
        edge_id = st.number_input("ID dòng để xóa", min_value=0, step=1)
        if st.button("Xóa liên kết"):
            delete_edge(edge_id); st.success("Đã xóa!"); st.rerun()

# ============================================================
# TAB 4: TÀI NGUYÊN BÀI GIẢNG (GIỮ NGUYÊN)
# ============================================================
with tab4:
    st.info("Gắn video/tài liệu cho bài học.")
    all_nodes = []
    # Load danh sách node từ DB graph & question
    df_g = get_graph_structure(selected_subject)
    if not df_g.empty:
        all_nodes = sorted(list(set(df_g['source']).union(set(df_g['target']))))
    
    if all_nodes:
        sel_node = st.selectbox("Chọn bài học", all_nodes)
        curr = get_resource(sel_node)
        with st.form("res_form"):
            title = st.text_input("Tiêu đề", value=curr[1] if curr else "")
            ctype = st.selectbox("Loại", ["video", "pdf", "markdown"], index=0)
            url = st.text_input("URL", value=curr[3] if curr else "")
            desc = st.text_area("Mô tả", value=curr[4] if curr else "")
            if st.form_submit_button("Lưu"):
                save_resource(sel_node, title, ctype, url, desc)
                st.success("Đã lưu!"); st.rerun()
    else:
        st.warning("Cần nhập Cấu trúc Đồ thị trước.")

# ============================================================
# TAB 5: TỐI ƯU HÓA (TEST PACKETS)
# ============================================================
with tab4: # Note: tab4 variable name was reused in original code? No, tab1..tab4 defined. Need tab5.
    pass 

with tab5: # Wait, I need to define tab5 in the tabs list unpacking
    st.header("🚀 Tối ưu hóa Hệ thống")
    st.info("Tạo các gói dữ liệu tĩnh (Test Packets) để tăng tốc độ tải bài kiểm tra.")
    
    st.subheader("Gói Đề Thi (Test Packets)")
    st.markdown("Thay vì truy vấn Database liên tục, hệ thống sẽ tải 1 file JSON duy nhất chứa toàn bộ câu hỏi và cấu trúc.")
    
    # Chọn môn học (Hiện tại hardcode MayHoc, sau này dynamic)
    # Chọn môn học (Dynamic)
    target_subj = selected_subject # Use global selection
    st.write(f"Đang đóng gói cho môn: **{target_subj}**")
    
    if st.button("📦 Đóng gói Dữ liệu (Test Packet)"):
        with st.spinner("Đang tạo gói dữ liệu..."):
            success, msg = generate_test_packet(target_subj)
            if success:
                st.success(msg)
            else:
                st.error(msg)

    st.divider()
    st.subheader("⚠️ Vùng Nguy Hiểm (Danger Zone)")
    st.warning("Các hành động dưới đây không thể hoàn tác. Hãy cẩn thận!")
    
    col_del_1, col_del_2 = st.columns([3, 1])
    with col_del_1:
        st.markdown(f"**Xóa toàn bộ dữ liệu của môn: {target_subj}**")
        st.caption("Bao gồm: Câu hỏi, Cấu trúc đồ thị, Tiến độ học tập, Lịch sử.")
    
    with col_del_2:
        if st.button("🗑️ Xóa Dữ liệu Môn này", type="primary"):
            # Double check mechanism could be added here (e.g. session state flag)
            # For now, direct action as requested
            with st.spinner(f"Đang xóa dữ liệu môn {target_subj}..."):
                success, msg = delete_subject_content(target_subj)
                if success:
                    st.success(msg)
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(msg)