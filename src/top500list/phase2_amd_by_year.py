from pathlib import Path

import pandas as pd

from top500list import amd_cohort, amd_filter, io_utils
from top500list.paths import (
    AMD_BUILD_YEAR_COUNTS_BY_EDITION_NAME,
    AMD_BUILD_YEAR_TRANSITIONS_NAME,
    AMD_BY_YEAR_COMBINED_NAME,
    WORKING_AMD_BY_YEAR_DIR,
    WORKING_AMD_PER_FILE_DIR,
)


def buildAmdTableByBuildYear(
    amd_per_file_dir: Path,
    amd_by_year_dir: Path,
    reference_year: int | None = None,
    force: bool = False,
) -> pd.DataFrame:
    amd_files = sorted(path for path in amd_per_file_dir.glob("*_amd.csv") if path.is_file())
    if not amd_files:
        raise FileNotFoundError(f"No per-file AMD tables found in {amd_per_file_dir}")

    amd_frames = [pd.read_csv(amd_path) for amd_path in amd_files]
    years = amd_cohort.recentBuildYearsWithData(amd_frames, reference_year=reference_year)
    amd_by_year_dir.mkdir(parents=True, exist_ok=True)
    combined_path = amd_by_year_dir / AMD_BY_YEAR_COMBINED_NAME
    counts_by_edition_path = amd_by_year_dir / AMD_BUILD_YEAR_COUNTS_BY_EDITION_NAME
    transitions_path = amd_by_year_dir / AMD_BUILD_YEAR_TRANSITIONS_NAME
    year_label = "_".join(str(year) for year in years)
    year_output_path = amd_by_year_dir / f"amd_servers_build_years_{year_label}.csv"

    output_paths = [year_output_path, combined_path, counts_by_edition_path, transitions_path]
    source_paths = amd_files
    if all(io_utils.shouldSkip(output_path, source_paths, force) for output_path in output_paths):
        print(f"SKIP  {combined_path.name} (up to date)")
        return pd.read_csv(combined_path)

    latest_servers = amd_cohort.loadLatestEditionServers(amd_files, years)
    counts_by_edition = amd_cohort.buildPerEditionBuildYearCounts(amd_files, years)
    transitions = amd_cohort.buildEditionTransitions(amd_files, years)

    if latest_servers.empty:
        combined = pd.DataFrame(columns=["source_file", "source_list"])
    else:
        combined = latest_servers.copy()
        summary_columns = amd_filter.buildSummaryColumns(combined)
        combined = combined[summary_columns]

    print(f"WRITE {year_output_path.name} ({len(combined)} unique AMD servers, latest list edition only)")
    io_utils.writeCsv(combined, year_output_path)
    io_utils.writeCsv(combined, combined_path)
    io_utils.writeCsv(counts_by_edition, counts_by_edition_path)
    io_utils.writeCsv(transitions, transitions_path)
    return combined


def runPhase2_2(
    amd_per_file_dir: Path = WORKING_AMD_PER_FILE_DIR,
    amd_by_year_dir: Path = WORKING_AMD_BY_YEAR_DIR,
    reference_year: int | None = None,
    force: bool = False,
) -> pd.DataFrame:
    return buildAmdTableByBuildYear(
        amd_per_file_dir,
        amd_by_year_dir,
        reference_year=reference_year,
        force=force,
    )
