import re
from collections.abc import Callable

import pandas as pd

AMD_TEXT_PATTERN = re.compile(
    r"\b(?:AMD|EPYC|Opteron|Athlon|Zen-\d|MI\d{3})\b",
    re.IGNORECASE,
)

AMD_GPU_TEXT_PATTERN = re.compile(
    r"\b(?:Instinct|MI\d{2,4}\w*)\b",
    re.IGNORECASE,
)

AMD_GPU_SEARCH_COLUMN_TOKENS = [
    ["accelerator"],
    ["co", "processor"],
    ["processor"],
    ["processor", "generation"],
    ["computer"],
    ["name"],
    ["system"],
]

AMD_VENDOR_PATTERN = re.compile(r"\bAMD\b", re.IGNORECASE)

AMD_SEARCH_COLUMN_TOKENS = [
    ["processor"],
    ["processor", "family"],
    ["processor", "generation"],
    ["computer"],
    ["name"],
    ["system"],
    ["accelerator"],
    ["co", "processor"],
    ["manufacturer"],
    ["vendor"],
]

BUILD_YEAR_COLUMN_CANDIDATES = [
    ["year"],
    ["build", "year"],
    ["installation", "year"],
]

RANK_COLUMN_CANDIDATES = [
    ["rank"],
]

RMAX_COLUMN_CANDIDATES = [
    ["rmax"],
    ["r", "max"],
]

SITE_COLUMN_CANDIDATES = [
    ["site"],
]

COUNTRY_COLUMN_CANDIDATES = [
    ["country"],
]

ACCELERATOR_COLUMN_CANDIDATES = [
    ["accelerator", "co", "processor"],
]

PROCESSOR_GENERATION_COLUMN_CANDIDATES = [
    ["processor", "generation"],
]

ACCELERATOR_VENDOR_CATEGORIES = ["NVIDIA", "AMD", "Intel", "none", "other"]

NVIDIA_ACCELERATOR_PATTERN = re.compile(r"\bnvidia\b", re.IGNORECASE)
INTEL_GPU_ACCELERATOR_PATTERN = re.compile(
    r"\bintel\s+(?:data\s+center\s+gpu|xeon\s+max|ponte\s+vecchio|max\s+\d|gpu\s+max)\b",
    re.IGNORECASE,
)
AMD_GPU_ACCELERATOR_PATTERN = re.compile(r"\b(?:AMD\s+Instinct|Instinct|MI\d{2,4}\w*)\b", re.IGNORECASE)
AMD_PROCESSOR_GENERATION_PATTERN = re.compile(r"\bAMD\b", re.IGNORECASE)


def normalizeColumnName(name: object) -> str:
    text = str(name).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def findColumn(columns: list[str], must_include: list[str]) -> str | None:
    tokens = [normalizeColumnName(token) for token in must_include]
    for column in columns:
        normalized = normalizeColumnName(column)
        if all(token in normalized for token in tokens):
            return column
    return None


def resolveColumn(columns: list[str], candidates: list[list[str]]) -> str | None:
    for candidate_tokens in candidates:
        column = findColumn(columns, candidate_tokens)
        if column is not None:
            return column
    return None


def resolveBuildYearColumn(columns: list[str]) -> str | None:
    for column in columns:
        normalized = normalizeColumnName(column)
        if normalized == "year":
            return column
        if "year" in normalized and "first" not in normalized and "appearance" not in normalized:
            return column
    return resolveColumn(columns, BUILD_YEAR_COLUMN_CANDIDATES)


def _isMatchingText(value: object, pattern: re.Pattern[str]) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    text = str(value).strip()
    if not text:
        return False
    return bool(pattern.search(text))


def isAmdRelatedText(value: object) -> bool:
    return _isMatchingText(value, AMD_TEXT_PATTERN)


def isAmdGpuRelatedText(value: object) -> bool:
    return _isMatchingText(value, AMD_GPU_TEXT_PATTERN)


def _isMatchingRow(row: pd.Series, search_columns: list[str], matcher: Callable[[object], bool]) -> bool:
    for column in search_columns:
        if matcher(row.get(column)):
            return True
    return False


def isAmdServerRow(row: pd.Series, search_columns: list[str]) -> bool:
    return _isMatchingRow(row, search_columns, isAmdRelatedText)


def isAmdGpuServerRow(row: pd.Series, search_columns: list[str]) -> bool:
    return _isMatchingRow(row, search_columns, isAmdGpuRelatedText)


def getAmdSearchColumns(columns: list[str]) -> list[str]:
    resolved: list[str] = []
    for candidate_tokens in AMD_SEARCH_COLUMN_TOKENS:
        column = findColumn(columns, candidate_tokens)
        if column is not None and column not in resolved:
            resolved.append(column)
    return resolved


def getAmdGpuSearchColumns(columns: list[str]) -> list[str]:
    resolved: list[str] = []
    for candidate_tokens in AMD_GPU_SEARCH_COLUMN_TOKENS:
        column = findColumn(columns, candidate_tokens)
        if column is not None and column not in resolved:
            resolved.append(column)
    return resolved


def filterAmdServers(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    search_columns = getAmdSearchColumns(list(df.columns))
    if not search_columns:
        return df.iloc[0:0].copy()

    mask = df.apply(lambda row: isAmdServerRow(row, search_columns), axis=1)
    return df.loc[mask].copy()


def filterAmdGpuServers(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    search_columns = getAmdGpuSearchColumns(list(df.columns))
    if not search_columns:
        return df.iloc[0:0].copy()

    mask = df.apply(lambda row: isAmdGpuServerRow(row, search_columns), axis=1)
    return df.loc[mask].copy()


def coerceBuildYear(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.astype("Int64")


def filterAmdServersByBuildYears(df: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    year_column = resolveBuildYearColumn(list(df.columns))
    if year_column is None:
        raise ValueError("Could not find a build-year column (expected something like 'Year').")

    working = df.copy()
    working["_build_year"] = coerceBuildYear(working[year_column])
    allowed_years = set(years)
    filtered = working[working["_build_year"].isin(allowed_years)].copy()
    filtered = filtered.drop(columns=["_build_year"])
    return filtered


def resolveAcceleratorColumn(columns: list[str]) -> str | None:
    for column in columns:
        normalized = normalizeColumnName(column)
        if normalized == "accelerator co processor":
            return column

    for column in columns:
        normalized = normalizeColumnName(column)
        if "accelerator" in normalized and "co" in normalized and "processor" in normalized:
            if "core" in normalized:
                continue
            return column
    return None


def resolveProcessorGenerationColumn(columns: list[str]) -> str | None:
    return resolveColumn(columns, PROCESSOR_GENERATION_COLUMN_CANDIDATES)


def isAmdProcessorGeneration(value: object) -> bool:
    return _isMatchingText(value, AMD_PROCESSOR_GENERATION_PATTERN)


def filterAmdProcessorGenerationServers(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    processor_generation_column = resolveProcessorGenerationColumn(list(df.columns))
    if processor_generation_column is None:
        return df.iloc[0:0].copy()

    mask = df[processor_generation_column].apply(isAmdProcessorGeneration)
    return df.loc[mask].copy()


def _isNumericAcceleratorValue(value: object) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    text = str(value).strip()
    if not text:
        return False
    try:
        float(text.replace(",", ""))
    except ValueError:
        return False
    return True


def _classifyAcceleratorVendorText(text: str) -> str | None:
    if not text:
        return None
    if NVIDIA_ACCELERATOR_PATTERN.search(text):
        return "NVIDIA"
    if INTEL_GPU_ACCELERATOR_PATTERN.search(text):
        return "Intel"
    if AMD_GPU_ACCELERATOR_PATTERN.search(text):
        return "AMD"
    return None


def classifyAcceleratorVendor(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "none"

    if _isNumericAcceleratorValue(value):
        return "none"

    text = str(value).strip()
    if not text:
        return "none"

    vendor = _classifyAcceleratorVendorText(text)
    if vendor is not None:
        return vendor
    return "other"


def classifyAcceleratorVendorForRow(row: pd.Series, accelerator_column: str) -> str:
    return classifyAcceleratorVendor(row.get(accelerator_column))


def buildSummaryColumns(df: pd.DataFrame) -> list[str]:
    preferred = [
        resolveColumn(list(df.columns), RANK_COLUMN_CANDIDATES),
        resolveColumn(list(df.columns), [["name"]]) or resolveColumn(list(df.columns), [["computer"]]),
        resolveColumn(list(df.columns), SITE_COLUMN_CANDIDATES),
        resolveColumn(list(df.columns), COUNTRY_COLUMN_CANDIDATES),
        resolveBuildYearColumn(list(df.columns)),
        resolveColumn(list(df.columns), [["processor"]]),
        resolveColumn(list(df.columns), [["processor", "generation"]]),
        resolveColumn(list(df.columns), RMAX_COLUMN_CANDIDATES),
        "source_file",
        "source_list",
    ]
    ordered: list[str] = []
    for column in preferred:
        if column is not None and column in df.columns and column not in ordered:
            ordered.append(column)
    for column in df.columns:
        if column not in ordered:
            ordered.append(column)
    return ordered
