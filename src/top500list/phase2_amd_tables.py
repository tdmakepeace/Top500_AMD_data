from pathlib import Path

import pandas as pd

from top500list import amd_cohort, amd_filter, io_utils
from top500list.paths import (
    AMD_PER_FILE_MANIFEST_NAME,
    WORKING_AMD_PER_FILE_DIR,
    WORKING_CSV_DIR,
)


def buildAmdTablePerFile(
    working_csv_dir: Path,
    amd_per_file_dir: Path,
    force: bool = False,
) -> tuple[list[Path], pd.DataFrame]:
    csv_files = io_utils.loadWorkingCsvFiles(working_csv_dir)
    if not csv_files:
        raise FileNotFoundError(f"No converted CSV files found in {working_csv_dir}")

    amd_per_file_dir.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []
    manifest_rows: list[dict[str, object]] = []

    for csv_path in csv_files:
        output_path = amd_per_file_dir / f"{csv_path.stem}_amd.csv"
        if io_utils.shouldSkip(output_path, [csv_path], force):
            print(f"SKIP  {output_path.name} (up to date)")
            output_paths.append(output_path)
            amd_frame = pd.read_csv(output_path)
            amd_frame = amd_cohort.dedupeServers(amd_filter.filterAmdProcessorGenerationServers(amd_frame))
            manifest_rows.append(
                {
                    "source_csv": csv_path.name,
                    "amd_csv": output_path.name,
                    "amd_server_count": len(amd_frame),
                }
            )
            continue

        print(f"FILTER AMD {csv_path.name} -> {output_path.name}")
        frame = pd.read_csv(csv_path)
        amd_frame = amd_filter.filterAmdProcessorGenerationServers(frame)
        amd_frame = amd_cohort.dedupeServers(amd_frame)
        amd_frame = io_utils.attachSourceMetadata(
            amd_frame,
            source_file=csv_path.name,
            source_list=io_utils.inferListLabel(csv_path),
        )
        summary_columns = amd_filter.buildSummaryColumns(amd_frame)
        amd_frame = amd_frame[summary_columns]
        io_utils.writeCsv(amd_frame, output_path)
        output_paths.append(output_path)
        manifest_rows.append(
            {
                "source_csv": csv_path.name,
                "amd_csv": output_path.name,
                "amd_server_count": len(amd_frame),
            }
        )

    manifest = pd.DataFrame(manifest_rows)
    manifest_path = amd_per_file_dir / AMD_PER_FILE_MANIFEST_NAME
    io_utils.writeCsv(manifest, manifest_path)
    return output_paths, manifest


def runPhase2_1(
    working_csv_dir: Path = WORKING_CSV_DIR,
    amd_per_file_dir: Path = WORKING_AMD_PER_FILE_DIR,
    force: bool = False,
) -> tuple[list[Path], pd.DataFrame]:
    return buildAmdTablePerFile(working_csv_dir, amd_per_file_dir, force=force)
