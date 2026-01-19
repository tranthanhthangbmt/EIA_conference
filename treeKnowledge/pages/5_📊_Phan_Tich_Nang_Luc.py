import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys

# --- SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try: 
    # IMPORT THÊM get_user_settings
    from db_utils import get_user_progress, get_user_settings, get_all_users_list
except ImportError:
    st.error("Lỗi: Không tìm thấy module db_utils.")
    st.stop()

if "authentication_status" not in st.session_state or st.session_state["authentication_status"] is None:
    st.warning("🔒 Đăng nhập."); st.stop()

st.set_page_config(page_title="Phân tích năng lực", page_icon="📊", layout="wide")

# ============================================================
# 🎛️ SIDEBAR: CHỌN MÔN & XEM CẤU HÌNH
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
            enrolled = get_student_subjects(username)
            enrolled_ids = [item[0] for item in enrolled]
            return [s for s in all_subs if s in enrolled_ids]
        except ImportError: pass
             
    return all_subs
subjects = get_subjects()
if not subjects: st.stop()
if "current_subject" not in st.session_state: st.session_state.current_subject = subjects[0]
default_index = 0
if st.session_state.current_subject in subjects:
    default_index = subjects.index(st.session_state.current_subject)
selected_subject = st.sidebar.selectbox("Môn học:", subjects, index=default_index, key="sb_analytics_final")
st.session_state.current_subject = selected_subject

# --- LOAD SETTINGS ---
current_username = st.session_state.get('username', 'guest')
mastery_threshold, learning_rate = get_user_settings(current_username, selected_subject)

st.sidebar.markdown("---")
st.sidebar.info(f"""
**Cấu hình hiện tại:**
- 🎯 Ngưỡng đạt: **{mastery_threshold:.0%}**
- ⚡ Tốc độ học: **{learning_rate}**

*(Bạn có thể thay đổi các thông số này ở trang Luyện tập hoặc Đồ thị)*
""")

st.sidebar.markdown("---")
st.sidebar.write(f"👤 **{st.session_state.get('name', 'User')}**")

# --- MAIN CONTENT ---
current_subject = st.session_state["current_subject"]

# === 👇 ĐOẠN CODE CẬP NHẬT: ADMIN CHỌN USER 👇 ===

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
    from db_utils import get_all_users_list
    all_users = get_all_users_list()
    user_options = {u[0]: f"{u[1]} ({u[0]})" for u in all_users}
    
    selected_u = st.sidebar.selectbox(
        "👀 Xem dữ liệu của:", 
        options=list(user_options.keys()),
        format_func=lambda x: user_options[x],
        key="admin_select_user_analytics"
    )
    target_user = selected_u
    
    if target_user != real_user:
        st.info(f"📢 Đang xem Phân tích năng lực của học viên: **{user_options[target_user]}**")

username = target_user
# =================================================

st.title(f"📊 Phân tích năng lực: {current_subject}")

raw_progress = get_user_progress(username, current_subject)
if not raw_progress:
    st.info("👋 Chưa có dữ liệu học tập cho môn này.")
    st.markdown("Hãy bắt đầu bằng việc xem **📖 Bài giảng** hoặc làm **🎓 Luyện tập**.")
    st.stop()

# Tạo DataFrame
df = pd.DataFrame(raw_progress, columns=['Kỹ năng', 'Status_DB', 'Điểm số', 'Thời gian'])

# --- HÀM PHÂN LOẠI TRẠNG THÁI (DỰA TRÊN NGƯỠNG ĐỘNG) ---
def map_status(row):
    status_db = row['Status_DB']
    score = row['Điểm số']
    
    # 1. Ưu tiên trạng thái Cần ôn tập
    if status_db == 'Review': return 'Cần ôn tập'
    
    # 2. Đạt chuẩn nếu điểm >= Threshold (Lấy từ DB)
    if status_db == 'Completed' or score >= mastery_threshold: return 'Thành thạo'
    
    # 3. Còn lại
    if score > 0: return 'Đang học'
    return 'Mới bắt đầu'

df['Trạng thái hiển thị'] = df.apply(map_status, axis=1)

# --- METRICS TỔNG QUAN ---
c1, c2, c3, c4 = st.columns(4)

total = len(df)
mastered = len(df[df['Trạng thái hiển thị'] == 'Thành thạo'])
review_needed = len(df[df['Trạng thái hiển thị'] == 'Cần ôn tập'])
avg_score = df['Điểm số'].mean()

c1.metric("Tổng số kỹ năng", total)
c2.metric("Đã thành thạo", f"{mastered} ({mastered/total:.0%})", help=f"Số kỹ năng đạt điểm >= {mastery_threshold:.0%}")
c3.metric("Cần ôn tập", review_needed, delta_color="inverse")
c4.metric("Điểm trung bình", f"{avg_score:.1f} / 1.0")

st.divider()

# --- BIỂU ĐỒ ---
c1, c2 = st.columns(2)

# 1. Radar Chart
with c1:
    st.subheader("🕸️ Bản đồ năng lực (Radar)")
    if len(df) > 2:
        # Lấy 10 kỹ năng mới nhất hoặc quan trọng nhất
        df_radar = df.tail(10)
        fig = px.line_polar(
            df_radar, r='Điểm số', theta='Kỹ năng', 
            line_close=True, range_r=[0, 1], markers=True
        )
        fig.update_traces(fill='toself')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Cần ít nhất 3 kỹ năng để vẽ biểu đồ Radar.")

# 2. Pie Chart (Phân bố trạng thái)
with c2:
    st.subheader("🍰 Tỷ lệ hoàn thành")
    status_counts = df['Trạng thái hiển thị'].value_counts().reset_index()
    status_counts.columns = ['Loại', 'Số lượng']
    
    color_map = {
        'Thành thạo': '#00C853',   # Xanh
        'Đang học': '#FFD600',     # Vàng
        'Cần ôn tập': '#FF5252',   # Đỏ
        'Mới bắt đầu': '#FF6D00'   # Cam
    }
    
    fig_pie = px.pie(
        status_counts, values='Số lượng', names='Loại', 
        color='Loại', color_discrete_map=color_map,
        hole=0.4
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# 3. Bar Chart (Chi tiết điểm số)
st.subheader(f"📊 Chi tiết điểm số (Ngưỡng đạt: {mastery_threshold:.0%})")

# Thêm đường kẻ ngang biểu thị Threshold
fig_bar = px.bar(
    df, x='Kỹ năng', y='Điểm số',
    color='Điểm số', range_y=[0, 1],
    color_continuous_scale='Bluered_r'
)
# Vẽ đường line đỏ thể hiện ngưỡng
fig_bar.add_hline(y=mastery_threshold, line_dash="dash", line_color="green", annotation_text="Ngưỡng đạt")

st.plotly_chart(fig_bar, use_container_width=True)

# 4. Bảng dữ liệu
with st.expander("📋 Xem dữ liệu thô"):
    st.dataframe(df[['Kỹ năng', 'Trạng thái hiển thị', 'Điểm số', 'Thời gian']], use_container_width=True)