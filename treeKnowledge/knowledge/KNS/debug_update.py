
import pandas as pd
import os
import sys

log_file = r'd:\MY_CODE\treeKnowledge\update_log.txt'

def log(msg):
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')

log("Starting update script...")

file_path = r"d:\MY_CODE\treeKnowledge\knowledge\KNS\questions_KNS.csv" # Fixed path to target file

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

try:
    if not os.path.exists(file_path):
        log(f"File not found: {file_path}")
        sys.exit(1)

    log(f"Reading {file_path}")
    df = pd.read_csv(file_path)
    log(f"Rows read: {len(df)}")
    
    def mapper(x):
        s = str(x).strip().strip('"').strip("'")
        val = mapping.get(s, s)
        return val

    # Verify column existence
    cols = [c.strip().lower() for c in df.columns]
    # Check if 'Skill_ID_List' is in columns (case insensitive)
    target_col = None
    for c in df.columns:
        if c.strip().lower() == 'skill_id_list':
            target_col = c
            break
            
    if not target_col:
        # Fallback: maybe it's the 2nd column?
        if len(df.columns) >= 2:
            target_col = df.columns[1]
            log(f"Column 'Skill_ID_List' not found by name. Using 2nd column: {target_col}")
        else:
            log("Cannot identify Skill ID column.")
            sys.exit(1)
            
    log(f"Target column: {target_col}")
    
    # Check sample before
    log(f"Sample before: {df[target_col].head(3).tolist()}")

    df[target_col] = df[target_col].apply(mapper)
    
    # Check sample after
    log(f"Sample after: {df[target_col].head(3).tolist()}")

    output_path = file_path # Overwrite
    # output_path = r"d:\MY_CODE\treeKnowledge\knowledge\KNS\questions_KNS_v2.csv" # Write to v2 first to be safe? 
    # User asked to redo "questions_KNS.csv" directly implies overwrite or fixing it.
    # User script used overwrite. I will use overwrite.
    
    df.to_csv(output_path, index=False, encoding='utf-8-sig', quoting=1)
    log(f"Saved to {output_path}")

except Exception as e:
    log(f"Error: {e}")
