
def get_mastered_question_ids(username, subject_id, node_id):
    """
    Get list of question_ids that user has answered CORRECTLY (is_correct=1)
    for a specific skill.
    """
    conn = get_connection()
    if not conn: return []
    
    try:
        sql = """
            SELECT DISTINCT question_id 
            FROM learning_logs 
            WHERE username = %s 
              AND subject_id = %s 
              AND node_id = %s
              AND is_correct = 1
        """
        c = execute_query(conn, sql, (username, subject_id, node_id))
        rows = c.fetchall()
        return {r[0] for r in rows} # Return set for O(1) lookup
    except Exception as e:
        print(f"Error getting mastered questions: {e}")
        return set()
