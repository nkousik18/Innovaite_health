"""
Quick fix: Update alerts model to fix relationship issue
"""
import re

# Read the file
with open('models/alerts.py', 'r') as f:
    content = f.read()

# Backup
with open('models/alerts.py.backup', 'w') as f:
    f.write(content)

# Fix the relationship - add viewonly or proper foreign_keys
content = re.sub(
    r'subscriptions = relationship\("AlertSubscription"([^)]*)\)',
    r'subscriptions = relationship("AlertSubscription", viewonly=True)',
    content
)

# Write back
with open('models/alerts.py', 'w') as f:
    f.write(content)

print("✅ Fixed alerts.py - relationships set to viewonly")
print("Backup saved to models/alerts.py.backup")