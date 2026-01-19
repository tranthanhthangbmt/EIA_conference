import streamlit as st
import streamlit_authenticator as stauth
import os
import time
import pandas as pd

# --- IMPORT DB UTILS ---
try:
    from db_utils import init_db, create_user, load_users_config, get_user_role, get_pending_users, approve_user
except ImportError:
    st.error("⚠️ Lỗi: Không tìm thấy db_utils.py")
    st.stop()

# --- KHỞI TẠO ---
# Chỉ cần init_db 1 lần, ở đây cứ gọi, nhưng db_utils sẽ handle kết nối
init_db()
st.set_page_config(page_title="Hệ thống Học tập", page_icon="🧠", layout="wide")

# ============================================================
# 🔐 CẤU HÌNH XÁC THỰC
# ============================================================
users_config = load_users_config() # Direct read from Supabase

authenticator = stauth.Authenticate(
    credentials=users_config,
    cookie_name='k_graph_cookie_v2',
    key='random_key_secure_999', 
    cookie_expiry_days=30
)

# ============================================================
# 🖥️ GIAO DIỆN ĐĂNG NHẬP / ĐĂNG KÝ
# ============================================================
if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None

if st.session_state["authentication_status"] is None or st.session_state["authentication_status"] is False:
    # Reset state logic
    st.session_state["use_local_db"] = False

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Cổng thông tin học tập")
        tab1, tab2 = st.tabs(["🔑 Đăng Nhập", "📝 Đăng Ký Mới"])
        
        with tab1:
            try: authenticator.login(location='main')
            except Exception as e: st.error(f"Lỗi đăng nhập: {e}")
            if st.session_state["authentication_status"] is False: st.error('❌ Sai thông tin đăng nhập')
            elif st.session_state["authentication_status"] is None: st.warning('👉 Vui lòng nhập thông tin')

        with tab2:
            with st.form("register_form"):
                st.subheader("Tạo tài khoản")
                new_user = st.text_input("Username*").strip()
                new_name = st.text_input("Họ tên*").strip()
                new_pass = st.text_input("Mật khẩu*", type="password")
                
                # Chọn vai trò
                role = st.selectbox("Vai trò", ["student", "teacher", "manager", "admin"])
                if role != "student": st.caption("⚠️ Tài khoản này cần Admin duyệt.")
                
                if st.form_submit_button("🚀 Đăng ký"):
                    if new_user and new_pass:
                        success, msg = create_user(new_user, new_name, new_pass, role=role)
                        if success: 
                            st.success(msg)
                            # [AUTO-LOGIN] Tự động đăng nhập
                            st.session_state["authentication_status"] = True
                            st.session_state["username"] = new_user
                            st.session_state["name"] = new_name
                            st.session_state["role"] = role
                            # Force rerun to load Main Interface
                            time.sleep(1) # Chờ 1 chút cho user đọc thông báo
                            st.rerun()
                        else: st.error(msg)
                    else: st.warning("Điền đủ thông tin!")

# ============================================================
# 🏠 GIAO DIỆN CHÍNH (ĐÃ LOGIN)
# ============================================================
if st.session_state["authentication_status"]:
    current_username = st.session_state["username"]
    
    # Lấy Role mới nhất từ DB
    user_role = get_user_role(current_username)
    st.session_state["role"] = user_role

    # Cloud-Native Optimization: Direct Cloud Mode
    st.session_state['use_local_db'] = False 

    # --- SIDEBAR ---
    with st.sidebar:
        user_name = st.session_state.get('name', 'User')
        st.write(f"Xin chào, **{user_name}**! 👋")
        st.caption(f"Quyền hạn: **{user_role.upper()}**")
        
        # Nút Đăng xuất
        authenticator.logout(location='sidebar')
        st.divider()

        # Nút Đổi mật khẩu (Chuyển view)
        if st.button("🔑 Đổi mật khẩu", use_container_width=True):
            st.session_state["view_mode"] = "change_password"

        # --- MENU QUẢN TRỊ (ADMIN/MANAGER) ---
        if user_role in ["admin", "manager"]:
            st.subheader("🛠️ Quản trị")
            
            # 1. Duyệt User
            if user_role == "admin":
                pending = get_pending_users()
                if not pending.empty:
                    st.warning(f"🔔 Có {len(pending)} người chờ duyệt")
                    if st.button("Duyệt người dùng"):
                        st.session_state["view_mode"] = "approve"
                else:
                    st.caption("Không có yêu cầu duyệt mới.")
            
            # 2. Xem Database
            if st.button("👀 Xem Database"):
                st.session_state["view_mode"] = "database"

            # 3. Quản lý Hệ thống [NEW]
            if st.button("🗄️ Quản lý Hệ thống"):
                st.session_state["view_mode"] = "system_management"
        
        st.divider()
    
    # --- NỘI DUNG CHÍNH ---
    view_mode = st.session_state.get("view_mode", "home")
    
    # 1. Màn hình Đổi Mật Khẩu [NEW]
    if view_mode == "change_password":
        st.header("🔑 Đổi mật khẩu")
        try:
            if authenticator.reset_password(location='main'):
                st.success('Đổi mật khẩu thành công!')
        except Exception as e:
            st.warning("Chức năng đổi mật khẩu tự động gặp lỗi. Vui lòng sử dụng form bên dưới.")

        # --- FORM ĐỔI MẬT KHẨU THỦ CÔNG (ỔN ĐỊNH HƠN) ---
        st.markdown("---")
        with st.form("manual_reset_pass"):
            st.subheader("Nhập thông tin")
            old_pass = st.text_input("Mật khẩu cũ", type="password")
            new_pass = st.text_input("Mật khẩu mới", type="password")
            confirm_pass = st.text_input("Xác nhận mật khẩu mới", type="password")
            
            if st.form_submit_button("Lưu thay đổi"):
                from db_utils import update_user_password
                success, msg = update_user_password(current_username, old_pass, new_pass, confirm_pass)
                if success:
                    st.success(msg)
                    time.sleep(1)
                    st.session_state["view_mode"] = "home"
                    st.rerun()
                else:
                    st.error(msg)
        
        if st.button("Hủy"):
            st.session_state["view_mode"] = "home"; st.rerun()

    # 2. Màn hình Duyệt User (Giữ nguyên)
    elif view_mode == "approve" and user_role == "admin":
        st.header("✅ Duyệt tài khoản mới")
        pending = get_pending_users()
        if not pending.empty:
            for idx, row in pending.iterrows():
                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                c1.write(f"**{row['username']}**")
                c2.write(row['name'])
                c3.info(row['role'])
                if c4.button("Duyệt", key=f"app_{row['username']}"):
                    approve_user(row['username'])
                    st.success(f"Đã duyệt {row['username']}")
                    st.rerun()
                st.divider()
        if st.button("Quay lại"):
            st.session_state["view_mode"] = "home"; st.rerun()

    # 3. Màn hình Xem Database (Tạm Disable hoặc update logic nếu cần)
    elif view_mode == "database" and user_role in ["admin", "manager"]:
        st.header("📂 Dữ liệu hệ thống")
        st.info("Chức năng xem database trực tiếp đang bảo trì khi chuyển lên Cloud.")
        if st.button("Đóng"):
            st.session_state["view_mode"] = "home"; st.rerun()

    # 4. Màn hình Quản lý Hệ thống (Subject/Class) [NEW]
    elif view_mode == "system_management" and user_role in ["admin", "manager"]:
        st.header("🗄️ Quản lý Hệ thống")
        
        tab_sub, tab_cls = st.tabs(["📚 Quản lý Môn học", "🏫 Quản lý Lớp học"])
        
        # --- TAB 1: SUBJECTS ---
        with tab_sub:
            st.subheader("Danh sách Môn học")
            from db_utils import get_all_subjects, create_subject, delete_subject
            
            # Form Thêm Môn
            with st.expander("➕ Thêm Môn Học Mới"):
                with st.form("add_subject_form"):
                    c1, c2 = st.columns(2)
                    new_sub_id = c1.text_input("Mã môn (VD: KNS)").strip()
                    new_sub_name = c2.text_input("Tên môn (VD: Kỹ năng số)").strip()
                    new_sub_desc = st.text_area("Mô tả")
                    
                    if st.form_submit_button("Tạo Môn Học"):
                        if new_sub_id and new_sub_name:
                            succ, msg = create_subject(new_sub_id, new_sub_name, new_sub_desc)
                            if succ: st.success(msg); time.sleep(1); st.rerun()
                            else: st.error(msg)
                        else: st.warning("Vui lòng nhập Mã và Tên môn!")

            # List Môn
            subjects = get_all_subjects()
            if subjects:
                # Convert list of tuples to DataFrame for display
                df_sub = pd.DataFrame(subjects, columns=["Mã môn", "Tên môn"])
                
                for idx, row in df_sub.iterrows():
                    c1, c2, c3 = st.columns([1, 3, 1])
                    c1.write(f"**{row['Mã môn']}**")
                    c2.write(row['Tên môn'])
                    if c3.button("🗑️ Xóa", key=f"del_sub_{row['Mã môn']}"):
                        # Warning logic could be added here
                        succ, msg = delete_subject(row['Mã môn'])
                        if succ: st.success(msg); time.sleep(1); st.rerun()
                        else: st.error(msg)
                    st.divider()
            else:
                st.info("Chưa có môn học nào.")

        # --- TAB 2: CLASSES ---
        with tab_cls:
            st.subheader("Danh sách Lớp học")
            from db_utils import get_classes, delete_class
            
            classes = get_classes() # Gets all classes
            if not classes.empty:
                for idx, row in classes.iterrows():
                    c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
                    c1.write(f"ID: {row['class_id']}")
                    c2.write(f"**{row['class_name']}**")
                    c3.caption(f"GV: {row['teacher_id']} | Môn: {row['subject_id']}")
                    
                    if c4.button("🗑️ Xóa", key=f"del_class_{row['class_id']}"):
                        succ, msg = delete_class(row['class_id'])
                        if succ: st.success(msg); time.sleep(1); st.rerun()
                        else: st.error(msg)
                    st.divider()
            else:
                st.info("Chưa có lớp học nào.")

        if st.button("🔙 Quay lại Dashboard"):
            st.session_state["view_mode"] = "home"; st.rerun()

    # 4. Màn hình Chính (Dashboard / Hướng dẫn)
    else:
        # --- CSS CHO TRANG DASHBOARD ---
        st.markdown("""
        <style>
            .home-card {
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                border: 1px solid #e0e0e0;
                height: 100%;
            }
            .home-card h3 {
                color: #0078D4;
                font-size: 1.3rem;
                margin-bottom: 10px;
            }
            .home-card p {
                color: #555;
                font-size: 0.95rem;
            }
            .step-number {
                font-weight: bold;
                font-size: 1.5rem;
                color: #e0e0e0;
                float: right;
            }
        </style>
        """, unsafe_allow_html=True)

        # --- HEADER ---
        st.title("🏠 Trung tâm điều khiển")
        st.markdown(f"### Xin chào, **{user_name}**! 👋")
        
        # Thông báo quyền hạn (Nếu là Admin/Teacher)
        if user_role in ["admin", "manager", "teacher"]:
            st.info(f"🛡️ Bạn đang đăng nhập với quyền **{user_role.upper()}**. Hãy sử dụng menu **🛠️ Quản trị** ở thanh bên trái để quản lý hệ thống.")
        else:
            st.caption("Chúc bạn một ngày học tập hiệu quả!")
            
            # === 👇 [NEW] WIDGET RECOMMENDER SYSTEM (GỢI Ý HỌC TẬP) 👇 ===
            from db_utils import get_smart_recommendations
            
            # 1. Lấy môn học hiện tại (hoặc mặc định nếu chưa chọn)
            if "current_subject" not in st.session_state:
                # Tìm môn mặc định an toàn hơn
                from db_utils import get_all_subjects
                subs = get_all_subjects()
                st.session_state.current_subject = subs[0][0] if subs else "MayHoc"
                
            curr_sub = st.session_state.current_subject
            
            # 2. Gọi hàm lấy gợi ý từ DB
            recs = get_smart_recommendations(current_username, curr_sub, limit=3)
            
            if recs:
                st.markdown("---")
                st.subheader(f"🔥 Nhiệm vụ hôm nay ({curr_sub})")
                
                cols = st.columns(3)
                for i, (node_id, status, score) in enumerate(recs):
                    with cols[i]:
                        # Logic hiển thị
                        if status == 'Review':
                            msg = "🆘 Cần ôn tập gấp!"
                            icon = "🩸"
                            btn_label = "Ôn ngay 🔄"
                        elif status == 'In Progress':
                            msg = "🔥 Đang học dở"
                            icon = "🚧"
                            btn_label = "Tiếp tục 🚀"
                        elif status == 'New':
                            msg = "🌱 Bài học mới"
                            icon = "✨"
                            btn_label = "Khám phá 🆕"
                        else:
                            msg = "✨ Cải thiện điểm"
                            icon = "⭐"
                            btn_label = "Luyện thêm"
                        
                        with st.container(border=True):
                            st.markdown(f"**{icon} {node_id}**")
                            if status == 'New':
                                st.info("Sẵn sàng để học")
                            else:
                                st.progress(score, text=f"Điểm: {score:.0%}")
                            st.caption(f"*{msg}*")
                            
                            if st.button(btn_label, key=f"rec_{node_id}", use_container_width=True):
                                st.session_state["jump_to_lecture_id"] = node_id
                                st.switch_page("pages/1_📖_Bai_Giang.py")
            else:
                st.markdown("---")
                st.info(f"🎉 Bạn chưa có bài tập tồn đọng nào trong môn **{curr_sub}**. Hãy vào menu **Đồ thị tri thức** để mở khóa bài mới nhé!")

        st.divider()

        # --- QUY TRÌNH HỌC TẬP (3 BƯỚC) ---
        st.header("🚀 Quy trình học tập hiệu quả")
        st.write("Hệ thống này sử dụng **Đồ thị Tri thức** để cá nhân hóa lộ trình của bạn. Hãy tuân thủ 3 bước sau:")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("""
            <div class="home-card">
                <div class="step-number">01</div>
                <h3>📖 Nạp kiến thức</h3>
                <p>Truy cập mục <b>Bài Giảng</b> để xem video và tài liệu. Đây là bước đầu tiên để mở khóa các khái niệm mới.</p>
                <ul>
                    <li>Xem video bài giảng</li>
                    <li>Đọc tài liệu tham khảo</li>
                    <li>Đánh dấu hoàn thành</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown("""
            <div class="home-card">
                <div class="step-number">02</div>
                <h3>🎓 Luyện tập & Kiểm tra</h3>
                <p>Hệ thống sẽ <b>tự động gợi ý</b> câu hỏi dựa trên những gì bạn còn yếu. Không cần chọn bài, chỉ cần bấm "Kiểm tra".</p>
                <ul>
                    <li>Luyện tập theo lộ trình cây</li>
                    <li>Làm bài kiểm tra tổng hợp</li>
                    <li>Hệ thống tự chấm điểm</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown("""
            <div class="home-card">
                <div class="step-number">03</div>
                <h3>📈 Theo dõi & Phân tích</h3>
                <p>Xem <b>Đồ thị tri thức</b> của bạn đổi màu từ <span style='color:gray'>Xám</span> sang <span style='color:green'>Xanh</span>.</p>
                <ul>
                    <li>Xem cây kiến thức cá nhân</li>
                    <li>Phân tích điểm mạnh/yếu</li>
                    <li>Xem lại lịch sử làm bài</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- GIỚI THIỆU CÁC CHỨC NĂNG CHI TIẾT ---
        st.subheader("🧩 Chức năng chi tiết")
        
        with st.expander("📖 Bài Giảng là gì?"):
            st.write("Nơi chứa các tài liệu, slide và video bài học. Bạn cần đánh dấu 'Hoàn thành' để hệ thống ghi nhận bạn đã tiếp thu kiến thức nền.")
            
        with st.expander("🎓 Luyện Tập hoạt động thế nào?"):
            st.write("Đây là trái tim của hệ thống. Thuật toán sẽ tìm các bài học bạn chưa vững (Màu Vàng/Đỏ) hoặc các bài học tiếp theo (Màu Xám) để đưa ra câu hỏi trắc nghiệm phù hợp nhất.")
            
        with st.expander("📈 Đồ thị Tri thức dùng để làm gì?"):
            st.write("Một bản đồ trực quan hiển thị toàn bộ kiến thức môn học. Các nút sẽ đổi màu dựa trên điểm số của bạn. Mục tiêu của bạn là phủ xanh toàn bộ đồ thị.")

        st.divider()
        st.info("👈 **Bắt đầu ngay bằng cách chọn một chức năng từ thanh Sidebar bên trái!**")