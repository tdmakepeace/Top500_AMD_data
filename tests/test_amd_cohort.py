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

    assert set(counts["interconnect_family"]) == {"Infiniband", "Gigabit Ethernet"}
    assert set(combo_counts["combo_label"]) == {"2024 | Infiniband", "2024 | Gigabit Ethernet"}


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
