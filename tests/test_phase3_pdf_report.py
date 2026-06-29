import pytest

from top500list import phase3_pdf_report


@pytest.mark.parametrize(
    ("current", "previous", "expected"),
    [
        (110, 100, "+10%"),
        (90, 100, "-10%"),
        (100, 100, "0%"),
        (5, 0, "new"),
        (0, 0, None),
    ],
)
def test_formatGrowthPercent(current: int, previous: int, expected: str | None) -> None:
    assert phase3_pdf_report._formatGrowthPercent(current, previous) == expected


def test_computeGrowthPercents_skips_first_edition() -> None:
    assert phase3_pdf_report._computeGrowthPercents([100, 110, 99]) == [None, "+10%", "-10%"]


def test_formatMarketSharePercent() -> None:
    assert phase3_pdf_report._formatMarketSharePercent(25, 100) == "25%"
    assert phase3_pdf_report._formatMarketSharePercent(0, 100) == "0%"
