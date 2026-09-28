import sqlite3

with open("Chinook_Sqlite.sql", encoding="utf-8", errors="ignore") as f:
    script = f.read()

conn = sqlite3.connect("Chinook.db")
conn.executescript(script)
conn.close()
print("Chinook.db created")