import pandas as pd
import os

file_path = r"d:\MY_CODE\treeKnowledge\knowledge\Kỹ năng số\questions_KNS.csv"

# Mapping from Old ID to New ID
mapping = {
    # Module 1
    "KNS.1.1": "1.1_TongQuan",
    "KNS.1.2": "1.2_TimKiem",
    "KNS.1.3": "1.3_KiemChung",
    "KNS.1.4": "1.4_XuLy",
    
    # Module 2
    "KNS.2.1": "2.1_NguyenTac",
    "KNS.2.2": "2.2_LamViecNhom",
    "KNS.2.3": "2.3_CongDanSo",
    "KNS.2.4": "2.4_DichVuCong",
    
    # Module 3
    "KNS.3.1": "3.1_KeHoach",
    "KNS.3.2": "3.2_BanQuyen",
    "KNS.3.3": "3.3_CongCu",
    "KNS.3.4": "3.4_LapTrinh",
    
    # Module 4
    "KNS.4.1": "4.1_MoiDeDoa",
    "KNS.4.2": "4.2_BaoVeDuLieu",
    "KNS.4.3": "4.3_SucKhoeSo",
    "KNS.4.4": "4.4_CongNgheXanh",
    
    # Module 5
    "KNS.5.1": "5.1_SuCo",
    "KNS.5.2": "5.2_TuHoc",
    "KNS.5.3": "5.3_PhanTich",
    "KNS.5.4": "5.4_QuyTrinh",
    
    # Module 6
    "KNS.6.1": "6.1_TongQuanAI",
    "KNS.6.2": "6.2_UngDung",
    "KNS.6.3": "6.3_ChuyenDoiSo",
    "KNS.6.4": "6.4_NangLucSo"
}

try:
    df = pd.read_csv(file_path)
    print(f"Loaded {len(df)} questions.")
    
    # Update Skill_ID_List
    # Using replace for exact matches, or apply for more complex logic if lists are involved
    # Since Skill_ID_List usually contains a single ID string in this context
    
    # Function to replace ID if found in mapping
    def update_id(old_id):
        old_id = str(old_id).strip()
        return mapping.get(old_id, old_id)

    df['Skill_ID_List'] = df['Skill_ID_List'].apply(update_id)
    
    # Save back
    df.to_csv(file_path, index=False, encoding='utf-8-sig')
    print("Updated IDs successfully.")
    
    # Verify a few
    print("First 5 updated rows:")
    print(df[['Question_ID', 'Skill_ID_List']].head())

except Exception as e:
    print(f"Error: {e}")
