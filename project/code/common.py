"""Pengaturan bersama untuk semua skrip. Semua jalur relatif terhadap folder project/."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # folder project/
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"                                 # data simulasi mentah (tidak di-commit)
CLEAN_DIR = DATA / "clean"                             # data bersih (tidak di-commit)
REF_DIR = DATA / "reference"
DIM_DEFECT_CSV = REF_DIR / "dim_defect.csv"
GROUND_TRUTH = DATA / "ground_truth.json"
DB_PATH = ROOT / "yield.duckdb"
CODE = ROOT / "code"
SQL_PREP = CODE / "1-data-preparation" / "sql"
SQL_ANALYSIS = CODE / "2-analysis" / "sql"
HTML_DIR = CODE / "3-presentation" / "html"
RES_PREP = ROOT / "results" / "1-data-preparation"
RES_ANALYSIS = ROOT / "results" / "2-analysis"
RES_PRESENT = ROOT / "results" / "3-presentation"
DOCS_DIR = ROOT / "docs"

SEED = 20260302
START_DATE = "2026-03-02"      # Senin
N_DAYS = 75                    # hari kerja Senin-Jumat
MODELS = ["Basic", "Plus", "Pro"]
SHIFTS = ["Shift 1", "Shift 2"]
STATIONS = ["Solder Paste Printing", "Component Placement", "Reflow Soldering", "AOI Inspection",
            "Board Test (ICT)", "Screen Assembly", "Housing Assembly", "Final Inspection",
            "Functional Test", "Packaging"]
IMPACT_REDUCTIONS = [0.10, 0.20, 0.30]
FULL_MONTHS = ["2026-03", "2026-04", "2026-05"]   # dasar volume per bulan


def result(name):
    """Cari CSV hasil di folder hasil per tahap."""
    for d in (RES_PREP, RES_ANALYSIS, RES_PRESENT):
        p = d / name
        if p.exists():
            return p
    raise FileNotFoundError(name)


def chdir_root():
    os.chdir(ROOT)
