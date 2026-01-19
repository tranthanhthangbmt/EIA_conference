import sys
import os
import pandas as pd
from unittest.mock import MagicMock

# Mock streamlit before importing db_utils
import streamlit as st
st.secrets = {
    "connections": {
        "supabase": {
            "url": "postgresql://postgres.xoniyvjsmbzqsljmldkh:+T9English15011983@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
        }
    }
}

# Add parent directory to path to import db_utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_utils import init_db, add_edge, get_graph_structure, get_connection

def reproduce_issue():
    print("--- Reproducing Constraint Issue ---")
    init_db()
    
    subj_1 = "MayHoc"
    subj_2 = "TestConstraint"
    
    # 1. Ensure edge exists in Subj 1
    print(f"1. Adding edge A->B to {subj_1}...")
    add_edge("NodeA", "NodeB", subj_1)
    
    # 2. Try adding SAME edge to Subj 2
    print(f"2. Adding edge A->B to {subj_2}...")
    success, msg = add_edge("NodeA", "NodeB", subj_2)
    
    if success:
        print(f"✅ Success: {msg}")
    else:
        print(f"❌ Failed: {msg}")
        
    # 3. Verify
    g2 = get_graph_structure(subj_2)
    if not g2.empty and "NodeA" in g2['source'].values:
        print("✅ Edge found in Subj 2.")
    else:
        print("❌ Edge NOT found in Subj 2.")

if __name__ == "__main__":
    reproduce_issue()
