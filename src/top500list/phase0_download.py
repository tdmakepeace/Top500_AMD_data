import os
import re
import shutil
import stat
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

from top500list.paths import (
    RAW_DIR,
    WORKING_AMD_BY_YEAR_DIR,
    WORKING_AMD_PER_FILE_DIR,
    WORKING_CSV_DIR,
)

TOP500_SITE_BASE = "https://www.top500.org"
USER_AGENT = "top500list-phase0/0.1 (+https://www.top500.org/)"

TOP500_EXCEL_LINK_PATTERN = re.compile(
    r'href="([^"]+/download/[^"]+\.xlsx)"',
    re.IGNORECASE,
)

GREEN500_EXCEL_LINK_PATTERN = re.compile(
    r'href="([^"]*/files/green500/[^"]+\.xlsx)"',
    re.IGNORECASE,
)

LIST_TYPE_ALIASES = {
    "top500": "TOP500",
    "green500": "Green500",
}

PRESERVED_DIR_ENTRIES = {".gitkeep"}
DELETE_RETRY_ATTEMPTS = 5
DELETE_RETRY_DELAY_SECONDS = 0.5


class ListDownloadError(Exception):
    pass


def _clearReadonlyFlags(func, path: str, exc_info: object) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _isFileLockedError(exc: OSError) -> bool:
    if isinstance(exc, PermissionError):
        return True
    return getattr(exc, "winerror", None) == 32


def _deletePath(path: Path) -> None:
    last_error: OSError | None = None
    for attempt in range(DELETE_RETRY_ATTEMPTS):
        try:
            if path.is_dir():
                shutil.rmtree(path, onerror=_clearReadonlyFlags)
            else:
                path.unlink()
            return
        except OSError as exc:
            if not _isFileLockedError(exc):
                raise
            last_error = exc
            if attempt + 1 < DELETE_RETRY_ATTEMPTS:
                time.sleep(DELETE_RETRY_DELAY_SECONDS)

    raise ListDownloadError(
        f"Could not delete {path}. Close programs using this file (for example Excel), pause OneDrive "
        "sync if the project folder is synced, then retry. Use --skip-clean to download without "
        "clearing existing files."
    ) from last_error


def cleanDirectoryContents(directory: Path) -> tuple[int, list[Path]]:
    directory.mkdir(parents=True, exist_ok=True)
    removed = 0
    failed: list[Path] = []
    for path in directory.iterdir():
        if path.name in PRESERVED_DIR_ENTRIES:
            continue
        try:
            _deletePath(path)
        except ListDownloadError:
            failed.append(path)
            print(f"WARN  could not delete {path}")
            continue
        removed += 1
    return removed, failed


def cleanPipelineDataDirs(
    raw_dir: Path = RAW_DIR,
    working_csv_dir: Path = WORKING_CSV_DIR,
    working_amd_per_file_dir: Path = WORKING_AMD_PER_FILE_DIR,
    working_amd_by_year_dir: Path = WORKING_AMD_BY_YEAR_DIR,
) -> int:
    total_removed = 0
    failed_paths: list[Path] = []
    for directory in (raw_dir, working_csv_dir, working_amd_per_file_dir, working_amd_by_year_dir):
        removed, failed = cleanDirectoryContents(directory)
        failed_paths.extend(failed)
        if removed:
            print(f"CLEAN {directory} ({removed} item(s) removed)")
        total_removed += removed

    if failed_paths:
        locked_names = ", ".join(path.name for path in failed_paths)
        raise ListDownloadError(
            f"Cleanup incomplete; locked file(s): {locked_names}. Close Excel or pause OneDrive sync, "
            "then retry. Use --skip-clean to download without clearing existing files."
        )

    return total_removed


def normalizeListType(list_type: str) -> str:
    normalized = LIST_TYPE_ALIASES.get(list_type.lower())
    if normalized is None:
        supported = ", ".join(sorted({value for value in LIST_TYPE_ALIASES.values()}))
        raise ValueError(f"Unsupported list type: {list_type}. Expected one of: {supported}")
    return normalized


def buildEditionLabel(year: int, month: int) -> str:
    return f"{year}{month:02d}"


def buildListPageUrl(list_type: str, year: int, month: int) -> str:
    normalized = normalizeListType(list_type)
    slug = "top500" if normalized == "TOP500" else "green500"
    return f"{TOP500_SITE_BASE}/lists/{slug}/{year}/{month:02d}/"


def buildLocalFileName(list_type: str, year: int, month: int) -> str:
    edition_label = buildEditionLabel(year, month)
    normalized = normalizeListType(list_type)
    if normalized == "TOP500":
        return f"TOP500_{edition_label}.xlsx"
    return f"green500_top_{edition_label}.xlsx"


def buildDefaultExcelUrl(list_type: str, year: int, month: int) -> str:
    edition_label = buildEditionLabel(year, month)
    normalized = normalizeListType(list_type)
    if normalized == "TOP500":
        return f"{TOP500_SITE_BASE}/lists/top500/{year}/{month:02d}/download/TOP500_{edition_label}.xlsx"
    return f"{TOP500_SITE_BASE}/files/green500/green500_top_{edition_label}.xlsx"


def iterListEditions(years: int, today: date | None = None) -> list[tuple[int, int]]:
    if years < 1:
        raise ValueError("years must be at least 1")

    anchor = today or date.today()
    start_year = anchor.year - years + 1
    editions: list[tuple[int, int]] = []
    for year in range(start_year, anchor.year + 1):
        for month in (6, 11):
            if (year, month) > (anchor.year, anchor.month):
                continue
            editions.append((year, month))
    return editions


def _fetchText(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _resolveTop500ExcelDownloadUrl(year: int, month: int) -> str:
    page_url = buildListPageUrl("TOP500", year, month)
    try:
        html = _fetchText(page_url)
    except urllib.error.HTTPError as exc:
        raise ListDownloadError(f"List page not found: {page_url} ({exc.code})") from exc
    except urllib.error.URLError as exc:
        raise ListDownloadError(f"Could not reach list page: {page_url}") from exc

    for match in TOP500_EXCEL_LINK_PATTERN.finditer(html):
        return urljoin(page_url, match.group(1))

    return buildDefaultExcelUrl("TOP500", year, month)


def _resolveGreen500ExcelDownloadUrl(year: int, month: int) -> str:
    page_url = buildListPageUrl("Green500", year, month)
    try:
        html = _fetchText(page_url)
    except urllib.error.HTTPError:
        return buildDefaultExcelUrl("Green500", year, month)
    except urllib.error.URLError as exc:
        raise ListDownloadError(f"Could not reach list page: {page_url}") from exc

    for match in GREEN500_EXCEL_LINK_PATTERN.finditer(html):
        return urljoin(page_url, match.group(1))

    return buildDefaultExcelUrl("Green500", year, month)


def resolveExcelDownloadUrl(list_type: str, year: int, month: int) -> str:
    normalized = normalizeListType(list_type)
    if normalized == "Green500":
        return _resolveGreen500ExcelDownloadUrl(year, month)
    return _resolveTop500ExcelDownloadUrl(year, month)


def downloadExcelFile(
    list_type: str,
    year: int,
    month: int,
    raw_dir: Path,
    force: bool = False,
) -> Path | None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / buildLocalFileName(list_type, year, month)
    if output_path.exists() and not force:
        print(f"SKIP  {output_path.name} (already exists)")
        return output_path

    download_url = resolveExcelDownloadUrl(list_type, year, month)
    request = urllib.request.Request(download_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, output_path.open("wb") as handle:
            handle.write(response.read())
    except urllib.error.HTTPError as exc:
        if output_path.exists():
            output_path.unlink()
        if exc.code == 404:
            print(f"MISS  {output_path.name} (not published at {download_url})")
            return None
        raise ListDownloadError(f"Download failed for {download_url} ({exc.code})") from exc
    except urllib.error.URLError as exc:
        if output_path.exists():
            output_path.unlink()
        raise ListDownloadError(f"Download failed for {download_url}") from exc

    print(f"SAVE  {output_path.name} <- {download_url}")
    return output_path


def downloadListFiles(
    list_type: str,
    years: int,
    raw_dir: Path = RAW_DIR,
    force: bool = False,
    today: date | None = None,
) -> list[Path]:
    normalized_list_type = normalizeListType(list_type)
    downloaded: list[Path] = []
    for year, month in iterListEditions(years, today=today):
        result = downloadExcelFile(normalized_list_type, year, month, raw_dir, force=force)
        if result is not None:
            downloaded.append(result)
    return downloaded


def runPhase0(
    list_type: str,
    years: int = 4,
    raw_dir: Path = RAW_DIR,
    working_csv_dir: Path = WORKING_CSV_DIR,
    working_amd_per_file_dir: Path = WORKING_AMD_PER_FILE_DIR,
    working_amd_by_year_dir: Path = WORKING_AMD_BY_YEAR_DIR,
    force: bool = False,
    clean: bool = True,
    today: date | None = None,
) -> list[Path]:
    if clean:
        cleanPipelineDataDirs(
            raw_dir=raw_dir,
            working_csv_dir=working_csv_dir,
            working_amd_per_file_dir=working_amd_per_file_dir,
            working_amd_by_year_dir=working_amd_by_year_dir,
        )
    return downloadListFiles(list_type, years, raw_dir=raw_dir, force=force, today=today)
