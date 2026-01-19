import os
import sys
import webbrowser
from streamlit.web import bootstrap

def main():
    """
    Launcher cho PyInstaller 6.
    Khi chạy dạng exe, Streamlit + source code được PyInstaller đưa vào thư mục:
        <exe_dir>/_internal/
    """
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)

        # 1) Thử tìm app.py ngay cạnh exe
        candidate1 = os.path.join(exe_dir, "app.py")

        # 2) Nếu không có, tìm trong "_internal/app.py"
        internal_dir = os.path.join(exe_dir, "_internal")
        candidate2 = os.path.join(internal_dir, "app.py")

        if os.path.exists(candidate1):
            app_path = candidate1
        elif os.path.exists(candidate2):
            app_path = candidate2
        else:
            print("❌ Không tìm thấy app.py trong exe hoặc thư mục _internal.")
            sys.exit(1)
    else:
        # Chạy bằng python trực tiếp
        base_dir = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(base_dir, "app.py")

    # Đặt thư mục làm việc (quan trọng)
    os.chdir(os.path.dirname(app_path))

    # ⭐ Mở đúng port Streamlit 8501 ⭐
    webbrowser.open("http://localhost:8501", new=1)

    # Chạy Streamlit
    bootstrap.run(app_path, app_path, [], {})

if __name__ == "__main__":
    main()
