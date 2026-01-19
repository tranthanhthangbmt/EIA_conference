# 🚀 Cập nhật Hệ thống & Kế hoạch Mở rộng (20/12/2025)

## 1. Nâng cấp Dashboard Quan trị & CAT (Đã hoàn thành)

### A. Nâng cấp Giao diện & Trải nghiệm (UI/UX)
-   **Knowledge Graph (Cây tri thức)**:
    -   Chuyển đổi sang giao diện "Tree View" (Cây) với bố cục phân cấp (Hierarchical) từ trái sang phải.
    -   Thêm "Xương sống" (Spine) để kết nối các chương học, giúp người học hình dung lộ trình rõ ràng hơn.
    -   Phân biệt trực quan: Chương (Hình vuông to), Bài học (Hình tròn nhỏ).
    -   **Smart Coloring**: Tự động tô màu nút dựa trên kết quả học tập (Xanh: Hoàn thành, Vàng: Đang học, Đỏ: Cần ôn, Xám: Chưa học).

-   **Admin Dashboard**:
    -   Tích hợp tính năng **"View As Student"** (Xem với tư cách học viên): Admin có thể chọn bất kỳ học viên nào để xem chính xác giao diện và dữ liệu phân tích của họ.
    -   Thêm **Debug Panel** thông minh: Tự động phát hiện và cảnh báo nếu chọn sai môn học hoặc khi dữ liệu bị thiếu.

### B. Chức năng Lịch sử Kiểm tra (Test History)
-   Người dùng và Admin có thể xem lại **Lịch sử làm bài** chi tiết.
-   **Session Selector**: Cho phép chọn xem lại trạng thái tri thức của một lần kiểm tra cụ thể trong quá khứ.
-   Đồ thị tri thức sẽ tự động **re-render** (vẽ lại) màu sắc dựa trên kết quả của bài kiểm tra được chọn, giúp phân tích lỗi sai tại thời điểm đó.

---

## 2. Kế hoạch Nâng cấp Hệ thống cho 2.000 Người dùng (Planned)

Để đáp ứng 2.000 người dùng đồng thời (Concurrent Users), hệ thống sẽ chuyển đổi từ môi trường Dev/Streamlit Cloud sang hạ tầng **Oracle Cloud Infrastructure (OCI)**.

### A. Hạ tầng Phần cứng (Infrastructure)
*Sử dụng gói Oracle Cloud Always Free (ARM Ampere)*

*   **CPU**: 4 OCPU (ARM64 Architecture) - Tối ưu cho xử lý đa luồng.
*   **RAM**: 24 GB - Cực kỳ quan trọng để lưu Session State của Streamlit cho hàng nghìn user.
*   **Network**: 10 TB Bandwidth/tháng - Đủ cho lưu lượng lớn.

### B. Kiến trúc Triển khai (Deployment Architecture)
Do Streamlit chạy đơn luồng (Single-threaded), việc phục vụ 2.000 user trên 1 instance sẽ gây nghẽn. Giải pháp là **Containerization & Load Balancing**.

1.  **Dockerization**:
    -   Đóng gói ứng dụng thành **Docker Container**.
    -   Image base: `python:3.10-slim` để tối ưu kích thước.
    -   Mỗi container sẽ chạy một instance Streamlit độc lập.

2.  **Load Balancer (Nginx)**:
    -   Sử dụng **Nginx** làm Reverse Proxy & Load Balancer.
    -   Triển khai 4-6 Container Streamlit (Worker) song song.
    -   Nginx sẽ phân phối traffic đều cho các container này, tận dụng tối đa 4 vCPU.

3.  **Database (Supabase)**:
    -   Tiếp tục sử dụng **Supabase** (PostgreSQL) để quản lý dữ liệu người dùng và logs.
    -   *Lưu ý*: Cần theo dõi giới hạn Connection Pool của Supabase. Nếu vượt quá, cần nâng cấp lên gói Pro ($25/mo) hoặc sử dụng Connection Pooling (PgBouncer).

### C. Các bước thực hiện (Roadmap)
1.  **Chuẩn bị**: Tạo `Dockerfile` và tối ưu `requirements.txt`.
2.  **Server Setup**: Đăng ký Oracle Cloud, tạo VM Instance (Ubuntu/Oracle Linux).
3.  **Deploy**:
    -   Cài đặt Docker & Docker Compose trên Server.
    -   Pull code từ Git.
    -   Build & Run Docker Compose (bao gồm App services và Nginx).
4.  **Config**: Cấu hình Domain, SSL (Certbot) và mở port 443.
5.  **Monitoring**: Cài đặt công cụ giám sát RAM/CPU (ví dụ: Glances hoặc Portainer) để theo dõi sức khỏe hệ thống.

---
*Tài liệu này được cập nhật tự động dựa trên tiến độ phát triển dự án.*
