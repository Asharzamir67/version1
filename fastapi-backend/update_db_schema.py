# update_db_schema.py
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")

url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(url)

def update_schema():
    print(f"Connecting to {DB_NAME}...")
    # engine.begin() starts a transaction and commits at the end of the block
    with engine.begin() as conn:
        print("Checking for missing columns...")
        
        # Check if columns exist first to avoid errors (PostgreSQL specific query)
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='inference_results' AND column_name='is_test_set';
        """)
        result = conn.execute(check_query).fetchone()
        
        if not result:
            conn.execute(text("ALTER TABLE inference_results ADD COLUMN is_test_set BOOLEAN DEFAULT FALSE;"))
            print("✅ Column 'is_test_set' added.")
        else:
            print("ℹ️ Column 'is_test_set' already exists.")
            
        check_query_2 = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='inference_results' AND column_name='dataset_paths';
        """)
        result_2 = conn.execute(check_query_2).fetchone()
        
        if not result_2:
            conn.execute(text("ALTER TABLE inference_results ADD COLUMN dataset_paths TEXT;"))
            print("✅ Column 'dataset_paths' added.")
        else:
            print("ℹ️ Column 'dataset_paths' already exists.")

if __name__ == "__main__":
    update_schema()
