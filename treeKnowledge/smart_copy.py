
import os
import shutil
import sys

# Set encoding
sys.stdout.reconfigure(encoding='utf-8')

pages_dir = "pages"
target_name = "10_🐱_CAT.py"
search_term = "Kiem_Tra"

print(f"Searching for file containing '{search_term}' in '{pages_dir}'...")

found_file = None
if os.path.exists(pages_dir):
    for f in os.listdir(pages_dir):
        if search_term in f:
            found_file = f
            break

if found_file:
    src = os.path.join(pages_dir, found_file)
    dst = os.path.join(pages_dir, target_name)
    print(f"Found source: {src}")
    print(f"Copying to: {dst}")
    
    try:
        shutil.copy(src, dst)
        print("Copy successful!")
    except Exception as e:
        print(f"Copy failed: {e}")
else:
    print(f"File containing '{search_term}' not found.")
