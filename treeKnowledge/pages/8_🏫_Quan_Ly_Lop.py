import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys
import time

# --- SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from db_utils import (
    create_class, get_classes, enroll_student, 
    get_students_in_class, get_class_matrix, 
    get_all_users_list, get_all_questions,
    get_student_classes
)

st.set_page_config(page_title="Quản lý Lớp học", page_icon="🏫", layout="wide")

# 1. CHECK QUYỀN
if "authentication_status" not in st.session_state or not st.session_state["authentication_status"]:
    st.warning("🔒 Vui lòng đăng nhập."); st.stop()

role = st.session_state.get("role", "student")
username = st.session_state.get("username")

# ==================================================
# 🎓 STUDENT VIEW (Dành cho Sinh viên)
# ==================================================
if role == "student":
    st.title("🎓 Quản lý Lớp học cá nhân")
    
    # [MOVED UP] Fetch student classes once
    my_classes = get_student_classes(username)

    tab1, tab2 = st.tabs(["📚 Lớp của tôi", "➕ Đăng ký lớp mới"])
    
    # --- TAB 1: LỚP ĐÃ THAM GIA ---
    with tab1:
        if not my_classes.empty:
            st.dataframe(my_classes, use_container_width=True)
            st.success(f"Bạn đang tham gia **{len(my_classes)}** lớp học.")
        else:
            st.info("Bạn chưa tham gia lớp học nào.")
            
    # --- TAB 2: ĐĂNG KÝ LỚP ---
    with tab2:
        st.subheader("Ghi danh vào lớp học mở")
        
        # Lấy tất cả các lớp
        all_classes = get_classes() 
        
        # [FIXED] Filter out classes user is already in
        available_classes = all_classes.copy()
        if not my_classes.empty and not all_classes.empty:
            joined_class_ids = my_classes['class_id'].tolist()
            # Filter rows where class_id is NOT in joined_class_ids
            # Ensure type compatibility (string vs int)
            joined_str = [str(x) for x in joined_class_ids]
            available_classes = all_classes[~all_classes['class_id'].astype(str).isin(joined_str)]

        if not available_classes.empty:
            # Tạo dictionary chọn lớp: ID -> "Name (Subject - Teacher)"
            class_opts = {}
            for _, row in available_classes.iterrows():
                class_opts[row['class_id']] = f"{row['class_name']} ({row['subject_id']} - GV: {row['teacher_id']})"
            
            selected_cls_id = st.selectbox("Chọn lớp để tham gia", list(class_opts.keys()), 
                                          format_func=lambda x: class_opts[x])
            
            if st.button("🚀 Tham gia ngay"):
                success, msg = enroll_student(selected_cls_id, username)
                if success:
                    st.balloons()
                    st.success(f"✅ Chúc mừng! Bạn đã tham gia lớp thành công.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning(msg) # "Đã tồn tại" or DB error
        else:
            if all_classes.empty: st.warning("Hiện tại chưa có lớp học nào được mở.")
            else: st.info("Bạn đã tham gia tất cả các lớp hiện có.")

# ==================================================
# 🧑‍🏫 TEACHER/ADMIN VIEW (Quản lý)
# ==================================================
else:
    st.title("🏫 Quản lý Lớp học & Đánh giá Tập thể")

    # EMERGENCY FIX BUTTON
    with st.sidebar:
        st.markdown("---")
        if st.button("🔧 Sửa lỗi dữ liệu Lớp"):
            from db_utils import reset_classes_table_schema
            succ, msg = reset_classes_table_schema()
            if succ: st.success(msg)
            else: st.error(msg)
    
    tab1, tab2 = st.tabs(["⚙️ Cấu hình Lớp", "📊 Dashboard Năng lực (Heatmap)"])
    
    # ... (Rest of Teacher Code) ...
    # Copy existing logic for Teacher
    
    # ==================================================
    # TAB 1: CẤU HÌNH LỚP (Tạo lớp, Gán SV)
    # ==================================================
    with tab1:
        col_creat, col_add = st.columns([1, 2])
        
        # --- A. TẠO LỚP MỚI ---
        with col_creat:
            st.subheader("1. Tạo Lớp Mới")
            with st.form("create_class_form"):
                new_class_name = st.text_input("Tên Lớp (VD: AI-K15)")
                
                # Chọn môn học
                root = os.path.join(parent_dir, "knowledge")
                try:
                    subjects = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
                except: subjects = ["MayHoc"] # Fallback
                
                # Better: Get from DB
                from db_utils import get_all_subjects
                db_subs = get_all_subjects()
                if db_subs: subjects = [s[0] for s in db_subs]
                
                subj = st.selectbox("Môn học", subjects)
                
                # Chọn giảng viên (Nếu là Admin thì chọn đc, Teacher thì tự gán chính mình)
                teachers = [u[0] for u in get_all_users_list() if u[2] in ['teacher', 'admin']]
                if role == 'admin':
                    assigned_teacher = st.selectbox("Giảng viên phụ trách", teachers)
                else:
                    assigned_teacher = st.session_state["username"]
                    st.text(f"Giảng viên: {assigned_teacher}")
                
                if st.form_submit_button("Tạo Lớp"):
                    success, msg = create_class(new_class_name, assigned_teacher, subj)
                    if success: st.success(msg); st.rerun()
                    else: st.error(msg)
        
        # --- B. THÊM SINH VIÊN VÀO LỚP ---
        with col_add:
            st.subheader("2. Ghi danh Sinh viên")
            
            # Lấy danh sách lớp thuộc quyền quản lý
            teacher_filter = None if role == 'admin' else st.session_state["username"]
            classes_df = get_classes(teacher_filter)
            
            if classes_df.empty:
                st.info("Chưa có lớp nào. Hãy tạo lớp trước.")
            else:
                c_select, c_stud = st.columns(2)
                
                with c_select:
                    # Chọn lớp để thêm
                    class_opts = dict(zip(classes_df['class_id'], classes_df['class_name']))
                    selected_class_id = st.selectbox("Chọn Lớp", list(class_opts.keys()), format_func=lambda x: class_opts[x])
                    
                    # Hiển thị môn học của lớp này
                    # Robust filtering: Handle potential type mismatch (int/str) between SQLite and value
                    filtered_class = classes_df[classes_df['class_id'].astype(str) == str(selected_class_id)]
                    if not filtered_class.empty:
                        curr_class_info = filtered_class.iloc[0]
                        st.caption(f"Môn học: **{curr_class_info['subject_id']}**")
                    else:
                        st.warning("Không tìm thấy thông tin lớp (có thể danh sách đã thay đổi). Hãy thử tải lại trang.")
                        st.stop()
                
                with c_stud:
                    # Lấy danh sách Student chưa vào lớp (đơn giản hóa: lấy all students)
                    all_users = get_all_users_list() # [(username, name, role), ...]
                    students_only = [u for u in all_users if u[2] == 'student']
                    student_opts = {u[0]: f"{u[1]} ({u[0]})" for u in students_only}
                    
                    selected_students = st.multiselect("Chọn Sinh viên thêm vào lớp", list(student_opts.keys()), format_func=lambda x: student_opts[x])
                    
                    if st.button("➕ Thêm vào lớp"):
                        count = 0
                        errors = []
                        for s_user in selected_students:
                            succ, msg = enroll_student(selected_class_id, s_user)
                            if succ: count += 1
                            else: errors.append(f"{s_user}: {msg}")
                        
                        if count > 0: 
                            st.success(f"Đã thêm {count} sinh viên!")
                            if errors: st.warning("\n".join(errors)) # Show errors if mixed success
                            st.rerun()
                        else: 
                            st.error(f"Không thể thêm sinh viên:\n" + "\n".join(errors))
    
            # Hiển thị danh sách hiện tại
            if not classes_df.empty:
                st.markdown("---")
                st.caption(f"📋 Danh sách sinh viên lớp: **{class_opts.get(selected_class_id, '')}**")
                
                current_students = get_students_in_class(selected_class_id)
                if not current_students.empty:
                    st.dataframe(current_students)
                    
                    # Feature: Click to see other classes? 
                    # Better: Add a lookup section
                else:
                    st.info("Lớp này chưa có sinh viên.")
    
        # --- C. TRA CỨU SINH VIÊN ---
        st.markdown("---")
        st.subheader("3. Tra cứu Sinh viên")
        
        # Get all students for lookup
        all_users_lookup = get_all_users_list()
        students_lookup = [u for u in all_users_lookup if u[2] == 'student']
        
        if students_lookup:
            lookup_opts = {u[0]: f"{u[1]} ({u[0]})" for u in students_lookup}
            target_student = st.selectbox("Chọn sinh viên để xem các lớp đã tham gia:", 
                                         list(lookup_opts.keys()), 
                                         format_func=lambda x: lookup_opts[x],
                                         index=None,
                                         placeholder="Chọn sinh viên...")
            
            if target_student:
                st_classes = get_student_classes(target_student)
                if not st_classes.empty:
                    st.write(f"Sinh viên **{target_student}** đang tham gia các lớp:")
                    st.dataframe(st_classes)
                else:
                    st.info(f"Sinh viên **{target_student}** chưa tham gia lớp học nào.")
    
    
    # ==================================================
    # TAB 2: DASHBOARD HEATMAP (PHÂN TÍCH LỚP)
    # ==================================================
    with tab2:
        st.header("📊 Bản đồ Năng lực Lớp học (Heatmap)")
        
        # 1. Selector Lớp
        teacher_filter = None if role == 'admin' else st.session_state["username"]
        classes_df = get_classes(teacher_filter)
        
        if classes_df.empty:
            st.warning("Bạn chưa quản lý lớp nào.")
            st.stop()
            
        class_map = dict(zip(classes_df['class_id'], classes_df['class_name']))
        target_class_id = st.selectbox("Chọn lớp để phân tích:", list(class_map.keys()), format_func=lambda x: class_map[x], key="sb_hm_class")
        
        # Lấy thông tin môn học của lớp
        # Robust filtering
        filtered_hm_class = classes_df[classes_df['class_id'].astype(str) == str(target_class_id)]
        if filtered_hm_class.empty:
             st.warning("Không tìm thấy thông tin lớp (dữ liệu có thể đã thay đổi).")
             st.stop()
             
        class_info = filtered_hm_class.iloc[0]
        target_subject = class_info['subject_id']
        st.caption(f"Đang phân tích môn: **{target_subject}**")
        
        # 2. Lấy dữ liệu Matrix
        # Pivot Table: Index=User, Columns=Node, Values=Score
        df_matrix = get_class_matrix(target_class_id, target_subject)
        
        if df_matrix.empty:
            st.info("Chưa có dữ liệu học tập nào từ sinh viên trong lớp này.")
            st.stop()
            
        # 3. Vẽ Heatmap
        # Sắp xếp lại columns (Node) theo thứ tự nếu có thể (để đẹp hơn), hiện tại để mặc định
        
        fig = px.imshow(
            df_matrix,
            labels=dict(x="Bài học (Kỹ năng)", y="Sinh viên", color="Điểm số"),
            x=df_matrix.columns,
            y=df_matrix.index,
            color_continuous_scale="RdYlGn", # Đỏ -> Vàng -> Xanh
            range_color=[0, 1], # Điểm từ 0 đến 1
            aspect="auto"
        )
        
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # 4. Phân tích chi tiết (Insights)
        st.divider()
        c1, c2 = st.columns(2)
        
        # --- Tìm bài học mà cả lớp đang yếu ---
        # Tính trung bình điểm theo cột (Bài học)
        avg_scores_by_node = df_matrix.mean(axis=0).sort_values()
        weakest_nodes = avg_scores_by_node.head(5)
        
        with c1:
            st.subheader("⚠️ Bài học cần giảng lại")
            st.write("Các bài có điểm trung bình thấp nhất lớp:")
            for node, score in weakest_nodes.items():
                st.error(f"**{node}**: {score:.1%} (Trung bình)")
                
        # --- Tìm sinh viên cần kèm cặp ---
        # Tính trung bình điểm theo hàng (Sinh viên)
        avg_scores_by_student = df_matrix.mean(axis=1).sort_values()
        weakest_students = avg_scores_by_student.head(5)
        
        with c2:
            st.subheader("🆘 Sinh viên cần hỗ trợ")
            st.write("Các sinh viên có điểm trung bình thấp nhất:")
            for user, score in weakest_students.items():
                st.warning(f"**{user}**: {score:.1%} (Trung bình)")
    
        # 5. Xem chi tiết dạng bảng
        with st.expander("📋 Xem dữ liệu thô (Excel)"):
            st.dataframe(df_matrix.style.background_gradient(cmap='RdYlGn', axis=None), use_container_width=True)