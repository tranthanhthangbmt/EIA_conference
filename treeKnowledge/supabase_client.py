from supabase import create_client, Client
import streamlit as st

@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["https://xoniyvjsmbzqsljmldkh.supabase.co"]
    key = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhvbml5dmpzbWJ6cXNsam1sZGtoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM2NjM4MjMsImV4cCI6MjA3OTIzOTgyM30.17p_97cbjUp_WpnnBx7UFmYz28ZtCIEjSb_ji9PZVLo"]
    return create_client(url, key)
