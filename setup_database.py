import sqlite3
import os

DATA_DIR = "winddata" # Using a local directory
DB_FILE = os.path.join(DATA_DIR, "reunion.db")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")

# Ensure the data directory exists
os.makedirs(DATA_DIR, exist_ok=True)
# Delete the database file if it already exists to start fresh
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Create the students table
cursor.execute("""
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL UNIQUE,
    secret_fact TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'No Response',
    guests INTEGER DEFAULT 0,
    biography TEXT,
    photo_filename TEXT
)
""")

# --- IMPORTANT ---
# TODO: Add all 45 of your students here.
# The 'secret_fact' is their password. For now, it's set to their first name in lowercase.
# It's recommended to change these to something more secure.
# Format: ("Full Name", "Secret Fact", "Initial Biography (optional)", "photo_filename (optional)")
students_to_add = [
    # This is the special admin user. You can log in with this to edit anyone.
    ("Reunion Admin", "GoRoosters1975!", "Admin account, not a real person.", None),

    ("Alan Zimmerman", "alan", None, None),
    ("Allison DeWitz", "allison", None, None),
    ("Amy Braunschweiger", "amy", None, None),
    ("Art Harrison", "art", None, None),
    ("Cindy Kranich", "cindy", None, None),
    ("Craig Huffsmith", "craig", None, None),
    ("Debbie Gaylord", "debbie", None, None),
    ("Eileen Anderson", "eileen", None, None),
    ("Gene Schaefer", "gene", None, None),
    ("Ginger Spears", "ginger", None, None),
    ("Jayson Krall", "jayson", None, None),
    ("Jim Zagel", "jim", None, None),
    ("JoEllen Schmutzer", "joellen", None, None),
    ("John Pemberton", "john", None, None),
    ("Julie Hahn", "julie", None, None),
    ("Karen Nygaard", "karen", None, None),
    ("Kent Einspahr", "kent", None, None),
    ("Kit Sundling", "kit", None, None),
    ("Leslie McKichan", "leslie", None, None),
    ("Linda Hall", "linda", None, None),
    ("Lori Krebs", "lori", None, None),
    ("Margo Stark", "margo", None, None),
    ("Marsha Albrecht", "marsha", None, None),
    ("Marsha Patrick", "marsha", None, None),
    ("Marty Tyler", "marty", None, None),
    ("Mike Hanson", "mike", None, None),
    ("Mimi Wahlers", "mimi", None, None),
    ("Patti Palmer", "patti", None, None),
    ("Ray Hermann", "ray", None, None),
    ("Rick Johnson", "rick", None, None),
    ("Rick Suffield", "rick", None, None),
    ("Steve Scheffel", "steve", None, None),
    ("Shawn Reiton", "shawn", None, None),
    ("Tom May Pender", "tom", None, None),
    ("Tom Watson", "tom", None, None),
]

print("Populating database...")

for student in students_to_add:
    name, fact, bio, photo = student
    cursor.execute(
        "INSERT INTO students (full_name, secret_fact, biography, photo_filename) VALUES (?, ?, ?, ?)",
        (name, fact, bio, photo)
    )

conn.commit()
conn.close()

# Create the 'uploads' directory for photos if it doesn't exist
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)
    print(f"Created '{UPLOADS_DIR}' directory for photos.")

print(f"Database '{DB_FILE}' created and populated successfully.")
print("IMPORTANT: You can now run 'python main.py' to start the web server.")