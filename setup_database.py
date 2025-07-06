import sqlite3
import os

# Define paths relative to the script's execution directory.
# This allows the script to be run on the host before starting Docker.
DATA_DIR = "winddata"
REUNION_DB = os.path.join(DATA_DIR, "reunion.db")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")

# Ensure the data directory exists
os.makedirs(DATA_DIR, exist_ok=True)
# Delete the database file if it already exists to start fresh
if os.path.exists(REUNION_DB):
    os.remove(REUNION_DB)

conn = sqlite3.connect(REUNION_DB)
cursor = conn.cursor()

# Create the students table
cursor.execute("""
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL UNIQUE,
    secret_fact TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'No Response',
    guests INTEGER DEFAULT 0,
    biography TEXT
)
""")

# Create the photos table
cursor.execute("""
CREATE TABLE photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    student_id INTEGER NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
)
""")

# --- IMPORTANT ---
# TODO: Add all 45 of your students here.
# The 'secret_fact' is their password. For now, it's set to their first name in lowercase.
# It's recommended to change these to something more secure.
# Format: ("Full Name", "Secret Fact", "Initial Biography (optional)")
students_to_add = [
    # This is the special admin user. You can log in with this to edit anyone.
    ("Reunion Admin", "GoRoosters1975!", "Admin account, not a real person."),

    ("Alan Zimmerman", "alan", None),
    ("Allison DeWitz", "allison", None),
    ("Amy Braunschweiger", "amy", None),
    ("Art Harrison", "art", None),
    ("Cindy Kranich", "cindy", None),
    ("Craig Huffsmith", "craig", None),
    ("Debbie Gaylord", "debbie", None),
    ("Eileen Anderson", "eileen", None),
    ("Gene Schaefer", "gene", None),
    ("Ginger Spears", "ginger", None),
    ("Jayson Krall", "jayson", None),
    ("Jim Zagel", "jim", None),
    ("JoEllen Schmutzer", "joellen", None),
    ("John Pemberton", "john", None),
    ("Julie Hahn", "julie", None),
    ("Karen Nygaard", "karen", None),
    ("Kent Einspahr", "kent", None),
    ("Kit Sundling", "kit", None),
    ("Leslie McKichan", "leslie", None),
    ("Linda Hall", "linda", None),
    ("Lori Krebs", "lori", None),
    ("Margo Stark", "margo", None),
    ("Marsha Albrecht", "marsha", None),
    ("Marsha Patrick", "marsha", None),
    ("Marty Tyler", "marty", None),
    ("Mike Hanson", "mike", None),
    ("Mimi Wahlers", "mimi", None),
    ("Patti Palmer", "patti", None),
    ("Ray Hermann", "ray", None),
    ("Rick Johnson", "rick", None),
    ("Rick Suffield", "rick", None),
    ("Steve Scheffel", "steve", None),
    ("Shawn Reiton", "shawn", None),
    ("Tom May Pender", "tom", None),
    ("Tom Watson", "tom", None),
]

print("Populating database...")

for student in students_to_add:
    name, fact, bio = student
    cursor.execute(
        "INSERT INTO students (full_name, secret_fact, biography) VALUES (?, ?, ?)",
        (name, fact, bio)
    )

conn.commit()
conn.close()

# Create the 'uploads' directory for photos if it doesn't exist
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)
    print(f"Created '{UPLOADS_DIR}' directory for photos.")

print(f"Database '{REUNION_DB}' created and populated successfully.")
print("IMPORTANT: You can now run 'python main.py' to start the web server.")