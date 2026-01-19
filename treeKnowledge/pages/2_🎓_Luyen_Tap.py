import streamlit as st
import os
import sys
import time

# --- SETUP PATHS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# --- IMPORTS TỪ PROJECT ---
try:
    from db_utils import (
        get_user_settings, 
        save_user_settings, 
        apply_forgetting_decay
    )
    # Import logic lõi từ practice_engine mới
    from practice_engine import (
        load_practice_context,
        recommend_next_skill_strict,
        pick_question_for_skill,
        grade_and_update
    )
except ImportError as e:
    st.error(f"Lỗi: Không tìm thấy module cần thiết. Chi tiết: {e}")
    st.stop()

# --- AUTHENTICATION CHECK ---
if "authentication_status" not in st.session_state or st.session_state["authentication_status"] is None:
    st.warning("🔒 Vui lòng đăng nhập để sử dụng tính năng này."); st.stop()

st.set_page_config(page_title="Luyện tập", page_icon="🎓", layout="wide")

# ============================================================
# 🎨 CSS TÙY CHỈNH GIAO DIỆN (BLUE THEME & CARD UI)
# ============================================================
st.markdown("""
<style>
    /* Nút bấm chính (Primary) màu Xanh Dương */
    div.stButton > button:first-child {
        background-color: #0078D4;
        color: white;
        border-radius: 6px;
        border: none;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    div.stButton > button:first-child:hover {
        background-color: #005A9E;
        border-color: #005A9E;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* Khung kết quả */
    .result-box {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        text-align: center;
        font-weight: bold;
        font-size: 1.1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .success-box { background-color: #DFF6DD; color: #107C10; border: 1px solid #107C10; }
    .error-box { background-color: #FDE7E9; color: #A80000; border: 1px solid #A80000; }
    
    /* Tiêu đề câu hỏi */
    .question-text {
        font-size: 1.2rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 15px;
    }
    .stRadio > div { gap: 12px; padding-top: 10px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 🚨 ERROR BOUNDARY (DEBUGGING WHITE SCREEN)
# ============================================================
try:
    print("DEBUG: Starting Luyen_Tap execution...")
    # ============================================================
    # 🎛️ SIDEBAR: CẤU HÌNH & SETTINGS
    # ============================================================
    st.sidebar.header("📂 Chọn Môn Học")
    def get_subjects():
        root = os.path.join(parent_dir, "knowledge")
        if not os.path.exists(root): return []
        all_subs = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
        
        # Filter for Student
        role = st.session_state.get('role', 'guest')
        if role == 'student':
            try:
                from db_utils import get_student_subjects
                username = st.session_state.get('username')
                # get_student_subjects returns [(id, name), ...]
                enrolled = get_student_subjects(username)
                enrolled_ids = [item[0] for item in enrolled]
                
                # Only return subjects that exist on disk AND are enrolled
                filtered = [s for s in all_subs if s in enrolled_ids]
                # Fallback: If enrolled list is empty (new student), show warning or empty?
                # User wants "Only enrolled". So if empty, return empty list (or handle graceful stop).
                return filtered
            except ImportError:
                 pass # Fallback to all
                 
        return all_subs

    subjects = get_subjects()
    if not subjects: st.stop()

    # Xử lý chọn môn học
    if "current_subject" not in st.session_state: st.session_state.current_subject = subjects[0]
    default_index = subjects.index(st.session_state.current_subject) if st.session_state.current_subject in subjects else 0
    selected_subject = st.sidebar.selectbox("Môn học:", subjects, index=default_index, key="sb_pra_fix_final")
    st.session_state.current_subject = selected_subject

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Cấu hình Cá nhân")

    current_username = st.session_state.get('username', 'guest')
    db_threshold, db_alpha = get_user_settings(current_username, selected_subject)

    new_threshold = st.sidebar.slider(
        "🎯 Ngưỡng thành thạo:", 0.5, 1.0, float(db_threshold), 0.05,
        key="slider_threshold_pra",
        help="Điểm số cần đạt để coi là 'Hoàn thành' bài học."
    )

    new_alpha = st.sidebar.slider(
        "⚡ Tốc độ học (Alpha):", 0.1, 1.0, float(db_alpha), 0.1,
        key="slider_alpha_pra",
        help="Tốc độ thay đổi điểm số. Cao = Thay đổi nhanh."
    )

    if new_threshold != db_threshold or new_alpha != db_alpha:
        save_user_settings(current_username, selected_subject, new_threshold, new_alpha)
        st.rerun()

    mastery_threshold = new_threshold
    learning_rate = new_alpha

    st.sidebar.markdown("---")
    st.sidebar.write(f"👤 **{st.session_state.get('name', 'User')}**")

    # Reset state khi đổi cấu hình/môn học
    state_key = f"{selected_subject}_{mastery_threshold}_{learning_rate}"
    if "last_state_key" not in st.session_state: st.session_state.last_state_key = state_key
    if st.session_state.last_state_key != state_key:
        st.session_state.current_question = None
        st.session_state.last_question_id = None
        st.session_state.last_state_key = state_key
        st.rerun()

    # ============================================================
    # 🧠 LOGIC & DATA LOADING
    # ============================================================
    st.title(f"🎓 Luyện tập: {selected_subject}")

    # 1. Kích hoạt FASS (Forgetting Curve) - Chỉ chạy 1 lần khi load trang
    if "decay_applied" not in st.session_state:
        with st.spinner("⏳ Đang tính toán đường cong lãng quên..."):
            apply_forgetting_decay(current_username, selected_subject, decay_rate=0.1)
        st.session_state.decay_applied = True

    # 2. Load dữ liệu ngữ cảnh (Sử dụng hàm từ practice_engine)
    k_graph_df, q_matrix_df, user_mastery = load_practice_context(current_username, selected_subject)

    # --- SESSION STATE INIT ---
    if 'current_question' not in st.session_state: st.session_state.current_question = None
    if 'last_question_id' not in st.session_state: st.session_state.last_question_id = None
    if 'answer_submitted' not in st.session_state: st.session_state.answer_submitted = False
    if 'warning_msg' not in st.session_state: st.session_state.warning_msg = None

    # 3. Logic lấy câu hỏi mới (Nếu chưa có)
    if st.session_state.current_question is None:
        # A. Tìm node (skill) tiếp theo cần học
        target_node, strategy, debug_log = recommend_next_skill_strict(
            user_mastery, k_graph_df, q_matrix_df, 
            threshold=mastery_threshold
        )

        # B. Xử lý kết quả tìm node
        if target_node is None:
            # Trường hợp đã học xong hết hoặc không tìm thấy
            st.balloons()
            st.success(strategy) # strategy lúc này chứa thông báo hoàn thành
            if st.button("Làm lại từ đầu"):
                st.session_state.last_question_id = None
                st.rerun()
            with st.expander("Chi tiết Debug"):
                for line in debug_log: st.markdown(line)
            st.stop()
        
        # C. Lấy câu hỏi cho node đó (Sử dụng hàm từ practice_engine)
        # Lấy điểm hiện tại của skill này để chọn độ khó phù hợp
        cur_score = user_mastery.get(target_node, 0.0)
        
        q_dict = pick_question_for_skill(
            target_node, q_matrix_df, 
            current_mastery=cur_score,
            last_question_id=st.session_state.last_question_id,
            shuffle=True # Engine tự xử lý trộn đáp án
        )

        if q_dict:
            st.session_state.current_question = q_dict
            st.session_state.target_skill = target_node
            st.session_state.strategy_msg = strategy
            st.session_state.debug_info = debug_log
            st.session_state.answer_submitted = False
            # --- TIMER STARTED ---
            st.session_state.question_start_time = time.time()
            st.rerun()
        else:
            st.warning("⚠️ Đã tìm được chủ đề nhưng không tìm thấy câu hỏi phù hợp.")
            st.stop()

    # ============================================================
    # 🖥️ GIAO DIỆN CHÍNH (CARD UI 2 CỘT)
    # ============================================================
    print(f"DEBUG: Rendering UI. Question: {st.session_state.current_question is not None}")
    
    q_data = st.session_state.current_question
    t_skill = st.session_state.target_skill

    # Header Thông tin
    curr_score = user_mastery.get(t_skill, 0.0)
    st.info(f"🎯 Mục tiêu: **{t_skill}**")
    progress_val = min(1.0, curr_score / mastery_threshold)
    st.progress(progress_val, text=f"Tiến độ hiện tại: {curr_score:.0%} / {mastery_threshold:.0%}")

    # --- FUNCTION: XỬ LÝ NỘP BÀI ---
    def submit_handler():
        # 1. Validate
        sel = st.session_state.get("user_choice_key")
        if not sel:
            st.session_state.warning_msg = "⚠️ Vui lòng chọn một đáp án!"
            return

        st.session_state.warning_msg = None
        st.session_state.answer_submitted = True
        
        # Calculate duration
        start_t = st.session_state.get('question_start_time', time.time())
        duration = time.time() - start_t
        
        # Strategy context
        strat_info = st.session_state.get('strategy_msg', 'Unknown')

        # 2. Gọi Engine để chấm điểm và update DB
        is_correct, new_score, corr_text, status = grade_and_update(
            q_data=q_data,
            selected_option=sel,
            username=current_username,
            subject_id=selected_subject,
            node_id=t_skill,
            user_mastery=user_mastery,
            q_matrix_df=q_matrix_df,
            mastery_threshold=mastery_threshold,
            learning_rate=learning_rate,
            duration=duration,
            strategy_info=strat_info
        )

        # 3. Lưu kết quả hiển thị ra UI
        st.session_state.last_result = is_correct
        st.session_state.last_correct_ans = corr_text
        st.session_state.new_score_display = new_score
        
        # Lưu ID để tránh lặp ngay lập tức
        st.session_state.last_question_id = q_data['question_id']
        
        # Reset FASS flag để lần sau vào lại sẽ tính lại decay nếu cần
        st.session_state.decay_applied = False

    # --- UI CARD ---
    with st.container(border=True):
        col_content, col_action = st.columns([7, 3], gap="large")
        
        # --- CỘT TRÁI: NỘI DUNG CÂU HỎI ---
        with col_content:
            st.markdown(f"<div class='question-text'>❓ {q_data['content']}</div>", unsafe_allow_html=True)
            
            # Parse options để hiển thị (Engine đã shuffle và lưu dạng string list trong q_data['options'])
            import ast
            try: ops = ast.literal_eval(q_data['options'])
            except: ops = []
            
            st.radio(
                "Lựa chọn của bạn:", 
                ops, 
                key="user_choice_key", 
                index=None, 
                label_visibility="collapsed",
                disabled=st.session_state.answer_submitted
            )

        # --- CỘT PHẢI: ACTIONS & FEEDBACK ---
        with col_action:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            
            if st.session_state.answer_submitted:
                # === KẾT QUẢ SAU KHI NỘP ===
                if st.session_state.last_result:
                    st.markdown("<div class='result-box success-box'>🎉 CHÍNH XÁC!</div>", unsafe_allow_html=True)
                    st.balloons()
                else:
                    st.markdown("<div class='result-box error-box'>❌ SAI RỒI</div>", unsafe_allow_html=True)
                    st.caption("💡 **Đáp án đúng:**")
                    st.info(st.session_state.last_correct_ans)
                    
                    # Thông báo nhỏ về việc phạt kiến thức cha (nếu có)
                    st.toast("Kiến thức nền tảng đã được kiểm tra lại.", icon="⚠️")
                
                # Hiển thị điểm số mới
                # st.metric("Điểm kỹ năng mới", f"{st.session_state.new_score_display:.0%}")

                # Nút Next
                if st.button("Câu tiếp theo ➡", type="primary", use_container_width=True):
                    st.session_state.answer_submitted = False
                    st.session_state.last_result = None
                    st.session_state.warning_msg = None
                    st.session_state.current_question = None
                    if "user_choice_key" in st.session_state:
                        del st.session_state["user_choice_key"]
                    st.rerun()
                    
            else:
                # === TRẠNG THÁI CHƯA NỘP ===
                if st.session_state.warning_msg:
                    st.warning(st.session_state.warning_msg, icon="⚠️")
                    
                if st.button("Kiểm tra ✨", type="primary", use_container_width=True):
                    submit_handler()
                    st.rerun()

    # --- DEBUG INFO ---
    with st.expander("ℹ️ Chi tiết lộ trình (Debug)"):
        st.write(f"**Strategy:** {st.session_state.get('strategy_msg', '')}")
        st.write("---")
        for line in st.session_state.get('debug_info', []):
            st.markdown(line)

except Exception as e:
    import traceback
    print(f"CRITICAL ERROR in Luyen_Tap: {e}")
    print(traceback.format_exc())
    st.error("❌ Đã xảy ra lỗi nghiêm trọng (White Screen Error):")
    st.code(traceback.format_exc())
    st.warning("Vui lòng chụp ảnh màn hình này và gửi cho Admin để sửa lỗi.")
    
# DEBUG FOOTER
print("DEBUG: End of Luyen_Tap script reached.")