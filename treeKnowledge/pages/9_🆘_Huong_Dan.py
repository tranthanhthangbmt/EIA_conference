import streamlit as st
import os

st.set_page_config(page_title="Hướng dẫn sử dụng", page_icon="🆘", layout="wide")

# ============================================================
# 🛠️ CẤU HÌNH ĐƯỜNG DẪN ẢNH
# ============================================================
# Lấy đường dẫn thư mục gốc của dự án (nơi chứa app.py và thư mục images)
current_dir = os.path.dirname(os.path.abspath(__file__)) # Thư mục pages/
project_root = os.path.dirname(current_dir)              # Thư mục gốc dự án
IMAGES_DIR = os.path.join(project_root, "images")

# Hàm hỗ trợ hiển thị ảnh hoặc Placeholder
def render_guide_step(title, content, filename, icon="🔹"):
    """
    Hiển thị một bước hướng dẫn.
    - title: Tiêu đề bước
    - content: Nội dung hướng dẫn (Markdown)
    - filename: Tên file ảnh trong thư mục images (VD: 'dashboard.png')
    """
    st.subheader(f"{icon} {title}")
    
    col_text, col_img = st.columns([1.5, 2.5], gap="large") # Text nhỏ, Ảnh to
    
    with col_text:
        st.markdown(content)
        
    with col_img:
        # Đường dẫn tuyệt đối đến file ảnh
        image_path = os.path.join(IMAGES_DIR, filename)
        
        if os.path.exists(image_path):
            # Nếu có ảnh -> Hiển thị
            st.image(image_path, caption=title, use_container_width=True)
        else:
            # Nếu chưa có ảnh -> Hiển thị khung Placeholder
            st.warning(f"⚠️ Chưa tìm thấy ảnh: `images/{filename}`")
            st.markdown(
                f"""
                <div style="
                    border: 2px dashed #ccc; 
                    border-radius: 10px; 
                    padding: 60px 20px; 
                    text-align: center; 
                    background-color: #f8f9fa;
                    color: #6c757d;">
                    <h3>🖼️ VỊ TRÍ ẢNH MINH HỌA</h3>
                    <p>Vui lòng chụp màn hình chức năng: <b>{title}</b></p>
                    <p>Lưu tên file: <code>{filename}</code></p>
                    <p>Vào thư mục: <code>{IMAGES_DIR}</code></p>
                </div>
                """, 
                unsafe_allow_html=True
            )
    st.divider()

# ============================================================
# 🏠 HEADER & GIỚI THIỆU CHUNG
# ============================================================
st.title("📚 Cẩm nang Hướng dẫn Sử dụng")
st.markdown("""
Hệ thống học tập thông minh này được thiết kế để **cá nhân hóa** lộ trình của bạn. 
Dưới đây là hướng dẫn chi tiết từng bước để bạn khai thác tối đa sức mạnh của hệ thống.
""")

# ============================================================
# 📑 CÁC TAB CHỨC NĂNG
# ============================================================
# Cập nhật: Tách thành 6 tab riêng biệt
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏠 Tổng quan", 
    "📖 Bài giảng", 
    "🎓 Luyện tập", 
    "📈 Đồ thị Tri thức",
    "🛠️ Quản trị Nội dung",
    "🏫 Quản lý Lớp học"
])

# --- TAB 1: TỔNG QUAN (ĐÃ LÀM CHI TIẾT) ---
with tab1:
    st.header("Quy trình học tập chuẩn")
    st.info("Hướng dẫn tổng quan về giao diện Dashboard và quy trình học tập 3 bước: Học -> Luyện -> Theo dõi.")
    
    # 1. Màn hình Dashboard (Tổng quan)
    render_guide_step(
        title="Màn hình Dashboard",
        content="""
        **Giao diện chính gồm:**
        - **Sidebar (Trái):** Menu điều hướng các chức năng chính (Bài giảng, Luyện tập...).
        - **Thông tin tài khoản:** Hiển thị tên, vai trò (Student/Teacher) và nút Đăng xuất.
        - **Trung tâm thông báo:** Các nhắc nhở quan trọng từ hệ thống.
        """,
        filename="guide_dashboard.png",
        icon="1️⃣"
    )

    # 2. Widget Gợi ý Thông minh (Chi tiết hóa phần 'Gợi ý hôm nay')
    render_guide_step(
        title="Gợi ý Học tập (Smart Recommendations)",
        content="""
        Đây là phần quan trọng nhất trên Dashboard. Hệ thống tự động đề xuất **3 nhiệm vụ** tối ưu nhất cho bạn:
        
        - 🩸 **Cần ôn tập gấp (Thẻ Đỏ):** Các bài học bạn sắp quên (dựa trên thuật toán đường cong quên lãng). Hãy ôn ngay để cứu vãn kiến thức!
        - 🚧 **Đang học dở (Thẻ Vàng):** Các bài bạn đã bắt đầu nhưng chưa hoàn thành (điểm < 70%).
        - ✨ **Bài học mới (Thẻ Xanh):** Các bài học tiếp theo được mở khóa dựa trên cấu trúc cây tri thức.
        
        👉 *Mẹo: Hãy ưu tiên xử lý các thẻ Đỏ và Vàng trước khi học bài mới.*
        """,
        filename="guide_dashboard_recs.png", # Bạn hãy chụp riêng phần 3 thẻ gợi ý
        icon="2️⃣"
    )

    # 3. Quy trình 3 bước
    render_guide_step(
        title="Vòng lặp Học tập Hiệu quả",
        content="""
        Để "phủ xanh" cây tri thức, hãy tuân thủ quy trình 3 bước được giới thiệu ở cuối Dashboard:
        
        1. **📖 Nạp kiến thức:** Xem bài giảng, video và tài liệu.
        2. **🎓 Luyện tập:** Làm bài tập trắc nghiệm thích ứng.
        3. **📈 Theo dõi:** Xem biểu đồ năng lực để biết điểm mạnh/yếu.
        """,
        filename="guide_learning_flow.png", # Chụp phần "Quy trình học tập hiệu quả" ở cuối dashboard
        icon="3️⃣"
    )

# --- TAB 2: BÀI GIẢNG (CHI TIẾT HÓA) ---
with tab2:
    st.header("📖 Hướng dẫn Học Lý thuyết & Tài liệu")
    st.info("Phần này chứa kho kiến thức nền tảng. Bạn cần hoàn thành các bài học ở đây trước khi hệ thống cho phép làm bài tập nâng cao.")

    # Bước 1: Điều hướng Sidebar
    render_guide_step(
        title="1. Chọn bài học từ Mục lục",
        content="""
        Nhìn sang thanh **Sidebar bên trái**, bạn sẽ thấy cấu trúc cây thư mục:
        
        - **Mục lục (Chương):** Bấm vào tên Chương để mở rộng danh sách các bài học con.
        - **Trạng thái bài học (Icon):**
            - ⚪ **Tròn trắng:** Bài chưa học.
            - 🟡 **Tròn vàng:** Bài đang học dở (tiến độ > 0%).
            - ✅ **Tích xanh:** Bài đã hoàn thành (đạt điểm > 70%).
            - 👉 **Ngón tay:** Bài đang được chọn xem.
            
        *Mẹo: Bạn có thể bấm vào nút "Giới thiệu chương" để xem tổng quan trước khi đi vào từng bài.*
        """,
        filename="guide_lecture_sidebar.png", # Ảnh chụp sidebar có các icon trạng thái
        icon="🗂️"
    )

    # Bước 2: Xem nội dung
    render_guide_step(
        title="2. Xem Nội dung Bài giảng",
        content="""
        Nội dung bài học sẽ hiển thị ở khung chính giữa màn hình. Hệ thống hỗ trợ đa dạng định dạng:
        
        - **📺 Video:** Xem trực tiếp video bài giảng (YouTube/MP4).
        - **📄 Tài liệu PDF:** Link tải hoặc xem trước tài liệu tham khảo.
        - **📝 Văn bản/HTML:** Bài đọc chi tiết với công thức toán học (MathJax) và hình ảnh minh họa.
        
        Hãy đọc kỹ và ghi chép lại các ý chính quan trọng.
        """,
        filename="guide_lecture_content.png", # Ảnh chụp màn hình nội dung bài học (có video hoặc text)
        icon="👀"
    )

    # Bước 3: Xác nhận hoàn thành (QUAN TRỌNG)
    render_guide_step(
        title="3. Đánh dấu 'Đã xem'",
        content="""
        Đây là bước quan trọng nhất! Sau khi học xong, hãy kéo xuống **cuối trang** và tìm nút màu xanh:
        
        > **✅ Đánh dấu Đã xem**
        
        **Tại sao cần bấm nút này?**
        - Để hệ thống ghi nhận bạn đã có kiến thức nền tảng.
        - Để **mở khóa** các bài tập thực hành liên quan trong phần *Luyện tập*.
        - Để chuyển trạng thái bài học từ ⚪ sang 🟡 trên đồ thị tri thức.
        """,
        filename="guide_lecture_finish_btn.png", # Bạn cần chụp ảnh nút bấm ở cuối trang bài giảng
        icon="✅"
    )

# --- TAB 3: LUYỆN TẬP (CHI TIẾT HÓA) ---
with tab3:
    st.header("🎓 Chế độ Luyện tập Thích ứng")
    st.warning("Đây là 'trái tim' của hệ thống. Không giống các bài kiểm tra thông thường, hệ thống sẽ tự động chọn câu hỏi dựa trên năng lực thực tế của bạn.")

    # 1. Cơ chế chọn câu hỏi (Tại sao lại hiện câu này?)
    render_guide_step(
        title="1. Tại sao hệ thống chọn câu hỏi này?",
        content="""
        Khi bạn vào màn hình Luyện tập, bạn sẽ **không** thấy danh sách bài để chọn. Thay vào đó, thuật toán AI sẽ phân tích lịch sử của bạn để đưa ra **1 câu hỏi tối ưu nhất** tại thời điểm đó:
        
        - **Ưu tiên 1 (Cứu vãn):** Các bài học bạn đang có dấu hiệu quên (dựa trên thời gian lần cuối ôn tập).
        - **Ưu tiên 2 (Củng cố):** Các bài bạn đang học dở dang (điểm số thấp).
        - **Ưu tiên 3 (Mở rộng):** Các bài học mới tiếp theo trong lộ trình cây tri thức.
        
        *Mục tiêu là giúp bạn học đúng cái cần học, tránh lãng phí thời gian vào những gì đã biết.*
        """,
        filename="guide_practice_algo.png", # Chụp màn hình giao diện luyện tập khi mới vào (chưa chọn đáp án)
        icon="🧠"
    )

    # 2. Làm bài và Xem kết quả
    render_guide_step(
        title="2. Thao tác Làm bài & Kiểm tra",
        content="""
        Giao diện làm bài được thiết kế tối giản để bạn tập trung:
        
        1. **Đọc câu hỏi:** Nằm ở khung bên trái.
        2. **Chọn đáp án:** Tích vào lựa chọn bạn cho là đúng.
        3. **Bấm 'Kiểm tra ✨':** Hệ thống sẽ chấm điểm ngay lập tức.
        
        - **Nếu Đúng:** 🎉 Xin chúc mừng! Điểm năng lực của bạn sẽ tăng lên.
        - **Nếu Sai:** ❌ Đừng lo! Hệ thống sẽ hiện đáp án đúng và lời giải thích chi tiết. Tuy nhiên, điểm của bài học đó sẽ bị trừ nhẹ để nhắc nhở bạn cần ôn lại.
        """,
        filename="guide_practice_submit.png", # Chụp màn hình sau khi đã bấm "Kiểm tra" (hiện kết quả đúng/sai)
        icon="✍️"
    )

    # 3. Thanh tiến độ & Nút Next
    render_guide_step(
        title="3. Thanh Tiến độ & Câu tiếp theo",
        content="""
        Sau mỗi câu hỏi, hãy chú ý **Thanh Tiến độ** ở góc trên:
        
        - Nó cho biết bạn còn cách ngưỡng "Thành thạo" bao xa.
        - Khi thanh này đầy (100%), bài học đó coi như hoàn thành.
        
        Bấm nút **"Câu tiếp theo ➡"** để chuyển sang thử thách mới. Hệ thống có thể sẽ đổi sang một chủ đề khác nếu thấy bạn đã nắm vững chủ đề hiện tại.
        """,
        filename="guide_practice_progress.png", # Chụp cận cảnh thanh progress bar và nút Next
        icon="⏭️"
    )

# --- TAB 4: ĐỒ THỊ (CẬP NHẬT MỚI) ---
with tab4:
    st.header("📈 Bản đồ Tư duy & Đồ thị Tri thức")
    st.info("Đồ thị này không chỉ để trang trí! Nó là bản đồ dẫn đường, cho bạn biết bạn đang đứng ở đâu trong hành trình chinh phục môn học.")

    # 1. Giải mã màu sắc
    render_guide_step(
        title="1. Ý nghĩa các màu sắc",
        content="""
        Mỗi chấm tròn (Node) đại diện cho một bài học hoặc kỹ năng cụ thể. Màu sắc của nó phản ánh trạng thái hiện tại của bạn:
        
        - ⚪ **Màu Xám (Chưa học):** Vùng đất chưa được khám phá. Bạn cần hoàn thành các bài học tiên quyết (nối với nó) trước.
        - 🟡 **Màu Vàng (Đang học):** Bạn đã bắt đầu học nhưng chưa vững (Điểm < 70%). Cần luyện tập thêm!
        - 🟢 **Màu Xanh lá (Thành thạo):** Xin chúc mừng! Bạn đã nắm vững kiến thức này (Điểm >= 70%).
        - 🔴 **Màu Đỏ (Cảnh báo):** Nguy hiểm! Bạn đang quên kiến thức này hoặc làm sai quá nhiều. Hãy ôn tập ngay lập tức.
        """,
        filename="guide_graph_colors.png", # Sử dụng ảnh bạn đã upload
        icon="🎨"
    )

    # 2. Xem chi tiết & Chỉ số (Mới bổ sung)
    render_guide_step(
        title="2. Xem Thông tin Chi tiết",
        content="""
        Khi bấm vào một nút (Node), một hộp thoại sẽ hiện ra với tab **"Tổng quan & Chỉ số"**:
        
        - **Điểm năng lực:** Điểm số chính xác của bạn (0-100%).
        - **Ngân hàng câu hỏi:** Số lượng câu hỏi có sẵn trong hệ thống cho bài này.
        - **Nút "Học lý thuyết ngay":** Đường tắt để nhảy nhanh đến bài giảng video/tài liệu của bài học này mà không cần tìm trong danh sách.
        """,
        filename="guide_graph_colors_tong_quan.png", # Sử dụng ảnh bạn đã upload
        icon="📊"
    )

    # 3. Luyện tập nhanh (Mới bổ sung)
    render_guide_step(
        title="3. Luyện tập nhanh trên Đồ thị",
        content="""
        Bạn có thể ôn tập nhanh ngay trên đồ thị mà không cần chuyển trang. Hãy chọn tab **"Luyện tập & Câu hỏi"** trong hộp thoại:
        
        - **Chọn câu hỏi:** Bấm vào các số (1, 2, 3...) để chọn câu hỏi.
        - **Làm bài:** Đọc câu hỏi và chọn đáp án.
        - **Giải thích:** Xem ngay đáp án đúng và giải thích chi tiết bên cạnh.
        
        *Tính năng này rất hữu ích để ôn tập nhanh (Review) các khái niệm màu Đỏ hoặc Vàng.*
        """,
        filename="guide_graph_colors_cau_hoi_luyen_tap.png", # Sử dụng ảnh bạn đã upload
        icon="📝"
    )

# --- TAB 5: QUẢN TRỊ NỘI DUNG (CMS) (CHI TIẾT HÓA) ---
with tab5:
    # Kiểm tra quyền
    #if st.session_state.get("role") in ["admin", "teacher", "manager"]:
    if (1==1): # MỞ CHO TẤT CẢ XEM HƯỚNG DẪN CMS
        st.header("🛠️ Quản trị Nội dung (CMS)")
        st.info("Dành cho Admin & Giáo viên để xây dựng kho học liệu.")

        render_guide_step(
            title="Import Dữ liệu hàng loạt",
            content="""
            Vào menu **Quản trị nội dung** > Tab **Import Dữ liệu**.
            
            Bạn cần chuẩn bị các file CSV theo mẫu:
            1. **Upload k-graph.csv:** Định nghĩa cấu trúc cây (Cha -> Con).
            2. **Upload q-matrix.csv:** Ngân hàng câu hỏi trắc nghiệm.
            3. **Upload lectures.csv:** Link tài liệu/Video.
            
            *Mẹo:* Bạn cũng có thể upload file **Word (.docx)** để hệ thống tự động cắt bài giảng.
            """,
            filename="guide_cms_import.png",
            icon="📥"
        )
    else:
        st.warning("⛔ Nội dung này chỉ dành cho Giảng viên/Admin.")
# --- TAB 6: QUẢN LÝ LỚP HỌC ---
with tab6:
    # Kiểm tra quyền
    #if st.session_state.get("role") in ["admin", "teacher", "manager"]:
    if (1==1): # MỞ CHO TẤT CẢ XEM HƯỚNG DẪN QUẢN LÝ LỚP
        st.header("🏫 Quản lý Lớp học & Học viên")
        st.info("Theo dõi tiến độ của cả lớp và phát hiện sinh viên yếu kém.")

        render_guide_step(
            title="Tạo lớp & Gán học viên",
            content="""
            Vào menu **Quản lý Lớp**:
            1. **Tạo lớp mới:** Đặt tên lớp và chọn môn học tương ứng.
            2. **Ghi danh:** Chọn sinh viên từ danh sách hệ thống để thêm vào lớp.
            """,
            filename="guide_class_create.png", # Bạn cần chụp ảnh phần tạo lớp
            icon="➕"
        )

        render_guide_step(
            title="Bản đồ nhiệt (Heatmap)",
            content="""
            Chuyển sang tab **Dashboard Năng lực**:
            - **Hàng ngang:** Là các sinh viên.
            - **Cột dọc:** Là các bài học.
            - **Ô màu đỏ:** Cả lớp đang yếu ở bài đó -> Cần giảng lại.
            - **Hàng màu đỏ:** Sinh viên đó đang mất gốc -> Cần kèm cặp riêng.
            """,
            filename="guide_class_heatmap.png",
            icon="📊"
        )
        
        # 3. Báo cáo phân tích (Mới bổ sung)
        render_guide_step(
            title="3. Phát hiện Vấn đề & Cảnh báo",
            content="""
            Hệ thống tự động phân tích dữ liệu để đưa ra các cảnh báo quan trọng ở cuối trang:

            **⚠️ Bài học cần giảng lại:**
            Danh sách các bài mà điểm trung bình của cả lớp rất thấp.
            *Ví dụ:* `3.7_ThucHanh_PhanLoai: 2.5%` -> Bài này quá khó hoặc tài liệu chưa tốt, cần giảng lại trên lớp.

            **🆘 Sinh viên cần hỗ trợ:**
            Danh sách các sinh viên có điểm trung bình thấp nhất so với cả lớp.
            *Ví dụ:* `student1: 45.8%` -> Sinh viên này đang có nguy cơ trượt môn, cần kèm cặp riêng.
            """,
            filename="guide_class_analytics.png", # Bạn cần chụp thêm phần phân tích thống kê ở cuối trang Quản lý lớp
            icon="🚨"
        )
    else:
        st.warning("⛔ Nội dung này chỉ dành cho Giảng viên/Admin.")

# --- FOOTER ---
st.divider()
st.caption("© 2025 Hệ thống Học tập Thông minh. Tài liệu hướng dẫn nội bộ.")