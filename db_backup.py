import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def backup_postgres():
    """
    Creates a backup of the PostgreSQL database using pg_dump.
    Requires DATABASE_URL in .env
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url or "postgresql" not in db_url:
        print("❌ DATABASE_URL is missing or not PostgreSQL. Skip.")
        return

    # Create backups directory
    os.makedirs("backups", exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backups/db_backup_{timestamp}.sql"
    
    print(f"🚀 Starting backup to {filename}...")
    
    try:
        # We use pg_dump directly. Assumes pg_dump is in PATH.
        # Railway usually has it.
        result = subprocess.run(
            ["pg_dump", db_url, "-f", filename],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Backup successful: {filename}")
        else:
            print(f"❌ Backup failed: {result.stderr}")
            if os.path.exists(filename):
                os.remove(filename)
                
    except Exception as e:
        print(f"❌ Error during backup: {e}")

if __name__ == "__main__":
    backup_postgres()
