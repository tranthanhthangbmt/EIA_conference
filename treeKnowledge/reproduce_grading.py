
import pandas as pd
import ast
import practice_engine  # This will load the LATEST version from disk

def reproduce():
    print("search for question...")
    df = pd.read_csv(r'knowledge/KNS/questions_KNS.csv')
    
    # 1. Find the question
    target_q = None
    for idx, row in df.iterrows():
        if "dữ liệu có cấu trúc" in str(row['Content']) and "KHÔNG đúng" in str(row['Content']):
            target_q = row
            break
            
    if target_q is None:
        print("❌ Could not find question matching 'dữ liệu có cấu trúc' + 'KHÔNG đúng'")
        return

    print(f"✅ Found Question: {target_q['Question_ID']}")
    print(f"   Content: {target_q['Content']}")
    print(f"   Raw Answer in CSV: '{target_q['Answer']}'")
    print(f"   Raw Options: {target_q['Options']}")
    
    # 2. Simulate User Selection "B. Linh hoạt cao khi thay đổi"
    # Need to find the exact string from options that corresponds to B
    try:
        ops = ast.literal_eval(target_q['Options'])
        user_sel = None
        for o in ops:
            if o.strip().startswith("B."):
                user_sel = o
                break
        
        if not user_sel:
            print("⚠️ Could not find Option B in options list.")
            user_sel = "B. Linh hoạt cao khi thay đổi" # Force it
            
        print(f"   Simulated User Selection: '{user_sel}'")
        
        # 3. Call Grade
        # grade_and_update(q_data, selected_option, ...)
        # We dummy the other params
        print("\n--- Calling grade_and_update ---")
        
        # Mock dependencies if needed? 
        # practice_engine imports db_utils. We need to handle that.
        # It should work if db is accessible.
        
        is_correct, new_score, corr_text, status = practice_engine.grade_and_update(
            q_data=target_q.to_dict(),
            selected_option=user_sel,
            username="test_user",
            subject_id="KNS",
            node_id="1.1_TongQuan",
            user_mastery={},
            q_matrix_df=pd.DataFrame(),
            mastery_threshold=0.7,
            learning_rate=0.3
        )
        
        print(f"\n✅ RESULT: Correct={is_correct}")
        print(f"   Correct Text Returned: '{corr_text}'")
        
        if is_correct:
            print("SUCCESS: logic works locally.")
        else:
            print("FAILURE: logic failed locally.")
            
    except Exception as e:
        print(f"❌ Error reproducing: {e}")

if __name__ == "__main__":
    reproduce()
