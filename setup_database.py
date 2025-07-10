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
    password TEXT NOT NULL,
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

    ("Marsha Albrecht", "marsha", None),
    ("Eileen Anderson", "eileen", None),
    ("Amy Braunschweiger", "amy", None),
    ("Greg Dittmer", "greg", None),
    ("Allison DeWitz", "allison", None),
    ("Kent Einspahr", "kent", None),
    ("Debbie Gaylord", "debbie", None),
    ("Julie Hahn", "julie", None),
    ("Linda Hall", "linda", None),
    ("Mike Hanson", "mike", None),
    ("Art Harrison", "art", None),
    ("Ray Hermann", "ray", None),
    ("Craig Huffsmith", "craig", None),
    ("Jayson Krall", "jayson", None),
    ("Cindy Kranich", "cindy", None),
    ("Lori Krebs", "lori", None),
    ("Rick Johnson", "rick", None),
    ("Leslie McKichan", "leslie", None),
    ("Karen Nygaard", "karen", None),
    ("Patti Palmer", "patti", None),
    ("Marsha Patrick", "marsha", None),
    ("John Pemberton", "john", None),
    ("Tom May Pender", "tom", None),
    ("Shawn Reiton", "shawn", None),
    ("Gene Schaefer", "gene", None),
    ("Steve Scheffel", "steve", None),
    ("JoEllen Schmutzer", "joellen", None),
    ("Ginger Spears", "ginger", None),
    ("Margo Stark", "margo", None),
    ("Rick Suffield", "rick", None),
    ("Kit Sundling", "kit", None),
    ("Marty Tyler", "marty", None),
    ("Mimi Wahlers", "mimi", None),
    ("Tom Watson", "tom", None),
    ("Jim Zagel", "jim", None),
    ("Alan Zimmerman", "alan", None),
    
# Passed away before the reunion
    ("Sandra Chatterton", "sandra", None),
    ("Rick Eike", "rick", None),
    ("Elaine Grothe", "elaine", None),
    ("Theresa Harth", "theresa", None),
    ("Donna Schultz", "joellen", None),
    ("Fred Teifel", "fred", None),
    ("Randy Wovert", "randy", None),
    ("Kurt Baldwin", "kurt", None),

]

print("Populating database...")

for student in students_to_add:
    name, password, bio = student
    cursor.execute(
        "INSERT INTO students (full_name, password, biography) VALUES (?, ?, ?)",
        (name, password, bio)
    )

conn.commit()
conn.close()

# Create the 'uploads' directory for photos if it doesn't exist
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)
    print(f"Created '{UPLOADS_DIR}' directory for photos.")

print(f"Database '{REUNION_DB}' created and populated successfully.")
print("IMPORTANT: You can now run 'python main.py' to start the web server.")