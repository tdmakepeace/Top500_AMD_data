import re
from pathlib import Path

import pandas as pd

from top500list import amd_filter

SYSTEM_ID_COLUMN_CANDIDATES = [
    ["system", "id"],
]

NAME_COLUMN_CANDIDATES = [
    ["name"],
    ["computer"],
    ["system"],
]

SITE_ID_COLUMN_CANDIDATES = [
    ["site", "id"],
]


def parseListEditionKey(source_name: str) -> int:
    match = re.search(r"(20\d{4})", source_name)
    if match:
        return int(match.group(1))
    match = re.search(r"(20\d{2})", source_name)
    if match:
        return int(match.group(1)) * 100
    return 0


def sortAmdFilesByEdition(amd_files: list[Path]) -> list[Path]:
    return sorted(amd_files, key=lambda path: parseListEditionKey(path.stem))


def resolveSystemIdColumn(columns: list[str]) -> str | None:
    return amd_filter.resolveColumn(columns, SYSTEM_ID_COLUMN_CANDIDATES)


def resolveServerKeyColumn(columns: list[str]) -> str | None:
    system_id_column = resolveSystemIdColumn(columns)
    if system_id_column is not None:
        return system_id_column

    name_column = amd_filter.resolveColumn(columns, NAME_COLUMN_CANDIDATES)
    site_id_column = amd_filter.resolveColumn(columns, SITE_ID_COLUMN_CANDIDATES)
    if name_column is not None and site_id_column is not None:
        return "__server_key__"
    if name_column is not None:
        return name_column
    return None


def _attachServerKey(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    key_column = resolveServerKeyColumn(list(working.columns))
    if key_column is None:
        working["_server_key"] = working.index.astype(str)
        return working

    if key_column == "__server_key__":
        name_column = amd_filter.resolveColumn(list(working.columns), NAME_COLUMN_CANDIDATES)
        site_id_column = amd_filter.resolveColumn(list(working.columns), SITE_ID_COLUMN_CANDIDATES)
        working["_server_key"] = working[name_column].astype(str) + "::" + working[site_id_column].astype(str)
        return working

    working["_server_key"] = working[key_column].astype(str)
    return working


def dedupeServers(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()

    working = _attachServerKey(frame)
    return working.drop_duplicates(subset=["_server_key"], keep="first").drop(columns=["_server_key"])


def attachBuildYear(frame: pd.DataFrame) -> pd.DataFrame:
    year_column = amd_filter.resolveBuildYearColumn(list(frame.columns))
    if year_column is None:
        raise ValueError("Could not find a build-year column (expected something like 'Year').")

    working = frame.copy()
    working["_build_year"] = amd_filter.coerceBuildYear(working[year_column])
    return working


def filterToBuildYears(frame: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    working = attachBuildYear(frame)
    allowed_years = set(years)
    filtered = working[working["_build_year"].isin(allowed_years)].copy()
    return filtered.drop(columns=["_build_year"])


def countUniqueServersByBuildYear(frame: pd.DataFrame, years: list[int]) -> pd.Series:
    filtered = filterToBuildYears(frame, years)
    deduped = dedupeServers(filtered)
    if deduped.empty:
        return pd.Series(dtype="int64")

    with_years = attachBuildYear(deduped)
    counts = with_years["_build_year"].value_counts().sort_index()
    return counts.astype(int)


def _identityFrame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame


def buildPerEditionBuildYearCounts(
    amd_files: list[Path],
    years: list[int],
    frame_transform=None,
) -> pd.DataFrame:
    if frame_transform is None:
        frame_transform = _identityFrame

    rows: list[dict[str, object]] = []
    for amd_path in sortAmdFilesByEdition(amd_files):
        frame = pd.read_csv(amd_path)
        frame = frame_transform(frame)
        source_csv = amd_path.stem.replace("_amd", "") + ".csv"
        if "source_file" in frame.columns and not frame.empty:
            source_csv = str(frame["source_file"].iloc[0])

        counts = countUniqueServersByBuildYear(frame, years)
        for build_year, server_count in counts.items():
            rows.append(
                {
                    "source_csv": source_csv,
                    "list_edition": parseListEditionKey(source_csv),
                    "build_year": int(build_year),
                    "server_count": int(server_count),
                }
            )

    if not rows:
        return pd.DataFrame(columns=["source_csv", "list_edition", "build_year", "server_count"])
    return pd.DataFrame(rows)


def resolveCountryColumn(columns: list[str]) -> str | None:
    return amd_filter.resolveColumn(columns, [["country"]])


def topCountriesFromFrame(frame: pd.DataFrame, top_n: int = 10) -> list[str]:
    country_column = resolveCountryColumn(list(frame.columns))
    if country_column is None or frame.empty:
        return []

    counts = frame[country_column].fillna("Unknown").value_counts()
    return counts.head(top_n).index.astype(str).tolist()


def countUniqueServersByCountry(
    frame: pd.DataFrame,
    years: list[int],
    countries: list[str] | None = None,
) -> pd.Series:
    filtered = filterToBuildYears(frame, years)
    deduped = dedupeServers(filtered)
    if deduped.empty:
        return pd.Series(dtype="int64")

    country_column = resolveCountryColumn(list(deduped.columns))
    if country_column is None:
        return pd.Series(dtype="int64")

    working = deduped.copy()
    working[country_column] = working[country_column].fillna("Unknown").astype(str)
    if countries is not None:
        allowed_countries = set(countries)
        working = working[working[country_column].isin(allowed_countries)]
        if working.empty:
            return pd.Series(dtype="int64")

    counts = working[country_column].value_counts().sort_index()
    return counts.astype(int)


def buildPerEditionCountryCounts(
    amd_files: list[Path],
    years: list[int],
    top_countries: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for amd_path in sortAmdFilesByEdition(amd_files):
        frame = pd.read_csv(amd_path)
        source_csv = amd_path.stem.replace("_amd", "") + ".csv"
        if "source_file" in frame.columns and not frame.empty:
            source_csv = str(frame["source_file"].iloc[0])

        counts = countUniqueServersByCountry(frame, years, countries=top_countries)
        for country, server_count in counts.items():
            rows.append(
                {
                    "source_csv": source_csv,
                    "list_edition": parseListEditionKey(source_csv),
                    "country": str(country),
                    "server_count": int(server_count),
                }
            )

    if not rows:
        return pd.DataFrame(columns=["source_csv", "list_edition", "country", "server_count"])
    return pd.DataFrame(rows)


INTERCONNECT_FAMILY_COLUMN_CANDIDATES = [
    ["interconnect", "family"],
]


def resolveInterconnectFamilyColumn(columns: list[str]) -> str | None:
    return amd_filter.resolveColumn(columns, INTERCONNECT_FAMILY_COLUMN_CANDIDATES)


def _prepareInterconnectFrame(
    frame: pd.DataFrame,
    years: list[int] | None = None,
    require_amd_processor_generation: bool = True,
) -> pd.DataFrame:
    working = dedupeServers(frame)
    if require_amd_processor_generation:
        working = amd_filter.filterAmdProcessorGenerationServers(working)
    if years is not None:
        working = filterToBuildYears(working, years)
    return working


def countUniqueServersByInterconnectFamily(
    frame: pd.DataFrame,
    years: list[int] | None = None,
    require_amd_processor_generation: bool = True,
) -> pd.Series:
    working = _prepareInterconnectFrame(frame, years, require_amd_processor_generation)
    if working.empty:
        return pd.Series(dtype="int64")

    interconnect_column = resolveInterconnectFamilyColumn(list(working.columns))
    if interconnect_column is None:
        return pd.Series(dtype="int64")

    working[interconnect_column] = working[interconnect_column].fillna("Unknown").astype(str)
    counts = working[interconnect_column].value_counts().sort_index()
    return counts.astype(int)


def countUniqueServersByBuildYearInterconnect(
    frame: pd.DataFrame,
    years: list[int],
    require_amd_processor_generation: bool = True,
) -> pd.Series:
    working = _prepareInterconnectFrame(frame, years, require_amd_processor_generation)
    if working.empty:
        return pd.Series(dtype="int64")

    interconnect_column = resolveInterconnectFamilyColumn(list(working.columns))
    if interconnect_column is None:
        return pd.Series(dtype="int64")

    with_years = attachBuildYear(working)
    with_years[interconnect_column] = with_years[interconnect_column].fillna("Unknown").astype(str)
    with_years["_combo_label"] = with_years["_build_year"].astype(str) + " | " + with_years[interconnect_column]
    counts = with_years["_combo_label"].value_counts().sort_index()
    return counts.astype(int)


def buildPerEditionInterconnectCounts(
    amd_files: list[Path],
    years: list[int] | None = None,
    require_amd_processor_generation: bool = True,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for amd_path in sortAmdFilesByEdition(amd_files):
        frame = pd.read_csv(amd_path)
        source_csv = amd_path.stem.replace("_amd", "") + ".csv"
        if "source_file" in frame.columns and not frame.empty:
            source_csv = str(frame["source_file"].iloc[0])

        counts = countUniqueServersByInterconnectFamily(
            frame,
            years=years,
            require_amd_processor_generation=require_amd_processor_generation,
        )
        for interconnect_family, server_count in counts.items():
            rows.append(
                {
                    "source_csv": source_csv,
                    "list_edition": parseListEditionKey(source_csv),
                    "interconnect_family": str(interconnect_family),
                    "server_count": int(server_count),
                }
            )

    if not rows:
        return pd.DataFrame(columns=["source_csv", "list_edition", "interconnect_family", "server_count"])
    return pd.DataFrame(rows)


def buildPerEditionBuildYearInterconnectCounts(amd_files: list[Path], years: list[int]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for amd_path in sortAmdFilesByEdition(amd_files):
        frame = pd.read_csv(amd_path)
        source_csv = amd_path.stem.replace("_amd", "") + ".csv"
        if "source_file" in frame.columns and not frame.empty:
            source_csv = str(frame["source_file"].iloc[0])

        counts = countUniqueServersByBuildYearInterconnect(frame, years)
        for combo_label, server_count in counts.items():
            build_year_text, interconnect_family = combo_label.split(" | ", maxsplit=1)
            rows.append(
                {
                    "source_csv": source_csv,
                    "list_edition": parseListEditionKey(source_csv),
                    "build_year": int(build_year_text),
                    "interconnect_family": interconnect_family,
                    "combo_label": combo_label,
                    "server_count": int(server_count),
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "source_csv",
                "list_edition",
                "build_year",
                "interconnect_family",
                "combo_label",
                "server_count",
            ]
        )
    return pd.DataFrame(rows)


def topBuildYearInterconnectCombosFromFrame(
    frame: pd.DataFrame,
    years: list[int],
    top_n: int = 20,
) -> list[str]:
    counts = countUniqueServersByBuildYearInterconnect(frame, years)
    if counts.empty:
        return []
    return counts.sort_values(ascending=False).head(top_n).index.astype(str).tolist()


def topInterconnectFamiliesFromFrame(
    frame: pd.DataFrame,
    years: list[int] | None = None,
    require_amd_processor_generation: bool = True,
) -> list[str]:
    counts = countUniqueServersByInterconnectFamily(
        frame,
        years=years,
        require_amd_processor_generation=require_amd_processor_generation,
    )
    if counts.empty:
        return []
    return counts.sort_values(ascending=False).index.astype(str).tolist()


def buildPerEditionAcceleratorVendorCounts(amd_files: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for amd_path in sortAmdFilesByEdition(amd_files):
        frame = pd.read_csv(amd_path)
        deduped = dedupeServers(frame)
        deduped = amd_filter.filterAmdProcessorGenerationServers(deduped)
        source_csv = amd_path.stem.replace("_amd", "") + ".csv"
        if "source_file" in frame.columns and not frame.empty:
            source_csv = str(frame["source_file"].iloc[0])

        accelerator_column = amd_filter.resolveAcceleratorColumn(list(deduped.columns))
        if accelerator_column is None or deduped.empty:
            for vendor_category in amd_filter.ACCELERATOR_VENDOR_CATEGORIES:
                rows.append(
                    {
                        "source_csv": source_csv,
                        "list_edition": parseListEditionKey(source_csv),
                        "accelerator_vendor": vendor_category,
                        "server_count": 0,
                    }
                )
            continue

        working = deduped.copy()
        working["_accelerator_vendor"] = working.apply(
            lambda row: amd_filter.classifyAcceleratorVendorForRow(row, accelerator_column),
            axis=1,
        )
        counts = working["_accelerator_vendor"].value_counts()
        for vendor_category in amd_filter.ACCELERATOR_VENDOR_CATEGORIES:
            rows.append(
                {
                    "source_csv": source_csv,
                    "list_edition": parseListEditionKey(source_csv),
                    "accelerator_vendor": vendor_category,
                    "server_count": int(counts.get(vendor_category, 0)),
                }
            )

    if not rows:
        return pd.DataFrame(columns=["source_csv", "list_edition", "accelerator_vendor", "server_count"])
    return pd.DataFrame(rows)


def _serverIdsByBuildYear(frame: pd.DataFrame, years: list[int]) -> dict[int, set[str]]:
    filtered = filterToBuildYears(frame, years)
    deduped = _attachServerKey(filtered)
    if deduped.empty:
        return {}

    with_years = attachBuildYear(deduped)
    grouped: dict[int, set[str]] = {}
    for build_year, group in with_years.groupby("_build_year", dropna=True):
        grouped[int(build_year)] = set(group["_server_key"].astype(str))
    return grouped


def buildEditionTransitions(amd_files: list[Path], years: list[int]) -> pd.DataFrame:
    sorted_files = sortAmdFilesByEdition(amd_files)
    rows: list[dict[str, object]] = []

    for previous_path, current_path in zip(sorted_files, sorted_files[1:], strict=False):
        previous_frame = pd.read_csv(previous_path)
        current_frame = pd.read_csv(current_path)
        previous_source = previous_path.stem.replace("_amd", "") + ".csv"
        current_source = current_path.stem.replace("_amd", "") + ".csv"
        if "source_file" in previous_frame.columns and not previous_frame.empty:
            previous_source = str(previous_frame["source_file"].iloc[0])
        if "source_file" in current_frame.columns and not current_frame.empty:
            current_source = str(current_frame["source_file"].iloc[0])

        previous_ids = _serverIdsByBuildYear(previous_frame, years)
        current_ids = _serverIdsByBuildYear(current_frame, years)
        all_build_years = sorted(set(previous_ids) | set(current_ids))

        for build_year in all_build_years:
            previous_set = previous_ids.get(build_year, set())
            current_set = current_ids.get(build_year, set())
            rows.append(
                {
                    "previous_source_csv": previous_source,
                    "current_source_csv": current_source,
                    "build_year": build_year,
                    "previous_count": len(previous_set),
                    "current_count": len(current_set),
                    "added": len(current_set - previous_set),
                    "dropped": len(previous_set - current_set),
                    "net_change": len(current_set) - len(previous_set),
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "previous_source_csv",
                "current_source_csv",
                "build_year",
                "previous_count",
                "current_count",
                "added",
                "dropped",
                "net_change",
            ]
        )
    return pd.DataFrame(rows)


def loadLatestEditionServers(amd_files: list[Path], years: list[int]) -> pd.DataFrame:
    if not amd_files:
        return pd.DataFrame()

    latest_path = sortAmdFilesByEdition(amd_files)[-1]
    frame = pd.read_csv(latest_path)
    filtered = filterToBuildYears(frame, years)
    return dedupeServers(filtered)
