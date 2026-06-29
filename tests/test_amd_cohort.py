from pathlib import Path

import pandas as pd

from top500list import amd_cohort

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _writeAmdFixture(path: Path, rows: list[dict[str, object]]) -> None:
    frame = pd.DataFrame(rows)
    frame.to_csv(path, index=False)


def test_dedupeServers_counts_each_system_once(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        [
            {"System ID": 1, "Name": "Alpha", "Year": 2024},
            {"System ID": 1, "Name": "Alpha", "Year": 2024},
            {"System ID": 2, "Name": "Beta", "Year": 2023},
        ]
    )

    deduped = amd_cohort.dedupeServers(frame)

    assert len(deduped) == 2


def test_recentBuildYearsWithData_limits_to_years_present_in_frames() -> None:
    frames = [
        pd.DataFrame({"Year": [2026, 2025, 2024]}),
        pd.DataFrame({"Year": [2023, 2020]}),
    ]

    years = amd_cohort.recentBuildYearsWithData(frames, reference_year=2026, span=6)

    assert years == [2026, 2025, 2024, 2023]


def test_recentBuildYearsWithData_falls_back_to_candidate_window_when_no_years() -> None:
    frames = [pd.DataFrame({"Name": ["Alpha"]})]

    years = amd_cohort.recentBuildYearsWithData(frames, reference_year=2026, span=6)

    assert years == [2026, 2025, 2024, 2023, 2022, 2021]


def test_buildPerEditionBuildYearCounts_uses_unique_servers_per_file(tmp_path: Path) -> None:
    first_path = tmp_path / "TOP500_202306_amd.csv"
    second_path = tmp_path / "TOP500_202311_amd.csv"
    _writeAmdFixture(
        first_path,
        [
            {"source_file": "TOP500_202306.csv", "System ID": 1, "Name": "A", "Year": 2023},
            {"source_file": "TOP500_202306.csv", "System ID": 2, "Name": "B", "Year": 2024},
            {"source_file": "TOP500_202306.csv", "System ID": 2, "Name": "B", "Year": 2024},
        ],
    )
    _writeAmdFixture(
        second_path,
        [
            {"source_file": "TOP500_202311.csv", "System ID": 1, "Name": "A", "Year": 2023},
            {"source_file": "TOP500_202311.csv", "System ID": 3, "Name": "C", "Year": 2024},
        ],
    )

    counts = amd_cohort.buildPerEditionBuildYearCounts([first_path, second_path], [2024, 2023])

    first_2024 = counts[(counts["source_csv"] == "TOP500_202306.csv") & (counts["build_year"] == 2024)][
        "server_count"
    ].iloc[0]
    second_2024 = counts[(counts["source_csv"] == "TOP500_202311.csv") & (counts["build_year"] == 2024)][
        "server_count"
    ].iloc[0]
    second_2023 = counts[(counts["source_csv"] == "TOP500_202311.csv") & (counts["build_year"] == 2023)][
        "server_count"
    ].iloc[0]

    assert first_2024 == 1
    assert second_2024 == 1
    assert second_2023 == 1


def test_buildEditionTransitions_tracks_added_and_dropped(tmp_path: Path) -> None:
    first_path = tmp_path / "TOP500_202306_amd.csv"
    second_path = tmp_path / "TOP500_202311_amd.csv"
    _writeAmdFixture(
        first_path,
        [
            {"source_file": "TOP500_202306.csv", "System ID": 1, "Name": "A", "Year": 2023},
            {"source_file": "TOP500_202306.csv", "System ID": 2, "Name": "B", "Year": 2024},
        ],
    )
    _writeAmdFixture(
        second_path,
        [
            {"source_file": "TOP500_202311.csv", "System ID": 2, "Name": "B", "Year": 2024},
            {"source_file": "TOP500_202311.csv", "System ID": 3, "Name": "C", "Year": 2024},
        ],
    )

    transitions = amd_cohort.buildEditionTransitions([first_path, second_path], [2024, 2023])
    year_2024 = transitions[transitions["build_year"] == 2024].iloc[0]
    year_2023 = transitions[transitions["build_year"] == 2023].iloc[0]

    assert year_2024["added"] == 1
    assert year_2024["dropped"] == 0
    assert year_2024["net_change"] == 1
    assert year_2023["added"] == 0
    assert year_2023["dropped"] == 1
    assert year_2023["net_change"] == -1


def test_buildPerEditionInterconnectCounts_tracks_unique_servers(tmp_path: Path) -> None:
    amd_path = tmp_path / "TOP500_202606_amd.csv"
    _writeAmdFixture(
        amd_path,
        [
            {
                "source_file": "TOP500_202606.csv",
                "System ID": 1,
                "Name": "A",
                "Year": 2024,
                "Processor Generation": "AMD Zen-4 (Genoa)",
                "Interconnect Family": "Infiniband",
            },
            {
                "source_file": "TOP500_202606.csv",
                "System ID": 2,
                "Name": "B",
                "Year": 2024,
                "Processor Generation": "AMD Zen-4 (Genoa)",
                "Interconnect Family": "Gigabit Ethernet",
            },
            {
                "source_file": "TOP500_202606.csv",
                "System ID": 2,
                "Name": "B",
                "Year": 2024,
                "Processor Generation": "AMD Zen-4 (Genoa)",
                "Interconnect Family": "Gigabit Ethernet",
            },
        ],
    )

    counts = amd_cohort.buildPerEditionInterconnectCounts([amd_path])
    combo_counts = amd_cohort.buildPerEditionBuildYearInterconnectCounts([amd_path], [2024, 2023])

    assert set(counts["interconnect_family"]) == {"Infiniband", "Ethernet"}
    assert set(combo_counts["combo_label"]) == {"2024 | Infiniband", "2024 | Ethernet"}


def test_buildPerEditionAcceleratorVendorCounts_uses_processor_generation_and_accel_name(
    tmp_path: Path,
) -> None:
    amd_path = tmp_path / "TOP500_202606_amd.csv"
    _writeAmdFixture(
        amd_path,
        [
            {
                "System ID": 1,
                "Processor Generation": "AMD Zen-4 (Genoa)",
                "Accelerator/Co-Processor": "NVIDIA H100",
                "Accelerator/Co-Processor Cores": 9988224,
            },
            {
                "System ID": 2,
                "Processor Generation": "AMD Zen-4 (Genoa)",
                "Accelerator/Co-Processor": "AMD Instinct MI300A",
                "Accelerator/Co-Processor Cores": 10260000,
            },
            {
                "System ID": 3,
                "Processor Generation": "AMD Zen-4 (Genoa)",
                "Accelerator/Co-Processor": "",
                "Accelerator/Co-Processor Cores": "",
            },
            {
                "System ID": 4,
                "Processor Generation": "Intel Sapphire Rapids",
                "Accelerator/Co-Processor": "AMD Instinct MI300X",
                "Accelerator/Co-Processor Cores": 20096,
            },
        ],
    )

    counts = amd_cohort.buildPerEditionAcceleratorVendorCounts([amd_path])
    by_vendor = dict(zip(counts["accelerator_vendor"], counts["server_count"], strict=True))

    assert by_vendor["NVIDIA"] == 1
    assert by_vendor["AMD"] == 1
    assert by_vendor["none"] == 1
    assert by_vendor["other"] == 0
    assert by_vendor["Intel"] == 0


def test_buildPerEditionProcessorTechnologyVendorCounts_uses_all_systems(tmp_path: Path) -> None:
    first_path = tmp_path / "TOP500_202306.csv"
    second_path = tmp_path / "TOP500_202311.csv"
    pd.DataFrame(
        [
            {
                "System ID": 1,
                "Name": "A",
                "Processor Generation": "AMD Zen-4 (Genoa)",
                "Accelerator/Co-Processor": "AMD Instinct MI300A",
            },
            {
                "System ID": 2,
                "Name": "B",
                "Processor Generation": "Intel Sapphire Rapids",
                "Accelerator/Co-Processor": "NVIDIA H100",
            },
        ]
    ).to_csv(first_path, index=False)
    pd.DataFrame(
        [
            {
                "System ID": 3,
                "Name": "C",
                "Processor Generation": "ARMv8.2-A SVE",
                "Accelerator/Co-Processor": "",
            },
        ]
    ).to_csv(second_path, index=False)

    counts = amd_cohort.buildPerEditionProcessorTechnologyVendorCounts([first_path, second_path])
    amd_first = counts[
        (counts["source_csv"] == "TOP500_202306.csv") & (counts["processor_technology_vendor"] == "AMD")
    ]["server_count"].iloc[0]
    arm_second = counts[
        (counts["source_csv"] == "TOP500_202311.csv") & (counts["processor_technology_vendor"] == "ARM")
    ]["server_count"].iloc[0]

    assert amd_first == 1
    assert arm_second == 1


def test_buildPerEditionAcceleratorVendorCountsAllSystems_includes_non_amd_cpus(tmp_path: Path) -> None:
    list_path = tmp_path / "TOP500_202406.csv"
    pd.DataFrame(
        [
            {
                "System ID": 1,
                "Name": "A",
                "Processor Generation": "Intel Sapphire Rapids",
                "Accelerator/Co-Processor": "NVIDIA H100",
            },
            {
                "System ID": 2,
                "Name": "B",
                "Processor Generation": "AMD Zen-4 (Genoa)",
                "Accelerator/Co-Processor": "AMD Instinct MI300A",
            },
        ]
    ).to_csv(list_path, index=False)

    counts = amd_cohort.buildPerEditionAcceleratorVendorCountsAllSystems([list_path])
    nvidia_count = counts[counts["accelerator_vendor"] == "NVIDIA"]["server_count"].iloc[0]

    assert nvidia_count == 1


def test_buildPerEditionGpuMarketVendorCounts_excludes_systems_without_gpu(tmp_path: Path) -> None:
    list_path = tmp_path / "TOP500_202406.csv"
    pd.DataFrame(
        [
            {
                "System ID": 1,
                "Name": "A",
                "Processor Generation": "AMD Zen-4 (Genoa)",
                "Accelerator/Co-Processor": "NVIDIA H100",
            },
            {
                "System ID": 2,
                "Name": "B",
                "Processor Generation": "AMD Zen-4 (Genoa)",
                "Accelerator/Co-Processor": "",
            },
        ]
    ).to_csv(list_path, index=False)

    counts = amd_cohort.buildPerEditionGpuMarketVendorCounts([list_path])
    other_count = counts[counts["gpu_vendor"] == "Other"]["server_count"].iloc[0]
    nvidia_count = counts[counts["gpu_vendor"] == "NVIDIA"]["server_count"].iloc[0]

    assert nvidia_count == 1
    assert other_count == 0
