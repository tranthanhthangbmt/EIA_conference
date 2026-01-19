import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys

# --- SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from db_utils import get_user_logs, get_all_users_list

st.set_page_config(page_title="Lịch sử học tập", page_icon="📜", layout="wide")

if "authentication_status" not in st.session_state or st.session_state["authentication_status"] is None:
    st.warning("🔒 Vui lòng đăng nhập."); st.stop()

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
        "👀 Xem nhật ký của:", 
        options=list(user_options.keys()),
        format_func=lambda x: user_options[x],
        key="admin_select_user_history"
    )
    target_user = selected_u
    
    if target_user != real_user:
        st.info(f"📢 Đang xem Lịch sử học tập của: **{user_options[target_user]}**")

username = target_user
# =================================================

st.title(f"📜 Nhật ký học tập: {username}")

# 1. Lấy dữ liệu
df = get_user_logs(username)

if df.empty:
    st.info("Chưa có dữ liệu lịch sử. Hãy làm bài tập đi nhé!")
    st.stop()

# Xử lý thời gian
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['date'] = df['timestamp'].dt.date
df['hour'] = df['timestamp'].dt.hour

# ==================================================
# 🔄 XỬ LÝ DỮ LIỆU
# ==================================================
# Handle missing duration (for old logs)
if 'duration_seconds' not in df.columns:
    df['duration_seconds'] = 0.0
df['duration_seconds'] = df['duration_seconds'].fillna(0.0)

# ==================================================
# 🗂️ GIAO DIỆN TAB (3 Tabs)
# ==================================================
tab1, tab2, tab3 = st.tabs(["📊 Tổng Quan", "🔥 Hoạt Động", "📝 Chi Tiết Log"])

# --- TAB 1: TỔNG QUAN ---
with tab1:
    st.markdown("### 🌟 Hiệu suất tổng thể")
    
    total_qs = len(df)
    correct_qs = len(df[df['is_correct'] == 1])
    accuracy = correct_qs / total_qs if total_qs > 0 else 0
    avg_duration = df[df['duration_seconds'] > 0]['duration_seconds'].mean() # Only count logged times
    if pd.isna(avg_duration): avg_duration = 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng số câu", total_qs, help="Tổng số câu hỏi đã làm")
    c2.metric("Số câu đúng", correct_qs, delta=f"{accuracy:.1%}")
    c3.metric("Độ chính xác", f"{accuracy:.1%}")
    c4.metric("Thời gian suy nghĩ TB", f"{avg_duration:.1f}s", help="Thời gian trung bình để trả lời 1 câu hỏi")

    st.divider()
    
    st.subheader("🎯 Năng lực theo môn học")
    
    # Aggregation per subject
    subj_stats = df.groupby('subject_id').agg(
        accuracy=('is_correct', 'mean'),
        avg_time=('duration_seconds', 'mean'),
        count=('is_correct', 'count')
    ).reset_index()
    subj_stats['accuracy'] = subj_stats['accuracy'] * 100
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_bar = px.bar(subj_stats, x='subject_id', y='accuracy', 
                         title="Độ chính xác theo môn (%)",
                         labels={'subject_id': 'Môn', 'accuracy': 'Độ chính xác'},
                         text_auto='.1f',
                         color='accuracy', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col_chart2:
        fig_time = px.bar(subj_stats, x='subject_id', y='avg_time',
                          title="Thời gian suy nghĩ trung bình (giây)",
                          labels={'subject_id': 'Môn', 'avg_time': 'Giây'},
                          text_auto='.1f',
                          color='avg_time', color_continuous_scale='Blues')
        st.plotly_chart(fig_time, use_container_width=True)

# --- TAB 2: HOẠT ĐỘNG ---
with tab2:
    st.markdown("### 📅 Tiến trình học tập")
    
    # 1. Activity over time (Count)
    daily_activity = df.groupby('date').size().reset_index(name='counts')
    fig_line = px.line(daily_activity, x='date', y='counts', markers=True, 
                       title="Số lượng câu hỏi làm được theo ngày",
                       labels={'date': 'Ngày', 'counts': 'Số câu'})
    st.plotly_chart(fig_line, use_container_width=True)
    
    st.divider()
    
    # 2. Avg Duration over time (Are they getting faster?)
    # Filter valid times only for trend
    df_time = df[df['duration_seconds'] > 0]
    if not df_time.empty:
        daily_time = df_time.groupby('date')['duration_seconds'].mean().reset_index(name='avg_seconds')
        fig_trend = px.area(daily_time, x='date', y='avg_seconds', markers=True,
                            title="Xu hướng tốc độ làm bài (Giây/Câu)",
                            labels={'date': 'Ngày', 'avg_seconds': 'Giây trung bình'},
                            color_discrete_sequence=['#FF9F36'])
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Chưa có đủ dữ liệu thời gian để vẽ biểu đồ xu hướng.")

# --- TAB 3: CHI TIẾT ---
with tab3:
    st.markdown("### 🗂️ Dữ liệu chi tiết")
    
    # Bộ lọc
    c_filter, _ = st.columns([1, 2])
    with c_filter:
        filter_subj = st.selectbox("Lọc theo môn:", ["Tất cả"] + list(df['subject_id'].unique()), key="hist_tab3_filter")
    
    if filter_subj != "Tất cả":
        df_show = df[df['subject_id'] == filter_subj]
    else:
        df_show = df

    # Display Table with formatting
    # Format timestamp
    df_display = df_show[['timestamp', 'subject_id', 'node_id', 'question_id', 'is_correct', 'duration_seconds', 'details']].copy()
    df_display['timestamp'] = df_display['timestamp'].dt.strftime('%d-%m-%Y %H:%M')
    
    # Rename columns for friendly UI
    df_display.rename(columns={
        'timestamp': 'Thời gian',
        'subject_id': 'Môn',
        'node_id': 'Kỹ năng',
        'question_id': 'Câu hỏi',
        'is_correct': 'Kết quả',
        'duration_seconds': 'Giây',
        'details': 'Lý do / Chiến lược',
        'action_type': 'Hành động'
    }, inplace=True)

    def highlight_correct(val):
        color = '#d4edda' if val == 1 else '#f8d7da' 
        return f'background-color: {color}'

    st.dataframe(
        df_display.style.applymap(highlight_correct, subset=['Kết quả'])
                        .format("{:.1f}s", subset=['Giây']),
        use_container_width=True,
        height=500,
        column_config={
            "Lý do / Chiến lược": st.column_config.TextColumn(width="medium")
        }
    )
    
    st.divider()
    
    # Download Button
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Tải toàn bộ dữ liệu (.csv)",
        data=csv_data,
        file_name=f"learning_history_{username}.csv",
        mime="text/csv",
        type="primary"
    )