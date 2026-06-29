from pathlib import Path

import pandas as pd
import pytest

from top500list import amd_filter, io_utils, phase1_convert, phase2_amd_by_year, phase2_amd_tables, phase3_pdf_report

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_frames() -> dict[str, pd.DataFrame]:
    paths = {
        "2024": FIXTURES_DIR / "top500_sample_2024.csv",
        "2026": FIXTURES_DIR / "top500_sample_2026.csv",
    }
    return {label: pd.read_csv(path) for label, path in paths.items()}


def test_filterAmdServers_detects_amd_rows(sample_frames: dict[str, pd.DataFrame]) -> None:
    frame = sample_frames["2024"]
    amd_frame = amd_filter.filterAmdServers(frame)

    assert len(amd_frame) == 2


def test_filterAmdGpuServers_detects_instinct_and_mi(sample_frames: dict[str, pd.DataFrame]) -> None:
    frame = sample_frames["2024"]
    gpu_frame = amd_filter.filterAmdGpuServers(frame)

    assert len(gpu_frame) == 2


def test_recentBuildYears_uses_six_year_window() -> None:
    assert io_utils.recentBuildYears(reference_year=2026) == [2026, 2025, 2024, 2023, 2022, 2021]


def test_filterAmdServersByBuildYears_keeps_recent_four_years(sample_frames: dict[str, pd.DataFrame]) -> None:
    frame = sample_frames["2026"]
    amd_frame = amd_filter.filterAmdServers(frame)
    filtered = amd_filter.filterAmdServersByBuildYears(amd_frame, [2026, 2025, 2024, 2023])

    assert len(filtered) == 3
    assert set(filtered["Year"].tolist()) == {2026, 2025, 2024}


def test_filterAmdServersByBuildYears_keeps_explicit_year_list(sample_frames: dict[str, pd.DataFrame]) -> None:
    frame = sample_frames["2026"]
    amd_frame = amd_filter.filterAmdServers(frame)
    filtered = amd_filter.filterAmdServersByBuildYears(amd_frame, [2026, 2025, 2024])

    assert len(filtered) == 3
    assert set(filtered["Year"].tolist()) == {2026, 2025, 2024}


def test_phase_pipeline_end_to_end(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    working_csv_dir = tmp_path / "working" / "csv"
    amd_per_file_dir = tmp_path / "working" / "amd_per_file"
    amd_by_year_dir = tmp_path / "working" / "amd_by_year"
    output_dir = tmp_path / "output"
    raw_dir.mkdir()

    for fixture_name in ["top500_sample_2024.csv", "top500_sample_2026.csv"]:
        source = FIXTURES_DIR / fixture_name
        target = raw_dir / fixture_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    phase1_convert.runPhase1(raw_dir=raw_dir, working_csv_dir=working_csv_dir, force=True)
    _, manifest = phase2_amd_tables.runPhase2_1(
        working_csv_dir=working_csv_dir,
        amd_per_file_dir=amd_per_file_dir,
        force=True,
    )
    by_year = phase2_amd_by_year.runPhase2_2(
        amd_per_file_dir=amd_per_file_dir,
        amd_by_year_dir=amd_by_year_dir,
        reference_year=2026,
        force=True,
    )
    pdf_path = phase3_pdf_report.runPhase2_3(
        amd_per_file_dir=amd_per_file_dir,
        amd_by_year_dir=amd_by_year_dir,
        output_dir=output_dir,
        force=True,
    )

    assert len(list(working_csv_dir.glob("*.csv"))) == 2
    assert int(manifest["amd_server_count"].sum()) == 6
    assert len(by_year) == 4
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0


def test_shouldSkip_respects_force_and_mtime(tmp_path: Path) -> None:
    source_path = tmp_path / "source.csv"
    output_path = tmp_path / "output.csv"
    source_path.write_text("a\n1\n", encoding="utf-8")
    output_path.write_text("a\n1\n", encoding="utf-8")

    assert io_utils.shouldSkip(output_path, [source_path], force=False) is True
    assert io_utils.shouldSkip(output_path, [source_path], force=True) is False
