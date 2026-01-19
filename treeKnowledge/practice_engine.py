import ast
import random
from collections import defaultdict
import heapq

from db_utils import (
    get_user_progress, save_progress, get_all_questions,
    get_graph_structure, log_activity,
    apply_forgetting_decay, penalize_parents,
    get_connection
)

# =========================================================================================
# 1. CORE ENGINE (Knowledge Graph & Question Selection)
# =========================================================================================

def load_practice_context(username, subject_id):
    """Dùng chung cho cả tab Luyện tập và Đồ thị tri thức."""
    k_graph_df = get_graph_structure(subject_id)
    q_matrix_df = get_all_questions(subject_id)
    raw_progress = get_user_progress(username, subject_id)
    user_mastery = {row[0]: row[2] for row in raw_progress} if raw_progress else {}
    return k_graph_df, q_matrix_df, user_mastery

def get_strict_topological_order(k_graph):
    adj_list = defaultdict(list)
    in_degree = defaultdict(int)
    all_nodes = set(k_graph['source']).union(set(k_graph['target']))

    for node in all_nodes:
        in_degree[node] = 0
    for _, row in k_graph.iterrows():
        u, v = row['source'], row['target']
        adj_list[u].append(v)
        in_degree[v] += 1

    min_heap = []
    for node in all_nodes:
        if in_degree[node] == 0:
            heapq.heappush(min_heap, node)

    topo_order = []
    while min_heap:
        u = heapq.heappop(min_heap)
        topo_order.append(u)
        for v in adj_list[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                heapq.heappush(min_heap, v)

    if len(topo_order) < len(all_nodes):
        rem = list(all_nodes - set(topo_order))
        topo_order.extend(sorted(rem))
    return topo_order


def has_q(skill, q_matrix_df):
    return not q_matrix_df[q_matrix_df['skill_id_list'].str.contains(skill, na=False, regex=False)].empty


def recommend_next_skill_strict(user_mastery, k_graph_df, q_matrix_df, threshold, exclude_id=None):
    """
    Trả về (target_skill, strategy_msg, debug_log)
    -> Tab Luyện tập dùng cái này để biết hôm nay học node nào.
    """
    learning_path = get_strict_topological_order(k_graph_df)
    debug_log = []
    target = None
    strat = ""

    for node in learning_path:
        score = user_mastery.get(node, 0.0)

        if score >= threshold:
            debug_log.append(f"✅ {node}: Đã xong ({score:.0%}) → Bỏ qua.")
            continue

        if not has_q(node, q_matrix_df):
            debug_log.append(f"⏭️ {node}: Không có câu hỏi → Bỏ qua.")
            continue

        parents = k_graph_df[k_graph_df['target'] == node]['source'].tolist()
        is_locked = False
        locked_by = None
        for p in parents:
            if has_q(p, q_matrix_df) and user_mastery.get(p, 0.0) < threshold:
                is_locked = True
                locked_by = p
                break

        if is_locked:
            debug_log.append(f"🔒 {node}: Bị khóa bởi {locked_by}.")
            continue

        target = node
        
        # --- XAI LOGIC ---
        reason_code = "NEW"
        reason_desc = "Đây là bài học tiếp theo trong lộ trình."
        
        if score > 0:
            reason_code = "DECAY"
            reason_desc = f"Kiến thức đang bị hao mòn ({score:.0%}). Cần ôn tập lại ngay!"
        else:
            reason_code = "NEW"
            if parents:
                 # Check if parents are strongly mastered
                 strong_parents = [p for p in parents if user_mastery.get(p,0) >= 0.8]
                 if len(strong_parents) == len(parents):
                     reason_desc = "Bạn đã nắm vững kiến thức nền. Đã sẵn sàng học bài mới!"
                 else:
                     reason_desc = "Đã đủ điều kiện qua môn. Tiếp tục tiến lên!"
            else:
                 reason_desc = "Bắt đầu hành trình với bài học đầu tiên."

        strat = {
            "name": "Strict Tree",
            "reason_code": reason_code,
            "reason_desc": reason_desc,
            "current_score": score
        }
        
        debug_log.append(f"🎯 CHỌN: {target} (Lý do: {reason_code})")
        break

    if not target:
        return None, {"reason_code": "COMPLETED", "reason_desc": "Hoàn thành xuất sắc!"}, debug_log

    return target, strat, debug_log

def pick_question_for_skill(skill_id, q_matrix_df, current_mastery=0.0, last_question_id=None, shuffle=True):
    """Lấy 1 câu hỏi cho skill_id, có tính đến độ khó (CLAD)."""
    qs = q_matrix_df[q_matrix_df['skill_id_list'].str.contains(skill_id, na=False, regex=False)]
    if qs.empty:
        return None

    # Tránh lặp lại ngay
    if last_question_id and len(qs) > 1:
        qs2 = qs[qs['question_id'] != last_question_id]
        if not qs2.empty:
            qs = qs2

    # --- CLAD: Difficulty Control ---
    # Phân loại độ khó dựa trên Mastery hiện tại
    # Quy ước DB: 1/Easy/Dễ, 2/Medium/TB, 3/Hard/Khó
    target_diffs = []
    if current_mastery < 0.4:
        target_diffs = ['1', 'Easy', 'De', 'Dễ']        # Mới học -> Dễ
    elif current_mastery < 0.7:
        target_diffs = ['2', 'Medium', 'TB', 'Trung bình', 'Normal'] # Đang học -> Vừa
    else:
        target_diffs = ['3', 'Hard', 'Kho', 'Khó', 'Advanced']     # Thành thạo -> Khó

    final_q = None
    
    # Thử tìm câu hỏi có độ khó phù hợp
    if 'difficulty' in qs.columns:
        # Case-insensitive check
        qs_filtered = qs[qs['difficulty'].astype(str).str.strip().str.lower().isin([d.lower() for d in target_diffs])]
        
        if not qs_filtered.empty:
            final_q = qs_filtered.sample(1).iloc[0]
        else:
            # Fallback 1: Nếu master cao mà ko có câu khó -> Lấy câu TB
            if current_mastery >= 0.7:
                fallback_diffs = ['2', 'Medium', 'TB', 'Trung bình', 'Normal']
                qs_fb = qs[qs['difficulty'].astype(str).str.strip().str.lower().isin([d.lower() for d in fallback_diffs])]
                if not qs_fb.empty: final_q = qs_fb.sample(1).iloc[0]

    # Fallback cuối cùng: Random trong tập còn lại (hoặc toàn bộ qs)
    if final_q is None:
        final_q = qs.sample(1).iloc[0]

    q_dict = final_q.to_dict()

    if shuffle:
        try:
            ops_list = ast.literal_eval(q_dict['options'])
            true_ans = str(q_dict['answer']).strip().upper()

            parsed_items = []
            valid_format = True
            for op in ops_list:
                parts = op.split('.', 1)
                if len(parts) < 2:
                    valid_format = False
                    break
                label = parts[0].strip().upper()
                content = parts[1].strip()
                is_target = (label == true_ans)
                parsed_items.append({"content": content, "is_target": is_target})

            if valid_format and parsed_items:
                random.shuffle(parsed_items)
                labels = ['A', 'B', 'C', 'D', 'E', 'F']
                new_ops_list = []
                new_ans_char = true_ans

                for idx, item in enumerate(parsed_items):
                    lab = labels[idx] if idx < len(labels) else str(idx)
                    new_ops_list.append(f"{lab}. {item['content']}")
                    if item['is_target']:
                        new_ans_char = lab

                q_dict['options'] = str(new_ops_list)
                q_dict['answer'] = new_ans_char
        except Exception:
            pass

    return q_dict

def grade_and_update(
    q_data, selected_option, username, subject_id, node_id,
    user_mastery, q_matrix_df, mastery_threshold, learning_rate,
    duration=0.0, strategy_info=None
):
    """
    Trả về:
      is_correct, new_score, correct_answer_text, status
    và đồng thời cập nhật DB + log_activity + penalize_parents + FASS.
    """
    # 1. Parse options & check
    try:
        ops = ast.literal_eval(q_data['options'])
    except Exception:
        ops = []

    # --- IMPROVED ROBUST GRADING LOGIC ---
    try:
        # 1. Prepare Key (Database Answer)
        raw_key = str(q_data.get('answer', '')).strip()
        # Handle "A.", "A)", "Option A" -> "A"
        # If it's a single letter (possibly with punctuation), take the letter.
        # If it's a full word "True", keep "True".
        
        # Heuristic: If starts with single letter + punctuation, take first char.
        clean_key = raw_key.upper()
        if len(clean_key) > 1 and not clean_key.isalpha():
             # e.g. "A." or "B)" or "C "
             if clean_key[0].isalpha() and not clean_key[1].isalpha():
                 clean_key = clean_key[0]
        
        # 2. Prepare User Selection
        raw_sel = str(selected_option).strip()
        # User selection often comes as "A. Content..."
        clean_sel = raw_sel.upper()
        if len(clean_sel) > 0:
            clean_sel = clean_sel[0] # Always take first char "A" from "A. Content"
            
        # 3. Compare
        is_correct = (clean_sel == clean_key)
        
        # [DEBUG LOG]
        print(f"DEBUG GRADING: '[{raw_sel}]' -> '{clean_sel}' VS Key '[{raw_key}]' -> '{clean_key}' => {is_correct}")
        
        # [FILE LOGGING]
        try:
             with open("grading_debug.txt", "a", encoding="utf-8") as f:
                 f.write(f"\\n[{datetime.now()}] Grade Q: {node_id}\\n")
                 f.write(f"Raw Sel: {repr(raw_sel)} | Clean Sel: {clean_sel}\\n")
                 f.write(f"Raw Key: {repr(raw_key)} | Clean Key: {clean_key}\\n")
                 f.write(f"Correct? {is_correct}\\n")
        except: pass

    except Exception as e:
        print(f"Grade Error: {e}")
        clean_key = str(q_data.get('answer', '')).strip().upper()
        is_correct = False
    
    corr = clean_key # Ensure compatibility with rest of function
    correct_answer_text = next((o for o in ops if o.startswith(corr)), corr)

    old_score = user_mastery.get(node_id, 0.0)

    # A. Tổng số câu trong kho cho node_id
    skill_qs = q_matrix_df[q_matrix_df['skill_id_list'].str.contains(node_id, na=False, regex=False)]
    all_question_ids = set(skill_qs['question_id'].unique())
    total_questions_in_bank = len(all_question_ids)

    if is_correct:
        # Lấy danh sách câu đã làm đúng từ DB (Postgres)
        conn = get_connection()
        if conn:
            c = conn.cursor()
            try:
                c.execute("""
                SELECT DISTINCT question_id FROM learning_logs
                WHERE username = %s AND subject_id = %s AND node_id = %s AND is_correct = 1
                """, (username, subject_id, node_id))
                answered_correctly_ids = {row[0] for row in c.fetchall()}
            except Exception:
                answered_correctly_ids = set()
            finally:
                conn.close()
        else:
            answered_correctly_ids = set()

        answered_correctly_ids.add(q_data['question_id'])
        valid_correct_count = len(answered_correctly_ids.intersection(all_question_ids))

        # LOGIC MỚI: Nếu làm đúng hết câu hỏi trong ngân hàng -> 100% (Completed)
        if valid_correct_count >= total_questions_in_bank and total_questions_in_bank > 0:
            new_score = 1.0 # Set max score
        else:
            att = 1.0
            new_score = (1 - learning_rate) * old_score + learning_rate * att

        # reset FASS flag ở phía UI (caller sẽ set)
    else:
        att = 0.0
        new_score = (1 - learning_rate) * old_score + learning_rate * att
        # phạt cha (GAKT)
        penalize_parents(username, subject_id, node_id, penalty_factor=0.15)

    status = "Completed" if new_score >= mastery_threshold else ("Review" if new_score <= 0.3 else "In Progress")
    save_progress(username, node_id, subject_id, status, new_score)

    # log
    log_activity(
        username=username,
        action_type='practice',
        subject_id=subject_id,
        node_id=node_id,
        question_id=q_data['question_id'],
        is_correct=is_correct,
        duration_seconds=duration,
        details=strategy_info
    )

    return is_correct, new_score, correct_answer_text, status


# =========================================================================================
# 2. CAT ENGINE (Testing Logic) - NEWLY MOVED FROM PAGE 4
# =========================================================================================

def get_smart_test_nodes(username, subject_id, k_graph_df=None):
    """
    Thuật toán tìm các Node cần kiểm tra dựa trên Cây tri thức:
    1. Tìm Frontier Nodes (Cha đã xong, con chưa xong).
    2. Tìm Review Nodes (Cần ôn tập).
    """
    if k_graph_df is None:
        k_graph_df = get_graph_structure()
        
    # 1. Lấy dữ liệu
    progress = get_user_progress(username, subject_id)
    user_map = {r[0]: {'status': r[1], 'score': r[2]} for r in progress}
    
    # Lấy cấu trúc cây
    parents_map = {} # node -> [parents]
    all_nodes = set()
    
    # Build graph map
    for _, row in k_graph_df.iterrows():
        src, tgt = str(row['source']), str(row['target'])
        if tgt not in parents_map: parents_map[tgt] = []
        parents_map[tgt].append(src)
        all_nodes.add(src); all_nodes.add(tgt)
        
    target_nodes = set()
    
    # LOGIC 1: REVIEW (Ưu tiên cao nhất)
    for node, info in user_map.items():
        if info['status'] == 'Review' or (info['status'] == 'In Progress' and info['score'] < 0.5):
            target_nodes.add(node)
            
    # LOGIC 2: FRONTIER (Vùng biên)
    # Node chưa xong (hoặc chưa học) NHƯNG tất cả cha đã xong
    for node in all_nodes:
        # Bỏ qua nếu node đã master
        if node in user_map and user_map[node]['score'] >= 0.8:
            continue
            
        parents = parents_map.get(node, [])
        if not parents: # Node gốc
            # Nếu chưa học node gốc -> Thêm vào
            if node not in user_map: target_nodes.add(node)
        else:
            # Kiểm tra xem tất cả cha đã master chưa
            all_parents_done = True
            for p in parents:
                p_score = user_map.get(p, {}).get('score', 0.0)
                if p_score < 0.7: # Ngưỡng qua môn
                    all_parents_done = False
                    break
            
            if all_parents_done:
                target_nodes.add(node)
    
    return list(target_nodes)

def check_stopping_condition(history, limit_min=10, limit_max=50):
    """
    Quyết định khi nào dừng bài kiểm tra Smart CAT
    """
    n = len(history)
    if n < limit_min: return False
    if n >= limit_max: return True
    
    # 1. Stability Check (Sự ổn định)
    # Nếu 5 câu gần nhất đều Đúng (Mastery) hoặc đều Sai (Fail) -> Có thể dừng
    if n >= 15:
        last_5 = [h['is_correct'] for h in history[-5:]]
        if all(last_5): return True # Quá giỏi
        if not any(last_5): return True # Cần học lại
        
    return False

def get_parents(node, k_df):
    return k_df[k_df['target'] == str(node)]['source'].tolist()

def get_children(node, k_df):
    return k_df[k_df['source'] == str(node)]['target'].tolist()

def get_strategic_question(history, user_map, k_df, q_df, valid_nodes_pool=None):
    """
    Chiến lược chọn câu hỏi thông minh dựa trên đồ thị:
    1. EXPLORATION (Đầu trận): Khảo sát ngẫu nhiên các nhánh khác nhau.
    2. REMEDIATION (Khi sai): Quay lui về node cha (kiến thức nền).
    3. PROGRESSION (Khi đúng): Tiến lên node con hoặc tăng độ khó.
    4. FRONTIER (Mặc định): Đánh vào vùng biên kiến thức.
    """
    # 0. Setup
    hist_q_ids = [h['q_id'] for h in history]
    
    # Filter available questions (exclude history)
    # Filter available questions (exclude history)
    available_qs = q_df[~q_df['question_id'].isin(hist_q_ids)].copy()
    
    # --- CRITICAL FIX: STRICT SCOPE ENFORCEMENT ---
    if valid_nodes_pool:
        # Only allow questions belonging to nodes in the pool
        # Using simple string check for list-like column
        pattern = '|'.join([str(n) for n in valid_nodes_pool])
        available_qs = available_qs[available_qs['skill_id_list'].str.contains(pattern, na=False, regex=True)]
        
    if available_qs.empty: return None, None, "Hết ngân hàng câu hỏi (Scope Limit)"

    # --- STRATEGY SELECTION ---
    target_node = None
    strategy_name = "Random"
    difficulty_target = 'medium'

    # Case 1: EXPLORATION (Under 5 questions)
    if len(history) < 5:
        strategy_name = "Exploration"
        # Try to find a node in a chapter/branch not yet touched
        touched_nodes = set([h.get('skill') for h in history if h.get('skill')])
        
        # Simple heuristic: Pick a random node from valid pool NOT in touched
        candidates = list(valid_nodes_pool) if valid_nodes_pool else []
        untouched = [n for n in candidates if n not in touched_nodes]
        
        if untouched:
            target_node = random.choice(untouched)
        else:
            target_node = random.choice(candidates) if candidates else None

    # Case 2: FEEDBACK LOOP (After 5 questions)
    else:
        last_record = history[-1]
        last_node = last_record.get('skill')
        last_correct = last_record.get('is_correct')
        
        if not last_correct:
            # ---> REMEDIATION: Backtrack to Parent
            strategy_name = "Remediation"
            parents = get_parents(last_node, k_df)
            if parents:
                # Pick a parent that is strictly NOT Mastered yet (or weak)
                weak_parents = [p for p in parents if user_map.get(p, 0.5) < 0.8]
                if weak_parents:
                    target_node = random.choice(weak_parents)
                    difficulty_target = 'easy' # Remedial should be easier
                else:
                    # If all parents master, maybe staying on current node but easier
                    target_node = last_node
                    difficulty_target = 'easy'
            else:
                # No parent (Root node), stay here logic
                target_node = last_node
                difficulty_target = 'easy'
        
        else:
            # ---> PROGRESSION: Move to Children or Harder
            children = get_children(last_node, k_df)
            
            # Prioritize children that are NOT Mastered
            unmastered_children = [c for c in children if user_map.get(c, 0.0) < 0.7]
            
            if unmastered_children:
                strategy_name = "Progression"
                target_node = random.choice(unmastered_children)
                difficulty_target = 'medium'
            else:
                # Mastery on this branch? Jump to a Frontier node
                strategy_name = "Frontier"
                difficulty_target = 'hard'
                # target_node will be None, allowing fallback search below

    # --- EXECUTE SEARCH (OPTIMIZED) ---
    # 1. Try finding Q for specific target_node
    if target_node:
        target_node_s = str(target_node)
        
        # Filter available by skill
        candidates = available_qs[available_qs['skill_id_list'].str.contains(target_node_s, na=False)]
        
        if not candidates.empty:
            # Filter by difficulty
            diff_matches = candidates[candidates['difficulty'].astype(str).str.lower() == difficulty_target]
            final_pool = diff_matches if not diff_matches.empty else candidates
            
            if not final_pool.empty:
                chosen = final_pool.sample(1).iloc[0].to_dict()
                return chosen, target_node_s, f"{strategy_name} ({difficulty_target})"

    # 2. Fallback: If no target node found or empty pool -> General Adaptive
    if valid_nodes_pool:
        # Quick Random Sample from VALID NODES
        shuffled_nodes = list(valid_nodes_pool)
        random.shuffle(shuffled_nodes)
        
        for node in shuffled_nodes[:5]: # Try 5 nodes max
            candidates = available_qs[available_qs['skill_id_list'].str.contains(str(node), na=False)]
            
            if not candidates.empty:
                chosen = candidates.sample(1).iloc[0].to_dict()
                return chosen, str(node), "Fallback"

    # 3. Last Resort: Random from available
    if not available_qs.empty:
        rand_row = available_qs.sample(1).iloc[0].to_dict()
        # Use parsed skills
        # Just grab random skill string from the list if possible, or "General"
        skills_str = str(rand_row.get('skill_id_list', 'General'))
        return rand_row, skills_str, "Random Last Resort"

    return None, None, "Hết câu hỏi"
