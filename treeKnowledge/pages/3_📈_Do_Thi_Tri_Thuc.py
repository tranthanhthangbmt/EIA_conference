import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import ast
import streamlit.components.v1 as components # Module để hiển thị HTML/MathJax
from streamlit_agraph import agraph, Node, Edge, Config
from collections import defaultdict

# --- SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try: 
    from db_utils import (
        get_user_progress, 
        get_user_settings, 
        save_user_settings, 
        get_all_users_list
    )
    # 🔁 Dùng chung engine luyện tập
    from practice_engine import (
        pick_question_for_skill,
        grade_and_update,
        recommend_next_skill_strict
    )
except ImportError: 
    st.error("Lỗi: Không tìm thấy module db_utils hoặc practice_engine.")
    st.stop()


if "authentication_status" not in st.session_state or st.session_state["authentication_status"] is None:
    st.warning("🔒 Đăng nhập."); st.stop()

st.set_page_config(page_title="Đồ thị tri thức", page_icon="📈", layout="wide")

# ============================================================
# 🎛️ SIDEBAR
# ============================================================
# 🎛️ SIDEBAR
# ============================================================
st.sidebar.header("📂 Chọn Môn Học")
from db_utils import get_all_subjects

all_subjects = get_all_subjects() # Returns list of tuples (id, name)

# FILTER FOR STUDENT
role = st.session_state.get('role', 'guest')
if role == 'student':
    try:
        from db_utils import get_student_subjects
        username = st.session_state.get('username')
        student_subs = get_student_subjects(username) # [(id, name), ...]
        
        # If student has enrolled subjects, use only those
        # If empty (new student), keep all_subjects?
        # User implies "Only ... enrolled ...", so if empty, likely empty list.
        # But to avoid crashing index calls, we might handle carefully.
        # But get_student_subjects returns a list.
        
        # Intersection logic based on IDs to be safe
        # (Though get_student_subjects logic already joins with subjects table, so likely good)
        if student_subs:
             all_subjects = student_subs
        else:
             # If strictly enforcement:
             # all_subjects = [] 
             # But this might stop the page at line 47.
             # User wants restrictive.
             # Let's verify if get_student_subjects returns empty list.
             # If so, the next block handles "if not all_subjects: st.error..."
             all_subjects = []
             
    except ImportError: pass

if not all_subjects:
    st.error("Chưa có môn học nào. Vui lòng tạo trong CMS.")
    st.stop()

subject_options = [s[0] for s in all_subjects]
subject_map = {s[0]: s[1] for s in all_subjects}

# Tìm index mặc định
default_index = 0
if "current_subject" in st.session_state and st.session_state.current_subject in subject_options:
    default_index = subject_options.index(st.session_state.current_subject)

selected_subject_id = st.sidebar.selectbox(
    "Môn học:", 
    subject_options, 
    index=default_index, 
    format_func=lambda x: f"{x} - {subject_map.get(x, '')}",
    key="sb_graph_smart_match"
)
st.session_state.current_subject = selected_subject_id
selected_subject = selected_subject_id # Alias

st.sidebar.markdown("---")
st.sidebar.header("🎨 Hiển thị & Cài đặt")

current_username = st.session_state.get('username', 'guest')
db_threshold, db_alpha = get_user_settings(current_username, selected_subject)

new_threshold = st.sidebar.slider(
    "🎯 Ngưỡng thành thạo:", 0.5, 1.0, float(db_threshold), 0.05,
    key="slider_graph_threshold",
    help="Điểm số tối thiểu để bài học chuyển sang màu Xanh."
)

if new_threshold != db_threshold:
    save_user_settings(current_username, selected_subject, new_threshold, db_alpha)
    st.rerun()

mastery_threshold = new_threshold
st.sidebar.markdown("---"); st.sidebar.write(f"👤 **{st.session_state.get('name', 'User')}**")

# --- MAIN CONTENT ---
current_subject = st.session_state["current_subject"]

# === 👇 ĐOẠN CODE CẬP NHẬT: ADMIN CHỌN USER 👇 ===
# Logic cũ: username = st.session_state["username"]

# Logic mới:
# Logic phân quyền xem dữ liệu
real_user = st.session_state["username"]
user_role = st.session_state.get("role", "student")

# Admin/Manager/Teacher được phép xem dữ liệu người khác
can_view_others = user_role in ["admin", "manager", "teacher"]

target_user = real_user # Mặc định

if can_view_others:
    st.sidebar.warning(f"👮‍♂️ Chế độ {user_role.title()}")
    
    all_users = get_all_users_list()
    # Teacher chỉ nên thấy Student (Logic nâng cao sau này, hiện tại cứ cho thấy hết)
    # if user_role == 'teacher':
    #    all_users = [u for u in all_users if u[2] == 'student']
    
    st.sidebar.markdown("---")
    st.sidebar.warning("👮‍♂️ Chế độ Admin")
    
    # Import hàm lấy danh sách user (cần đảm bảo đã thêm vào db_utils)
    from db_utils import get_all_users_list
    all_users = get_all_users_list()
    
    # Tạo dictionary để hiển thị tên đẹp hơn: "Tên (username)"
    user_options = {u[0]: f"{u[1]} ({u[0]})" for u in all_users}
    
    selected_u = st.sidebar.selectbox(
        "👀 Xem dữ liệu của:", 
        options=list(user_options.keys()),
        format_func=lambda x: user_options[x],
        key="admin_select_user_graph" # Key riêng cho trang này
    )
    target_user = selected_u
    
    if target_user != real_user:
        st.info(f"📢 Đang xem Đồ thị tri thức của học viên: **{user_options[target_user]}**")

# Gán biến username để các hàm bên dưới hoạt động như bình thường
username = target_user 
# =================================================

# =================================================
subject_name = subject_map.get(st.session_state.current_subject, st.session_state.current_subject)
st.markdown(f"<h1 style='text-align: center;'>📈 Bản đồ Tri thức: {subject_name}</h1>", unsafe_allow_html=True)

# [NEW] Horizontal Legend Layout
st.markdown("""
<div style="display: flex; justify-content: center; align-items: center; flex-wrap: wrap; gap: 15px; margin-bottom: 20px;">
    <div style="display: flex; align-items: center;"><span style="height: 10px; width: 10px; background-color: #CFD8DC; border-radius: 50%; display: inline-block; margin-right: 5px;"></span>0% (Chưa học)</div>
    <div style="display: flex; align-items: center;"><span style="height: 10px; width: 10px; background-color: #FFD600; border-radius: 50%; display: inline-block; margin-right: 5px;"></span>Đang học</div>
    <div style="display: flex; align-items: center;"><span style="height: 10px; width: 10px; background-color: #B9F6CA; border-radius: 50%; display: inline-block; margin-right: 5px;"></span>70-84% (Đạt)</div>
    <div style="display: flex; align-items: center;"><span style="height: 10px; width: 10px; background-color: #69F0AE; border-radius: 50%; display: inline-block; margin-right: 5px;"></span>85-99% (Tốt)</div>
    <div style="display: flex; align-items: center;"><span style="height: 10px; width: 10px; background-color: #00C853; border-radius: 50%; display: inline-block; margin-right: 5px;"></span>100% (Hoàn thành)</div>
    <div style="display: flex; align-items: center;"><span style="height: 10px; width: 10px; background-color: #FF5252; border-radius: 50%; display: inline-block; margin-right: 5px;"></span>Cần ôn tập</div>
    <div style="display: flex; align-items: center; border: 1px solid #D50000; padding: 2px 6px; border-radius: 12px; background-color: #FFEBEE; color: #D50000; font-weight: bold;">🎯 Mục tiêu tiếp theo</div>
</div>
""", unsafe_allow_html=True)

DATA_FOLDER = os.path.join(parent_dir, "knowledge", current_subject)
GRAPH_FILE = os.path.join(DATA_FOLDER, "k-graph.csv")
MATRIX_FILE = os.path.join(DATA_FOLDER, "q-matrix.csv")

@st.cache_data
def load_data(g, m):
    try:
        if not os.path.exists(g) or not os.path.exists(m): return None, None
        # Strip whitespace to be safe
        k = pd.read_csv(g, comment='#')
        k.columns = k.columns.str.strip()
        k['source'] = k['source'].astype(str).str.strip()
        k['target'] = k['target'].astype(str).str.strip()
        
        q = pd.read_csv(m, comment='#')
        return k, q
    except: return None, None

#k_graph_df, q_matrix_df = load_data(GRAPH_FILE, MATRIX_FILE)
from db_utils import get_all_questions
from db_utils import get_graph_structure
k_graph_df = get_graph_structure(selected_subject) # Load từ DB
q_matrix_df = get_all_questions(selected_subject) # Load từ DB

# [FIX] Clean Whitespace
if not k_graph_df.empty:
    k_graph_df['source'] = k_graph_df['source'].astype(str).str.strip()
    k_graph_df['target'] = k_graph_df['target'].astype(str).str.strip()


if k_graph_df is None: st.stop()

# --- LẤY DỮ LIỆU ĐIỂM SỐ ---
raw_progress = get_user_progress(username, current_subject)
direct_scores = {} # {id_in_db: score}
direct_status = {}
db_keys = [] # Danh sách key có trong DB để đối chiếu

if raw_progress:
    for row in raw_progress:
        clean_id = str(row[0]).strip()
        direct_scores[clean_id] = row[2]
        direct_status[clean_id] = row[1]
        db_keys.append(clean_id)

user_mastery = direct_scores # Alias for practice engine compatibility
            

# ============================================================
# 🧠 SMART MATCHING & AGGREGATION
# ============================================================
children_map = defaultdict(list)
for _, row in k_graph_df.iterrows():
    children_map[row['source']].append(row['target'])

memo_calc = {} 
matched_keys_log = {} # Để debug xem nó map cái gì với cái gì

def find_best_score_in_db(graph_node_id):
    """
    Tìm điểm trong DB. Nếu không khớp chính xác, thử tìm khớp một phần (Prefix).
    Ví dụ: Graph='2.2' sẽ khớp với DB='2.2_BucTranhLon'
    """
    # 1. Exact Match (Ưu tiên cao nhất)
    if graph_node_id in direct_scores:
        matched_keys_log[graph_node_id] = f"Exact: {graph_node_id}"
        return direct_scores[graph_node_id], direct_status.get(graph_node_id, "")
    
    # 2. Prefix Match (Thông minh)
    # Chỉ áp dụng cho node lá (có dấu chấm như 1.1, 2.2...) để tránh map nhầm '1' vào '10'
    if "." in graph_node_id:
        for db_k in db_keys:
            if db_k.startswith(graph_node_id + "_") or db_k.startswith(graph_node_id + " "):
                matched_keys_log[graph_node_id] = f"Smart Match: {db_k}"
                return direct_scores[db_k], direct_status[db_k]
                
    return None, None # Không tìm thấy

def calculate_node_status(node, threshold):
    if node in memo_calc: return memo_calc[node]
    
    # --- SỬA ĐỔI QUAN TRỌNG ---
    # 1. Luôn ưu tiên kiểm tra xem nút này có phải là bài học đã có điểm trong DB không
    score, status = find_best_score_in_db(node)
    
    if score is not None: 
        # Nếu ĐÃ CÓ điểm thực tế của chính nó (Dù nó có con hay không)
        # Thì trạng thái của nó phụ thuộc vào chính nó, không phụ thuộc vào con.
        is_mastered = (score >= threshold)
        memo_calc[node] = (score, is_mastered, status)
        return score, is_mastered, status

    # 2. Chỉ khi KHÔNG có điểm trong DB (Ví dụ: Nút Chương/Mục lục "Chg1_TongQuan")
    # Thì mới dùng logic gộp điểm từ các con
    kids = children_map.get(node, [])
    
    # Trường hợp cô lập (không con, không điểm)
    if not kids:
        memo_calc[node] = (0.0, False, None)
        return 0.0, False, None

    # Trường hợp là Nút Chương (Container) -> Tính trung bình các con
    total_score = 0
    all_kids_mastered = True
    
    for kid in kids:
        s, m, _ = calculate_node_status(kid, threshold)
        total_score += s
        if not m: all_kids_mastered = False
            
    avg_score = total_score / len(kids) if kids else 0.0
    is_mastered = all_kids_mastered
    
    memo_calc[node] = (avg_score, is_mastered, None)
    return avg_score, is_mastered, None

# Tính toán toàn bộ
all_nodes = set(k_graph_df['source']).union(set(k_graph_df['target']))
node_info_map = {} 

# --- 👇 QUAN TRỌNG: PHẢI BỎ COMMENT ĐOẠN NÀY ĐỂ TÍNH TOÁN ---
# --- 👇 QUAN TRỌNG: PHẢI BỎ COMMENT ĐOẠN NÀY ĐỂ TÍNH TOÁN ---
for n in all_nodes:
    node_info_map[n] = calculate_node_status(n, mastery_threshold)
# ------------------------------------------------------------

# ============================================================
# [NEW] GIAO DIỆN & XỬ LÝ DỮ LIỆU ĐỒ THỊ
# ============================================================

# [CHANGED] Default to Full Mode always, no UI controls
show_mode = "Đầy đủ (+)"
st.session_state.graph3_auto_expanded = True # Flag compatibility

# --- GRAPH DATA GENERATION ---
nodes = []
edges = []
added_nodes = set()
node_to_chapter = {}

# 1. Identify Chapters & Map Nodes
# Re-using previous logic or simplified:
all_graph_nodes = set(k_graph_df['source']).union(set(k_graph_df['target']))
chapters = []
for n in all_graph_nodes:
     if "Chg" in str(n) or str(n).isdigit() or (len(str(n)) < 5 and "." not in str(n)):
         chapters.append(str(n))

# BFS/Map Logic to find owner chapter
adj = defaultdict(list)
for _, row in k_graph_df.iterrows():
    adj[str(row['source'])].append(str(row['target']))

for chap in chapters:
    queue = [chap]
    visited = set()
    while queue:
        curr = queue.pop(0)
        if curr not in node_to_chapter: node_to_chapter[curr] = chap
        if curr in adj:
            for child in adj[curr]:
                if child in chapters and child != chap: continue
                if child not in visited:
                    visited.add(child); queue.append(child)

# 2. Sort Chapters
import re
try:
    sorted_chapters = sorted(chapters, key=lambda x: int(re.search(r'\d+', x).group()))
except: 
    sorted_chapters = list(chapters)

# 3. Determine Visibility
visible_nodes = set()

# Pre-check scores for filtering
nodes_with_scores = set()
for n in all_graph_nodes:
    # Use existing node_info_map if available or re-calc
    # We have node_info_map from line 285
    # node_info_map[n] = (score, is_mastered, status)
    if node_info_map.get(n, (None, False, None))[0] is not None:
         nodes_with_scores.add(n)

# Check active chapters (having any tested child)
active_chapters = set()
for n, c in node_to_chapter.items():
    if n in nodes_with_scores:
        active_chapters.add(c)

for n in all_graph_nodes:
    is_chap = n in chapters
    if show_mode == "Đầy đủ (+)":
        visible_nodes.add(n)
    else:
        # Rút gọn
        if is_chap:
            if n in active_chapters or n in nodes_with_scores:
                visible_nodes.add(n)
        elif n in nodes_with_scores:
            visible_nodes.add(n)

visible_chapters_ordered = [c for c in sorted_chapters if c in visible_nodes]

# ============================================================
# [NEW] LEARNING PATH VISUALIZATION (PHASE 6)
# ============================================================
recommended_node = None
try:
    # Calculate next recommended node for visualization
    # We use the same strict logic as the Practice Page
    # Reuse user_mastery, k_graph_df, q_matrix_df loaded above
    rec_target, _, _ = recommend_next_skill_strict(
        user_mastery, k_graph_df, q_matrix_df, 
        threshold=mastery_threshold
    )
    recommended_node = rec_target
    
    # [VISUALIZATION] Banner thông báo mục tiêu
    if recommended_node:
        st.markdown(
            f"""
            <div style="
                background-color: #e3f2fd; 
                border-left: 5px solid #2196F3; 
                padding: 12px 20px; 
                border-radius: 4px; 
                margin-bottom: 20px; 
                display: flex; 
                align-items: center;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            ">
                <span style="font-size: 1.5rem; margin-right: 15px;">🎯</span>
                <div>
                    <div style="font-weight: bold; color: #0d47a1; font-size: 1.1rem;">MỤC TIÊU TIẾP THEO</div>
                    <div style="color: #555;">Hệ thống gợi ý bạn nên học bài: <b>{recommended_node}</b></div>
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )
except Exception as e:
    pass

# 4. Create Nodes & Edges
for idx, row in k_graph_df.iterrows():
    src = str(row['source'])
    tgt = str(row['target'])
    
    final_src = None
    if src in visible_nodes and tgt in visible_nodes:
        final_src = src
    elif src not in visible_nodes and tgt in visible_nodes:
        owner_chap = node_to_chapter.get(tgt)
        if owner_chap and owner_chap in visible_nodes:
            final_src = owner_chap
            
    if final_src:
        # Add Nodes
        for node in [final_src, tgt]:
            if node not in added_nodes:
                score, is_mastered, status = node_info_map.get(node, (None, False, None))
                
                # Logic màu sắc (Đồng bộ)
                color = "#CFD8DC" # Xám
                if is_mastered:
                    if score >= 1.0: color = "#00C853"
                    elif score >= 0.85: color = "#69F0AE"
                    else: color = "#B9F6CA"
                elif status == "Review": color = "#FF5252"
                elif score is not None and score > 0: color = "#FFD600"
                
                # --- [PHASE 6] HIGHLIGHT RECOMMENDED NODE ---
                is_target = (node == recommended_node)
                if is_target:
                    # Target Style: Red Border + Pulse Effect (Simulated by width)
                    borderColor = "#D50000" # Red
                    borderWidth = 8
                    shadow = {"enabled": True, "color": "#D50000", "size": 20}
                    label_prefix = "🎯 "
                    title_suffix = "\n🔥 BÀI TIẾP THEO (Recommended)"
                else:
                    borderColor = "#2c3e50"
                    shadow = {"enabled": False}
                    label_prefix = ""
                    title_suffix = ""

                # Style
                is_chapter_node = node in chapters
                label = label_prefix + node
                
                if is_chapter_node:
                    num_match = re.search(r"\d+", node)
                    num_str = num_match.group(0) if num_match else "?"
                    label = f"{num_str}. {node}"
                    shape = "square"
                    size = 50 
                    font = "bold 40px arial black" 
                    if not is_target: borderWidth = 6 
                else:
                    shape = "dot"
                    size = 40
                    font = {'size': 28, 'color': 'black'} 
                    if not is_target: borderWidth = 2 
                
                # Level
                level = 0
                try:
                    owner_chap = node_to_chapter.get(node)
                    c_idx = -1
                    if owner_chap in visible_chapters_ordered:
                        c_idx = visible_chapters_ordered.index(owner_chap)
                    if c_idx != -1:
                        level = c_idx * 2 if is_chapter_node else c_idx * 2 + 1
                except: pass

                nodes.append(Node(
                    id=node,
                    label=label,
                    size=size,
                    color=color,
                    shape=shape,
                    font=font,
                    borderWidth=borderWidth,
                    border_color=borderColor if is_target else None,
                    shadow=shadow,
                    title=f"{node}\nTiến độ: {score:.0%}{title_suffix}" if score is not None else node,
                    level=level,
                    shapeProperties={"borderRadius": 5} if shape=="box" else {}
                ))
                added_nodes.add(node)
        
        # Add Edge
        w = 6 if final_src in chapters else 2 # [ZOOM 2x] 3->6, 1->2
        edges.append(Edge(source=final_src, target=tgt, color="#bdc3c7", width=w))

# 5. Spine
visible_chapters_sorted = [c for c in sorted_chapters if c in added_nodes]
num_spine = len(visible_chapters_sorted) - 1
max_w, min_w = 24, 4 # [ZOOM 2x] 12->24, 2->4

for i in range(num_spine):
    c1 = visible_chapters_sorted[i]
    c2 = visible_chapters_sorted[i+1]
    
    decay = (max_w - min_w) * (i / (num_spine - 1)) if num_spine > 1 else 0
    cur_w = max_w - decay
    
    edges.append(Edge(source=c1, target=c2, color="#2979FF", width=int(cur_w), dashes=[15, 15]))


# 1. CSS ĐỂ TẠO LAYOUT TRÀN MÀN HÌNH & THẺ NỔI
# ============================================================
# 🎨 VẼ GIAO DIỆN: FULL SCREEN GRAPH & FLOATING LEGEND
# ============================================================
# 1. CSS ĐỂ TẠO LAYOUT TRÀN MÀN HÌNH, TẮT SCROLL & SỬA LỖI SIDEBAR
# [REMOVED] Floating Legend (Moved to Top)
pass

# --- JS ĐỂ BIẾN DISPLAY MODE THÀNH FLOATING PANEL ---
# [CLEANED] JS Floating Hacks Removed
pass

# --- LOGIC FORCE REFRESH KHI ĐÓNG DIALOG ---
if "graph_version" not in st.session_state:
    st.session_state.graph_version = 0
if "last_selected_node" not in st.session_state:
    st.session_state.last_selected_node = None

# Hack: Thay đổi height một chút xíu để force update vì agraph không hỗ trợ key
# Khi graph_version chẵn -> 800px, lẻ -> 801px
dynamic_height = 800 + (st.session_state.graph_version % 2)

# 2. CẤU HÌNH ĐỒ THỊ (FULL HEIGHT)
# 2. CẤU HÌNH ĐỒ THỊ (FULL HEIGHT)
config = Config(
    width="100%", 
    height=450, 
    directed=True, 
    hierarchical=True,
    physics={
        "enabled": False, 
        "stabilization": True 
    },
    fit=False, # [CHANGED] Do NOT fit to screen (Zoom 100% initially)
    layout={
        "hierarchical": {
            "enabled": True,
            "levelSeparation": 300, # [ZOOM 2x] 150 -> 300
            "nodeSpacing": 200,     # [ZOOM 2x] 100 -> 200
            "direction": "LR", # Left to Right
            "sortMethod": "directed"
        }
    },
    interaction={"dragView": True, "zoomView": True, "hover": True}
)

# 3. VẼ ĐỒ THỊ
with st.container(border=True):
    selected_skill = agraph(nodes=nodes, edges=edges, config=config)

# --- LOGIC GIỮ DIALOG KHÔNG BỊ ĐÓNG KHI RERUN TỪ BÊN TRONG ---
if "keep_dialog_open" not in st.session_state:
    st.session_state.keep_dialog_open = False

if st.session_state.keep_dialog_open:
    # Nếu cờ này bật, ta giả vờ như người dùng vẫn đang chọn node cũ
    # để tránh lọt vào logic "đóng dialog" bên dưới
    if st.session_state.last_selected_node:
        selected_skill = st.session_state.last_selected_node
    
    # Reset cờ ngay lập tức để lần sau nếu user click ra ngoài thật thì nó vẫn đóng được
    st.session_state.keep_dialog_open = False
# -------------------------------------------------------------

# Kiểm tra sự kiện đóng dialog
# Nếu trước đó có chọn (last_selected_node != None) mà giờ không chọn (selected_skill == None)
# -> Người dùng vừa đóng dialog -> Cần refresh để cập nhật màu
if selected_skill is None and st.session_state.last_selected_node is not None:
    st.session_state.last_selected_node = None
    st.session_state.graph_version += 1
    st.cache_data.clear() # Xóa cache toàn bộ để đảm bảo dữ liệu mới nhất
    st.toast("🔄 Đang làm mới đồ thị...", icon="🔄")
    st.rerun()

# Cập nhật trạng thái chọn hiện tại
if selected_skill is not None:
    st.session_state.last_selected_node = selected_skill

@st.dialog(" ", width="large") 
def show_node_details(node_id):
    # --- CSS TÙY CHỈNH: ẨN HEADER, NÚT XANH & BỐ CỤC ---
    st.markdown("""
        <style>
            /* 1. ẨN TIÊU ĐỀ MẶC ĐỊNH CỦA DIALOG */
            div[data-testid="stDialog"] h2 {
                display: none; /* Ẩn hoàn toàn dòng chữ tiêu đề */
            }
            /* Đẩy nội dung lên sát mép trên (giảm khoảng trắng thừa) */
            div.stDialog > div[data-testid="stDialogContent"] {
                padding-top: 10px !important;
            }

            /* 2. Style cho các nút BÌNH THƯỜNG (Secondary) */
            button[data-testid="baseButton-secondary"] {
                background-color: #ffffff; 
                color: #555;
                border: 1px solid #dce0e6;
                transition: all 0.2s;
            }
            button[data-testid="baseButton-secondary"]:hover {
                border-color: #0078D4;
                color: #0078D4;
                background-color: #f0f8ff;
            }

            /* 3. Style cho nút ĐANG CHỌN (Primary) */
            button[data-testid="baseButton-primary"] {
                background-color: #0078D4 !important;
                color: white !important;
                border: 1px solid #0078D4 !important;
                font-weight: bold;
            }
            button[data-testid="baseButton-primary"]:hover {
                background-color: #005a9e !important;
                border-color: #005a9e !important;
                color: white !important;
            }

            /* 4. Box câu hỏi màu xanh nhạt */
            .question-box {
                background-color: #E3F2FD; 
                border-left: 5px solid #2196F3; 
                padding: 15px;
                border-radius: 5px;
                color: #0d47a1;
                font-weight: 500;
                margin-bottom: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

    # 1. Lấy dữ liệu
    s_score, s_mastered, _ = node_info_map.get(node_id, (0.0, False, None))
    kids = children_map.get(node_id, [])
    
    # Lọc câu hỏi
    if q_matrix_df is not None:
        qs = q_matrix_df[q_matrix_df['skill_id_list'].astype(str).str.contains(node_id, na=False)]
        qs = qs.reset_index(drop=True)
        total_qs = len(qs)
    else:
        qs = pd.DataFrame()
        total_qs = 0

    # --- TABS (Sẽ hiển thị ngay trên cùng) ---
    tab_info, tab_theory, tab_practice = st.tabs(["📊 Tổng quan & Chỉ số", "📖 Lý thuyết", "📝 Luyện tập & Câu hỏi"])

    # ========================================================
    # TAB 2: LÝ THUYẾT (MỚI)
    # ========================================================
    with tab_theory:
        # Lấy nội dung từ DB
        from db_utils import get_resource
        resource = get_resource(node_id)
        
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

            # --- C. TEXT / MARKDOWN / HTML ---
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
                            height=600,  # Chiều cao khung hiển thị
                            scrolling=True,
                        )
                    else:
                        # markdown/text thường không có công thức phức tạp → render như cũ
                        st.markdown(res_desc, unsafe_allow_html=True)
        else:
            st.info(f"📭 Chưa có nội dung lý thuyết cho: {node_id}")

    # ========================================================
    # TAB 1: TỔNG QUAN
    # ========================================================
    with tab_info:
        # Header nội dung (Tên bài học & Badge)
        c_title, c_badge = st.columns([3, 1.2], vertical_alignment="center")
        with c_title:
            st.subheader(f"📍 {node_id}", help=f"ID tham chiếu: {node_id}")
        with c_badge:
            if s_mastered:
                st.markdown(f"<div style='background:#d1e7dd;color:#0f5132;padding:6px 12px;border-radius:20px;text-align:center;font-weight:600;font-size:0.9rem;border:1px solid #badbcc;'>✅ Hoàn thành</div>", unsafe_allow_html=True)
            elif s_score > 0:
                st.markdown(f"<div style='background:#fff3cd;color:#664d03;padding:6px 12px;border-radius:20px;text-align:center;font-weight:600;font-size:0.9rem;border:1px solid #ffecb5;'>⚠️ Đang học</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background:#f8f9fa;color:#6c757d;padding:6px 12px;border-radius:20px;text-align:center;font-weight:600;font-size:0.9rem;border:1px solid #dee2e6;'>⚪ Chưa học</div>", unsafe_allow_html=True)
        
        st.divider()
        # (Đã bỏ nút Học lý thuyết ngay vì đã có tab Lý thuyết riêng)
        # =====================================================

        # Metrics
        m1, m2, m3 = st.columns(3)
        with m1:
            with st.container(border=True):
                st.metric("Điểm năng lực", f"{s_score:.0%}")
                st.progress(s_score)
        with m2:
            with st.container(border=True):
                st.metric("Ngân hàng câu hỏi", f"{total_qs} câu")
        with m3:
            with st.container(border=True):
                st.metric("Chủ đề con", f"{len(kids)} mục")
        
        # Danh sách con
        st.markdown("#### 📂 Cấu trúc nội dung")
        if kids:
            for k in kids:
                k_score, k_mastered, _ = node_info_map.get(k, (0, False, None))
                icon = "✅" if k_mastered else ("🔥" if k_score > 0 else "⚪")
                with st.container(border=True):
                    col_a, col_b = st.columns([4, 1])
                    col_a.markdown(f"**{icon} {k}**")
                    col_b.caption(f"{k_score:.0%}")
                    col_a.progress(k_score)
        else:
            st.info("💡 Đây là bài học chi tiết (Node lá), không có mục con.")

    # ========================================================
    # ========================================================
    # TAB 2: Luyện tập dùng chung engine với tab 🎓 Luyện tập
    # ========================================================
    with tab_practice:
        if qs.empty:
            st.markdown(
                """<div style="text-align: center; padding: 40px; color: #6c757d; 
                            border: 2px dashed #dee2e6; border-radius: 10px; margin-top: 10px;">
                        <h3>📭 Chưa có dữ liệu</h3>
                        <p>Hiện chưa có câu hỏi nào cho mục này.</p>
                   </div>""",
                unsafe_allow_html=True
            )
        else:
            # --- Session keys riêng cho mỗi node trên graph ---
            session_prefix = f"graph_prac_{node_id}"
            q_key        = session_prefix + "_q"
            submitted_key = session_prefix + "_submitted"
            choice_key    = session_prefix + "_choice"
            result_key    = session_prefix + "_result"
            correct_key   = session_prefix + "_correct"
            last_qid_key  = session_prefix + "_last_qid"
            score_key     = session_prefix + "_score"

            # Điểm ban đầu của node
            base_score, _, _ = node_info_map.get(node_id, (0.0, False, None))
            if score_key not in st.session_state:
                st.session_state[score_key] = base_score

            # Khởi tạo câu hỏi nếu chưa có
            if q_key not in st.session_state or st.session_state[q_key] is None:
                # MẶC ĐỊNH CHỌN CÂU ĐẦU TIÊN NẾU CÓ
                if not qs.empty:
                    q_dict = qs.iloc[0].to_dict()
                else:
                    q_dict = None
                
                st.session_state[q_key] = q_dict
                st.session_state.setdefault(submitted_key, False)
                st.session_state.setdefault(choice_key, None)
                st.session_state.setdefault(result_key, None)
                st.session_state.setdefault(correct_key, None)

            q_data = st.session_state[q_key]

            if q_data is None:
                st.warning("⚠️ Không tìm thấy câu hỏi phù hợp cho mục này.")
                return

            # Lấy biến trạng thái hiện tại
            submitted = st.session_state.get(submitted_key, False)
            result    = st.session_state.get(result_key, None)
            curr_score = st.session_state.get(score_key, base_score)

            # Header area with columns
            h_col1, h_col2 = st.columns([2.5, 1])
            with h_col1:
                st.markdown(f"### 📝 Luyện tập nhanh: `{node_id}`")
                st.caption(f"📚 Ngân hàng: **{total_qs}** câu hỏi cho mục này.")
            
            with h_col2:
                # Render Progress Bar IMMEDIATELY
                st.progress(curr_score, text=f"Điểm hiện tại: {curr_score:.0%} / {mastery_threshold:.0%}")

            st.divider()

            # --- LAYOUT CHÍNH: 2 CỘT (TRÁI: INDEX, PHẢI: NỘI DUNG) ---
            c_left, c_right = st.columns([1.2, 3], gap="medium")

            # ===== CỘT TRÁI: DANH SÁCH CÂU HỎI (CALENDAR STYLE) =====
            with c_left:
                st.markdown("###### 🗓️ Danh sách câu hỏi")
                if not qs.empty:
                    # Tạo lưới 5 cột cho giống lịch
                    grid_cols = st.columns(5)
                    
                    # Hàm callback
                    def set_specific_question(row_dict):
                        st.session_state.keep_dialog_open = True # Giữ dialog
                        st.session_state[q_key] = row_dict
                        st.session_state[submitted_key] = False
                        st.session_state[result_key] = None
                        st.session_state[correct_key] = None
                        st.session_state[choice_key] = None

                    for idx, row in qs.iterrows():
                        q_id_display = idx + 1
                        real_q_id = row['question_id']
                        
                        is_active = False
                        if q_data and q_data['question_id'] == real_q_id:
                            is_active = True
                        
                        btn_type = "primary" if is_active else "secondary"
                        
                        with grid_cols[idx % 5]:
                            st.button(
                                f"{q_id_display}", 
                                key=f"btn_q_{node_id}_{real_q_id}", 
                                type=btn_type, 
                                use_container_width=True,
                                on_click=set_specific_question,
                                args=(row.to_dict(),)
                            )
                else:
                    st.info("Trống")

            # ===== CỘT PHẢI: NỘI DUNG & THAO TÁC =====
            with c_right:
                # 1. Nội dung câu hỏi
                st.markdown(
                    f"""
                    <div class="question-box">
                        ❓ {q_data['content']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # 2. Các lựa chọn
                try:
                    ops = ast.literal_eval(q_data["options"])
                except Exception:
                    ops = []

                st.radio(
                    "Lựa chọn của bạn:",
                    options=ops,
                    key=choice_key,
                    index=None,
                    label_visibility="collapsed",
                    disabled=submitted
                )

                # Logic tìm index cho Prev/Next
                current_q_idx = -1
                if q_data and not qs.empty:
                    matches = qs.index[qs['question_id'] == q_data['question_id']].tolist()
                    if matches: current_q_idx = matches[0]

                def change_question(new_row):
                    st.session_state.keep_dialog_open = True # Giữ dialog
                    st.session_state[q_key] = new_row.to_dict()
                    st.session_state[submitted_key] = False
                    st.session_state[result_key] = None
                    st.session_state[correct_key] = None
                    st.session_state[choice_key] = None

                # 3. Hiển thị kết quả (Feedback) & Nút điều hướng
                if submitted:
                    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                    
                    # Layout: [Kết quả] [Trước] [Sau]
                    r_col, nav_prev, nav_next = st.columns([2, 1, 1])
                    
                    with r_col:
                        if result:
                            st.markdown(
                                "<div class='result-box success-box'>🎉 CHÍNH XÁC!</div>",
                                unsafe_allow_html=True
                            )
                            st.balloons()
                        else:
                            st.markdown(
                                "<div class='result-box error-box'>❌ SAI RỒI</div>",
                                unsafe_allow_html=True
                            )
                            st.caption(f"💡 Đáp án: {st.session_state[correct_key]}")
                    
                    with nav_prev:
                        if current_q_idx > 0:
                            prev_row = qs.iloc[current_q_idx - 1]
                            st.button("⬅ Trước", use_container_width=True, key=f"{session_prefix}_btn_prev_sub", on_click=change_question, args=(prev_row,))
                        else:
                            st.button("⬅ Trước", disabled=True, use_container_width=True, key=f"{session_prefix}_btn_prev_sub_dis")
                            
                    with nav_next:
                        if current_q_idx < len(qs) - 1:
                            next_row = qs.iloc[current_q_idx + 1]
                            st.button("Sau ➡", use_container_width=True, key=f"{session_prefix}_btn_next_sub", on_click=change_question, args=(next_row,))
                        else:
                            st.button("Sau ➡", disabled=True, use_container_width=True, key=f"{session_prefix}_btn_next_sub_dis")

                else:
                    # Chưa nộp -> Hiện nút Kiểm tra & Điều hướng ở dưới
                    st.divider()
                    
                    # Layout: [Kiểm tra] ... [Trước] [Sau]
                    b_check, b_spacer, b_prev, b_next = st.columns([1.5, 0.5, 1, 1])
                    
                    with b_check:
                        if st.button("Kiểm tra ✨", use_container_width=True, key=f"{session_prefix}_submit", type="primary"):
                            sel = st.session_state.get(choice_key)
                            if not sel:
                                st.warning("⚠️ Chọn đáp án!")
                            else:
                                is_correct, new_score, correct_ans_text, status = grade_and_update(
                                    q_data=q_data,
                                    selected_option=sel,
                                    username=username,
                                    subject_id=current_subject,
                                    node_id=node_id,
                                    user_mastery=direct_scores,
                                    q_matrix_df=q_matrix_df,
                                    mastery_threshold=mastery_threshold,
                                    learning_rate=db_alpha
                                )
                                # Update State
                                direct_scores[node_id] = new_score
                                st.session_state.graph_version += 1
                                st.session_state[submitted_key] = True
                                st.session_state[result_key]    = is_correct
                                st.session_state[correct_key]   = correct_ans_text
                                st.session_state[last_qid_key]  = q_data["question_id"]
                                st.session_state[score_key]     = new_score
                                st.session_state.keep_dialog_open = True # Giữ dialog
                                st.rerun()

                    with b_prev:
                        if current_q_idx > 0:
                            prev_row = qs.iloc[current_q_idx - 1]
                            st.button("⬅ Trước", use_container_width=True, key=f"{session_prefix}_btn_prev", on_click=change_question, args=(prev_row,))
                        else:
                            st.button("⬅ Trước", disabled=True, use_container_width=True, key=f"{session_prefix}_btn_prev_dis")

                    with b_next:
                        if current_q_idx < len(qs) - 1:
                            next_row = qs.iloc[current_q_idx + 1]
                            st.button("Sau ➡", use_container_width=True, key=f"{session_prefix}_btn_next", on_click=change_question, args=(next_row,))
                        else:
                            st.button("Sau ➡", disabled=True, use_container_width=True, key=f"{session_prefix}_btn_next_dis")






# ============================================================
# 🚀 KÍCH HOẠT POPUP
# ============================================================
if selected_skill:
    show_node_details(selected_skill)

# --- DEBUGGER (ẨN/HIỆN) ---
# with st.expander("🔍 Debug Dữ liệu (Kiểm tra kết nối)"):
#     st.write("**1. Dữ liệu trong Database (User Progress):**")
#     st.write(db_keys)
    
#     st.write("**2. Kết quả khớp nối (Graph Node -> DB Key):**")
#     st.json(matched_keys_log)
    
#     st.write("**3. Các Node trên cây không tìm thấy dữ liệu:**")
#     unmatched = [n for n in all_nodes if n not in matched_keys_log and not children_map.get(n)]
#     st.write(unmatched)