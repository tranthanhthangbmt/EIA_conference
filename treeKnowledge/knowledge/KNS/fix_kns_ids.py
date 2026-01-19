
import csv
import os

# Define the mapping for KNS IDs
id_mapping = {
    # 4.x
    "KNS.4.1": "4.1_MoiDeDoa",
    "KNS.4.2": "4.2_BaoVeDuLieu",
    "KNS.4.3": "4.3_SucKhoeSo",
    "KNS.4.4": "4.4_CongNgheXanh",
    # 5.x
    "KNS.5.1": "5.1_SuCo",
    "KNS.5.2": "5.2_TuHoc",
    "KNS.5.3": "5.3_PhanTich",
    "KNS.5.4": "5.4_QuyTrinh",
    # 6.x
    "KNS.6.1": "6.1_TongQuanAI",
    "KNS.6.2": "6.2_UngDung",
    "KNS.6.3": "6.3_ChuyenDoiSo",
    "KNS.6.4": "6.4_NangLucSo"
}

file_path = r"d:\MY_CODE\treeKnowledge\knowledge\KNS\questions_KNS.csv"
output_path = file_path + ".temp"

updated_count = 0
not_found_count = 0
not_found_ids = set()

with open(file_path, 'r', encoding='utf-8', newline='') as infile, \
     open(output_path, 'w', encoding='utf-8', newline='') as outfile:
    
    reader = csv.reader(infile)
    writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
    
    for row in reader:
        if not row:
            continue
            
        # Assuming ID is in the second column (index 1)
        if len(row) > 1:
            current_id = row[1]
            if current_id.startswith("KNS."):
                if current_id in id_mapping:
                    row[1] = id_mapping[current_id]
                    updated_count += 1
                else:
                    not_found_count += 1
                    not_found_ids.add(current_id)
                    
        writer.writerow(row)

print(f"Updated {updated_count} IDs.")
if not_found_count > 0:
    print(f"IDs not found in mapping: {not_found_count}")
    for missing_id in not_found_ids:
        print(f"Missing: {missing_id}")

# Replace the original file
if updated_count > 0:
    import shutil
    shutil.move(output_path, file_path)
    print("File updated successfully.")
else:
    os.remove(output_path)
    print("No changes needed.")
