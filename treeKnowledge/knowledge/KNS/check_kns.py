
import csv

file_path = r"d:\MY_CODE\treeKnowledge\knowledge\KNS\questions_KNS.csv"

with open(file_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if "KNS." in line:
            print(f"Line {i}: {line.strip()}")
