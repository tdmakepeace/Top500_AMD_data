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
