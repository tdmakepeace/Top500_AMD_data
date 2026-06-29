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

PROCESSOR_TECHNOLOGY_COLUMN_CANDIDATES = [
    ["processor", "technology"],
]

MANUFACTURER_COLUMN_CANDIDATES = [
    ["manufacturer"],
]

ACCELERATOR_VENDOR_CATEGORIES = ["NVIDIA", "AMD", "Intel", "none", "other"]

STACKED_ACCELERATOR_VENDOR_CATEGORIES = ["NVIDIA", "AMD", "Intel", "other"]

PROCESSOR_TECHNOLOGY_VENDOR_CATEGORIES = ["AMD", "Intel", "NVIDIA", "ARM", "Other"]

GPU_MARKET_VENDOR_CATEGORIES = ["AMD", "Intel", "NVIDIA", "Other"]

NVIDIA_ACCELERATOR_PATTERN = re.compile(r"\bnvidia\b", re.IGNORECASE)
INTEL_GPU_ACCELERATOR_PATTERN = re.compile(
    r"\bintel\s+(?:data\s+center\s+gpu|xeon\s+max|ponte\s+vecchio|max\s+\d|gpu\s+max)\b",
    re.IGNORECASE,
)
AMD_GPU_ACCELERATOR_PATTERN = re.compile(r"\b(?:AMD\s+Instinct|Instinct|MI\d{2,4}\w*)\b", re.IGNORECASE)
AMD_PROCESSOR_GENERATION_PATTERN = re.compile(r"\bAMD\b", re.IGNORECASE)

NVIDIA_ACCELERATOR_MODEL_B200_PATTERN = re.compile(
    r"\bB200\b|\bGB200\b|\bDGX\s+B200\b|\bHGX\s+B200\b",
    re.IGNORECASE,
)
NVIDIA_ACCELERATOR_MODEL_H200_PATTERN = re.compile(
    r"\bH200\b|\bGH200\b|\bHGX\s+H200\b",
    re.IGNORECASE,
)
NVIDIA_ACCELERATOR_MODEL_H100_PATTERN = re.compile(
    r"\bH100\b|\bHGX\s+H100\b",
    re.IGNORECASE,
)

NVIDIA_ACCELERATOR_MODEL_FAMILY_ORDER = [
    "B200 (incl. GB200, HGX B200, DGX B200)",
    "H200 (incl. GH200, HGX H200, H100/H200)",
    "H100",
    "Ampere and older (A100, V100, Volta, P100, A40, etc.)",
]

AMD_ACCELERATOR_MODEL_FAMILY_ORDER = [
    "MI355X",
    "MI300X",
    "MI300A",
    "MI200 series (MI250X, MI210)",
]

INTEL_ACCELERATOR_MODEL_FAMILY_ORDER = [
    "Data Center GPU Max",
    "Data Center GPU Max 1550",
]

NVIDIA_AMPERE_OLDER_DETAIL_ORDER = [
    "A100 variants",
    "Tesla V100",
    "Volta GV100",
    "Tesla P100",
    "Tesla GP100",
    "A40",
]

INTEL_PROCESSOR_TECHNOLOGY_PATTERN = re.compile(
    r"\b(?:Intel|Xeon|Pentium|Itanium|Phi|Sapphire Rapids|Cascade Lake|Skylake|Ice Lake|Cooper Lake)\b",
    re.IGNORECASE,
)
NVIDIA_PROCESSOR_TECHNOLOGY_PATTERN = re.compile(r"\b(?:NVIDIA|Grace(?:\s+Hopper)?)\b", re.IGNORECASE)
ARM_PROCESSOR_TECHNOLOGY_PATTERN = re.compile(
    r"\b(?:ARM|Neoverse|A64FX|Ampere|ThunderX|Graviton|ARMv\d)\b",
    re.IGNORECASE,
)

MANUFACTURER_GROUP_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"asustek|\basus\b", re.IGNORECASE), "ASUSTeK"),
    (re.compile(r"\bnvidia\b", re.IGNORECASE), "NVIDIA"),
    (re.compile(r"\bhpe\b|hewlett\s*packard|hp\s*enterprise|\bcray\b", re.IGNORECASE), "HPE"),
    (re.compile(r"\bdell\b", re.IGNORECASE), "Dell"),
    (re.compile(r"\blenovo\b", re.IGNORECASE), "Lenovo"),
    (re.compile(r"\bibm\b", re.IGNORECASE), "IBM"),
    (re.compile(r"\bfujitsu\b", re.IGNORECASE), "Fujitsu"),
    (re.compile(r"\bsugon\b|dawning", re.IGNORECASE), "Sugon"),
    (re.compile(r"\binspur\b", re.IGNORECASE), "Inspur"),
    (re.compile(r"\batos\b|\bbull\b", re.IGNORECASE), "Atos"),
    (re.compile(r"\bintel\b", re.IGNORECASE), "Intel"),
    (re.compile(r"\bamd\b", re.IGNORECASE), "AMD"),
]


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


def resolveProcessorTechnologyColumn(columns: list[str]) -> str | None:
    return resolveColumn(columns, PROCESSOR_TECHNOLOGY_COLUMN_CANDIDATES)


def resolveProcessorTechnologySourceColumn(columns: list[str]) -> str | None:
    return (
        resolveProcessorTechnologyColumn(columns)
        or resolveProcessorGenerationColumn(columns)
        or resolveProcessorColumn(columns)
    )


def resolveProcessorColumn(columns: list[str]) -> str | None:
    for column in columns:
        if normalizeColumnName(column) == "processor":
            return column
    return None


def resolveManufacturerColumn(columns: list[str]) -> str | None:
    return resolveColumn(columns, MANUFACTURER_COLUMN_CANDIDATES)


def resolveNameColumn(columns: list[str]) -> str | None:
    return resolveColumn(columns, [["name"]]) or resolveColumn(columns, [["computer"]])


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


def filterAmdProcessorTechnologyServers(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    columns = list(df.columns)
    processor_technology_column = resolveProcessorTechnologyColumn(columns)
    if processor_technology_column is not None:
        mask = df[processor_technology_column].apply(isAmdRelatedText)
        return df.loc[mask].copy()

    return filterAmdProcessorGenerationServers(df)


def filterAmdAcceleratorServers(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    accelerator_column = resolveAcceleratorColumn(list(df.columns))
    if accelerator_column is None:
        return df.iloc[0:0].copy()

    mask = df[accelerator_column].apply(lambda value: classifyAcceleratorVendor(value) == "AMD")
    return df.loc[mask].copy()


def selectTopSystemsByRank(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    rank_column = resolveColumn(list(df.columns), RANK_COLUMN_CANDIDATES)
    if rank_column is None:
        return df.head(top_n).copy()

    working = df.copy()
    working["_rank_sort"] = pd.to_numeric(working[rank_column], errors="coerce")
    return (
        working.sort_values("_rank_sort", ascending=True, na_position="last").head(top_n).drop(columns=["_rank_sort"])
    )


def buildTopSystemsDisplayFrame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=["Rank", "Name", "Manufacturer", "Country", "Year", "Processor", "Accelerator/Co-Processor"]
        )

    columns = list(df.columns)
    column_map = {
        "Rank": resolveColumn(columns, RANK_COLUMN_CANDIDATES),
        "Name": resolveNameColumn(columns),
        "Manufacturer": resolveManufacturerColumn(columns),
        "Country": resolveColumn(columns, COUNTRY_COLUMN_CANDIDATES),
        "Year": resolveBuildYearColumn(columns),
        "Processor": resolveProcessorColumn(columns),
        "Accelerator/Co-Processor": resolveAcceleratorColumn(columns),
    }

    display = pd.DataFrame()
    for label, source_column in column_map.items():
        if source_column is None:
            display[label] = ""
        else:
            display[label] = df[source_column].fillna("").astype(str)

    return display


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


def classifyNvidiaAcceleratorModelFamily(text: str) -> str:
    if NVIDIA_ACCELERATOR_MODEL_B200_PATTERN.search(text):
        return NVIDIA_ACCELERATOR_MODEL_FAMILY_ORDER[0]
    if NVIDIA_ACCELERATOR_MODEL_H200_PATTERN.search(text):
        return NVIDIA_ACCELERATOR_MODEL_FAMILY_ORDER[1]
    if NVIDIA_ACCELERATOR_MODEL_H100_PATTERN.search(text):
        return NVIDIA_ACCELERATOR_MODEL_FAMILY_ORDER[2]
    return NVIDIA_ACCELERATOR_MODEL_FAMILY_ORDER[3]


def classifyNvidiaAmpereOlderDetail(text: str) -> str:
    upper = text.upper()
    if re.search(r"A100", upper):
        return "A100 variants"
    if re.search(r"VOLTA|GV100", upper):
        return "Volta GV100"
    if re.search(r"V100", upper):
        return "Tesla V100"
    if re.search(r"GP100", upper):
        return "Tesla GP100"
    if re.search(r"P100", upper):
        return "Tesla P100"
    if re.search(r"\bA40\b", upper):
        return "A40"
    return "Other Ampere and older"


def classifyAmdAcceleratorModelFamily(text: str) -> str:
    upper = text.upper()
    if re.search(r"\bMI355", upper):
        return AMD_ACCELERATOR_MODEL_FAMILY_ORDER[0]
    if re.search(r"\bMI300X\b", upper):
        return AMD_ACCELERATOR_MODEL_FAMILY_ORDER[1]
    if re.search(r"\bMI300A\b", upper):
        return AMD_ACCELERATOR_MODEL_FAMILY_ORDER[2]
    if re.search(r"\bMI2\d{2}", upper):
        return AMD_ACCELERATOR_MODEL_FAMILY_ORDER[3]
    return "Other AMD"


def classifyIntelAcceleratorModelFamily(text: str) -> str:
    upper = text.upper()
    if "MAX 1550" in upper or "MAX1550" in upper:
        return INTEL_ACCELERATOR_MODEL_FAMILY_ORDER[1]
    if "MAX" in upper:
        return INTEL_ACCELERATOR_MODEL_FAMILY_ORDER[0]
    return "Other Intel"


def _appendModelFamilyRows(
    rows: list[tuple[str, str]],
    subset: pd.DataFrame,
    accelerator_column: str,
    family_labels: list[str],
    classify_family: Callable[[str], str],
) -> None:
    families = subset[accelerator_column].astype(str).apply(classify_family)
    for family_label in family_labels:
        family_count = int((families == family_label).sum())
        if family_count > 0:
            rows.append((f"  {family_label}", str(family_count)))


def buildAcceleratorModelBreakdownRows(frame: pd.DataFrame) -> list[tuple[str, str]]:
    accelerator_column = resolveAcceleratorColumn(list(frame.columns))
    if accelerator_column is None or frame.empty:
        return []

    rows: list[tuple[str, str]] = []
    working = frame.copy()
    working["_vendor"] = working[accelerator_column].apply(classifyAcceleratorVendor)

    rows.append((f"Total systems ({len(working)} deduped)", ""))

    for vendor in ["NVIDIA", "AMD", "Intel", "other", "none"]:
        subset = working[working["_vendor"] == vendor]
        if subset.empty:
            continue

        if vendor == "none":
            rows.append((f"None (no accelerator / numeric-only field) — {len(subset)}", ""))
            continue

        if vendor == "other":
            rows.append((f"Other — {len(subset)}", ""))
            for value, count in subset[accelerator_column].astype(str).value_counts().items():
                rows.append((f"  {value}", str(int(count))))
            continue

        rows.append((f"{vendor} — {len(subset)}", ""))

        if vendor == "NVIDIA":
            families = subset[accelerator_column].astype(str).apply(classifyNvidiaAcceleratorModelFamily)
            for family_label in NVIDIA_ACCELERATOR_MODEL_FAMILY_ORDER:
                family_count = int((families == family_label).sum())
                if family_count == 0:
                    continue
                rows.append((f"  {family_label}", str(family_count)))
                if family_label != NVIDIA_ACCELERATOR_MODEL_FAMILY_ORDER[3]:
                    continue
                ampere_subset = subset[families == family_label]
                details = ampere_subset[accelerator_column].astype(str).apply(classifyNvidiaAmpereOlderDetail)
                for detail_label in NVIDIA_AMPERE_OLDER_DETAIL_ORDER:
                    detail_count = int((details == detail_label).sum())
                    if detail_count > 0:
                        rows.append((f"    {detail_label}", str(detail_count)))
            continue

        if vendor == "AMD":
            _appendModelFamilyRows(
                rows,
                subset,
                accelerator_column,
                AMD_ACCELERATOR_MODEL_FAMILY_ORDER,
                classifyAmdAcceleratorModelFamily,
            )
            continue

        _appendModelFamilyRows(
            rows,
            subset,
            accelerator_column,
            INTEL_ACCELERATOR_MODEL_FAMILY_ORDER,
            classifyIntelAcceleratorModelFamily,
        )

    return rows


def classifyProcessorTechnologyVendor(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Other"

    text = str(value).strip()
    if not text:
        return "Other"

    if isAmdRelatedText(text) or AMD_PROCESSOR_GENERATION_PATTERN.search(text):
        return "AMD"
    if _isMatchingText(text, NVIDIA_PROCESSOR_TECHNOLOGY_PATTERN):
        return "NVIDIA"
    if _isMatchingText(text, INTEL_PROCESSOR_TECHNOLOGY_PATTERN):
        return "Intel"
    if _isMatchingText(text, ARM_PROCESSOR_TECHNOLOGY_PATTERN):
        return "ARM"
    return "Other"


def classifyProcessorTechnologyVendorForRow(row: pd.Series, processor_column: str) -> str:
    return classifyProcessorTechnologyVendor(row.get(processor_column))


def classifyGpuMarketVendor(value: object) -> str | None:
    vendor = classifyAcceleratorVendor(value)
    if vendor == "none":
        return None
    if vendor in {"AMD", "Intel", "NVIDIA"}:
        return vendor
    return "Other"


def classifyGpuMarketVendorForRow(row: pd.Series, accelerator_column: str) -> str:
    return classifyGpuMarketVendor(row.get(accelerator_column))


def normalizeManufacturerGroup(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Unknown"

    text = str(value).strip()
    if not text:
        return "Unknown"

    for pattern, group_name in MANUFACTURER_GROUP_RULES:
        if pattern.search(text):
            return group_name

    return text


def normalizeInterconnectFamily(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Unknown"

    text = str(value).strip()
    if not text:
        return "Unknown"

    normalized = normalizeColumnName(text)
    if normalized in {"gigabit ethernet", "ethernet"}:
        return "Ethernet"
    return text


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
