import pandas as pd
import os

files_to_update = [
    r"d:\MY_CODE\treeKnowledge\knowledge\KNS\questions_KNS.csv",
    r"d:\MY_CODE\treeKnowledge\knowledge\KNS\questions_KNS_v2.csv"
]

mapping = {
    "KNS.1.1": "1.1_TongQuan",
    "KNS.1.2": "1.2_TimKiem",
    "KNS.1.3": "1.3_KiemChung",
    "KNS.1.4": "1.4_XuLy",
    "KNS.2.1": "2.1_NguyenTac",
    "KNS.2.2": "2.2_LamViecNhom",
    "KNS.2.3": "2.3_CongDanSo",
    "KNS.2.4": "2.4_DichVuCong",
    "KNS.3.1": "3.1_KeHoach",
    "KNS.3.2": "3.2_BanQuyen",
    "KNS.3.3": "3.3_CongCu",
    "KNS.3.4": "3.4_LapTrinh",
    "KNS.4.1": "4.1_MoiDeDoa",
    "KNS.4.2": "4.2_BaoVeDuLieu",
    "KNS.4.3": "4.3_SucKhoeSo",
    "KNS.4.4": "4.4_CongNgheXanh",
    "KNS.5.1": "5.1_SuCo",
    "KNS.5.2": "5.2_TuHoc",
    "KNS.5.3": "5.3_PhanTich",
    "KNS.5.4": "5.4_QuyTrinh",
    "KNS.6.1": "6.1_TongQuanAI",
    "KNS.6.2": "6.2_UngDung",
    "KNS.6.3": "6.3_ChuyenDoiSo",
    "KNS.6.4": "6.4_NangLucSo"
}

def update_file(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}", flush=True)
        return

    try:
        print(f"Reading {file_path}...", flush=True)
        df = pd.read_csv(file_path)
        
        # Helper to clean and map
        def mapper(x):
            s = str(x).strip().strip('"').strip("'")
            return mapping.get(s, s)

        df['Skill_ID_List'] = df['Skill_ID_List'].apply(mapper)
        
        # Save
        df.to_csv(file_path, index=False, encoding='utf-8-sig', quoting=1) # quoting=1 is QUOTE_ALL (adds quotes to all fields) to match user format
        print(f"Updated {file_path} successfully.", flush=True)
        
    except Exception as e:
        print(f"Error updating {file_path}: {e}", flush=True)

for f in files_to_update:
    update_file(f)
