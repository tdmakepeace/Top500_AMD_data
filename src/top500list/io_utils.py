from pathlib import Path

import pandas as pd

from top500list.paths import BUILD_YEAR_SPAN


def shouldSkip(output_path: Path, source_paths: list[Path], force: bool) -> bool:
    if force:
        return False
    if not output_path.exists():
        return False
    if not source_paths:
        return True
    output_mtime = output_path.stat().st_mtime
    return all(source_path.stat().st_mtime <= output_mtime for source_path in source_paths if source_path.exists())


def readTabularFile(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".tsv":
        return pd.read_csv(path, sep="\t")
    if suffix == ".xlsx":
        return pd.read_excel(path, engine="openpyxl")
    if suffix == ".xls":
        return pd.read_excel(path, engine="xlrd")
    raise ValueError(f"Unsupported file type: {path.suffix}")


def writeCsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def listSourceFiles(raw_dir: Path, supported_suffixes: set[str]) -> list[Path]:
    if not raw_dir.exists():
        return []
    files = [
        path
        for path in sorted(raw_dir.iterdir())
        if path.is_file() and path.suffix.lower() in supported_suffixes and not path.name.startswith(".")
    ]
    return files


def inferListLabel(path: Path) -> str:
    stem = path.stem
    match = __import__("re").search(r"(20\d{2})", stem)
    if match:
        return match.group(1)
    return stem


def attachSourceMetadata(df: pd.DataFrame, source_file: str, source_list: str) -> pd.DataFrame:
    enriched = df.copy()
    enriched["source_file"] = source_file
    enriched["source_list"] = source_list
    return enriched


def loadWorkingCsvFiles(working_csv_dir: Path) -> list[Path]:
    if not working_csv_dir.exists():
        return []
    return sorted(path for path in working_csv_dir.glob("*.csv") if path.is_file())


def recentBuildYears(reference_year: int | None = None, span: int | None = None) -> list[int]:
    if reference_year is None:
        reference_year = pd.Timestamp.now().year
    if span is None:
        span = BUILD_YEAR_SPAN
    return [reference_year - offset for offset in range(span)]
