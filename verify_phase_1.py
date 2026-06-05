import sys
import os

# Set PYTHONPATH to 'bot/' so imports like config, database.db, etc. work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

def test_imports_and_config():
    print("Testing imports and config verification...")
    try:
        import config
        print("Import config: OK")
        print(f"  BOT_TOKEN is loaded: {bool(config.BOT_TOKEN)}")
        print(f"  ADMIN_ID is loaded: {config.ADMIN_ID}")
        print(f"  MONGO_URI is loaded: {config.MONGO_URI}")
        print(f"  DB_NAME is loaded: {config.DB_NAME}")
        
        import database.db as db
        print("Import database.db: OK")
        
        import handlers.user as user
        print("Import handlers.user: OK")
        
        import handlers.admin as admin
        print("Import handlers.admin: OK")
        
        import scheduler.tasks as tasks
        print("Import scheduler.tasks: OK")
        
        import bot
        print("Import bot: OK")
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
    print("All checks passed successfully!")

if __name__ == "__main__":
    test_imports_and_config()
