import streamlit as st
import os
import sys
import time
import pandas as pd
from streamlit_agraph import agraph, Node, Edge, Config
import ast
from datetime import datetime
import re
from collections import defaultdict

# --- SETUP PATHS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# --- IMPORTS TỪ PROJECT ---
try:
    from db_utils import (
        get_user_settings, 
        save_user_settings, 
        apply_forgetting_decay,
        get_graph_structure,
        get_resource,
        get_all_questions, 
        get_node_status,
        get_mastered_question_ids,  # [NEW] Import for Smart Navigation
        get_question_status_map    # [NEW] Status Icons
    )
    # Import logic lõi từ practice_engine mới
    from practice_engine import (
        load_practice_context,
        recommend_next_skill_strict,
        pick_question_for_skill,
        grade_and_update,
        # CAT Logic
        get_smart_test_nodes,
        get_strategic_question,
        check_stopping_condition
    )
    # [HOTFIX] Force reload to apply recent grading logic updates
    import importlib
    import practice_engine
    importlib.reload(practice_engine)
except ImportError as e:
    st.error(f"Lỗi: Không tìm thấy module cần thiết. Chi tiết: {e}")
    st.stop()

# --- AUTHENTICATION CHECK ---
if "authentication_status" not in st.session_state or st.session_state["authentication_status"] is None:
    st.warning("🔒 Vui lòng đăng nhập để sử dụng tính năng này."); st.stop()

st.set_page_config(page_title="Học Tập Thông Minh", page_icon="🚀", layout="wide")

# ============================================================
# 🎨 CSS TÙY CHỈNH
# ============================================================
st.markdown("""
<style>
    /* --- BUTTON STYLES --- */
    
    /* 1. Default Button (Secondary) -> Used for Quiz Options & Navigation */
    div.stButton > button {
        background-color: #ffffff;
        color: #333;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
        /* Card-like for Options */
        text-align: left; 
        height: auto;
        white-space: normal;
        display: flex;
        align-items: center;
        width: 100%;
    }
    div.stButton > button:hover {
        border-color: #0078D4;
        background-color: #f0f8ff;
        color: #0078D4;
    }
    div.stButton > button:focus:not(:active) {
        border-color: #0078D4;
        color: #0078D4;
    }

    /* 2. Primary Button (Action) -> Used for Submit/Next */
    /* Streamlit renders primary buttons with specific classes, but we can try targeting them via hierarchy or just assume we use 'type="primary"' */
    /* Target buttons that DO NOT have the default secondary look if possible, or override with specificity */
    
    /* [HACK] In Streamlit, type="primary" renders with a specific internal structure. 
       We often rely on the fact they are "Actions". 
       Let's try to target them more specifically if possible. 
       Actually, `st.button(type="primary")` usually gets a different class but it varies.
       However, if we use the simple CSS injection, we might affect all buttons.
       Let's stick to a safe default (White) and override for Primary if we can find a hook.
       
       Tricky: Streamlit doesn't expose stable class names for "primary". 
       But the user's previous CSS targeted `button:first-child` blindly.
       
       Let's try to target the CSS based on exact usage.
       Options are in a loop.
       
       Let's Use a specific Container for Quiz Options if possible?
       Streamlit doesn't support adding classes to containers.
       
       Visual fix: 
       Let's make ALL buttons White/Card-like (Cleaner).
       And explicitly Style the "Answer" buttons.
       
       Wait, the user liked the Blue buttons for Actions.
       Let's try to inspect commonly used Streamlit Attributes.
       button[kind="primary"] or similar.
    */
    
    div.stButton > button[kind="primary"] { 
        background-color: #0078D4; 
        color: white; 
        border: none;
        text-align: center;
        justify-content: center;
    }
     div.stButton > button[kind="primary"]:hover {
        background-color: #005A9E;
     }

    /* Fallback: If `kind` attribute isn't present in this Streamlit version (likely isn't),
       we might lose the Blue buttons.
       
       Alternative:
       We keep the GLOBAL style as Blue (for backward compatibility with other pages if they share this CSS? No, this is page-specific CSS).
       And we add a STYLE BLOCK *Right before* the Options loop to override buttons to White.
       Then add a STYLE BLOCK *Right after* to reset? No, styles are global to the page.
       
       BETTER PLAN:
       Use `div[data-testid="stVerticalBlock"] > div.stButton > button` ? No.
       
       Let's try to use the `key` hack involves creating a style block that targets exact element IDs if we knew them.
       But keys are hashed.
       
       Let's go with: Make ALL buttons "Card Like" (White/Border) because that is the "NotebookLM" aesthetic (Clean, Minimal). 
       Primary actions (Next) can also be White with Blue Text/Border (Ghost buttons), or we try to keep them Blue.
       
       Let's try targeting `p` inside button for alignment.
    */
    
    div.stButton > button {
        background-color: #ffffff;
        color: #1f1f1f;
        border: 1px solid #d1d5db;
        border-radius: 12px;
        padding: 12px 20px;
        font-size: 16px;
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        
        display: block; /* Important for text wrapping */
        width: 100%;
    }
    
    div.stButton > button:hover {
        border-color: #0078D4;
        background-color: #f8fafc;
        color: #0078D4;
    }
    
    div.stButton > button:active {
        background-color: #e2e8f0;
    }
    
    /* Alignment for text inside button */
    div.stButton > button p {
        text-align: left;
        font-weight: 500;
        margin: 0;
    }
    
    /* Restore Primary Buttons (Next/Check) to be Blue if we can? 
       If not, the Ghost Button style is also very nice and modern.
       Let's verify if `type="primary"` adds `data-testid="baseButton-primary"`.
       Use: button[data-testid="baseButton-secondary"] vs button[data-testid="baseButton-primary"]
    */
    div.stButton > button[data-testid="baseButton-primary"] {
        background-color: #0078D4;
        color: white;
        border: none;
        text-align: center;
    }
    div.stButton > button[data-testid="baseButton-primary"]:hover {
        background-color: #005A9E;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    div.stButton > button[data-testid="baseButton-primary"] p {
        text-align: center;
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
    
    /* Box câu hỏi */
    .question-box {
        background-color: #E3F2FD; 
        border-left: 5px solid #2196F3; 
        padding: 12px 15px;
        border-radius: 5px;
        color: #0d47a1;
        font-weight: 500;
        margin-bottom: 10px;
        font-size: 1.1rem;
    }
    
    /* Smart Action Card */
    .smart-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        border: 1px solid #ddd;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

try:
    # ------------------------------------------------------------
    # 1. SIDEBAR CONFIG
    # ------------------------------------------------------------
    st.sidebar.title("📁 Chọn Môn Học")
    
    # Load List Subjects
    from db_utils import get_all_subjects
    all_subs = get_all_subjects() # [(id, name), ...]
    if not all_subs:
        st.error("Chưa có môn học nào.")
        st.stop()
        
    sub_names = [s[1] for s in all_subs]
    sub_ids = [s[0] for s in all_subs]
    
    if 'current_subject_idx' not in st.session_state: st.session_state.current_subject_idx = 0
    
    selected_sub_name = st.sidebar.selectbox("Môn học:", sub_names, index=st.session_state.current_subject_idx)
    selected_subject = sub_ids[sub_names.index(selected_sub_name)]
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
        st.session_state.target_skill = None
        st.session_state.current_question = None
        st.session_state.current_q_idx = 0 
        st.session_state.last_question_id = None
        st.session_state.last_state_key = state_key
        st.session_state.learning_mode = 'learning' # Default mode
        st.rerun()

    # ============================================================
    # 🧠 LOGIC & DATA LOADING
    # ============================================================
    st.title(f"🚀 Học Tập Thông Minh: {selected_subject}")
    
    # 1. Kích hoạt FASS
    if "decay_applied" not in st.session_state:
        with st.spinner("⏳ Đang tính toán đường cong lãng quên..."):
            apply_forgetting_decay(current_username, selected_subject, decay_rate=0.1)
        st.session_state.decay_applied = True

    # 2. Load dữ liệu ngữ cảnh
    k_graph_df, q_matrix_df, user_mastery = load_practice_context(current_username, selected_subject)

    # --- SESSION STATE INIT ---
    if 'current_question' not in st.session_state: st.session_state.current_question = None
    if 'answer_submitted' not in st.session_state: st.session_state.answer_submitted = False
    if 'warning_msg' not in st.session_state: st.session_state.warning_msg = None
    if 'current_q_idx' not in st.session_state: st.session_state.current_q_idx = 0
    if 'learning_mode' not in st.session_state: st.session_state.learning_mode = 'learning' # 'learning' or 'testing'
    
    # [FIX] Initialize Missing Keys
    if 'target_skill' not in st.session_state: st.session_state.target_skill = None
    if 'strategy_msg' not in st.session_state: st.session_state.strategy_msg = ""
    
    # Test Session State
    if 'smart_test_session' not in st.session_state:
         st.session_state.smart_test_session = {
             "active": False,
             "history": [],
             "start_time": None,
             "limit_minutes": 15,
             "current_q": None
         }
         
    # Dynamic Height
    if 'graph_height' not in st.session_state:
        st.session_state.graph_height = 800

    # 3. RECOMMENDATION ENGINE (ALWAYS RUNS TO FIND TARGET SKILL)
    if not st.session_state.target_skill:
        target_node, strategy, debug_log = recommend_next_skill_strict(
            user_mastery, k_graph_df, q_matrix_df, 
            threshold=mastery_threshold
        )
        st.session_state.target_skill = target_node
        st.session_state.strategy_msg = strategy
        st.rerun()

    
    # Lấy thông tin Target Skill
    t_skill = st.session_state.target_skill
    if t_skill is None: # Finished all?
        st.balloons()
        st.success("🎉 Bạn đã hoàn thành toàn bộ lộ trình!")
        st.stop()

    # ============================================================
    # 🤖 SMART ACTION DECISION
    # ============================================================
    current_skill_score = user_mastery.get(t_skill, 0.0)
    is_mastered = current_skill_score >= mastery_threshold
    
    # Logic Decision
    action_type = "learn"
    action_label = "📖 Vào học ngay"
    action_sub = "Học lý thuyết & Luyện tập"
    action_icon = "🚀"
    
    if is_mastered:
        action_type = "test"
        action_label = "⚔️ Kiểm tra Tổng hợp (CAT)"
        action_sub = "Bạn đã thành thạo! Hãy thử thách để chốt kiến thức."
        action_icon = "🏆"
        
    # ============================================================
    # 📑 TABS CONFIGURATION (4 Top-Level Tabs)
    # ============================================================
    tab_map, tab_theory, tab_practice, tab_analytics = st.tabs([
        "🗺️ Bản đồ & Lộ trình", 
        "📖 Lý thuyết & Bài giảng", 
        "📝 Luyện tập & Câu hỏi", 
        "📊 Phân tích & Chỉ số"
    ])
    
    # ============================================================
    # TAB 1: KNOWLEDGE GRAPH MAP
    # ============================================================
    with tab_map:
        if not k_graph_df.empty:
            k_graph_df['source'] = k_graph_df['source'].astype(str).str.strip()
            k_graph_df['target'] = k_graph_df['target'].astype(str).str.strip()

        # Children Map
        children_map = defaultdict(list)
        for _, row in k_graph_df.iterrows():
            children_map[str(row['source']).strip()].append(str(row['target']).strip())

        memo_calc = {} 
        db_keys = list(user_mastery.keys())

        def find_score_exact(node_id):
            return user_mastery.get(node_id)

        def find_score_fuzzy(node_id):
            if "." in node_id or str(node_id).isdigit():
                for k in db_keys:
                    if k.startswith(str(node_id) + "_") or k.startswith(str(node_id) + " "):
                        return user_mastery[k]
            return None

        def calculate_node_node_status(node, threshold):
            if node in memo_calc: return memo_calc[node]
            
            # 1. Exact Match
            score = find_score_exact(node)
            if score is not None: 
                is_m = (score >= threshold)
                memo_calc[node] = (score, is_m)
                return score, is_m
            
            # 2. Aggregation (If has children)
            kids = children_map.get(node, [])
            if kids:
                total_s = 0; all_m = True
                valid_kids = 0
                for kid in kids:
                    s, m = calculate_node_node_status(kid, threshold)
                    total_s += s
                    if not m: all_m = False
                    valid_kids += 1
                
                if valid_kids > 0:
                    avg_s = total_s / valid_kids
                    memo_calc[node] = (avg_s, all_m)
                    return avg_s, all_m

            # 3. Fuzzy Match (Fallback)
            score = find_score_fuzzy(node)
            if score is not None:
                is_m = (score >= threshold)
                memo_calc[node] = (score, is_m)
                return score, is_m

            memo_calc[node] = (0.0, False)
            return 0.0, False 

        all_nodes = set(k_graph_df['source']).union(set(k_graph_df['target']))
        node_info_map = {} 
        for n in all_nodes:
            node_info_map[n] = calculate_node_node_status(n, mastery_threshold)

        st.subheader("🗺️ Bản đồ Tri thức: Toàn cảnh")
        
        # Legend
        st.markdown("""
        <div style="display: flex; justify-content: flex-start; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 15px; font-size: 0.85rem;">
            <div style="display: flex; align-items: center;"><span style="height: 8px; width: 8px; background-color: #CFD8DC; border-radius: 50%; margin-right: 4px;"></span>0%</div>
            <div style="display: flex; align-items: center;"><span style="height: 8px; width: 8px; background-color: #FFD600; border-radius: 50%; margin-right: 4px;"></span>Đang học</div>
            <div style="display: flex; align-items: center;"><span style="height: 8px; width: 8px; background-color: #B9F6CA; border-radius: 50%; margin-right: 4px;"></span>70-84%</div>
            <div style="display: flex; align-items: center;"><span style="height: 8px; width: 8px; background-color: #00C853; border-radius: 50%; margin-right: 4px;"></span>100%</div>
             <div style="display: flex; align-items: center; border: 1px solid #D50000; padding: 1px 5px; border-radius: 8px; background-color: #FFEBEE; color: #D50000; font-weight: bold;">🎯 Mục tiêu</div>
        </div>
        """, unsafe_allow_html=True)

        # [RESTORED] Fixed Height
        current_h = 950

        # CSS Logic
        css_style = """
        <style>
        [data-testid="stVerticalBlockBorderWrapper"]:has(#graph-location-marker) {
            resize: vertical;
            overflow: auto;
            height: """ + str(current_h) + """px !important; 
            min-height: """ + str(current_h) + """px !important;
            max-height: 3000px;
            border: 2px solid #e0e0e0 !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            transition: border-color 0.3s, height 0.3s ease;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(#graph-location-marker):hover {
            border-color: #2979FF !important;
        }
        iframe { width: 100% !important; }
        </style>
        """
        st.markdown(css_style, unsafe_allow_html=True)

        # Chapters
        chapters = []
        for n in all_nodes:
             if "Chg" in str(n) or str(n).isdigit() or (len(str(n)) < 5 and "." not in str(n)):
                 chapters.append(str(n))
        try: sorted_chapters = sorted(chapters, key=lambda x: int(re.search(r'\d+', x).group()))
        except: sorted_chapters = list(chapters)

        # Build Graph
        nodes = []
        edges = []
        added_nodes = set()
        
        # [FIX] Enhanced Layout Logic (Ported from Page 3)
        # 1. Build Adjacency List for hierarchical mapping
        adj = defaultdict(list)
        for _, row in k_graph_df.iterrows():
            adj[str(row['source']).strip()].append(str(row['target']).strip())

        # 2. Map Nodes to Chapters via BFS
        node_to_chapter = {}
        for chap in chapters:
            queue = [chap]
            visited = set()
            while queue:
                curr = queue.pop(0)
                if curr not in node_to_chapter: node_to_chapter[curr] = chap
                if curr in adj:
                    for child in adj[curr]:
                        if child in chapters and child != chap: continue # Don't cross into next chapter
                        if child not in visited:
                            visited.add(child); queue.append(child)

        with st.container(border=True):
            st.markdown('<div id="graph-location-marker"></div>', unsafe_allow_html=True)
            for idx, row in k_graph_df.iterrows():
                src = str(row['source']).strip()
                tgt = str(row['target']).strip()
                final_src = src
                
                for node in [final_src, tgt]:
                    if node not in added_nodes:
                        score, is_m = node_info_map.get(node, (0.0, False))
                        color = "#CFD8DC"
                        if is_m:
                            if score >= 1.0: color = "#00C853"
                            elif score >= 0.85: color = "#69F0AE"
                            else: color = "#B9F6CA"
                        elif score > 0: color = "#FFD600"
                        
                        is_target = (node == t_skill)
                        borderColor = "#D50000" if is_target else "#2c3e50"
                        borderWidth = 6 if is_target else 2
                        shadow = {"enabled": True, "color": "#D50000", "size": 15} if is_target else {"enabled": False}
                        label_prefix = "🎯 " if is_target else ""
                        
                        is_chap = node in chapters
                        label = label_prefix + node
                        
                        if is_chap:
                             shape = "square"; size = 40; font = "bold 24px arial black"
                        else:
                             shape = "dot"; size = 30; font = {'size': 18, 'color': 'black'}
                             
                        # [FIX] Level Calculation (Zig-Zag Layout)
                        level = 0 
                        try:
                            owner_chap = node_to_chapter.get(node)
                            c_idx = -1
                            if owner_chap in sorted_chapters:
                                c_idx = sorted_chapters.index(owner_chap)
                            if c_idx != -1:
                                level = c_idx * 2 if is_chap else c_idx * 2 + 1
                        except: pass

                        nodes.append(Node(id=node, label=label, size=size, color=color, shape=shape, 
                                          font=font, borderWidth=borderWidth, border_color=borderColor, shadow=shadow,
                                          title=f"{node}\nĐiểm: {score:.0%}", level=level))
                        added_nodes.add(node)
                
                edges.append(Edge(source=final_src, target=tgt, color="#bdc3c7", width=2))
            
            # Spine
            visible_chapters_sorted = [c for c in sorted_chapters if c in added_nodes]
            for i in range(len(visible_chapters_sorted)-1):
                c1 = visible_chapters_sorted[i]; c2 = visible_chapters_sorted[i+1]
                edges.append(Edge(source=c1, target=c2, color="#2979FF", width=8, dashes=[10,10]))

            config_full = Config(
                width="100%", 
                height=f"{current_h}px", 
                directed=True, hierarchical=True,
                physics={"enabled": False, "stabilization": True},
                layout={
                    "hierarchical": {
                        "enabled": True,
                        "levelSeparation": 450, # Increased from 250 to reduce zoom-in effect
                        "nodeSpacing": 200,     # Increased from 150
                        "direction": "LR",
                        "sortMethod": "directed"
                    }
                },
                interaction={"dragView": True, "zoomView": True, "hover": True, "navigationButtons": False}
            )
            # Add unique key to prevent re-render issues (REVERTED due to TypeError)
            selected_full = agraph(nodes=nodes, edges=edges, config=config_full)

        # Dialog
        @st.dialog("Chi tiết bài học", width="large")
        def show_node_details_dialog(node_id):
            s_score, s_mastered = node_info_map.get(node_id, (0.0, False))
            st.subheader(f"📍 {node_id}")
            if s_mastered: st.success("✅ Đã hoàn thành")
            elif s_score > 0: st.warning(f"⚠️ Đang học ({s_score:.0%})")
            else: st.info("⚪ Chưa học")
            st.divider()
            t_info, t_theory_d = st.tabs(["📊 Tổng quan", "📖 Lý thuyết"])
            with t_theory_d:
                 res = get_resource(node_id)
                 if res:
                     r_title, r_type, r_url, r_desc = res[1], res[2], res[3], res[4]
                     if r_title: st.markdown(f"**{r_title}**")
                     if r_desc: st.markdown(r_desc, unsafe_allow_html=True)
                     if r_url: st.markdown(f"[Link tài liệu]({r_url})")
                 else: st.caption("Chưa có tài liệu.")
            with t_info:
                 st.write(f"Tiến độ hiện tại: {s_score:.0%}")
                 if st.button("🚀 Học bài này ngay", key=f"btn_study_{node_id}", type="primary", use_container_width=True):
                     st.session_state.target_skill = node_id
                     st.rerun()

        if selected_full: show_node_details_dialog(selected_full)

    # ============================================================
    # TAB 2: THEORY & LECTURE
    # ============================================================
    with tab_theory:
        # RECOMMENDATION CARD
        strat_info = st.session_state.get('strategy_msg', {})
        reason_desc = "Tiếp tục lộ trình."
        if isinstance(strat_info, dict): reason_desc = strat_info.get("reason_desc", reason_desc)
        elif isinstance(strat_info, str): reason_desc = strat_info

        st.markdown(f"""
        <div class="smart-card" style="margin-bottom: 20px;">
            <div style="display:flex; align-items:center; gap: 15px;">
                <div style="font-size: 2rem;">{action_icon}</div>
                <div>
                    <h4 style="margin:0;">Đề xuất: {t_skill}</h4>
                    <p style="margin:0; color:#666; font-size:0.9rem;">{action_sub}</p>
                </div>
            </div>
            <hr style="margin: 10px 0;">
            <p style="font-size: 0.85rem; color: #0078D4; margin:0;">
                <strong>💡 Tại sao?</strong> {reason_desc}
            </p>
        </div>
        """, unsafe_allow_html=True)

        if is_mastered:
             peek_node, _, _ = recommend_next_skill_strict(user_mastery, k_graph_df, q_matrix_df, threshold=mastery_threshold)
             if peek_node and peek_node != t_skill:
                 st.info(f"🎉 Bạn đã thành thạo **{t_skill}**. Bước tiếp theo:")
                 if st.button(f"➡️ Học bài tiếp theo: {peek_node}", type="primary", use_container_width=True):
                     st.session_state.target_skill = peek_node
                     st.session_state.current_q_idx = 0
                     st.rerun()
             else:
                 st.success("Bạn đã làm chủ chủ đề này!")
        
        st.divider()

        # CONTENT
        resource = get_resource(t_skill)
        if resource:
            try: res_title, res_type, res_url, res_desc = resource[1], resource[2], resource[3], resource[4]
            except: res_title, res_type, res_url, res_desc = "Bài học", "text", "", ""
            st.subheader(f"📚 {res_title if res_title else t_skill}")
            if res_type == 'video':
                if res_url: st.video(res_url)
                if res_desc: st.info(res_desc)
            elif res_type == 'pdf':
                if res_url: st.markdown(f'<iframe src="{res_url}" width="100%" height="600"></iframe>', unsafe_allow_html=True)
            elif res_type == 'html':
                if res_desc: st.components.v1.html(res_desc, height=500, scrolling=True)
            else:
                st.markdown(res_desc if res_desc else "Nội dung đang cập nhật.")

    # ============================================================
    # TAB 3: PRACTICE
    # ============================================================
    # ============================================================
    # 🎨 CSS TÙY CHỈNH (Quiz Update)
    # ============================================================
    st.markdown("""
    <style>
        /* CSS cho Option Card */
        .quiz-card-container {
            font-family: 'Source Sans Pro', sans-serif;
            margin-bottom: 20px;
        }
        .option-card {
            padding: 16px 20px;
            border-radius: 12px;
            margin-bottom: 12px;
            border: 1px solid #e0e0e0;
            background-color: #ffffff;
            transition: all 0.2s ease;
            position: relative;
        }
        
        /* Trạng thái CHÍNH XÁC */
        .option-card.correct {
            background-color: #DFF6DD; /* Light Green */
            border: 1px solid #107C10;
            color: #107C10;
        }
        
        /* Trạng thái SAI */
        .option-card.incorrect {
            background-color: #FDE7E9; /* Light Red */
            border: 1px solid #A80000;
            color: #A80000;
        }
        
        /* Trạng thái Neutral (Không chọn) */
        .option-card.neutral {
            background-color: #f9f9f9;
            border: 1px solid #eaeaea;
            color: #888;
            opacity: 0.7;
        }

        .card-header {
            font-weight: 600;
            font-size: 1rem;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .feedback-content {
            margin-top: 8px;
            font-size: 0.95rem;
            color: #333;
            background-color: rgba(255,255,255,0.5);
            padding: 8px;
            border-radius: 6px;
        }
        .option-card.correct .feedback-content { color: #0b500b; }
        .option-card.incorrect .feedback-content { color: #720000; }

        /* Icon Styles */
        .status-icon {
            font-size: 1.2rem;
            margin-right: 5px;
        }
        
        /* Button Style Override for Quiz Options */
        /* Note: Streamlit buttons are hard to style individually without Container Width hacks */
    </style>
    """, unsafe_allow_html=True)
    
    # ... (Tabs Config) ...

    # ============================================================
    # TAB 3: PRACTICE
    # ============================================================
    with tab_practice:
        if action_type == 'test': # CAT MODE
             st.info("Hệ thống đề xuất bạn làm bài kiểm tra CAT để đánh giá lại kỹ năng này.")
             
             # Calculate next skill for recommendation
             peek_node, _, _ = recommend_next_skill_strict(user_mastery, k_graph_df, q_matrix_df, threshold=mastery_threshold)
             
             c_cat, c_next = st.columns([1, 1])
             
             with c_cat:
                 if st.button("⚔️ Làm bài Test (CAT) ngay", type="primary", use_container_width=True):
                     st.session_state.learning_mode = 'testing'
                     st.session_state.smart_test_session["active"] = True
                     st.session_state.smart_test_session["target_nodes"] = [t_skill]
                     st.session_state.smart_test_session["start_time"] = datetime.now()
                     st.rerun()
             
             with c_next:
                 if peek_node and peek_node != t_skill:
                     if st.button(f"➡️ Học bài tiếp theo: {peek_node}", use_container_width=True):
                         st.session_state.target_skill = peek_node
                         st.session_state.current_q_idx = 0
                         st.rerun()
        
        # Load Questions
        q_data_dict = get_all_questions(selected_subject)
        relevant_qs = []
        if not q_data_dict.empty:
            for _, row in q_data_dict.iterrows():
                s_list = row['skill_id_list']
                if pd.isna(s_list): continue
                if t_skill in str(s_list): relevant_qs.append(row.to_dict())
        
        total_qs_count = len(relevant_qs)

        # [FIX] Define current_idx early for Header usage
        if 'current_q_idx' not in st.session_state: st.session_state.current_q_idx = 0
        current_idx = st.session_state.current_q_idx
        if current_idx >= total_qs_count: 
            current_idx = 0
            st.session_state.current_q_idx = 0

        # Header
        h_col1, h_col2 = st.columns([2.5, 1])
        with h_col1:
            st.subheader(f"📝 Luyện tập: {t_skill}")
            st.caption(f"📚 {current_idx + 1} / {total_qs_count}")
            
            # [SMART NAVIGATION] Auto-Jump logic (Existing)
            if total_qs_count > 0:
                mastered_ids = get_mastered_question_ids(current_username, selected_subject, t_skill)
                q_status_map = get_question_status_map(current_username, selected_subject, t_skill)
                smart_start_idx = 0
                for idx, q in enumerate(relevant_qs):
                    if q['question_id'] not in mastered_ids:
                        smart_start_idx = idx
                        break
                prev_skill = st.session_state.get('prev_skill_practice')
                if prev_skill != t_skill:
                    st.session_state.current_q_idx = smart_start_idx
                    current_idx = smart_start_idx # Update local var
                    st.session_state.prev_skill_practice = t_skill

        with h_col2:
            curr_score = user_mastery.get(t_skill, 0.0)
            progress_val = min(curr_score / mastery_threshold, 1.0)
            st.progress(progress_val, text=f"Điểm: {curr_score:.0%} / {mastery_threshold:.0%}")

        if total_qs_count == 0:
            st.warning("📭 Chưa có câu hỏi nào cho kỹ năng này.")
        else:
            st.divider()
            
            # --- NAVIGATION IN EXPANDER ---
            with st.expander("🗓️ Danh sách câu hỏi", expanded=False):
                grid_cols = st.columns(10)
                def set_q_index(idx):
                    st.session_state.current_q_idx = idx
                    st.session_state.warning_msg = None

                for i in range(total_qs_count):
                    is_active = (i == current_idx)
                    btn_type = "primary" if is_active else "secondary"
                    q_now = relevant_qs[i]
                    q_stat = q_status_map.get(q_now['question_id'])
                    label = f"{i+1}"
                    if q_stat == 'correct': label += " ✅"
                    elif q_stat == 'incorrect': label += " ❌"
                    
                    with grid_cols[i % 10]:
                         st.button(label, key=f"btn_nav_q_{t_skill}_{i}", 
                                   type=btn_type, use_container_width=True,
                                   on_click=set_q_index, args=(i,))

            # --- MAIN QUESTION CONTENT (NOTEBOOKLM STYLE) ---
            q_row = relevant_qs[current_idx]
            q_unique_key = f"{t_skill}_{q_row['question_id']}"
            
            # Question Text
            st.markdown(f"""
            <div style="font-size: 1.25rem; font-weight: 600; color: #1f1f1f; margin-bottom: 20px;">
                {q_row['content']}
            </div>
            """, unsafe_allow_html=True)
            
            try: ops = ast.literal_eval(q_row['options'])
            except: ops = []
            
            # Check previous result
            res_data = st.session_state.get(f"res_{q_unique_key}") # (is_correct, corr_text/selected_opt, user_selection)
            
            # Handle old format (is_correct, corr_text) vs new format
            user_selected_opt = None
            is_correct_prev = False
            
            if res_data:
                # Compatibility check
                if len(res_data) == 3: is_correct_prev, corr_text, user_selected_opt = res_data
                else: is_correct_prev, corr_text = res_data # Fallback

            submitted = (res_data is not None)
            
            # RENDER OPTIONS
            if not submitted:
                # INTERACTIVE MODE
                for opt in ops:
                    # Callback for option click
                    def on_option_click(selected_opt_text):
                        st.session_state.warning_msg = None
                        is_correct, new_score, corr_text, status = practice_engine.grade_and_update(
                            q_data=q_row,
                            selected_option=selected_opt_text,
                            username=current_username,
                            subject_id=selected_subject,
                            node_id=t_skill,
                            user_mastery=user_mastery,
                            q_matrix_df=q_matrix_df,
                            mastery_threshold=mastery_threshold,
                            learning_rate=learning_rate,
                            duration=0, strategy_info="Manual Practice"
                        )
                        # Save extended result: (is_correct, corr_text, user_selection)
                        st.session_state[f"res_{q_unique_key}"] = (is_correct, corr_text, selected_opt_text)
                        
                        if new_score >= mastery_threshold: st.toast("Đã thành thạo! 🎉", icon="🏆")
                        else: st.toast(f"Cập nhật kết quả: {new_score:.0%}")
                        st.rerun()
                        
                    st.button(opt, key=f"btn_opt_{q_unique_key}_{opt}", 
                              use_container_width=True, 
                              on_click=on_option_click, args=(opt,))
            else:
                # RESULT MODE (NOTEBOOKLM CARDS)
                correct_answer_text = str(res_data[1])
                # Clean up if it contains debug dump
                if "NAME: ANSWER" in correct_answer_text: correct_answer_text = "Xem giải thích chi tiết"

                expl = q_row.get('explanation', '')
                if pd.isna(expl) or str(expl).lower() == 'nan': expl = "Không có giải thích chi tiết."
                
                for opt in ops:
                    card_class = "neutral"
                    feedback_html = ""
                    icon_html = ""
                    
                    is_this_selected = (opt == user_selected_opt)
                    
                    # Determine State
                    if is_this_selected:
                        if is_correct_prev:
                            card_class = "correct"
                            icon_html = "✅"
                            feedback_html = f"""<div class="feedback-content"><strong>Right answer</strong><br>{expl}</div>"""
                        else:
                            card_class = "incorrect"
                            icon_html = "❌"
                            feedback_html = f"""<div class="feedback-content"><strong>Not quite</strong><br>Đáp án đúng là lựa chọn khác.</div>"""
                    elif opt == user_selected_opt and not is_correct_prev: # Should not happen based on logic above
                         pass 
                    
                    # Logic: If user was wrong, we SHOULD also highlight the correct answer (Green)
                    
                    # Check if this option matches the correct answer
                    is_actually_correct = (opt.strip() == correct_answer_text.strip()) or (opt.startswith(correct_answer_text.split('.')[0] + ".")) # basic heuristic
                    
                    if not is_correct_prev and is_actually_correct and not is_this_selected:
                        card_class = "correct"
                        icon_html = "✅"
                        feedback_html = f"""<div class="feedback-content"><strong>Right answer</strong><br>{expl}</div>"""

                    
                    st.markdown(f"""
                    <div class="option-card {card_class}">
                        <div class="card-header">
                            {icon_html} <span>{opt}</span>
                        </div>
                        {feedback_html}
                    </div>
                    """, unsafe_allow_html=True)

            # Footer Controls
            st.markdown("<br>", unsafe_allow_html=True)
            col_b1, col_b2 = st.columns([1, 4])
            
            with col_b1:
                if submitted:
                    st.button("🔄 Làm lại", key=f"retry_{q_unique_key}", 
                              on_click=lambda: st.session_state.pop(f"res_{q_unique_key}", None))
            
            with col_b2:
                if current_idx < total_qs_count - 1:
                     st.button("Câu tiếp theo ➡️", key=f"next_seq_{current_idx}", type="primary",
                               on_click=lambda: setattr(st.session_state, 'current_q_idx', current_idx + 1))
                else:
                    if submitted and is_correct_prev:
                        st.success("🎉 Bạn đã hoàn thành câu hỏi cuối cùng của kỹ năng này!")

            # Detailed Explanation Toggle (Optional extra)
            if submitted and not is_correct_prev:
                 with st.expander("💡 Xem giải thích chi tiết"):
                     st.info(f"Đáp án đúng: {correct_answer_text}")
                     st.write(expl)


    # ============================================================
    # TAB 4: ANALYTICS
    # ============================================================
    with tab_analytics:
        st.subheader("📊 Số liệu học tập")
        uniq_nodes = set(k_graph_df['source']).union(set(k_graph_df['target']))
        total_skills = len(uniq_nodes) if uniq_nodes else 1
        
        mastered_count = sum(1 for s in user_mastery.values() if s >= mastery_threshold)
        decay_count = sum(1 for s in user_mastery.values() if 0 < s < 0.4) 
        new_count = total_skills - mastered_count - decay_count
        if new_count < 0: new_count = 0
        
        p_master = (mastered_count / total_skills) * 100
        p_decay = (decay_count / total_skills) * 100
        p_new = (new_count / total_skills) * 100
        
        st.markdown(f"""
        <div style="display: flex; height: 30px; width: 100%; background-color: #f0f2f6; border-radius: 15px; overflow: hidden; margin-bottom: 12px; border: 1px solid #e0e0e0;">
            <div style="width: {p_master}%; background-color: #00C853;" title="Đã thạo: {mastered_count}">{f"{p_master:.0f}%" if p_master>5 else ""}</div>
            <div style="width: {p_decay}%; background-color: #FF1744;" title="Cần ôn: {decay_count}">{f"{p_decay:.0f}%" if p_decay>5 else ""}</div>
            <div style="width: {p_new}%; background-color: #B0BEC5;" title="Chưa học: {new_count}"></div>
        </div>
        """, unsafe_allow_html=True)
        
        if decay_count > 0:
            st.error(f"🚨 Có {decay_count} kỹ năng yếu.")
            weak_skills = [node for node, score in user_mastery.items() if 0 < score < 0.4]
            # Grid
            cols = st.columns(3)
            for idx, w in enumerate(weak_skills):
                 with cols[idx % 3]: st.error(w)

except Exception as e:
    import traceback
    st.error("❌ Đã xảy ra lỗi nghiêm trọng (White Screen Error):")
    st.code(traceback.format_exc())
