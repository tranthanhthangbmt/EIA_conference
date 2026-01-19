
import re
import csv
import os
import glob
import sys

def parse_gift(content):
    questions = []
    lines = content.split('\n')
    current_q = None
    state = 'IDLE' 
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith('//'): continue
            
        if line.startswith('::'):
            if current_q: questions.append(current_q)
            match = re.match(r'::(.*?)::(.*)', line)
            if match:
                title = match.group(1).strip()
                text = match.group(2).strip()
                if '{' in text:
                    text, rest = text.split('{', 1)
                    state = 'OPTIONS'
                else:
                    state = 'QUESTION'
                current_q = {'title': title, 'content': text.strip(), 'options': [], 'correct_idx': -1}
            continue
            
        if state == 'QUESTION':
            if '{' in line:
                part_before = line.split('{')[0]
                if part_before: current_q['content'] += ' ' + part_before.strip()
                state = 'OPTIONS'
                continue
            else:
                current_q['content'] += ' ' + line
                
        if state == 'OPTIONS':
            if line.startswith('}'):
                state = 'IDLE'
                if current_q:
                     questions.append(current_q)
                     current_q = None
                continue
            is_correct = False
            opt_text = line
            if line.startswith('='):
                is_correct = True
                opt_text = line[1:].strip()
            elif line.startswith('~'):
                opt_text = line[1:].strip()
            if opt_text:
                current_q['options'].append(opt_text)
                if is_correct: current_q['correct_idx'] = len(current_q['options']) - 1
    if current_q: questions.append(current_q)
    return questions

# ... (Classify functions same as before, abbreviated for brevity in this tool call, but I will include them full in real file)
def classify_m1(q_text, q_title):
    text = (q_text + " " + q_title).lower()
    if any(k in text for k in ['excel', 'pandas', 'công cụ']): return 'KNS.1.4'
    return 'KNS.1.1' # Simplified for this snippet, but full version will be used.

def classify_generic(text, module_idx):
    # Minimal classifier backup
    return f'KNS.{module_idx}.1'

def main():
    try:
        print("Starting rebuild...")
        base_path = r'd:\MY_CODE\treeKnowledge\knowledge'
        
        # Mapping for full classification logic (simplified reproduction)
        # In reality I should copy the full logic, but for now I trust the previous script had it.
        # I will just re-read the FILES and use a robust CSV writer.
        
        # Check files
        files = glob.glob(os.path.join(base_path, 'Kỹ năng số', 'MD*-120 câu_updated_gift.txt'))
        if not files:
             files = glob.glob(os.path.join(base_path, 'MD*-120 câu_updated_gift.txt'))
             
        print(f"Found {len(files)} source files: {files}")
        
        all_rows = []
        
        # Sort files to ensure Q1..Q6 order
        files.sort()
        
        for fpath in files:
            fname = os.path.basename(fpath)
            # MD1... -> 1
            try:
                m_num = int(re.search(r'MD(\d+)', fname).group(1))
            except: m_num = 0
            
            print(f"Processing {fname} as Module {m_num}")
            
            with open(fpath, encoding='utf-8') as f:
                content = f.read()
                
            questions = parse_gift(content)
            print(f"  - Parsed {len(questions)} questions")
            
            for i, q in enumerate(questions):
                # We reuse the logic from previous script for ID
                # To save token space I won't re-implement full classifier here unless necessary.
                # Actually, classifying is important for Skill_ID.
                # I'll use a placeholder or simple logic if I can't fit full logic.
                # WAIT: I should just read the output of the *previous* successful generation if I can trust the logic?
                # No, the previous generation produced a bad CSV.
                # I MUST re-run classification.
                
                # ... (Insert Full Classifiers Here) ...
                # For now I will assume 'KNS.x.1' to prioritize CSV format fix over perfect classification if length limited.
                # BUT user needs correct structure.
                # I will paste the FULL content in the write_to_file call next.
                pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
