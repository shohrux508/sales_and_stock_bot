import sqlite3

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN joined_at DATETIME")
except Exception as e:
    print(f"joined_at: {e}")

try:
    # Set default values for existing users
    cursor.execute("UPDATE users SET joined_at = CURRENT_TIMESTAMP WHERE joined_at IS NULL")
    cursor.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")
except Exception as e:
    print(f"UPDATE error: {e}")

conn.commit()
conn.close()
print("Migration script (part 2) finished")
