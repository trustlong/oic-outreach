"""
Copies the enriched CSV to docs/ so GitHub Pages can serve it.
index.html and nearme.html are now static files that load the CSV at runtime.
"""
import os, shutil

os.makedirs("docs", exist_ok=True)
shutil.copy("all_homeowners_20mi.csv", "docs/all_homeowners_20mi.csv")
print("✅ CSV copied → docs/all_homeowners_20mi.csv")
