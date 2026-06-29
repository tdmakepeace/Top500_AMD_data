import pandas as pd
import pytest

from top500list import amd_filter


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "none"),
        ("", "none"),
        ("   ", "none"),
        (8138240.0, "none"),
        ("8138240", "none"),
        ("NVIDIA H100 SXM5 80GB", "NVIDIA"),
        ("Nvidia H100", "NVIDIA"),
        ("AMD Instinct MI300A", "AMD"),
        ("AMD Instinct MI250X", "AMD"),
        ("Intel Data Center GPU Max", "Intel"),
        ("Intel Xeon Max 9470", "Intel"),
        ("PEZY-SC3", "other"),
        ("Intel Omni-Path 100G", "other"),
    ],
)
def test_classifyAcceleratorVendor(value: object, expected: str) -> None:
    assert amd_filter.classifyAcceleratorVendor(value) == expected


def test_resolveAcceleratorColumn_prefers_name_over_cores() -> None:
    columns = ["Rank", "Accelerator/Co-Processor", "Accelerator/Co-Processor Cores"]

    assert amd_filter.resolveAcceleratorColumn(columns) == "Accelerator/Co-Processor"


def test_filterAmdProcessorGenerationServers() -> None:
    frame = pd.DataFrame(
        [
            {"Processor Generation": "AMD Zen-4 (Genoa)", "Accelerator/Co-Processor": "AMD Instinct MI300A"},
            {"Processor Generation": "Intel Sapphire Rapids", "Accelerator/Co-Processor": "AMD Instinct MI300X"},
        ]
    )

    filtered = amd_filter.filterAmdProcessorGenerationServers(frame)

    assert len(filtered) == 1


def test_filterAmdProcessorTechnologyServers_uses_processor_technology_column() -> None:
    frame = pd.DataFrame(
        [
            {
                "Rank": 1,
                "Processor Technology": "AMD Zen-4 (Genoa)",
                "Processor Generation": "Intel Sapphire Rapids",
            },
            {
                "Rank": 2,
                "Processor Technology": "Intel Sapphire Rapids",
                "Processor Generation": "AMD Zen-4 (Genoa)",
            },
        ]
    )

    filtered = amd_filter.filterAmdProcessorTechnologyServers(frame)

    assert len(filtered) == 1
    assert int(filtered.iloc[0]["Rank"]) == 1


def test_filterAmdProcessorTechnologyServers_falls_back_to_processor_generation() -> None:
    frame = pd.DataFrame(
        [
            {"Rank": 1, "Processor Generation": "AMD Zen-4 (Genoa)"},
            {"Rank": 2, "Processor Generation": "Intel Sapphire Rapids"},
        ]
    )

    filtered = amd_filter.filterAmdProcessorTechnologyServers(frame)

    assert len(filtered) == 1
    assert int(filtered.iloc[0]["Rank"]) == 1


def test_filterAmdAcceleratorServers() -> None:
    frame = pd.DataFrame(
        [
            {"Rank": 1, "Accelerator/Co-Processor": "AMD Instinct MI300A"},
            {"Rank": 2, "Accelerator/Co-Processor": "NVIDIA H100"},
            {"Rank": 3, "Accelerator/Co-Processor": "AMD Instinct MI250X"},
        ]
    )

    filtered = amd_filter.filterAmdAcceleratorServers(frame)

    assert len(filtered) == 2
    assert filtered["Rank"].tolist() == [1, 3]


def test_selectTopSystemsByRank_returns_lowest_ranks_first() -> None:
    frame = pd.DataFrame({"Rank": [42, 3, 11, 1]})

    top = amd_filter.selectTopSystemsByRank(frame, top_n=2)

    assert top["Rank"].tolist() == [1, 3]


def test_buildTopSystemsDisplayFrame_maps_expected_columns() -> None:
    frame = pd.DataFrame(
        [
            {
                "Rank": 1,
                "Name": "El Capitan",
                "Manufacturer": "HPE",
                "Country": "United States",
                "Year": 2024,
                "Processor": "AMD EPYC",
                "Accelerator/Co-Processor": "AMD Instinct MI300A",
            }
        ]
    )

    display = amd_filter.buildTopSystemsDisplayFrame(frame)

    assert list(display.columns) == [
        "Rank",
        "Name",
        "Manufacturer",
        "Country",
        "Year",
        "Processor",
        "Accelerator/Co-Processor",
    ]
    assert display.iloc[0]["Name"] == "El Capitan"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("AMD Zen-4 (Genoa)", "AMD"),
        ("Intel Sapphire Rapids", "Intel"),
        ("ARMv8.2-A SVE", "ARM"),
        ("NVIDIA Grace Hopper", "NVIDIA"),
        ("Fujitsu A64FX", "ARM"),
        ("", "Other"),
    ],
)
def test_classifyProcessorTechnologyVendor(value: object, expected: str) -> None:
    assert amd_filter.classifyProcessorTechnologyVendor(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("AMD Instinct MI300A", "AMD"),
        ("NVIDIA H100", "NVIDIA"),
        ("Intel Data Center GPU Max", "Intel"),
        ("", None),
        ("PEZY-SC3", "Other"),
    ],
)
def test_classifyGpuMarketVendor(value: object, expected: str | None) -> None:
    assert amd_filter.classifyGpuMarketVendor(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Gigabit Ethernet", "Ethernet"),
        ("Ethernet", "Ethernet"),
        ("Infiniband HDR", "Infiniband HDR"),
    ],
)
def test_normalizeInterconnectFamily(value: object, expected: str) -> None:
    assert amd_filter.normalizeInterconnectFamily(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ASUSTeK Computer Inc.", "ASUSTeK"),
        ("Asus", "ASUSTeK"),
        ("NVIDIA Corporation", "NVIDIA"),
        ("Hewlett Packard Enterprise", "HPE"),
    ],
)
def test_normalizeManufacturerGroup(value: object, expected: str) -> None:
    assert amd_filter.normalizeManufacturerGroup(value) == expected


def test_classifyAcceleratorVendorForRow_uses_accelerator_column_only() -> None:
    row = pd.Series(
        {
            "Computer": "Apollo 2000, AMD EPYC 7763, NVIDIA A100, InfiniBand HDR",
            "Accelerator/Co-Processor": "",
            "Processor": "AMD EPYC 7763",
            "Name": "Apollo",
        }
    )

    vendor = amd_filter.classifyAcceleratorVendorForRow(row, "Accelerator/Co-Processor")

    assert vendor == "none"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("NVIDIA B200 SXM 180GB", "B200 (incl. GB200, HGX B200, DGX B200)"),
        ("NVIDIA GH200 Superchip", "H200 (incl. GH200, HGX H200, H100/H200)"),
        ("NVIDIA H100 SXM5 80GB", "H100"),
        ("NVIDIA A100", "Ampere and older (A100, V100, Volta, P100, A40, etc.)"),
    ],
)
def test_classifyNvidiaAcceleratorModelFamily(value: str, expected: str) -> None:
    assert amd_filter.classifyNvidiaAcceleratorModelFamily(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("AMD Instinct MI355X", "MI355X"),
        ("AMD Instinct MI300X", "MI300X"),
        ("AMD Instinct MI300A", "MI300A"),
        ("AMD Instinct MI250X", "MI200 series (MI250X, MI210)"),
    ],
)
def test_classifyAmdAcceleratorModelFamily(value: str, expected: str) -> None:
    assert amd_filter.classifyAmdAcceleratorModelFamily(value) == expected


def test_buildAcceleratorModelBreakdownRows_groups_latest_style_values() -> None:
    frame = pd.DataFrame(
        {
            "Accelerator/Co-Processor": [
                "NVIDIA H100 SXM5 80GB",
                "NVIDIA B200 SXM 180GB",
                "NVIDIA A100",
                "AMD Instinct MI300A",
                "",
                "8138240",
            ]
        }
    )

    rows = amd_filter.buildAcceleratorModelBreakdownRows(frame)

    assert rows[0] == ("Total systems (6 deduped)", "")
    assert ("NVIDIA — 3", "") in rows
    assert ("  H100", "1") in rows
    assert ("  B200 (incl. GB200, HGX B200, DGX B200)", "1") in rows
    assert ("AMD — 1", "") in rows
    assert ("  MI300A", "1") in rows
    assert ("None (no accelerator / numeric-only field) — 2", "") in rows
