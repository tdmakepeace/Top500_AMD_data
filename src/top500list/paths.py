from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
WORKING_DIR = PROJECT_ROOT / "working"
WORKING_CSV_DIR = WORKING_DIR / "csv"
WORKING_AMD_PER_FILE_DIR = WORKING_DIR / "amd_per_file"
WORKING_AMD_BY_YEAR_DIR = WORKING_DIR / "amd_by_year"
OUTPUT_DIR = PROJECT_ROOT / "output"

SUPPORTED_SOURCE_SUFFIXES = {".xlsx", ".xls", ".csv", ".tsv"}
AMD_REPORT_PDF_NAME = "amd_servers_report.pdf"
AMD_BY_YEAR_COMBINED_NAME = "amd_servers_by_build_year.csv"
AMD_BUILD_YEAR_COUNTS_BY_EDITION_NAME = "amd_build_year_counts_by_edition.csv"
AMD_BUILD_YEAR_TRANSITIONS_NAME = "amd_build_year_transitions.csv"
AMD_PER_FILE_MANIFEST_NAME = "amd_per_file_manifest.csv"
BUILD_YEAR_SPAN = 4
