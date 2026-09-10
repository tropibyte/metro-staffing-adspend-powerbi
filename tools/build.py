"""Assemble the complete Metro Staffing Power BI project (.pbip + PBIR report + TMDL model).

Usage (from a clone):
    python tools/build.py                     # regenerate in place
    python tools/build.py <out_dir> [xlsx]    # or somewhere else / with another workbook

Then open the generated .pbip in Power BI Desktop, click Refresh, and
File > Save as > Browse this device > "Power BI file (*.pbix)".
"""
import os, sys, json, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model, report

NAME = "Metro Staffing Ad Spend Analysis"
# This file lives in <repo>/tools/, so the repository root is one level up.
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = sys.argv[1] if len(sys.argv) > 1 else REPO
XLSX = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    REPO, "Data", "job-cloud-output-jan-2019.xlsx")

if not os.path.isfile(XLSX):
    sys.exit(f"source workbook not found: {XLSX}")

# Regenerate only the two project folders; leave Data/, tools/ and the docs alone.
for stale in (f"{NAME}.Report", f"{NAME}.SemanticModel"):
    d = os.path.join(ROOT, stale)
    if os.path.isdir(d):
        shutil.rmtree(d)

os.makedirs(os.path.join(ROOT, "Data"), exist_ok=True)
xlsx_dst = os.path.join(ROOT, "Data", os.path.basename(XLSX))
if os.path.abspath(XLSX) != os.path.abspath(xlsx_dst):
    shutil.copy2(XLSX, xlsx_dst)

model.build(ROOT, NAME, xlsx_dst)
rp, nvis, npages = report.build(ROOT, NAME)

pbip = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
    "version": "1.0",
    "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
    "settings": {"enableAutoRecovery": True},
}
with open(os.path.join(ROOT, f"{NAME}.pbip"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(json.dumps(pbip, indent=2) + "\n")

print(f"built: {ROOT}")
print(f"  pages: {npages}   visuals + text boxes: {nvis}")
