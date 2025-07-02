import re

# Read the file content
with open('testCustomTkinter.py', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Fix the line with the error - look for any lines where there might be two statements without a newline
fixed_content = re.sub(r'(self\.navbar = ctk\.CTkFrame\(self, width=300, fg_color="#F3E6F8"\))\s*(self\.navbar_nav_items = \[\])', 
                      r'\1\n        \2', 
                      content)

# Write the fixed content back
with open('testCustomTkinter.py', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("File fixed!")
