from pathlib import Path

from top500list import io_utils
from top500list.paths import RAW_DIR, SUPPORTED_SOURCE_SUFFIXES, WORKING_CSV_DIR


def convertRawFilesToCsv(raw_dir: Path, working_csv_dir: Path, force: bool = False) -> list[Path]:
    source_files = io_utils.listSourceFiles(raw_dir, SUPPORTED_SOURCE_SUFFIXES)
    if not source_files:
        raise FileNotFoundError(f"No source files found in {raw_dir}")

    written_paths: list[Path] = []
    for source_path in source_files:
        output_path = working_csv_dir / f"{source_path.stem}.csv"
        if io_utils.shouldSkip(output_path, [source_path], force):
            print(f"SKIP  {output_path.name} (up to date)")
            written_paths.append(output_path)
            continue

        print(f"CONVERT {source_path.name} -> {output_path.name}")
        frame = io_utils.readTabularFile(source_path)
        io_utils.writeCsv(frame, output_path)
        written_paths.append(output_path)

    return written_paths


def runPhase1(raw_dir: Path = RAW_DIR, working_csv_dir: Path = WORKING_CSV_DIR, force: bool = False) -> list[Path]:
    working_csv_dir.mkdir(parents=True, exist_ok=True)
    return convertRawFilesToCsv(raw_dir, working_csv_dir, force=force)
