
import re
import csv
import os
import glob
import sys

# --- CLASSIFIERS ---

def classify_m1(q_text, q_title):
    text = (q_text + " " + q_title).lower()
    if any(k in text for k in ['excel', 'pandas', 'công cụ', 'tool', 'phân tích dữ liệu', 'csv', 'sql', 'biểu đồ', 'google dataset', 'xử lý dữ liệu']):
        if not any(k in text for k in ['đánh giá', 'tin giả', 'fake news']): return 'KNS.1.4'
    if any(k in text for k in ['tin giả', 'fake news', 'đánh giá', 'kiểm chứng', 'craap', 'sift', 'bias', 'misinformation', 'disinformation', 'xác thực', 'tineye', 'invid', 'fact', 'đáng tin', 'nguồn tin', 'radcab', 'drama', 'imvain']): return 'KNS.1.3'
    if any(k in text for k in ['tìm kiếm', 'search', 'toán tử', 'google', 'scholar', 'filetype', 'site:', 'intitle', 'skimming', 'scanning', 'đọc lướt']): return 'KNS.1.2'
    return 'KNS.1.1'

def classify_m2(q_text, q_title):
    text = (q_text + " " + q_title).lower()
    if any(k in text for k in ['luật', 'nghị định', 'dịch vụ công', 'chính phủ điện tử', 'pháp lý', 'quy định', 'an ninh mạng 2018', 'pháp luật', 'vi phạm']): return 'KNS.2.4'
    if any(k in text for k in ['google docs', 'google drive', 'dropbox', 'onedrive', 'hợp tác', 'làm việc nhóm', 'chia sẻ', 'đồng bộ', 'trello', 'asana', 'slack', 'teams', 'zoom', 'meeting', 'họp trực tuyến', 'cộng tác', 'presence', 'wiki', 'single source', 'bản quyền', 'license']): return 'KNS.2.2'
    if any(k in text for k in ['công dân số', 'đạo đức', 'danh tính số', 'digital identity', 'dấu chân số', 'footprint', 'bắt nạt', 'bôi nhọ', 'nghiện', 'sức khỏe', 'cân bằng', 'wellbeing', 'well-being', 'quyền', 'trách nhiệm', 'ứng xử']): return 'KNS.2.3'
    if any(k in text for k in ['email', 'thư điện tử', 'giao tiếp', 'netiquette', 'lịch sự', 'chủ đề', 'password', 'mật khẩu', 'lắng nghe', 'phản hồi']): return 'KNS.2.1'
    return 'KNS.2.1'

def classify_m3(q_text, q_title):
    text = (q_text + " " + q_title).lower()
    if any(k in text for k in ['python', 'code', 'biến', 'vòng lặp', 'hàm', 'câu lệnh', 'lập trình', 'tư duy máy tính', 'thuật toán']): return 'KNS.3.4'
    if any(k in text for k in ['video', 'audio', 'ảnh', 'biên tập', 'chỉnh sửa', 'capcut', 'canva', 'thu âm', 'kỹ thuật quay']): return 'KNS.3.3'
    if any(k in text for k in ['bản quyền', 'giấy phép', 'creative commons', 'sở hữu trí tuệ', 'đạo văn', 'trích dẫn', 'công bằng']): return 'KNS.3.2'
    return 'KNS.3.1'

def classify_m4(q_text, q_title):
    text = (q_text + " " + q_title).lower()
    if any(k in text for k in ['xanh', 'môi trường', 'rác thải điện tử', 'tiết kiệm năng lượng', 'tái chế', 'bền vững']): return 'KNS.4.4'
    if any(k in text for k in ['sức khỏe', 'mắt', 'cột sống', 'nghiện', 'balance', 'cân bằng', 'wellbeing', 'fomo', 'doomscrolling']): return 'KNS.4.3'
    if any(k in text for k in ['mật khẩu', 'bảo mật', 'dữ liệu cá nhân', 'quyền riêng tư', 'xác thực 2 bước', '2fa', 'định danh']): return 'KNS.4.2'
    return 'KNS.4.1'

def classify_m5(q_text, q_title):
    text = (q_text + " " + q_title).lower()
    if any(k in text for k in ['quy trình', 'cải tiến', 'workflow', 'tự động hóa', 'năng suất', 'tối ưu']): return 'KNS.5.4'
    if any(k in text for k in ['phân tích', 'dữ liệu', 'biểu đồ', 'trực quan hóa', 'google sheets', 'lọc', 'sort']): return 'KNS.5.3'
    if any(k in text for k in ['tự học', 'stackoverflow', 'hỏi đáp', 'cộng đồng', 'diễn đàn', 'tìm kiếm giải pháp']): return 'KNS.5.2'
    return 'KNS.5.1'

def classify_m6(q_text, q_title):
    text = (q_text + " " + q_title).lower()
    if any(k in text for k in ['iot', 'big data', 'tương lai', 'kỹ năng mới', 'nghề nghiệp', 'tự động hóa']): return 'KNS.6.4'
    if any(k in text for k in ['chuyển đổi số', '4.0', 'công nghiệp', 'số hóa']): return 'KNS.6.3'
    if any(k in text for k in ['y tế', 'nông nghiệp', 'giao thông', 'nhà thông minh', 'ứng dụng', 'thực tế']): return 'KNS.6.2'
    return 'KNS.6.1'

# --- PARSER ---

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

def main():
    try:
        print("Starting rebuild...")
        
        # Determine Path
        base_path = r'd:\MY_CODE\treeKnowledge\knowledge'
        kns_dir = os.path.join(base_path, 'Kỹ năng số')
        if not os.path.exists(kns_dir):
            # Try finding generic K* dir
             dirs = [d for d in os.listdir(base_path) if d.startswith('K')]
             if dirs: kns_dir = os.path.join(base_path, dirs[0])
        
        print(f"Using directory: {kns_dir}")
        
        # Modules Config
        modules = {
            1: classify_m1, 2: classify_m2, 3: classify_m3,
            4: classify_m4, 5: classify_m5, 6: classify_m6
        }
        
        all_csv_rows = []
        
        # Find files
        for m_id, cls_func in modules.items():
            pattern = os.path.join(kns_dir, f"MD{m_id}*gift.txt")
            files = glob.glob(pattern)
            if not files:
                print(f"Warning: No file found for Module {m_id}")
                continue
                
            fpath = files[0]
            print(f"Processing Module {m_id}: {os.path.basename(fpath)}")
            
            with open(fpath, encoding='utf-8') as f:
                questions = parse_gift(f.read())
                
            print(f"  - Questions: {len(questions)}")
            
            for i, q in enumerate(questions):
                node_id = cls_func(q['content'], q['title'])
                q_id = f"Q{m_id}.{i+1:03d}"
                
                letters = ['A', 'B', 'C', 'D', 'E', 'F']
                correct_char = ''
                formatted_options = []
                for idx, opt in enumerate(q['options']):
                    char = letters[idx] if idx < len(letters) else '?'
                    # Escape quotes in options just in case
                    opt_clean = opt.replace('"', "'")
                    formatted_options.append(f"{char}. {opt_clean}")
                    if idx == q['correct_idx']: correct_char = char
                
                # Create the string for 'Options' column
                # We want it to look like: ['A. ...', 'B. ...']
                # We use simple string representation
                options_str = str(formatted_options)
                
                row = {
                    'Question_ID': q_id,
                    'Skill_ID_List': node_id,
                    'Content': q['content'],
                    'Options': options_str,
                    'Answer': correct_char,
                    'Difficulty': 'Medium',
                    'Explanation': ''
                }
                all_csv_rows.append(row)
                
        # Write Output
        output_template = r'd:\MY_CODE\treeKnowledge\import_templates\questions_KNS.csv'
        output_final = r'd:\MY_CODE\treeKnowledge\knowledge\Kỹ năng số\questions_KNS.csv'
        
        header = ['Question_ID', 'Skill_ID_List', 'Content', 'Options', 'Answer', 'Difficulty', 'Explanation']
        
        # 1. Write to Template
        print(f"Writing {len(all_csv_rows)} rows to {output_template}...")
        with open(output_template, 'w', encoding='utf-8-sig', newline='') as f:
            # QUOTE_ALL is Critical
            writer = csv.DictWriter(f, fieldnames=header, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(all_csv_rows)
            
        # 2. Copy to Final
        print(f"Copying to {output_final}...")
        import shutil
        shutil.copy(output_template, output_final)
        
        print("Done!")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == '__main__':
    main()
