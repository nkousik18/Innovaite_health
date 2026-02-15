"""Fix the alerts model relationship issue"""

# Read the file
with open('models/alerts.py', 'r') as f:
    lines = f.readlines()

# Find and fix the subscriptions relationship
fixed_lines = []
for i, line in enumerate(lines):
    if 'subscriptions' in line and 'relationship' in line:
        # Comment out the problematic line
        fixed_lines.append(f"    # TEMPORARILY DISABLED: {line}")
    else:
        fixed_lines.append(line)

# Write back
with open('models/alerts.py', 'w') as f:
    f.writelines(fixed_lines)

print("✅ Fixed models/alerts.py - commented out subscriptions relationship")
