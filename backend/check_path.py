import os

# Emulate backend/app/db/engine.py path logic
db_abs_path = os.path.join(
    os.path.abspath(os.curdir),  # backend/
    "data",
    "assitance.db"
)
print(f"Computed DB Path: {db_abs_path}")
print(f"Exists: {os.path.exists(db_abs_path)}")
if os.path.exists(db_abs_path):
    print(f"Size: {os.path.getsize(db_abs_path)}")

db_alt_path = os.path.join(
    os.path.abspath(os.curdir),
    "assistance.db"
)
print(f"Alt DB Path (assistance.db): {db_alt_path}")
print(f"Exists: {os.path.exists(db_alt_path)}")
if os.path.exists(db_alt_path):
    print(f"Size: {os.path.getsize(db_alt_path)}")
