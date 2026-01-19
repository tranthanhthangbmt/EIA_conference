import streamlit as st
import pandas as pd
import numpy as np
import ast
import os
import sys
import random
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from streamlit_agraph import agraph, Node, Edge, Config # [NEW] Interactive Graph

# --- SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from db_utils import (
    get_user_progress, save_progress, log_activity, 
    get_all_chapters, get_graph_structure, get_all_questions,
    get_students_in_class, get_test_packet, get_all_subjects # [NEW]
)


if "authentication_status" not in st.session_state or st.session_state["authentication_status"] is None:
    st.warning("🔒 Đăng nhập."); st.stop()

st.set_page_config(page_title="Kiểm tra & Đánh giá", page_icon="📝", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    /* --- BUTTON STYLES (From Page 2) --- */
    
    div.stButton > button {
        background-color: #ffffff;
        color: #1f1f1f;
        border: 1px solid #d1d5db;
        border-radius: 12px;
        padding: 12px 20px;
        font-size: 16px;
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        display: block; 
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
    div.stButton > button p {
        text-align: left;
        font-weight: 500;
        margin: 0;
    }
    
    /* Primary Action Buttons (Blue) */
    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="baseButton-primary"] {
        background-color: #0078D4;
        color: white;
        border: none;
        text-align: center;
        justify-content: center;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[data-testid="baseButton-primary"]:hover {
        background-color: #005A9E;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    div.stButton > button[kind="primary"] p,
    div.stButton > button[data-testid="baseButton-primary"] p {
        text-align: center;
    }

    /* Page 4 Specifics */
    .timer-box {
        font-size: 1.5rem;
        font-weight: bold;
        color: #d9534f;
        text-align: center;
        border: 2px solid #d9534f;
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .diagnostic-card {
        background-color: #e8f5e9;
        border: 1px solid #4caf50;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    
    /* Result & Question Boxes */
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
    
    /* Option Cards (Feedback) */
    .option-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        background-color: white;
    }
    .option-card.correct { border-left: 5px solid #107C10; background-color: #F0FDF4; }
    .option-card.incorrect { border-left: 5px solid #A80000; background-color: #FEF2F2; }
    .option-card.neutral { border-left: 5px solid #ccc; }
    
    .feedback-content {
        margin-top: 8px;
        font-size: 0.95rem;
        padding: 8px;
        border-radius: 6px;
        background-color: rgba(255,255,255,0.5);
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# 1. SIDEBAR CONFIG (Added Subject Selection)
# ------------------------------------------------------------
st.sidebar.title("📁 Chọn Môn Học")

all_subs = get_all_subjects() 
if not all_subs:
    st.error("Chưa có môn học nào.")
    st.stop()
    
sub_names = [s[1] for s in all_subs]
sub_ids = [s[0] for s in all_subs]

if 'current_subject_idx' not in st.session_state: st.session_state.current_subject_idx = 0

# Ensure index is valid
if st.session_state.current_subject_idx >= len(sub_names):
     st.session_state.current_subject_idx = 0

selected_sub_name = st.sidebar.selectbox("Môn học:", sub_names, index=st.session_state.current_subject_idx)
selected_subject = sub_ids[sub_names.index(selected_sub_name)]
st.session_state.current_subject = selected_subject

st.sidebar.markdown("---")
st.sidebar.write(f"👤 **{st.session_state.get('name', 'User')}**")
st.sidebar.markdown("---")

# --- DATA LOADING ---
current_subject = st.session_state.get("current_subject", "MayHoc")
username = st.session_state.get("username", "guest")

# [Thêm vào phần Helper Functions]

# --- HELPER FUNCTIONS ---
@st.cache_data(ttl=300) # Cache 5 phút để tránh tính toán lại liên tục
def get_smart_test_nodes(username, subject_id):
    """
    Thuật toán tìm các Node cần kiểm tra dựa trên Cây tri thức:
    1. Tìm Frontier Nodes (Cha đã xong, con chưa xong).
    2. Tìm Review Nodes (Cần ôn tập).
    """
    # 1. Lấy dữ liệu
    progress = get_user_progress(username, subject_id)
    user_map = {r[0]: {'status': r[1], 'score': r[2]} for r in progress}
    
    # Lấy cấu trúc cây
    parents_map = {} # node -> [parents]
    all_nodes = set()
    
    # Build graph map
    for _, row in k_graph_df.iterrows():
        src, tgt = str(row['source']), str(row['target'])
        if tgt not in parents_map: parents_map[tgt] = []
        parents_map[tgt].append(src)
        all_nodes.add(src); all_nodes.add(tgt)
        
    target_nodes = set()
    
    # LOGIC 1: REVIEW (Ưu tiên cao nhất)
    for node, info in user_map.items():
        if info['status'] == 'Review' or (info['status'] == 'In Progress' and info['score'] < 0.5):
            target_nodes.add(node)
            
    # LOGIC 2: FRONTIER (Vùng biên)
    # Node chưa xong (hoặc chưa học) NHƯNG tất cả cha đã xong
    for node in all_nodes:
        # Bỏ qua nếu node đã master
        if node in user_map and user_map[node]['score'] >= 0.8:
            continue
            
        parents = parents_map.get(node, [])
        if not parents: # Node gốc
            # Nếu chưa học node gốc -> Thêm vào
            if node not in user_map: target_nodes.add(node)
        else:
            # Kiểm tra xem tất cả cha đã master chưa
            all_parents_done = True
            for p in parents:
                p_score = user_map.get(p, {}).get('score', 0.0)
                if p_score < 0.7: # Ngưỡng qua môn
                    all_parents_done = False
                    break
            
            if all_parents_done:
                target_nodes.add(node)
    
    # Giới hạn số lượng node để không bị loãng (Lấy tối đa 5-7 node quan trọng nhất)
    return list(target_nodes)

@st.cache_data
def load_meta_data():
    # [OPTIMIZATION] Try loading from Test Packet first
    packet = get_test_packet(current_subject)
    
    if packet and packet.get('questions'):
        # Reconstruct DataFrames from JSON Packet
        # 1. Questions
        q_data = []
        for qid, info in packet['questions'].items():
            q_data.append({
                'question_id': qid,
                'content': info['c'],
                'options': info['o'],
                'answer': info['a'],
                'difficulty': info['d'],
                'skill_id_list': info['s'],
                'explanation': info.get('e', '')
            })
        q_df = pd.DataFrame(q_data)
        
        # 2. Graph
        # Packet stores edges as list of [src, tgt]
        k_df = pd.DataFrame(packet['graph']['edges'], columns=['source', 'target'])
        
        # 3. Chapters (Extract from nodes)
        nodes = packet['graph']['nodes']
        chapters = set()
        import re
        for n in nodes:
            # Match "1." or "Chg1"
            m = re.match(r"^(\d+)\.", str(n))
            if m: chapters.add(int(m.group(1)))
            else:
                m2 = re.search(r"Chg(\d+)", str(n))
                if m2: chapters.add(int(m2.group(1)))
        
        chapters = sorted(list(chapters))
        
    else:
        # Fallback to DB
        k_df = get_graph_structure(current_subject)
        q_df = get_all_questions(current_subject)
        chapters = get_all_chapters() 

    # --- INDEXING (Cached) ---
    # 1. Pre-parse skill_id_list
    def safe_parse(x):
        try:
            if isinstance(x, list): return [str(s).strip() for s in x]
            x = str(x).strip()
            if x.startswith('['):
                return [str(s).strip() for s in ast.literal_eval(x)]
            return [x]
        except:
            return []
            
    if 'parsed_skills' not in q_df.columns:
        q_df['parsed_skills'] = q_df['skill_id_list'].apply(safe_parse)
        
    # 2. Build Index: Skill -> List of Rows (dict)
    s_index = {}
    q_records = q_df.to_dict('records')
    
    for row in q_records:
        for s in row['parsed_skills']:
            if s not in s_index: s_index[s] = []
            s_index[s].append(row)
            
    return k_df, q_df, chapters, s_index

k_graph_df, q_matrix_df, available_chapters, q_skill_index = load_meta_data()

# --- HELPER FUNCTIONS ---
def load_local_data(username, subject_id):
    """Pre-load data into session state for offline/fast mode"""
    with st.spinner("📥 Đang tải dữ liệu bài thi (Offline Mode)..."):
        progress = get_user_progress(username, subject_id)
        st.session_state.local_data = {
            "user_progress": progress, # List of tuples
            "loaded_at": datetime.now()
        }

def get_user_mastery_map():
    # [OPTIMIZATION] Read from local_data if available
    if "local_data" in st.session_state and "user_progress" in st.session_state.local_data:
        raw = st.session_state.local_data["user_progress"]
    else:
        raw = get_user_progress(username, current_subject)
    return {r[0]: r[2] for r in raw} if raw else {}

@st.cache_data(ttl=3600) # Cache cấu trúc chương vì ít thay đổi
def get_nodes_in_chapters(chapters_list):
    """Lọc ra các node thuộc các chương đã chọn"""
    all_nodes = set(k_graph_df['source']).union(set(k_graph_df['target']))
    valid_nodes = set()
    for n in all_nodes:
        n_str = str(n)
        import re
        match = re.match(r"^(\d+)\.", n_str)
        if match:
            if int(match.group(1)) in chapters_list: valid_nodes.add(n_str)
        elif n_str.startswith("Chg"): # Support Chg1 format
             match = re.search(r"\d+", n_str)
             if match and int(match.group(0)) in chapters_list: valid_nodes.add(n_str)
    return valid_nodes

# ============================================================
# 1. LOGIC KIỂM TRA ĐẦU VÀO (DIAGNOSTIC)
# ============================================================
def generate_diagnostic_test():
    """
    Tạo đề thi đầu vào: Chọn 1 câu hỏi đại diện cho mỗi Chương.
    """
    questions = []
    chapters = available_chapters
    
    for chap in chapters:
        # Tìm các node thuộc chương này
        nodes = get_nodes_in_chapters([chap])
        if not nodes: continue
        
        # [OPTIMIZED] Use q_skill_index instead of Loop
        candidates = []
        for node in nodes:
            found_qs = q_skill_index.get(str(node), [])
            candidates.extend(found_qs)
            
        # Deduplicate by ID
        unique_cands = {c['question_id']: c for c in candidates}.values()
        candidates = list(unique_cands)
        
        # Chọn 1 câu ngẫu nhiên (ưu tiên độ khó Medium)
        if candidates:
            # Thử tìm medium
            mediums = [c for c in candidates if str(c.get('difficulty')).lower() == 'medium']
            chosen = random.choice(mediums) if mediums else random.choice(candidates)
            
            questions.append({
                "q_data": chosen,
                "chapter": chap,
                "type": "diagnostic"
            })
            
    return questions

def check_stopping_condition(history, limit_min=10, limit_max=50):
    """
    Quyết định khi nào dừng bài kiểm tra Smart CAT
    """
    n = len(history)
    if n < limit_min: return False
    if n >= limit_max: return True
    
    # 1. Stability Check (Sự ổn định)
    # Nếu 5 câu gần nhất đều Đúng (Mastery) hoặc đều Sai (Fail) -> Có thể dừng
    if n >= 15:
        last_5 = [h['is_correct'] for h in history[-5:]]
        if all(last_5): return True # Quá giỏi
        if not any(last_5): return True # Cần học lại
        
    return False

# ============================================================
# 2. LOGIC KIỂM TRA THÍCH ỨNG (SMART CAT - GRAPH TRAVERSAL)
# ============================================================

def get_parents(node, k_df):
    return k_df[k_df['target'] == str(node)]['source'].tolist()

def get_children(node, k_df):
    return k_df[k_df['source'] == str(node)]['target'].tolist()

def get_strategic_question(history, user_map, k_df, q_df, valid_nodes_pool=None):
    """
    Chiến lược chọn câu hỏi thông minh dựa trên đồ thị:
    1. EXPLORATION (Đầu trận): Khảo sát ngẫu nhiên các nhánh khác nhau.
    2. REMEDIATION (Khi sai): Quay lui về node cha (kiến thức nền).
    3. PROGRESSION (Khi đúng): Tiến lên node con hoặc tăng độ khó.
    4. FRONTIER (Mặc định): Đánh vào vùng biên kiến thức.
    """
    # 0. Setup
    if user_map is None: user_map = get_user_mastery_map()
    hist_q_ids = [h['q_id'] for h in history]
    
    # Filter available questions (exclude history)
    available_qs = q_df[~q_df['question_id'].isin(hist_q_ids)].copy()
    if available_qs.empty: return None, None, "Hết ngân hàng câu hỏi"

    # --- STRATEGY SELECTION ---
    target_node = None
    strategy_name = "Random"
    difficulty_target = 'medium'

    # Case 1: EXPLORATION (Under 5 questions)
    if len(history) < 5:
        strategy_name = "Exploration"
        # Try to find a node in a chapter/branch not yet touched
        touched_nodes = set([h.get('skill') for h in history if h.get('skill')])
        
        # Simple heuristic: Pick a random node from valid pool NOT in touched
        candidates = list(valid_nodes_pool) if valid_nodes_pool else []
        untouched = [n for n in candidates if n not in touched_nodes]
        
        if untouched:
            target_node = random.choice(untouched)
        else:
            target_node = random.choice(candidates) if candidates else None

    # Case 2: FEEDBACK LOOP (After 5 questions)
    else:
        last_record = history[-1]
        last_node = last_record.get('skill')
        last_correct = last_record.get('is_correct')
        
        if not last_correct:
            # ---> REMEDIATION: Backtrack to Parent
            strategy_name = "Remediation"
            parents = get_parents(last_node, k_df)
            if parents:
                # Pick a parent that is strictly NOT Mastered yet (or weak)
                weak_parents = [p for p in parents if user_map.get(p, 0.5) < 0.8]
                if weak_parents:
                    target_node = random.choice(weak_parents)
                    difficulty_target = 'easy' # Remedial should be easier
                else:
                    # If all parents master, maybe staying on current node but easier
                    target_node = last_node
                    difficulty_target = 'easy'
            else:
                # No parent (Root node), stay here logic
                target_node = last_node
                difficulty_target = 'easy'
        
        else:
            # ---> PROGRESSION: Move to Children or Harder
            children = get_children(last_node, k_df)
            # Filter children that are IN SCOPE (if valid_nodes_pool is strict, but here we want expansion)
            # Let's verify children exist in our world
            # valid_children = [c for c in children if c in valid_nodes_pool] if valid_nodes_pool else children
            
            # Prioritize children that are NOT Mastered
            unmastered_children = [c for c in children if user_map.get(c, 0.0) < 0.7]
            
            if unmastered_children:
                strategy_name = "Progression"
                target_node = random.choice(unmastered_children)
                difficulty_target = 'medium'
            else:
                # Mastery on this branch? Jump to a Frontier node (High priority from smart_nodes logic)
                strategy_name = "Frontier"
                # Fallback to random heavy node in pool
                difficulty_target = 'hard'
                # target_node will be None, allowing fallback search below

    # --- EXECUTE SEARCH (OPTIMIZED) ---
    # 1. Try finding Q for specific target_node
    if target_node:
        target_node_s = str(target_node)
        # Use Index
        raw_candidates = q_skill_index.get(target_node_s, [])
        # Filter already taken
        candidates = [r for r in raw_candidates if r['question_id'] not in hist_q_ids]
        
        # Filter by difficulty
        diff_matches = [r for r in candidates if str(r.get('difficulty', 'medium')).lower() == difficulty_target]
        final_pool = diff_matches if diff_matches else candidates
        
        if final_pool:
            chosen = random.choice(final_pool)
            return chosen, target_node_s, f"{strategy_name} ({difficulty_target})"

    # 2. Fallback: If no target node found or empty pool -> General Adaptive (IRT-ish)
    if valid_nodes_pool:
        # Pick random node from pool (Optimization: Don't pick blindly, pick from valid_nodes that have Qs)
        # valid_nodes_list = list(valid_nodes_pool)
        # Better: iterate valid nodes, check index
        
        # Quick Random Sample
        shuffled_nodes = list(valid_nodes_pool)
        random.shuffle(shuffled_nodes)
        
        for node in shuffled_nodes[:5]: # Try 5 nodes max
            qs = q_skill_index.get(str(node), [])
            valid_qs = [q for q in qs if q['question_id'] not in hist_q_ids]
            
            if valid_qs:
                chosen = random.choice(valid_qs)
                return chosen, str(node), "Fallback"

    # 3. Last Resort: Random from available
    if not available_qs.empty: # q_df passed in is 'available_qs' but we used index.
                               # Actually get_strategic_question passes 'q_matrix_df' usually.
                               # available_qs calculated at line 277 is a DF.
        # Just pick ONE from available_qs dataframe
        rand_row = available_qs.sample(1).iloc[0].to_dict()
        # Use parsed skills
        skills = rand_row.get('parsed_skills', [])
        rand_skill = skills[0] if skills else "General"
        
        return rand_row, rand_skill, "Random"

    return None, None, "Hết câu hỏi"

def prepare_speculative_next(valid_nodes, full_history, current_skill, current_q_id):
    """
    Tính toán trước câu hỏi tiếp theo cho cả 2 trường hợp Đúng/Sai
    """
    user_map = get_user_mastery_map()
    
    # 1. Scenario Correct
    map_correct = user_map.copy()
    map_correct[current_skill] = 1.0 
    
    # Append simulated result
    sim_hist_corr = full_history + [{"q_id": current_q_id, "skill": current_skill, "is_correct": True}]
    q_corr, s_corr, _ = get_strategic_question(sim_hist_corr, map_correct, k_graph_df, q_matrix_df, valid_nodes)
    
    # 2. Scenario Incorrect
    map_incorr = user_map.copy()
    map_incorr[current_skill] = 0.0
    
    sim_hist_inc = full_history + [{"q_id": current_q_id, "skill": current_skill, "is_correct": False}]
    q_inc, s_inc, _ = get_strategic_question(sim_hist_inc, map_incorr, k_graph_df, q_matrix_df, valid_nodes)
    
    return {
        True: (q_corr, s_corr) if q_corr is not None else None,
        False: (q_inc, s_inc) if q_inc is not None else None
    }

# ============================================================
# 🔄 QUẢN LÝ TRẠNG THÁI (SESSION)
# ============================================================
if 'test_session' not in st.session_state:
    st.session_state.test_session = {
        "active": False,
        "mode": None, # 'diagnostic' hoặc 'standard'
        "questions_queue": [], # Chỉ dùng cho Diagnostic (list cố định)
        "current_q_index": 0,  # Chỉ dùng cho Diagnostic
        "history": [],
        "start_time": None,
        "limit_minutes": 0,
        "score": 0,
        "next_q": None, # [OPTIMIZATION] Buffer cho câu hỏi tiếp theo
        "speculative_next": None, # [OPTIMIZATION] Buffer cho 2 trường hợp Đúng/Sai
        "speculative_prepared": False, # Cờ đánh dấu đã tính toán chưa
        "answer_submitted": False,
        "last_is_correct": False
    }

ts = st.session_state.test_session

# Kiểm tra User mới hay cũ
user_progress_data = get_user_progress(username, current_subject)
is_new_user = len(user_progress_data) == 0

# [FIX] AUTO-RESET SESSION IF USER CHANGED OR INVALID STATE
# 1. Ownership Check
if ts.get("owner") != username:
    st.session_state.test_session = {
        "active": False,
        "mode": None,
        "questions_queue": [],
        "current_q_index": 0,
        "history": [],
        "start_time": None,
        "limit_minutes": 0,
        "score": 0,
        "next_q": None,
        "speculative_next": None,
        "speculative_prepared": False,
        "owner": username # Mark ownership
    }
    st.session_state.show_result = False
    ts = st.session_state.test_session # Re-bind

# 2. Invalid State Check (Show Result but No History)
# [FIX] Allow if explicitly marked "incomplete" (User stopped early at Q1)
if st.session_state.get("show_result", False) and not ts.get("history") and not ts.get("incomplete"):
    st.session_state.show_result = False
    ts["active"] = False
    st.rerun()

# ============================================================
# 🖥️ MÀN HÌNH 1: LỰA CHỌN CHẾ ĐỘ
# ============================================================
if not ts["active"] and not st.session_state.get("show_result", False):
    st.title("📝 Trung tâm Kiểm tra & Đánh giá")
    
    # --- TAB A: KIỂM TRA ĐẦU VÀO (ƯU TIÊN NẾU USER MỚI) ---
    if "quiz_error" in st.session_state and st.session_state["quiz_error"]:
        st.error(st.session_state["quiz_error"])
        
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("🔄 Tải dữ liệu lại (Sync)"):
                try:
                    import sync_utils
                    with st.spinner("Đang đồng bộ dữ liệu..."):
                        sync_utils.sync_down(st.session_state.get("username", ""), skip_static=False)
                    st.success("Đã đồng bộ xong! Vui lòng thử lại.")
                    del st.session_state["quiz_error"]
                    time.sleep(1)
                    st.rerun()
                except ImportError:
                    st.error("Không tìm thấy module sync_utils.")
                except Exception as e:
                    st.error(f"Lỗi: {e}")
        
        with c2:
            if st.button("Đã hiểu / Xóa lỗi"):
                del st.session_state["quiz_error"]
                st.rerun()

    if is_new_user:
        st.info("👋 Chào bạn mới! Hãy làm bài kiểm tra đầu vào để hệ thống xây dựng lộ trình phù hợp.")
        with st.container():
            st.markdown("""
            <div class="diagnostic-card">
                <h3>🚀 Kiểm tra Đầu vào (Diagnostic Test)</h3>
                <p>Hệ thống sẽ hỏi 1 câu đại diện cho mỗi chương.</p>
                <p><b>Mục tiêu:</b> Xác định kiến thức nền tảng để bạn có thể bỏ qua các bài học cơ bản.</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Bắt đầu Kiểm tra Đầu vào", type="primary", use_container_width=True):
                # [MODIFIED] Switch to CAT Mode
                # Load all chapters as target scope
                all_nodes = get_nodes_in_chapters(available_chapters)
                
                st.session_state.test_session.update({
                    "active": True,
                    "mode": "diagnostic_cat", # New Mode
                    "target_nodes": list(all_nodes), # Broad scope
                    "questions_queue": [], # Not used
                    "current_q_index": 0,
                    "start_time": datetime.now(),
                    "limit_minutes": 30, 
                    "limit_questions": 30, # Max Cap
                    "min_questions": 10,   # Min Cap
                    "history": [],
                    "answer_submitted": False,
                    "score": 0, # Reset score
                    "owner": username,
                    "speculative_prepared": False
                })
                st.rerun()
        st.divider()

    # # --- TAB B: KIỂM TRA TÙY CHỌN (STANDARD CAT) ---
    # st.subheader("⚙️ Kiểm tra Thích ứng (Tùy chỉnh)")
    # if is_new_user:
    #     st.caption("Hoặc bạn có thể tự tạo bài kiểm tra thủ công:")
    
    # with st.form("config_standard_test"):
    #     c1, c2 = st.columns(2)
    #     with c1:
    #         sel_chaps = st.multiselect("Chọn Chương:", available_chapters, default=available_chapters[:1] if available_chapters else None)
    #     with c2:
    #         time_lim = st.number_input("Thời gian (phút):", 15, 120, 15)
    #         q_lim = st.number_input("Số câu hỏi:", 5, 50, 10)
            
    #     if st.form_submit_button("Bắt đầu Kiểm tra"):
    #         if not sel_chaps:
    #             st.error("Chọn ít nhất 1 chương.")
    #         else:
    #             st.session_state.test_session.update({
    #                 "active": True,
    #                 "mode": "standard",
    #                 "selected_chapters": sel_chaps,
    #                 "limit_minutes": time_lim,
    #                 "limit_questions": q_lim,
    #                 "start_time": datetime.now(),
    #                 "history": [],
    #                 "current_q": None, # Sẽ lấy dynamic
    #                 "answer_submitted": False
    #             })
    #             st.rerun()
    
    # --- PHẦN DÀNH CHO NGƯỜI DÙNG CŨ (SMART CAT) ---
    if not is_new_user:
        st.subheader("🎯 Kiểm tra Tổng quan Kiến thức")
        
        col_smart, col_manual = st.columns([3, 2])
        
        # CỘT TRÁI: REVIEW GENERAL (TỰ ĐỘNG)
        with col_smart:
            with st.container(border=True):
                st.markdown("### 🧠 Kiểm tra Tổng quan (Adaptive)")
                st.info("Hệ thống sẽ quét toàn bộ cây tri thức để đánh giá mức độ bao phủ và phát hiện lỗ hổng kiến thức của bạn.")
                
                if st.button("🚀 Bắt đầu Kiểm tra Tổng quan", type="primary", use_container_width=True):
                    # 1. Lấy danh sách node thông minh
                    smart_nodes = get_smart_test_nodes(username, current_subject)
                    
                    if not smart_nodes:
                        st.success("🎉 Tuyệt vời! Bạn đã hoàn thành xuất sắc lộ trình hiện tại. Hãy thử chế độ 'Thử thách' hoặc tự chọn chương để ôn tập.")
                    else:
                        # 2. Thiết lập bài thi
                        # [OPTIMIZATION] Pre-load data
                        load_local_data(username, current_subject)
                        
                        st.session_state.test_session.update({
                            "active": True,
                            "mode": "smart_cat",  # Chế độ mới
                            "target_nodes": smart_nodes, # Lưu danh sách node mục tiêu
                            "limit_minutes": 20,  # Mặc định 20p
                            "limit_questions": 50, # [DYNAMIC] Max cap
                            "start_time": datetime.now(),
                            "history": [],
                            "current_q": None,
                            "answer_submitted": False,
                            "owner": username # [FIX] Add owner
                        })
                        st.rerun()

        # CỘT PHẢI: THỦ CÔNG (MANUAL)
        with col_manual:
            with st.expander("⚙️ Tùy chỉnh thủ công (Nâng cao)"):
                with st.form("config_standard_test"):
                    sel_chaps = st.multiselect("Chọn Chương:", available_chapters)
                    time_lim = st.number_input("Thời gian (phút):", 5, 120, 15)
                    q_lim = st.number_input("Số câu hỏi:", 5, 50, 10)
                    
                    if st.form_submit_button("Tạo bài thi"):
                        if not sel_chaps:
                            st.error("Chọn ít nhất 1 chương.")
                        else:
                            st.session_state.test_session.update({
                                "active": True,
                                "mode": "standard",
                                "selected_chapters": sel_chaps,
                                "limit_minutes": time_lim,
                                "limit_questions": q_lim,
                                "start_time": datetime.now(),
                                "history": [],
                                "current_q": None,
                                "answer_submitted": False,
                                "owner": username # [FIX] Add owner
                            })
                            st.rerun()

# ============================================================
# 🖥️ MÀN HÌNH 2: ĐANG LÀM BÀI
# ============================================================
elif ts["active"]: # [FIX] Chỉ chạy khi Active = True
    # 🔁 Tự động refresh (TẠM TẮT ĐỂ TRÁNH TREO MÁY TRÊN CLOUD)
    # st_autorefresh(interval=2000, key="exam_timer")
    
    # === 👇 KIỂM TRA ĐIỀU KIỆN DỪNG (SMART STOP) 👇 ===
    should_stop = False
    if ts["mode"] in ["smart_cat", "diagnostic_cat"]:
        # Use generic stopping condition
        limit_min = ts.get("min_questions", 10)
        limit_max = ts.get("limit_questions", 30)
        should_stop = check_stopping_condition(ts["history"], limit_min, limit_max)
    elif len(ts["history"]) >= ts["limit_questions"]:
        should_stop = True
        
    if should_stop:
        ts["active"] = False
        st.session_state.show_result = True
        st.rerun() 
    # ===================================================================

    # 1. HEADER & TIMER
    now = datetime.now()
    elapsed = (now - ts["start_time"]).total_seconds()
    limit_mod = (ts["limit_minutes"] * 60)
    
    if elapsed >= limit_mod:
        st.warning("⏰ Hết giờ!")
        ts["active"] = False
        st.session_state.show_result = True
        st.rerun()
        
    mins, secs = divmod(int(elapsed), 60)
    
    # 1.2. TÍNH TIẾN ĐỘ CÂU HỎI
    if ts["mode"] == "diagnostic_cat":
         answered = len(ts["history"])
         prog_text = f"Câu {answered + 1} (Khảo sát Tùy biến)"
         limit = ts.get("limit_questions", 30)
         prog_val = min(answered / limit, 1.0)
         
    # elif ts["mode"] == "diagnostic": 
    #     pass
    else:
        # standard / smart_cat
        answered = len(ts["history"])
        # Dynamic Text
        if ts["mode"] == "smart_cat":
            prog_text = f"Câu {answered + 1} (Đang đánh giá...)"
            # Estimate progress: 50 is max cap
            limit = ts.get("limit_questions", 50)
            prog_val = min(answered / limit, 1.0)
        else:
            total_q = ts.get("limit_questions", max(1, answered))
            current = min(answered + 1, total_q)
            prog_text = f"Câu {current}/{total_q}"
            if total_q == 0: prog_val = 0.0
            else: prog_val = current / total_q


    # === HEADER 1 DÒNG: ĐỒNG HỒ + CÂU HỎI + SKILL ===
    display_skill = ts.get("current_skill", "")

    st.markdown(
        f"""
        <div style="
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:0.75rem;
            padding:0.35rem 0.75rem;
            border:1px solid #eee;
            border-radius:8px;
            margin-bottom:0.3rem;
            font-size:0.95rem;
        ">
            <span style="font-weight:bold;">⏱️ {mins:02}:{secs:02}</span>
            <span>{prog_text}</span>
            <span style="font-style:italic; color:#555;">{display_skill}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Thanh tiến độ vẫn nằm dưới, chiếm 1 dòng riêng
    st.progress(prog_val, text=prog_text)


    current_q_data = None
    current_skill = None
    
    # Unified Logic for Adaptive Modes
    if ts["mode"] in ["smart_cat", "diagnostic_cat", "standard"]:
        if ts.get("current_q") is None:
            # XÁC ĐỊNH PHẠM VI CÂU HỎI (VALID NODES)
            
            if ts["mode"] in ["smart_cat", "diagnostic_cat"]:
                 # Scope: target_nodes OR all chapters
                 valid_nodes = set(ts.get("target_nodes", []))
                 if not valid_nodes: 
                     valid_nodes = get_nodes_in_chapters(available_chapters)
                 
                 # [OPTIMIZATION] If diagnostic_cat, maybe force Exploration Strategy logic inside get_strategic_question?
                 # For now, get_strategic_question's "Exploration" (history < 5) works well.
                     
            else: # Standard (Manual)
                valid_nodes = get_nodes_in_chapters(ts["selected_chapters"])
            
            # Use cached index approach implicitly via get_strategic_question optimizations?
            # Wait, get_strategic_question was optimized to use q_skill_index inside? Yes.
            
            q, s, msg = get_strategic_question(ts["history"], None, k_graph_df, q_matrix_df, valid_nodes)
            
            if q is None: # Hết câu hỏi
                ts["active"] = False
                if len(ts["history"]) == 0:
                    msg = f"⚠️ Không tìm thấy câu hỏi! (Target: {len(valid_nodes)} nodes). Vui lòng kiểm tra dữ liệu."
                    st.session_state["quiz_error"] = msg
                    st.session_state.show_result = False
                else:
                    st.session_state.show_result = True
                st.rerun()
                
            ts["current_q"] = q
            ts["current_skill"] = s
            ts["answer_submitted"] = False
            st.rerun()
            
        current_q_data = ts["current_q"]
        current_skill = ts["current_skill"]
        
        # [REMOVED] Speculative Block (Disabled)

    # Callbacks simplified..
        
        # [OPTIMIZATION] SPECULATIVE PRE-CALCULATION
        # Tính toán ngầm trong khi user đang đọc câu hỏi (tận dụng vòng lặp timer)
        if False and not ts.get("speculative_prepared") and current_q_data:
            if ts["mode"] != "diagnostic" and len(ts["history"]) < ts["limit_questions"]:
                # Xác định valid_nodes
                if ts["mode"] == "smart_cat":
                    v_nodes = set(ts["target_nodes"])
                    if not v_nodes: v_nodes = get_nodes_in_chapters(available_chapters)
                else:
                    v_nodes = get_nodes_in_chapters(ts["selected_chapters"])
                
                # Gọi hàm tính toán
                ts["speculative_next"] = prepare_speculative_next(v_nodes, ts["history"], current_skill, current_q_data['question_id'])
                ts["speculative_prepared"] = True
                # Không rerun để tránh nháy màn hình, chỉ lưu vào session_state

    # --- CALLBACKS ---
    def submit_answer(choice_text):
        if not choice_text: return

        # Logic chấm điểm
        corr_ans = str(current_q_data['answer']).strip().upper()
        # Lấy ký tự đầu (A, B, C...)
        sel_char = choice_text.strip().upper()[0]
        # [ROBUST] Nếu option không có prefix A/B/C, so sánh full text? (Tạm thời giả sử format chuẩn)
        is_correct = (sel_char == corr_ans)
        
        ts["last_is_correct"] = is_correct
        ts["user_selection"] = choice_text # Theo dõi lựa chọn để hiển thị UI
        ts["answer_submitted"] = True 
        
        # 1. UPDATE HISTORY FIRST
        st.session_state.test_session["history"].append({
            "q_id": current_q_data['question_id'],
            "is_correct": is_correct,
            "skill": current_skill, 
            "diff": current_q_data.get('difficulty', 'medium'),
            "chapter": current_q_data.get('chapter', 1) 
        })
        st.session_state.test_session = st.session_state.test_session # Force update
        
        # 2. UPDATE LOCAL DATA
        if "local_data" in st.session_state and ts["mode"] != "diagnostic":
            st.session_state.local_data["user_progress"].append(
                (current_skill, 'Completed', 1.0 if is_correct else 0.0, datetime.now())
            )

        # 3. LOG TO DB
        try:
            log_activity(username, f'test_{ts["mode"]}', current_subject, 
                            current_skill if ts["mode"]=="standard" else "diagnostic", 
                            current_q_data['question_id'], is_correct)
        except Exception as e:
            print(f"Log Error: {e}")
        
        # 4. PRE-FETCH NEXT QUESTION
        if ts["mode"] != "diagnostic" and len(ts["history"]) < ts["limit_questions"]:
            spec_data = ts.get("speculative_next")
            if spec_data and is_correct in spec_data and spec_data[is_correct]:
                ts["next_q"] = spec_data[is_correct]
            else:
                # Fallback logic
                if ts["mode"] in ["smart_cat", "diagnostic_cat"]:
                    valid_nodes = set(ts.get("target_nodes", []))
                    if not valid_nodes: valid_nodes = get_nodes_in_chapters(available_chapters)
                else:
                    valid_nodes = get_nodes_in_chapters(ts["selected_chapters"])
                
                nq, ns, nmsg = get_strategic_question(ts["history"], None, k_graph_df, q_matrix_df, valid_nodes)
                if nq:
                    ts["next_q"] = (nq, ns)
        
        # Reset flags
        ts["speculative_next"] = None
        ts["speculative_prepared"] = False

    def handle_next():
        # Generic next handler
        if ts.get("next_q"): 
             ts["current_q"] = ts["next_q"][0]
             ts["current_skill"] = ts["next_q"][1]
             ts["next_q"] = None
        else:
             ts["current_q"] = None # Force fetch new
        
        ts["answer_submitted"] = False
        ts["user_selection"] = None # Reset selection
        if "radio_ans" in st.session_state: del st.session_state.radio_ans

    def handle_finish():
        ts["active"] = False
        st.session_state.show_result = True
        
        # [OPTIMIZATION]
        if not ts.get("speculative_prepared") and current_q_data:
             pass # Logic finish

    # 3. HIỂN THỊ CÂU HỎI
    if current_q_data:
        st.markdown(f"**{current_skill}**")
        
        # Content Format
        st.markdown(f"""
        <div class="question-box">
            {current_q_data['content']}
        </div>
        """, unsafe_allow_html=True)
        
        try: ops = ast.literal_eval(current_q_data['options'])
        except: ops = []
        
        # Check Mode
        submitted = ts.get("answer_submitted", False)
        
        if not submitted:
            # --- INTERACTIVE MODE (Loop Button) ---
            for opt in ops:
                st.button(opt, key=f"btn_opt_{current_q_data['question_id']}_{opt}", 
                          use_container_width=True, 
                          on_click=submit_answer, args=(opt,))
            
            st.caption("💡 Chọn một đáp án để nộp bài ngay.")
            
            # Stop Early
            if st.button("⏹️ Kết thúc sớm", key="btn_stop_early_interact"):
                 ts["incomplete"] = True
                 handle_finish()
                 st.rerun()

        else:
            # --- RESULT MODE (Card Style) ---
            user_sel = ts.get("user_selection", "")
            is_corr = ts.get("last_is_correct", False)
            correct_ans_char = str(current_q_data['answer']).strip().upper()
            expl = current_q_data.get('explanation', "Không có giải thích chi tiết.")
            
            if is_corr: 
                st.success("🎉 Chính xác!")
            else: 
                st.error(f"⚠️ Chưa chính xác.")
            
            # Render Option Cards
            for opt in ops:
                # Determine Styling
                card_class = "neutral"
                feedback_html = ""
                icon = ""
                
                # Check if this opt is the USER selection
                is_selected = (opt == user_sel)
                
                # Check if this opt is ACTUALLY correct
                # Heuristic: Compare first char or full text
                opt_char = opt.strip().upper()[0]
                is_actually_correct = (opt_char == correct_ans_char)
                
                if is_selected:
                    if is_corr:
                        card_class = "correct"
                        icon = "✅"
                        feedback_html = f'<div class="feedback-content"><strong>Chính xác!</strong><br>{expl}</div>'
                    else:
                        card_class = "incorrect"
                        icon = "❌"
                        feedback_html = f'<div class="feedback-content"><strong>Rất tiếc!</strong><br>Đáp án này chưa đúng.</div>'
                elif is_actually_correct and not is_corr:
                    # Highlight items user missed
                    card_class = "correct"
                    icon = "✅"
                    feedback_html = f'<div class="feedback-content"><strong>Đáp án đúng</strong><br>{expl}</div>'
                
                # Render HTML Card
                st.markdown(f"""
                <div class="option-card {card_class}">
                    <div style="font-weight:600; display:flex; gap:8px; align-items:center;">
                        <span>{icon}</span> {opt}
                    </div>
                    {feedback_html}
                </div>
                """, unsafe_allow_html=True)

            # Footer Actions
            is_last_question = False
            if ts["mode"] in ["smart_cat", "diagnostic_cat"]:
                limit_min = ts.get("min_questions", 10)
                limit_max = ts.get("limit_questions", 30)
                is_last_question = check_stopping_condition(ts["history"], limit_min, limit_max)
            elif len(ts["history"]) >= ts["limit_questions"]:
                is_last_question = True
            
            c_next, c_stop = st.columns([3, 1])
            with c_next:
                if is_last_question:
                    st.button("📊 Xem kết quả cuối cùng", type="primary", on_click=handle_finish, use_container_width=True)
                else:
                    st.button("Câu tiếp theo ➡", type="primary", on_click=handle_next, use_container_width=True)
            with c_stop:
                if st.button("⏹️ Dừng", key="btn_stop_res"):
                        ts["incomplete"] = True
                        handle_finish()

# ============================================================
# 📊 MÀN HÌNH KẾT QUẢ (XỬ LÝ SAU KHI THI)
# ============================================================
if st.session_state.get("show_result", False):
    st.balloons()
    st.title("🎉 Kết quả bài kiểm tra")
    
    # [FEATURE] Hiển thị thông báo nếu dừng sớm
    if ts.get("incomplete"):
        st.warning("⚠️ Bài kiểm tra chưa hoàn thành (Người dùng dừng sớm). Kết quả chỉ mang tính tham khảo.")

    # [FEATURE] TABBED RESULT SCREEN
    # [FIX] Removed "Bản đồ tĩnh" tab
    tab1, tab2, tab3 = st.tabs(["📊 Tổng quan", "🕸️ Đồ thị tương tác", "📜 Lịch sử chi tiết"])
    
    # ---------------- TAB 1: OVERVIEW ----------------
    with tab1:
        hist = ts["history"]
        n_correct = sum(1 for h in hist if h["is_correct"])
        total = len(hist)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Điểm số", f"{n_correct}/{total}")
        c2.metric("Tỷ lệ", f"{n_correct/total*100:.0f}%" if total else "0%")
        
        # Calculate Time
        if ts.get("start_time"):
            duration = datetime.now() - ts["start_time"]
            mins, secs = divmod(duration.total_seconds(), 60)
            c3.metric("Thời gian", f"{int(mins)}p {int(secs)}s")
        
        # Recommendation
        st.divider()
        if total > 0:
            score_pct = n_correct / total
            if score_pct >= 0.8:
                st.success("🌟 Xuất sắc! Bạn đã nắm vững các kiến thức được kiểm tra.")
            elif score_pct >= 0.5:
                st.info("👍 Khá tốt. Hãy ôn tập thêm các bài còn yếu.")
            else:
                st.warning("⚠️ Cần cố gắng hơn. Hãy xem lại kiến thức nền tảng.")
            
        # --- XỬ LÝ KẾT QUẢ ĐẦU VÀO (MAGIC HAPPENS HERE) ---
        if ts["mode"] == "diagnostic":
            st.subheader("🔍 Phân tích & Đề xuất lộ trình")
            st.write("Dựa trên kết quả đầu vào, hệ thống đã cập nhật Cây tri thức của bạn:")
            
            # Logic: Nếu đúng câu đại diện Chương X -> Set toàn bộ node con Chương X lên 0.7 (Passed)
            # Logic: Tìm các skill đã trả lời đúng -> Trace ngược về Chapter
            correct_skills = [h["skill"] for h in hist if h["is_correct"]]
            
            # Map Skill -> Chapter
            correct_chapters = set()
            for sk in correct_skills:
                 # Check explicit chapter field first
                 # If simple approach:
                 import re
                 m = re.match(r"^(\d+)\.", str(sk))
                 if m: correct_chapters.add(int(m.group(1)))
            
            if correct_chapters:
                count_updated = 0
                import sqlite3
                conn = sqlite3.connect('local_course.db') 
                c = conn.cursor()
                
                for chap in correct_chapters:
                    # Lấy tất cả node thuộc chương này
                    nodes = get_nodes_in_chapters([chap])
                    for n in nodes:
                        # Chỉ update nếu chưa có điểm
                        try:
                            timestamp = datetime.now()
                            # Set điểm 0.8 (Màu xanh) cho các bài thuộc chương đã pass
                            c.execute('''
                                INSERT OR IGNORE INTO user_progress (username, node_id, subject_id, status, score, timestamp)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (username, n, current_subject, 'Completed', 0.8, timestamp))
                            count_updated += 1
                        except: pass
                
                conn.commit()
                conn.close()
                
                st.success(f"✅ Đã mở khóa kiến thức cho **{len(correct_chapters)} chương** ({count_updated} bài học)!")
                st.info("Các bài học này đã chuyển sang màu Xanh. Bạn có thể bắt đầu học từ những chương chưa vượt qua.")
            else:
                st.warning("Bạn chưa vượt qua câu hỏi nào. Hệ thống khuyến nghị bắt đầu từ Chương 1.")

    # ---------------- TAB 2: INTERACTIVE GRAPH (Was Tab 3) ----------------
    with tab2:
        st.subheader("🕸️ Đồ thị Tri thức Tương tác")
        
        c_filter, c_legend = st.columns([1, 2])
        with c_filter:
            # [FEATURE] Filtering Controls
            # [FIX] Auto-Switch Logic: Start Reduced -> Wait -> Switch to Full
            # This simulates "Waiting a bit then pressing Full"
            if "graph_auto_expanded" not in st.session_state:
                st.session_state.graph_auto_expanded = False
            
            # [FIX] Handle Trigger BEFORE Widget Creation
            if st.session_state.get("do_auto_expand_next_run", False):
                st.session_state.show_mode_radio = "Đầy đủ (+)"
                st.session_state.graph_auto_expanded = True
                st.session_state.do_auto_expand_next_run = False # Reset trigger

            show_mode = st.radio(
                "Chế độ xem:", 
                ["Đầy đủ (+)", "Rút gọn (-)"], 
                index=1, # Default Reduced
                horizontal=True,
                help="Rút gọn: Chỉ hiện Chương và các bài đã làm.",
                key="show_mode_radio" # Key for programmatic control
            )
            
            # [FIX] Schedule Trigger POST-Widget
            if not st.session_state.graph_auto_expanded and not st.session_state.get("do_auto_expand_next_run", False):
                import time
                time.sleep(0.5) # Wait a bit (simulated delay)
                st.session_state.do_auto_expand_next_run = True # Schedule update for NEXT run
                st.rerun()
            
        with c_legend:
             st.caption("🟦 Chương | 🟢 Đã biết | 🔴 Cần ôn | ⚪ Chưa học")

        # 1. Prepare Data
        nodes = []
        edges = []
        
        # Re-calc map
        current_map = get_user_mastery_map().copy()
        for h in ts["history"]:
            skill = h.get('skill')
            if skill: current_map[skill] = 0.9 if h['is_correct'] else 0.4
            
        added_nodes = set()
        
        # [FEATURE] SMART RE-WIRING (Gắn nhánh rời vào Chương)
        # 1. Build map: Node -> Owner Chapter
        node_to_chapter = {}
        # Find all chapters first
        all_graph_nodes = set(k_graph_df['source']).union(set(k_graph_df['target']))
        chapters = []
        for n in all_graph_nodes:
             if "Chg" in str(n) or str(n).isdigit() or (len(str(n)) < 5 and "." not in str(n)):
                 chapters.append(str(n))
        
        # BFS to assign chapter
        # Build adjacency
        adj = {}
        for _, row in k_graph_df.iterrows():
            s, t = str(row['source']), str(row['target'])
            if s not in adj: adj[s] = []
            adj[s].append(t)
            
        for chap in chapters:
            queue = [chap]
            visited = set()
            while queue:
                curr = queue.pop(0)
                if curr not in node_to_chapter:
                    node_to_chapter[curr] = chap
                
                if curr in adj:
                    for child in adj[curr]:
                        # [FIX] Stop if we hit another Chapter!
                        # This prevents Chg1 from claiming Chg2's children.
                        if child in chapters and child != chap:
                             continue
                             
                        if child not in visited:
                            visited.add(child)
                            queue.append(child)

        # [FEATURE] CHAPTER AGGREGATION (Tính điểm trung bình cho Chương)
        chapter_agg_map = {}
        for chap in chapters:
            # Find all nodes belonging to this chapter (from node_to_chapter)
            # OR better: Traverse graph again? No, node_to_chapter is populated now.
            # But node_to_chapter only has *children*, not the chapter itself.
            
            # Find all children of this chapter
            children = [n for n, c in node_to_chapter.items() if c == chap]
            
            # Calculate stats
            total_tested = 0
            total_score = 0
            for child in children:
                s = current_map.get(child, -1)
                if s != -1:
                    total_tested += 1
                    total_score += s
            
            if total_tested > 0:
                avg_score = total_score / total_tested
                chapter_agg_map[chap] = avg_score
            else:
                chapter_agg_map[chap] = -1 # Not tested

        # [RESTORED] SMART LEAF PLACEMENT & SPINE LOGIC
        # 1. Sort Chapters for X-Axis placement
        import re
        sorted_chapters = []
        try:
             sorted_chapters = sorted(chapters, key=lambda x: int(re.search(r'\d+', x).group()))
        except: 
             sorted_chapters = list(chapters)
             
        # Map Chapter -> X Coordinate
        chapter_x = {}
        spacing_x = 300 # Distance between chapters
        for i, chap in enumerate(sorted_chapters):
             chapter_x[chap] = i * spacing_x

        # 2. Add Nodes & Edges
        # Pre-calculate visibility
        visible_nodes = set()
        for n in all_graph_nodes:
            is_chap = n in chapters
            if show_mode == "Đầy đủ (+)":
                visible_nodes.add(n)
            else:
                # Rút gọn: ONLY Tested Nodes AND Active Chapters
                has_score = current_map.get(n, -1) != -1
                
                keep_chapter = False
                if is_chap:
                    # Check if chapter has any tested children (via agg map)
                    # If chapter itself has score or agg_score is present
                    agg_score = chapter_agg_map.get(n, -1)
                    if agg_score != -1 or has_score:
                        keep_chapter = True
                
                if keep_chapter or (not is_chap and has_score):
                    visible_nodes.add(n)

        # [FIX] Pre-calculate visible chapters for Compact Leveling
        # Identifying valid chapters that are in visible_nodes
        # This allows us to assign Level 0, 2, 4... consecutively even if Ch 2 is missing.
        visible_chapters_ordered = [c for c in sorted_chapters if c in visible_nodes]
        for idx, row in k_graph_df.iterrows():
            src = str(row['source'])
            tgt = str(row['target'])
            
            # Logic:
            # Case 1: Both Visible -> Draw Edge
            # Case 2: Src Hidden, Tgt Visible -> Draw Edge (Chapter -> Tgt)
            
            final_src = None
            if src in visible_nodes and tgt in visible_nodes:
                final_src = src
            elif src not in visible_nodes and tgt in visible_nodes:
                # Re-wire to Chapter
                owner_chap = node_to_chapter.get(tgt)
                if owner_chap and owner_chap in visible_nodes:
                    final_src = owner_chap
            
            if final_src:
                # Add nodes if not added
                for node in [final_src, tgt]:
                    if node not in added_nodes:
                        score = current_map.get(node, -1)
                        
                        # COLOR
                        if score >= 0.7: color = "#00C853"
                        elif score >= 0.5: color = "#FFD600"
                        elif score >= 0.0: color = "#FF5252"
                        else: color = "#CFD8DC"
                        
                        # [FEATURE] OVERRIDE CHAPTER COLOR based on Aggregation
                        if node in chapters:
                            agg_score = chapter_agg_map.get(node, -1)
                            if agg_score != -1:
                                if agg_score >= 0.7: color = "#00C853" # Green
                                elif agg_score >= 0.5: color = "#FFD600" # Orange
                                else: color = "#FF5252" # Red
                            else:
                                # [FIX] User wants Gray for untested chapters
                                color = "#CFD8DC"
                        
                        # STYLE & SHAPE
                        # User wants: Circular nodes for chapters with Number inside.
                        # Distinct from leaves.
                        
                        import re
                        is_chapter_node = node in chapters
                        label = node
                        font = {"color": "black"} # Default
                        
                        if is_chapter_node:
                             # 1. Parse Number
                             num_match = re.search(r"\d+", node)
                             num_str = num_match.group(0) if num_match else "?"
                             
                             # [FIX] Label = Number + Name (Outside)
                             # Shape 'square' puts label outside.
                             label = f"{num_str}. {node}" 
                             shape = "square" # [FIX] Square shape (label defaults to outside)
                             size = 25 # Fixed size for square
                             
                             # Custom font for BOLD effect
                             # Vis.js allows shorthand string for font to set weight
                             font = "bold 20px arial black" # [FIX] Bold font string
                        
                        else:
                             # Leaf
                             # [FIX] User wants Circular nodes always
                             shape = "dot" 
                             size = 20
                        # Forces Ch1 -> Leftmost.
                        # Logic: Chapter i is Level 2*i. Children are Level 2*i + 1.
                        # [FIX] Use VISIBLE chapters only to avoid gaps in Condensed Mode
                        level = 0
                        try:
                            owner_chap = node_to_chapter.get(node)
                            # Identify visible order
                            # We need to compute visible_chapters dynamically or assume based on added_nodes (which is filling up)
                            # Safe approach: Use original index but 'compress' if mode is Rút gọn?
                            # Actually, Graphviz/VisJS handles gaps fine, but for spine we need exact connections.
                            # For Level: Keeping original index is safer for stability, gaps are okay.
                            
                            # [FIX] Compact Leveling Logic
                            # Use the index from 'visible_chapters_ordered' instead of global 'sorted_chapters'
                            # This removes the empty space where hidden chapters would be.
                            
                            c_idx = -1
                            if owner_chap in visible_chapters_ordered:
                                c_idx = visible_chapters_ordered.index(owner_chap)
                                
                            if c_idx != -1:
                                if is_chapter_node:
                                    level = c_idx * 2
                                else:
                                    level = c_idx * 2 + 1
                        except: pass

                        # Create Node
                        node_kwargs = {
                            "id": node, 
                            "label": label, 
                            "size": size, 
                            "color": color, 
                            "shape": shape, 
                            "title": f"{node}\nĐiểm: {score:.0%}",
                            "borderWidth": 3 if is_chapter_node else 1,
                            "font": {'size': 24} if is_chapter_node else {'size': 14}, # Bigger Font -> Bigger Box
                            "shapeProperties": {"borderRadius": 5} if is_chapter_node and shape == "box" else {},
                            "level": level # [FIX] Force Hierarchy Level
                        }
                        
                        # [REVERT] No manual fixing, let Hierarchical Engine handle it
                            
                        nodes.append(Node(**node_kwargs))
                        added_nodes.add(node)
                
                # Add Edge
                # [FIX] Thicker edges for Chapter -> Child (Root-like)
                edge_width = 1
                if final_src in chapters:
                    edge_width = 3
                
                edges.append(Edge(source=final_src, target=tgt, color="#bdc3c7", width=edge_width))

        # [FEATURE] FORCE SPINE EDGES (Connect Ch1->Ch2->Ch3)
        # [FIX] Smart Spine: Connect CONSECUTIVE VISIBLE chapters
        # Gather visible chapters in order
        visible_chapters_sorted = [c for c in sorted_chapters if c in added_nodes]
        
        num_spine_edges = len(visible_chapters_sorted) - 1
        max_width = 12
        min_width = 2
        
        for i in range(num_spine_edges):
            c1 = visible_chapters_sorted[i]
            c2 = visible_chapters_sorted[i+1]
            
            # [FIX] Tapered Width Logic
            # Width decreases linearly from max_width to min_width
            if num_spine_edges > 1:
                decay = (max_width - min_width) * (i / (num_spine_edges - 1))
                current_width = max_width - decay
            else:
                current_width = max_width
            
            # [FIX] Thicker Spine + Tapered
            edges.append(Edge(source=c1, target=c2, color="#2979FF", width=int(current_width), dashes=[15, 15]))
        
        # [DEBUG] Check data validity
        if not nodes:
            st.warning("⚠️ Không có dữ liệu đồ thị để hiển thị.")
        else:
            # [FIX] Container + Border + Maximize Area
            with st.container(border=True):
                # [FIX] Explicit Hierarchical Options to stabilize layout
                hierarchical_opts = {
                    "enabled": True,
                    "levelSeparation": 150, # [FIX] Closer spacing (250 -> 150)
                    "nodeSpacing": 100,     # [FIX] Closer vertical spacing (150 -> 100)
                    "treeSpacing": 200,     # Distance between trees
                    "blockShifting": True,
                    "edgeMinimization": True,
                    "parentCentralization": True,
                    "direction": "LR",        # Left to Right
                    "sortMethod": "directed"  # Strict dependency
                }
                
                config = Config(
                    width="100%",   
                    height=600,     
                    directed=True, 
                    hierarchical=True, # We pass implicit true, but options below might override if passed in **kwargs
                    # agraph wrapper might not support dict for 'hierarchical' in constructor args directly?
                    # Let's trust standard args, but use 'layout' if possible.
                    # Config object source suggests: self.hierarchical = hierarchical.
                    # If we pass dict to 'hierarchical', it might work? 
                    # Let's try passing dict to hierarchical arg.
                    
                    physics={
                        "enabled": False,
                        "stabilization": True # [FIX] Enable stabilization to center graph
                    },
                    nodeHighlightBehavior=True, 
                    highlightColor="#F7A531",
                    # fit=True (Default) - [FIX] Re-enable Fit to ensure visual presence
                    
                    # Extra options via kwargs if supported by library wrapper:
                    layout={"hierarchical": hierarchical_opts},
                    interaction={"dragView": True, "zoomView": True, "hover": True}
                )
                
                agraph(nodes=nodes, edges=edges, config=config)

    # ---------------- TAB 3: DETAILED HISTORY (Was Tab 4) ----------------
    with tab3:
        st.subheader("🔍 Chi tiết từng câu")
        
        res_df = pd.DataFrame(hist)
        if not res_df.empty:
            st.dataframe(
                res_df[['skill', 'is_correct', 'q_id']].style.map(
                    lambda x: 'background-color: #d4edda' if x == True else ('background-color: #f8d7da' if x == False else ''),
                    subset=['is_correct']
                ),
                use_container_width=True
            )
            
            # Phân tích điểm yếu
            wrong_skills = res_df[res_df['is_correct'] == False]['skill'].unique()
            if len(wrong_skills) > 0:
                st.warning("⚠️ Các chủ đề cần ôn tập lại:")
                for s in wrong_skills:
                    c_rev, c_btn = st.columns([4, 1])
                    with c_rev: st.markdown(f"- **{s}**")
                    with c_btn:
                        if st.button(f"Ôn tập", key=f"review_{s}"):
                            st.session_state["jump_to_lecture_id"] = s
                            st.switch_page("pages/1_📖_Bai_Giang.py")

    if st.button("🔄 Làm bài kiểm tra mới", type="primary"):
        # [FIX] Đồng nhất biến cờ
        st.session_state.show_result = False 
        # Reset toàn bộ session test
        st.session_state.test_session = {
            "active": False,
            "mode": None,
            "questions_queue": [],
            "current_q_index": 0,
            "history": [],
            "start_time": None,
            "limit_minutes": 0,
            "score": 0,
            "current_q": None,      # Reset câu hỏi hiện tại
            "answer_submitted": False
        }
        st.rerun()
        
    if st.button("Về trang chủ"):
        st.session_state.show_result = False
        ts["active"] = False
        ts["history"] = []
        st.session_state["view_mode"] = "home"
        st.switch_page("app.py")