# Fix script for app.py
import re

with open('app.py', 'rb') as f:
    data = f.read()

# Find and replace the typo: 'solution":  -> 'solution': 
# The typo is: 'solution":  (single quote, then solution, then double quote, then colon)
# Should be: 'solution':  (single quote, then solution, then single quote, then colon)

# Count occurrences
typo = b"'solution\": "
fixed = b"'solution': "
count = data.count(typo)
print(f"Found {count} occurrences of the typo")

# Replace all
data2 = data.replace(typo, fixed)

with open('app.py', 'wb') as f:
    f.write(data2)

print("Fixed!")