import matplotlib.pyplot as plt
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


def test_leftMarginForYLabels_scales_with_label_length() -> None:
    short_margin = phase3_pdf_report._leftMarginForYLabels(["TOP500_2026"])
    long_margin = phase3_pdf_report._leftMarginForYLabels(["TOP500_202606"] * 12)

    assert long_margin >= short_margin
    assert long_margin <= phase3_pdf_report.ACCELERATOR_Y_LABEL_MAX_LEFT_MARGIN


def test_shortSourceCsvLabel_removes_csv_suffix() -> None:
    assert phase3_pdf_report._shortSourceCsvLabel("TOP500_202606.csv") == "TOP500_202606"


def test_shrinkAxesWidthForRightLegend_reduces_plot_width() -> None:
    fig, axis = plt.subplots()
    axis.set_position([0.1, 0.1, 0.8, 0.8])

    phase3_pdf_report._shrinkAxesWidthForRightLegend(axis, 0.74)

    position = axis.get_position()
    assert position.x1 <= 0.74 + 1e-6
    plt.close(fig)


def test_placeLegendBottomRight_keeps_legend_inside_axes() -> None:
    fig, axis = plt.subplots()
    axis.plot([1, 2, 3], label="Series A")
    axis.legend(title="Example")

    phase3_pdf_report._placeLegendBottomRight(axis, title="Example", fontsize=7)

    legend = axis.get_legend()
    assert legend is not None
    assert legend._loc == 4
    plt.close(fig)
