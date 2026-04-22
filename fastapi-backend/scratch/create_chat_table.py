
from database import engine, Base
from models.model_registry import ChatMessage

def create_chat_table():
    print("Creating chat_history table...")
    Base.metadata.create_all(bind=engine)
    print("Done!")

if __name__ == "__main__":
    create_chat_table()
