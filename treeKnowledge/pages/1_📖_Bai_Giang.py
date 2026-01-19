import streamlit as st
import pandas as pd
import sys
import os
import time
import re
import streamlit.components.v1 as components # Module để hiển thị HTML/MathJax
import ast
from db_utils import (
    get_graph_structure,
    get_resource,
    save_progress,
    get_node_status,
    get_all_questions,
    get_user_settings,    # 👈 thêm
    log_activity,         # 👈 thêm
    get_user_progress,    # 👈 thêm (OPTIMIZATION)
)
# --- SETUP ĐƯỜNG DẪN ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import từ db_utils
#from db_utils import get_graph_structure, get_resource, save_progress, get_node_status
from db_utils import (
    get_graph_structure,
    get_resource,
    save_progress,
    get_node_status,
    get_all_questions,
    get_user_settings,
    log_activity,
    get_user_progress,
)


st.set_page_config(page_title="Bài Giảng", page_icon="📖", layout="wide")
# === 👇 [NEW] LOGIC DEEP LINK: NHẬN TÍN HIỆU TỪ TRANG KHÁC 👇 ===
if "jump_to_lecture_id" in st.session_state:
    target_node = st.session_state["jump_to_lecture_id"]
    # Gán vào biến điều khiển bài học đang chọn
    st.session_state.selected_lecture_node = target_node
    # Xóa tín hiệu để tránh lặp lại khi F5
    del st.session_state["jump_to_lecture_id"]
    st.toast(f"🚀 Đang chuyển đến bài: {target_node}...", icon="📖")
# ================================================================

# ============================================================
# 🎨 CSS TÙY CHỈNH (CẬP NHẬT GIAO DIỆN MỚI)
# ============================================================
st.markdown("""
    <style>
        /* 1. Căn trái nút bấm trong Sidebar */
        section[data-testid="stSidebar"] button {
            text-align: left !important;
            justify-content: flex-start !important;
            padding-left: 10px !important;
            width: 100% !important;
        }
        
        /* 2. Tùy chỉnh Expander gọn hơn */
        ul[data-testid="stExpander"] {
            padding-left: 0 !important;
        }
        
        /* 3. Tùy chỉnh ảnh trong bài giảng */
        div.stMarkdown img {
            max_width: 100%;
            height: auto;
            border-radius: 5px;
            margin-top: 10px;
            margin-bottom: 10px;
        }
        
        /* 4. Tiêu đề nhỏ gọn hơn */
        h1 {
            font-size: 26px !important;
            margin-bottom: 5px !important;
            padding-bottom: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- TẠO NEO ĐỂ CUỘN TRANG ---
st.markdown('<div id="top-of-page"></div>', unsafe_allow_html=True)

# 1. KIỂM TRA ĐĂNG NHẬP
if "authentication_status" not in st.session_state or not st.session_state["authentication_status"]:
    st.warning("🔒 Vui lòng đăng nhập để xem bài giảng."); st.stop()

username = st.session_state["username"]
role = st.session_state.get("role", "student")

# --- QUYỀN TRUY CẬP (STUDENT RESTRICTION) ---
# Student chỉ được xem môn mình đã đăng ký
from db_utils import get_student_subjects

if role == 'student':
    enrolled_subs = get_student_subjects(username) # List of tuples (id, name)
    if not enrolled_subs:
        st.error("🚫 Bạn chưa tham gia lớp học nào.")
        st.info("Vui lòng truy cập menu **Quản lý Lớp** để đăng ký tham gia lớp học.")
        if st.button("👉 Đến trang Quản lý Lớp"):
            st.switch_page("pages/8_🏫_Quan_Ly_Lop.py")
        st.stop()
    
    enrolled_ids = [s[0] for s in enrolled_subs]
    
    # Check current subject initialization
    if "current_subject" not in st.session_state or st.session_state.current_subject not in enrolled_ids:
        st.session_state.current_subject = enrolled_ids[0]

    # --- SIDEBAR: CHỌN MÔN HỌC ---
    with st.sidebar:
        st.header("📚 Chọn Môn Học")
        # Map ID -> Name
        sub_map = {s[0]: s[1] for s in enrolled_subs}
        selected_sub = st.selectbox(
            "Môn học đang xem:",
            enrolled_ids,
            format_func=lambda x: sub_map.get(x, x),
            index=enrolled_ids.index(st.session_state.current_subject) if st.session_state.current_subject in enrolled_ids else 0
        )
        
        if selected_sub != st.session_state.current_subject:
            st.session_state.current_subject = selected_sub
            st.session_state.selected_lecture_node = None # Reset lecture selection
            st.rerun()
            
    current_subject = st.session_state.current_subject

# 2. XỬ LÝ DỮ LIỆU CẤU TRÚC
# Non-students logic or fallback
if role != 'student':
    if "current_subject" not in st.session_state:
        st.session_state.current_subject = "MayHoc"
    current_subject = st.session_state.current_subject

st.title(f"📖 Thư viện Bài giảng: {current_subject}")

df_structure = get_graph_structure(current_subject)

# === Ngân hàng câu hỏi dùng lại ở nhiều chỗ ===
@st.cache_data
def load_questions_df(subject_id):
    df = get_all_questions(subject_id)
    if df is None or df.empty:
        return pd.DataFrame()
    df["skill_id_list"] = df["skill_id_list"].astype(str)
    return df

questions_df = load_questions_df(current_subject)

if df_structure.empty:
    st.error("⚠️ Chưa có dữ liệu cấu trúc bài học. Vui lòng nhờ Admin cập nhật.")
    st.stop()

# --- LOGIC GOM NHÓM & SẮP XẾP ---
structure_map = {}
all_nodes = sorted(list(set(df_structure['source'].unique()) | set(df_structure['target'].unique())))

def extract_chapter_id(node_name):
    """Hàm trích xuất ID chương để sắp xếp"""
    try:
        s_name = str(node_name)
        if s_name.startswith("Chg"):
            # Ví dụ: Chg1_TenChuong -> 1
            return int(re.search(r'\d+', s_name).group())
        elif "." in s_name: 
            # Ví dụ: 1.1 -> 1
            return int(s_name.split('.')[0])
    except:
        return 999
    return 999

# Lọc lấy các Node là Chương (bắt đầu bằng Chg)
chapters_nodes = [n for n in all_nodes if str(n).startswith("Chg")]
chapters_nodes = sorted(chapters_nodes, key=extract_chapter_id) 

# Gom nhóm bài học vào chương
for chap_node in chapters_nodes:
    structure_map[chap_node] = []
    current_chap_id = extract_chapter_id(chap_node)
    
    for node in all_nodes:
        if node == chap_node: continue 
        # Nếu node con có ID chương trùng với node cha thì gom vào
        if extract_chapter_id(node) == current_chap_id:
            structure_map[chap_node].append(node)

# --- QUẢN LÝ TRẠNG THÁI CHỌN BÀI ---
if "selected_lecture_node" not in st.session_state:
    st.session_state.selected_lecture_node = None

# === [OPTIMIZATION] BATCH FETCH PROGRESS ===
# Thay vì gọi DB trong vòng lặp, ta gọi 1 lần lấy hết tiến độ
progress_data = get_user_progress(username, current_subject)
# Convert to dict: node_id -> (status, score)
# progress_data row: (node_id, status, score, timestamp)
node_status_map = {}
if progress_data:
    for row in progress_data:
        # row[0] is node_id, row[1] is status, row[2] is score
        node_status_map[row[0]] = (row[1], row[2])

# 3. SIDEBAR: MỤC LỤC KHÓA HỌC
with st.sidebar:
    st.header("🗂️ Mục lục khóa học")
    
    # if st.button("🏠 Về trang chính", use_container_width=True):
    #     pass 

    # st.markdown("---")

    for chap in chapters_nodes:
        # Kiểm tra xem chương này có cần mở rộng không (nếu đang chọn bài bên trong)
        is_expanded = (st.session_state.selected_lecture_node == chap) or \
                      (st.session_state.selected_lecture_node in structure_map[chap])
            
        with st.expander(f"📂 {chap}", expanded=is_expanded):
            
            # Nút chọn Chương
            if st.button(f"📑 Giới thiệu chương", key=f"btn_chap_{chap}", use_container_width=True):
                st.session_state.selected_lecture_node = chap
                st.rerun()

            # Hàm key để sắp xếp bài học (VD: 1.1, 1.2, 1.10)
            def sort_lesson_key(name):
                try:
                    parts = re.split(r'[._]', str(name))
                    return [int(p) if p.isdigit() else p for p in parts]
                except: return [999]

            # List các bài học con
            # List các bài học con
            for child in sorted(structure_map[chap], key=sort_lesson_key):
                # [OPTIMIZATION] Lookup from map instead of DB call
                # status_row = get_node_status(username, child, current_subject) 
                status_info = node_status_map.get(child, None)
                
                # Icon trạng thái
                icon = "⚪"
                if status_info:
                    # status_info is (status, score)
                    if status_info[1] >= 0.7: icon = "✅"
                    elif status_info[1] > 0: icon = "🟡"
                
                # Style nút bấm
                btn_label = f"{icon}  {child}"
                type_btn = "secondary"
                if st.session_state.selected_lecture_node == child:
                    type_btn = "primary" 
                    btn_label = f"👉  {child}"

                unique_key = f"btn_child_{chap}_{child}"
                
                if st.button(btn_label, key=unique_key, use_container_width=True, type=type_btn):
                    st.session_state.selected_lecture_node = child
                    st.rerun()

# 4. HIỂN THỊ NỘI DUNG CHÍNH
current_node = st.session_state.selected_lecture_node

if current_node:
    # --- JAVASCRIPT: TỰ ĐỘNG CUỘN LÊN ĐẦU TRANG ---
    components.html(
        """
        <script>
            setTimeout(function() {
                window.parent.scrollTo({top: 0, behavior: 'auto'});
                var main = window.parent.document.querySelector('.main');
                if (main) {
                    main.scrollTo({top: 0, behavior: 'auto'});
                    main.scrollTop = 0;
                }
            }, 350); 
        </script>
        """,
        height=0
    )
    # ---------------------------------------------

    # CSS chỉnh tiêu đề bài học
    st.markdown("""
    <style>
    h3 {
        font-size: 20px !important;
        margin-top: 4px !important;
        margin-bottom: 4px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.subheader(f"📍 {current_node}")
    
    # TẠO TABS: NỘI DUNG & TRẮC NGHIỆM
    tab_content, tab_quiz = st.tabs(["📖 Nội dung bài học", "📝 Bài tập vận dụng"])
    
    with tab_content:
        # Lấy nội dung từ DB
        resource = get_resource(current_node)
        
        if resource:
            res_title = resource[1]
            res_type = resource[2] # video, pdf, markdown, html
            res_url = resource[3]
            res_desc = resource[4] # Nội dung chính

            if res_title:
                st.markdown(f"#### {res_title}")
            
            st.divider()

            # --- A. VIDEO ---
            if res_type == 'video':
                if res_url:
                    st.video(res_url)
                else:
                    st.warning("⚠️ Link video đang cập nhật.")
                if res_desc:
                    st.info(res_desc)

            # --- B. PDF ---
            elif res_type == 'pdf':
                col_link, col_desc = st.columns([1, 2])
                with col_link:
                    if res_url:
                        st.success("📄 Tài liệu sẵn sàng")
                        st.markdown(f"### [👉 Nhấn để mở tài liệu]({res_url})")
                    else:
                        st.warning("⚠️ Link tài liệu đang cập nhật.")
                with col_desc:
                    if res_desc:
                        st.markdown("### Tóm tắt nội dung")
                        st.write(res_desc)

            # --- C. TEXT / MARKDOWN / HTML (CẬP NHẬT MỚI) ---
            elif res_type in ['markdown', 'text', 'html']:
                if res_url:
                    st.markdown(f"🔗 **Link bài giảng gốc:** [{res_url}]({res_url})")

                if not res_desc:
                    st.caption("Chưa có mô tả chi tiết.")
                else:
                    # XỬ LÝ ĐẶC BIỆT CHO HTML (TỪ FILE WORD/PANDOC)
                    if res_type == 'html':
                        # Render toàn bộ HTML + MathJax trong một iframe độc lập
                        components.html(
                            f"""
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <meta charset="utf-8" />
                                <style>
                                    body {{
                                        font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
                                        padding: 0 12px 12px 12px;
                                        color: #31333F; 
                                    }}
                                    img {{
                                        max-width: 100%;
                                        height: auto;
                                        border-radius: 4px;
                                    }}
                                </style>
                                <script>
                                window.MathJax = {{
                                tex: {{
                                    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                                    displayMath: [['\\\\[', '\\\\]']]
                                }},
                                svg: {{ fontCache: 'global' }}
                                }};
                                </script>
                                <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
                            </head>
                            <body>
                            {res_desc}
                            </body>
                            </html>
                            """,
                            height=700,  # Chiều cao khung hiển thị
                            scrolling=True,
                        )
                    else:
                        # markdown/text thường không có công thức phức tạp → render như cũ
                        st.markdown(res_desc, unsafe_allow_html=True)
                    
        else:
            st.warning(f"📭 Chưa có nội dung cho: {current_node}")

    with tab_quiz:
        # --- CÂU HỎI LIÊN QUAN ĐẾN BÀI HỌC NÀY ---
        st.markdown("### 📝 Câu hỏi liên quan đến mục này")

        # CSS cho hộp câu hỏi (tương tự Đồ thị tri thức)
        st.markdown("""
        <style>
            .question-box {
                background-color: #E3F2FD; 
                border-left: 5px solid #2196F3; 
                padding: 12px 15px;
                border-radius: 5px;
                color: #0d47a1;
                font-weight: 500;
                margin-bottom: 10px;
            }
        </style>
        """, unsafe_allow_html=True)

        if questions_df.empty:
            st.caption("📭 Ngân hàng câu hỏi chưa được cấu hình.")
        else:
            # Lọc các câu hỏi có chứa current_node trong skill_id_list
            qs = questions_df[questions_df["skill_id_list"].str.contains(current_node, na=False)]
            qs = qs.reset_index(drop=True)
            total_qs = len(qs)

            if total_qs == 0:
                st.caption("Chưa có câu hỏi nào gắn với mục này.")
            else:
                # Giống logic viewer bên Đồ thị tri thức: có thanh chọn câu
                session_key = f"q_viewer_idx_{current_node}"
                if session_key not in st.session_state:
                    st.session_state[session_key] = 0

                current_idx = st.session_state[session_key]
                
                # CHIA LAYOUT: 75% Nội dung câu hỏi (Trái) - 25% Danh sách câu hỏi (Phải)
                col_q_main, col_q_nav = st.columns([3, 1], gap="large")

                # --- CỘT PHẢI: DANH SÁCH CÂU HỎI (CALENDAR STYLE) ---
                with col_q_nav:
                    st.markdown("#### 🧭 Danh sách câu")
                    
                    # Tạo lưới nút bấm (ví dụ: 4 cột)
                    nav_cols_count = 4
                    rows = (total_qs + nav_cols_count - 1) // nav_cols_count
                    
                    for r in range(rows):
                        cols = st.columns(nav_cols_count)
                        for c in range(nav_cols_count):
                            idx = r * nav_cols_count + c
                            if idx < total_qs:
                                is_active = (idx == current_idx)
                                # Kiểm tra xem câu này đã làm đúng chưa để đổi màu
                                # (Logic này cần check session_state của từng câu)
                                # q_id_check = qs.iloc[idx]["question_id"]
                                # result_key_check = f"lec_{current_node}_{q_id_check}_result"
                                # is_done_correct = st.session_state.get(result_key_check, False)
                                
                                btn_type = "primary" if is_active else "secondary"
                                # if is_done_correct and not is_active: btn_type = ... (optional)
                                
                                with cols[c]:
                                    if st.button(f"{idx+1}", key=f"btn_bg_q_{current_node}_{idx}", 
                                                 type=btn_type, use_container_width=True):
                                        st.session_state[session_key] = idx
                                        st.rerun()

                # --- CỘT TRÁI: NỘI DUNG CÂU HỎI ---
                with col_q_main:
                    # Hiển thị nội dung câu hỏi được chọn
                    row = qs.iloc[current_idx]
                    q_id = row["question_id"]

                    # Tạo các key riêng cho câu hỏi hiện tại
                    choice_key   = f"lec_{current_node}_{q_id}_choice"
                    submit_key   = f"lec_{current_node}_{q_id}_submitted"
                    result_key   = f"lec_{current_node}_{q_id}_result"

                    # Determine box colors based on result
                    box_bg = "#E3F2FD" # Default Blue
                    box_border = "#2196F3"
                    box_text = "#0d47a1"
                    
                    if st.session_state.get(submit_key, False):
                        if st.session_state.get(result_key, False):
                            # Correct -> Green
                            box_bg = "#E8F5E9"
                            box_border = "#4CAF50"
                            box_text = "#1B5E20"
                        else:
                            # Incorrect -> Red
                            box_bg = "#FFEBEE"
                            box_border = "#F44336"
                            box_text = "#B71C1C"

                    st.markdown(f"""
                    <div class="question-box" style="background-color: {box_bg}; border-left: 5px solid {box_border}; color: {box_text};">
                        ❓ Câu {current_idx + 1}: {row['content']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Parse options
                    try:
                        ops = ast.literal_eval(row["options"])
                    except Exception:
                        ops = [row["options"]]

                    # Radio đáp án
                    selected = st.radio(
                        "Lựa chọn của bạn:",
                        ops,
                        key=choice_key,
                        index=None,
                        # label_visibility="collapsed", # Bỏ collapsed để dễ nhìn hơn hoặc giữ nguyên tuỳ ý
                        disabled=st.session_state.get(submit_key, False)
                    )

                    # Nút hành động
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Nếu đã nộp -> hiển thị kết quả & giải thích
                    if st.session_state.get(submit_key, False):
                        is_correct = st.session_state.get(result_key, False)

                        if is_correct:
                            st.success("🎉 Chính xác!")
                        else:
                            st.error("❌ Sai rồi.")
                        
                        # Hiển thị giải thích ngay dưới
                        with st.expander("💡 Xem Giải thích & Đáp án", expanded=True):
                            corr_char = str(row["answer"]).strip().upper()
                            difficulty = row.get("difficulty", "Medium")
                            
                            st.markdown(f"**Đáp án đúng:** :blue[{corr_char}]")
                            st.markdown(f"**Độ khó:** {difficulty}")
                            
                            explanation = row.get("explanation", None)
                            if pd.notna(explanation):
                                st.info(explanation)
                            else:
                                st.caption("Chưa có giải thích chi tiết.")

                        # Nút làm lại
                        if st.button("Làm lại câu này", key=f"retry_{current_node}_{q_id}"):
                            st.session_state.pop(submit_key, None)
                            st.session_state.pop(result_key, None)
                            st.session_state.pop(choice_key, None)
                            st.rerun()

                    else:
                        # Chưa nộp -> nút Kiểm tra
                        if st.button("Kiểm tra ✨", key=f"check_{current_node}_{q_id}", type="primary"):
                            if not selected:
                                st.warning("⚠️ Vui lòng chọn một đáp án.")
                            else:
                                # Logic kiểm tra
                                sel_char = selected.strip()[0].upper()
                                corr_char = str(row["answer"]).strip().upper()
                                is_correct = (sel_char == corr_char)

                                # Update progress
                                mastery_threshold, learning_rate = get_user_settings(username, current_subject)
                                status_row = get_node_status(username, current_node, current_subject)
                                old_score = status_row[1] if status_row else 0.0
                                att = 1.0 if is_correct else 0.0
                                new_score = (1 - learning_rate) * old_score + learning_rate * att
                                
                                if new_score >= mastery_threshold: new_status = "Completed"
                                elif new_score <= 0.3: new_status = "Review"
                                else: new_status = "In Progress"

                                save_progress(username, current_node, current_subject, new_status, new_score)
                                log_activity(username, "lecture_quiz", current_subject, current_node, q_id, is_correct)

                                st.session_state[submit_key] = True
                                st.session_state[result_key] = is_correct
                                st.rerun()

                    # Nút điều hướng Trước / Sau
                    st.divider()
                    c_prev, _, c_next = st.columns([1, 3, 1])
                    if c_prev.button("⬅️ Câu trước", key=f"prev_bg_{current_node}", disabled=(current_idx == 0)):
                        st.session_state[session_key] -= 1
                        st.rerun()
                    if c_next.button("Câu sau ➡️", key=f"next_bg_{current_node}", disabled=(current_idx == total_qs-1)):
                        st.session_state[session_key] += 1
                        st.rerun()
                
    # --- FOOTER: TRẠNG THÁI & HOÀN THÀNH ---
    st.divider()
    status_row = get_node_status(username, current_node, current_subject)
    curr_status = status_row[0] if status_row else None
    curr_score  = status_row[1] if status_row else 0.0

    c1, c2 = st.columns([3, 1])

    with c1:
        if curr_score >= 0.7:
            st.markdown(
                "#### Trạng thái: <span style='color:green'>✅ Đã hoàn thành</span>",
                unsafe_allow_html=True,
            )
        elif curr_score > 0:
            st.markdown(
                "#### Trạng thái: <span style='color:orange'>🟡 Đang học</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown("#### Trạng thái: ⚪ Chưa học", unsafe_allow_html=True)

    with c2:
        # Nút này dùng để "chốt" bài là ĐÃ XEM / HOÀN THÀNH
        if st.button("✅ Đánh dấu Đã xem", type="primary", use_container_width=True):
            # Nếu điểm hiện tại < 0.7 thì cập nhật lên Completed 0.7
            if curr_score < 0.7:
                save_progress(
                    username,
                    current_node,
                    current_subject,
                    "Completed",
                    0.7,
                )
                st.toast("Đã đánh dấu bài này là ✅ ĐÃ HOÀN THÀNH.", icon="✅")
            else:
                # Đã hoàn thành từ trước rồi
                st.toast("Bài này đã được đánh dấu hoàn thành trước đó.", icon="ℹ️")

            st.session_state.graph_version += 1 # Force graph refresh
            st.rerun()


