import sqlite3

# Connect to the database
conn = sqlite3.connect('test.db')

# Create a cursor object
cursor = conn.cursor()

# Execute a query to fetch all rows from a table
# cursor.execute('SELECT * FROM wind')
cursor.execute("SELECT * FROM wind WHERE date(time) = '2024-04-15'")

# Fetch all rows from the result set
rows = cursor.fetchall()

# Print the contents of the database
for row in rows:
    print(row)

# Close the cursor and the connection
# cursor.close()
# conn.close()