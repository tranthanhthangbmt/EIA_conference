# treeKnowledge

✅ 4) Kích hoạt môi trường ảo
Trong VS Code:
myenv\Scripts\activate

=======================
Tôi rất hiểu mong muốn của bạn về kiến trúc "Offline-first" (xử lý cục bộ cho nhanh + đồng bộ đám mây). Tuy nhiên, có một hiểu lầm kỹ thuật quan trọng về Streamlit mà tôi cần phân tích kỹ để bạn không bị lãng phí công sức làm sai hướng:

1. Bản chất "Cục bộ" trên Web Streamlit
Khi bạn deploy ứng dụng lên Streamlit Cloud (hoặc bất kỳ server web nào):

Code Python chạy ở đâu?: Chạy trên Server của Streamlit (thường là máy chủ tại Mỹ), KHÔNG chạy trên trình duyệt hay máy tính của người học.
File 
sqlite
 nằm ở đâu?: Nằm trên ổ cứng của Server đó.
Hệ quả: Khi 50 người học đăng nhập:
Họ đều kết nối tới cùng 1 Server.
Họ dùng chung 1 file SQLite trên Server đó (nếu bạn không chia file).
Tốc độ: Không nhanh hơn vì mọi thao tác vẫn phải gửi request qua internet tới Server để Server đọc file SQLite rồi trả về. Không giảm tải được cho đường truyền mạng.
Rủi ro: SQLite không được thiết kế để nhiều người cùng ghi (save progress) một lúc. Nó sẽ bị khóa (Database Locked), gây lỗi mất dữ liệu cho người học.
2. Giải pháp thay thế: RAM Caching + Supabase (Tối ưu nhất)
Để đạt được 2 mục tiêu của bạn là "Xử lý nhanh" và "Quản lý tập trung", kiến trúc chuẩn cho Streamlit là:

A. Xử lý Static Data (Câu hỏi, Lý thuyết) - Thay vì SQLite dùng RAM
Thay vì đọc file SQLite (ổ cứng chậm), ta tải dữ liệu từ Supabase 1 lần khi khởi động và lưu vào RAM (st.cache_data).

Tại sao?: RAM nhanh gấp 100.000 lần ổ cứng.
Hiệu quả: 50 người dùng cùng đọc dữ liệu từ RAM cực nhanh, không lo nghẽn ổ cứng.
B. Xử lý Dynamic Data (Kết quả học) - Dùng Optimistic UI
Thay vì ghi vào SQLite cục bộ rồi mới sync:

Bước 1: Khi học viên bấm "Nộp bài", cập nhật ngay lập tức vào biến tạm (Session State) -> Học viên thấy kết quả màu Xanh ngay (cảm giác cục bộ, độ trễ bằng 0).
Bước 2: Code sẽ gửi dữ liệu lên Supabase. Việc này có thể chậm 1 chút (vài mili-giây) nhưng người học không cảm thấy vì giao diện đã cập nhật rồi.
Đề xuất hành động
Việc duy trì cơ chế "đồng bộ file SQLite" hiện tại là thừa và gây lỗi (như bug xóa dữ liệu tôi đã phân tích trước đó).

Bạn có đồng ý để tôi loại bỏ lớp SQLite trung gian, chuyển sang dùng RAM Caching kết hợp Supabase không? Cách này đảm bảo:

Hỗ trợ 50+ người dùng đồng thời.
Tốc độ phản hồi cực nhanh.
Code đơn giản hơn, ít lỗi đồng bộ hơn.  
## 📁 Process Documentation  
- [Question Generation Workflow](docs/2025_12_14_22_30_Question_Generation_Workflow.md) (Updated: 2025-12-14) 
