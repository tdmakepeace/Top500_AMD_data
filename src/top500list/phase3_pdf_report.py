from collections.abc import Callable
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from top500list import amd_cohort, amd_filter, io_utils
from top500list.paths import (
    AMD_BUILD_YEAR_COUNTS_BY_EDITION_NAME,
    AMD_BUILD_YEAR_TRANSITIONS_NAME,
    AMD_BY_YEAR_COMBINED_NAME,
    AMD_PER_FILE_MANIFEST_NAME,
    AMD_REPORT_PDF_NAME,
    BUILD_YEAR_SPAN,
    OUTPUT_DIR,
    WORKING_AMD_BY_YEAR_DIR,
    WORKING_AMD_PER_FILE_DIR,
    WORKING_CSV_DIR,
)


def _annotateBarhCounts(ax: plt.Axes, bars: object, values: pd.Series) -> None:
    for bar, value in zip(bars, values, strict=True):
        ax.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f" {int(value)}",
            va="center",
            ha="left",
            fontsize=9,
        )


def _annotateBarCounts(ax: plt.Axes, bars: object, values: pd.Series) -> None:
    for bar, value in zip(bars, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            str(int(value)),
            ha="center",
            va="bottom",
            fontsize=9,
        )


def _editionLabels(counts_frame: pd.DataFrame) -> tuple[list[str], list[int]]:
    editions = counts_frame.drop_duplicates("list_edition").sort_values("list_edition")
    return editions["source_csv"].tolist(), editions["list_edition"].tolist()


def _latestEditionCounts(counts_by_edition: pd.DataFrame) -> pd.DataFrame:
    if counts_by_edition.empty:
        return counts_by_edition
    latest_edition = counts_by_edition["list_edition"].max()
    return counts_by_edition[counts_by_edition["list_edition"] == latest_edition].sort_values("build_year")


def _latestSourceLabel(latest_servers: pd.DataFrame) -> str:
    if "source_file" in latest_servers.columns and not latest_servers.empty:
        return str(latest_servers["source_file"].iloc[0])
    return "latest list"


def _plotCountPerSource(
    manifest: pd.DataFrame,
    count_column: str,
    title: str,
    ax: plt.Axes,
) -> None:
    if manifest.empty or count_column not in manifest.columns:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center")
        ax.set_axis_off()
        return

    plot_frame = manifest.sort_values(count_column, ascending=True)
    bars = ax.barh(plot_frame["source_csv"], plot_frame[count_column], color="#ED1C24")
    _annotateBarhCounts(ax, bars, plot_frame[count_column])
    ax.set_title(title)
    ax.set_xlabel("Count")
    ax.set_ylabel("Source CSV")


def _plotUniqueBuildYearLatestEdition(
    counts_by_edition: pd.DataFrame,
    ax: plt.Axes,
    title: str,
) -> None:
    latest_counts = _latestEditionCounts(counts_by_edition)
    if latest_counts.empty:
        ax.text(0.5, 0.5, "No build-year data available", ha="center", va="center")
        ax.set_axis_off()
        return

    labels = latest_counts["build_year"].astype(str)
    values = latest_counts["server_count"]
    bars = ax.bar(labels, values, color="#ED1C24")
    _annotateBarCounts(ax, bars, values)
    latest_source = str(latest_counts["source_csv"].iloc[0])
    ax.set_title(f"{title}\n(latest list: {latest_source})")
    ax.set_xlabel("Build Year")
    ax.set_ylabel("Unique Server Count")


def _plotBuildYearTrendByEdition(
    counts_by_edition: pd.DataFrame,
    ax: plt.Axes,
    title: str,
) -> None:
    if counts_by_edition.empty:
        ax.text(0.5, 0.5, "No edition trend data available", ha="center", va="center")
        ax.set_axis_off()
        return

    plot_frame = counts_by_edition.sort_values(["list_edition", "build_year"])
    edition_labels, edition_order = _editionLabels(plot_frame)

    for build_year, group in plot_frame.groupby("build_year", sort=True):
        ordered = group.set_index("list_edition").reindex(edition_order)
        ax.plot(
            edition_labels,
            ordered["server_count"].fillna(0),
            marker="o",
            linewidth=2,
            label=str(int(build_year)),
        )

    ax.set_title(title)
    ax.set_xlabel("TOP500 List File")
    ax.set_ylabel("Unique Server Count")
    ax.tick_params(axis="x", rotation=35)
    ax.legend(title="Build Year", fontsize=8)


def _plotSeriesTrendByEdition(
    counts_frame: pd.DataFrame,
    series_column: str,
    series_values: list[str],
    ax: plt.Axes,
    title: str,
    legend_title: str,
) -> None:
    if counts_frame.empty or not series_values:
        ax.text(0.5, 0.5, "No trend data available", ha="center", va="center")
        ax.set_axis_off()
        return

    plot_frame = counts_frame.sort_values(["list_edition", series_column])
    edition_labels, edition_order = _editionLabels(plot_frame)

    for series_value in series_values:
        group = plot_frame[plot_frame[series_column] == series_value]
        if group.empty:
            continue
        ordered = group.set_index("list_edition").reindex(edition_order)
        ax.plot(
            edition_labels,
            ordered["server_count"].fillna(0),
            marker="o",
            linewidth=2,
            label=series_value,
        )

    ax.set_title(title)
    ax.set_xlabel("TOP500 List File")
    ax.set_ylabel("Unique Server Count")
    ax.tick_params(axis="x", rotation=35)
    ax.legend(title=legend_title, fontsize=7, loc="best")


def _plotCountryTrendByEdition(
    counts_by_country: pd.DataFrame,
    top_countries: list[str],
    ax: plt.Axes,
    title: str,
) -> None:
    _plotSeriesTrendByEdition(counts_by_country, "country", top_countries, ax, title, "Country")


def _plotInterconnectTrendByEdition(
    counts_by_interconnect: pd.DataFrame,
    interconnect_families: list[str],
    ax: plt.Axes,
    title: str,
) -> None:
    _plotSeriesTrendByEdition(
        counts_by_interconnect,
        "interconnect_family",
        interconnect_families,
        ax,
        title,
        "Interconnect Family",
    )


def _plotBuildYearInterconnectTrendByEdition(
    counts_by_combo: pd.DataFrame,
    combo_labels: list[str],
    ax: plt.Axes,
    title: str,
) -> None:
    _plotSeriesTrendByEdition(
        counts_by_combo,
        "combo_label",
        combo_labels,
        ax,
        title,
        "Build Year | Interconnect",
    )


def _plotTransitionInventoryByEdition(
    counts_by_edition: pd.DataFrame,
    ax: plt.Axes,
    title: str,
) -> None:
    _plotBuildYearTrendByEdition(counts_by_edition, ax, title)


def _plotTopCountries(latest_servers: pd.DataFrame, ax: plt.Axes, top_n: int = 10) -> None:
    country_column = amd_filter.resolveColumn(list(latest_servers.columns), [["country"]])
    if country_column is None or latest_servers.empty:
        ax.text(0.5, 0.5, "No country data available", ha="center", va="center")
        ax.set_axis_off()
        return

    counts = latest_servers[country_column].fillna("Unknown").value_counts().head(top_n).sort_values()
    bars = ax.barh(counts.index, counts.values, color="#ED1C24")
    _annotateBarhCounts(ax, bars, counts)
    latest_source = _latestSourceLabel(latest_servers)
    ax.set_title(f"Top {top_n} Countries (Recent Build Years)\n(latest list: {latest_source})")
    ax.set_xlabel("Unique AMD Server Count")
    ax.set_ylabel("Country")


def _buildGpuManifest(working_csv_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for csv_path in io_utils.loadWorkingCsvFiles(working_csv_dir):
        frame = pd.read_csv(csv_path)
        gpu_frame = amd_cohort.dedupeServers(amd_filter.filterAmdGpuServers(frame))
        rows.append({"source_csv": csv_path.name, "amd_gpu_count": len(gpu_frame)})

    if not rows:
        return pd.DataFrame(columns=["source_csv", "amd_gpu_count"])
    return pd.DataFrame(rows)


ACCELERATOR_VENDOR_COLORS = {
    "NVIDIA": "#76B900",
    "AMD": "#ED1C24",
    "Intel": "#0071C5",
    "none": "#BDBDBD",
    "other": "#6E6E6E",
}


def _plotStackedAcceleratorVendorByFile(
    accelerator_vendor_counts: pd.DataFrame,
    ax: plt.Axes,
) -> None:
    if accelerator_vendor_counts.empty:
        ax.text(0.5, 0.5, "No accelerator data available", ha="center", va="center")
        ax.set_axis_off()
        return

    plot_frame = accelerator_vendor_counts.sort_values("list_edition")
    file_labels = plot_frame.drop_duplicates("list_edition").sort_values("list_edition")["source_csv"].tolist()
    y_positions = np.arange(len(file_labels))
    left_offsets = np.zeros(len(file_labels))

    for vendor_category in amd_filter.ACCELERATOR_VENDOR_CATEGORIES:
        vendor_frame = plot_frame[plot_frame["accelerator_vendor"] == vendor_category]
        values = []
        for source_csv in file_labels:
            match = vendor_frame[vendor_frame["source_csv"] == source_csv]
            values.append(int(match["server_count"].iloc[0]) if not match.empty else 0)

        values_array = np.array(values)
        bars = ax.barh(
            y_positions,
            values_array,
            left=left_offsets,
            label=vendor_category,
            color=ACCELERATOR_VENDOR_COLORS[vendor_category],
        )
        for bar, value in zip(bars, values_array, strict=True):
            if value <= 0:
                continue
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_y() + bar.get_height() / 2,
                str(int(value)),
                ha="center",
                va="center",
                fontsize=7,
                color="white" if vendor_category in {"NVIDIA", "AMD", "Intel", "other"} else "black",
            )
        left_offsets += values_array

    ax.set_yticks(y_positions)
    ax.set_yticklabels(file_labels)
    ax.set_title(
        "AMD Servers by Accelerator / Co-Processor Vendor per TOP500 List File\n"
        "(Processor Generation: AMD; classified from Accelerator/Co-Processor only)"
    )
    ax.set_xlabel("Number of Unique Servers")
    ax.set_ylabel("Source CSV")
    ax.legend(title="Accelerator/Co-Processor", fontsize=8, loc="lower right")


def _saveTwoPanelPage(pdf: PdfPages, plotters: list[Callable[[plt.Axes], None]]) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11, 8.5))
    for axis, plotter in zip(axes, plotters, strict=True):
        plotter(axis)
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def _saveThreePanelPage(pdf: PdfPages, plotters: list[Callable[[plt.Axes], None]]) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(11, 11))
    for axis, plotter in zip(axes, plotters, strict=True):
        plotter(axis)
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def _plotTopSystemsTable(ax: plt.Axes, table_frame: pd.DataFrame, title: str) -> None:
    ax.axis("off")
    ax.set_title(title, fontsize=10, pad=10)

    if table_frame.empty:
        ax.text(0.5, 0.5, "No matching systems in latest list", ha="center", va="center")
        return

    table = ax.table(
        cellText=table_frame.values,
        colLabels=list(table_frame.columns),
        loc="upper center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1, 1.35)


def _saveTopSystemsPage(pdf: PdfPages, latest_list_frame: pd.DataFrame, latest_source_label: str) -> None:
    processor_technology_table = amd_filter.buildTopSystemsDisplayFrame(
        amd_filter.selectTopSystemsByRank(amd_filter.filterAmdProcessorTechnologyServers(latest_list_frame))
    )
    accelerator_table = amd_filter.buildTopSystemsDisplayFrame(
        amd_filter.selectTopSystemsByRank(amd_filter.filterAmdAcceleratorServers(latest_list_frame))
    )

    fig, axes = plt.subplots(2, 1, figsize=(11, 11))
    _plotTopSystemsTable(
        axes[0],
        processor_technology_table,
        f"Top 10 Systems: Processor Technology AMD\n(latest list: {latest_source_label})",
    )
    _plotTopSystemsTable(
        axes[1],
        accelerator_table,
        f"Top 10 Systems: Accelerator/Co-Processor AMD\n(latest list: {latest_source_label})",
    )
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def buildAmdReportPdf(
    amd_per_file_dir: Path,
    amd_by_year_dir: Path,
    output_dir: Path,
    working_csv_dir: Path = WORKING_CSV_DIR,
    force: bool = False,
) -> Path:
    manifest_path = amd_per_file_dir / AMD_PER_FILE_MANIFEST_NAME
    by_year_path = amd_by_year_dir / AMD_BY_YEAR_COMBINED_NAME
    counts_by_edition_path = amd_by_year_dir / AMD_BUILD_YEAR_COUNTS_BY_EDITION_NAME
    transitions_path = amd_by_year_dir / AMD_BUILD_YEAR_TRANSITIONS_NAME
    output_path = output_dir / AMD_REPORT_PDF_NAME

    amd_files = sorted(path for path in amd_per_file_dir.glob("*_amd.csv") if path.is_file())
    source_paths = [
        path for path in [manifest_path, by_year_path, counts_by_edition_path, transitions_path] if path.exists()
    ]
    source_paths.extend(amd_files)
    if not source_paths:
        raise FileNotFoundError("Run phase 2.1 and 2.2 before generating the PDF report.")

    if io_utils.shouldSkip(output_path, source_paths, force):
        print(f"SKIP  {output_path.name} (up to date)")
        return output_path

    manifest = pd.read_csv(manifest_path)
    latest_servers = pd.read_csv(by_year_path) if by_year_path.exists() else pd.DataFrame()
    counts_by_edition = pd.read_csv(counts_by_edition_path) if counts_by_edition_path.exists() else pd.DataFrame()
    csv_files = io_utils.loadWorkingCsvFiles(working_csv_dir)
    gpu_manifest = _buildGpuManifest(working_csv_dir)
    latest_list_path = amd_cohort.sortAmdFilesByEdition(csv_files)[-1] if csv_files else None
    latest_list_frame = pd.read_csv(latest_list_path) if latest_list_path is not None else pd.DataFrame()
    latest_list_label = latest_list_path.name if latest_list_path is not None else "latest list"

    years = io_utils.recentBuildYears(span=BUILD_YEAR_SPAN)
    gpu_counts_by_edition = amd_cohort.buildPerEditionBuildYearCounts(
        csv_files,
        years,
        frame_transform=amd_filter.filterAmdGpuServers,
    )
    top_countries = amd_cohort.topCountriesFromFrame(latest_servers)
    country_counts_by_edition = amd_cohort.buildPerEditionCountryCounts(amd_files, years, top_countries)
    latest_amd_path = amd_cohort.sortAmdFilesByEdition(amd_files)[-1]
    latest_amd_frame = amd_filter.filterAmdProcessorGenerationServers(
        amd_cohort.dedupeServers(pd.read_csv(latest_amd_path))
    )
    interconnect_counts_by_edition = amd_cohort.buildPerEditionInterconnectCounts(amd_files)
    interconnect_families = amd_cohort.topInterconnectFamiliesFromFrame(latest_amd_frame)
    year_interconnect_counts = amd_cohort.buildPerEditionBuildYearInterconnectCounts(amd_files, years)
    year_interconnect_combos = amd_cohort.topBuildYearInterconnectCombosFromFrame(latest_servers, years)
    accelerator_vendor_counts = amd_cohort.buildPerEditionAcceleratorVendorCounts(amd_files)

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"WRITE {output_path.name}")

    with PdfPages(output_path) as pdf:
        _saveThreePanelPage(
            pdf,
            [
                lambda ax: _plotCountPerSource(
                    manifest,
                    "amd_server_count",
                    "AMD Servers per TOP500 List File\n(Processor Generation: AMD)",
                    ax,
                ),
                lambda ax: _plotUniqueBuildYearLatestEdition(
                    counts_by_edition,
                    ax,
                    "Unique AMD Servers by Build Year",
                ),
                lambda ax: _plotBuildYearTrendByEdition(
                    counts_by_edition,
                    ax,
                    "AMD Servers by Build Year Across List Editions",
                ),
            ],
        )

        _saveThreePanelPage(
            pdf,
            [
                lambda ax: _plotCountPerSource(
                    gpu_manifest,
                    "amd_gpu_count",
                    "AMD Instinct / MI GPU Systems per TOP500 List File",
                    ax,
                ),
                lambda ax: _plotUniqueBuildYearLatestEdition(
                    gpu_counts_by_edition,
                    ax,
                    "Unique AMD Instinct / MI GPU Systems by Build Year",
                ),
                lambda ax: _plotBuildYearTrendByEdition(
                    gpu_counts_by_edition,
                    ax,
                    "AMD Instinct / MI GPU Systems by Build Year Across List Editions",
                ),
            ],
        )

        _saveThreePanelPage(
            pdf,
            [
                lambda ax: _plotTopCountries(latest_servers, ax),
                lambda ax: _plotCountryTrendByEdition(
                    country_counts_by_edition,
                    top_countries,
                    ax,
                    "Top 10 Countries Across List Editions",
                ),
                lambda ax: _plotTransitionInventoryByEdition(
                    counts_by_edition,
                    ax,
                    "List Transition: AMD Servers by Build Year Across List Editions",
                ),
            ],
        )

        _saveTwoPanelPage(
            pdf,
            [
                lambda ax: _plotInterconnectTrendByEdition(
                    interconnect_counts_by_edition,
                    interconnect_families,
                    ax,
                    "List Transition: AMD Servers by Interconnect Family Across List Editions\n"
                    "(Processor Generation: AMD)",
                ),
                lambda ax: _plotBuildYearInterconnectTrendByEdition(
                    year_interconnect_counts,
                    year_interconnect_combos,
                    ax,
                    "List Transition: AMD Servers by Build Year and Interconnect Family Across List Editions",
                ),
            ],
        )

        fig, axis = plt.subplots(figsize=(11, 8.5))
        _plotStackedAcceleratorVendorByFile(accelerator_vendor_counts, axis)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        _saveTopSystemsPage(pdf, latest_list_frame, latest_list_label)

    return output_path


def runPhase2_3(
    amd_per_file_dir: Path = WORKING_AMD_PER_FILE_DIR,
    amd_by_year_dir: Path = WORKING_AMD_BY_YEAR_DIR,
    output_dir: Path = OUTPUT_DIR,
    working_csv_dir: Path = WORKING_CSV_DIR,
    force: bool = False,
) -> Path:
    return buildAmdReportPdf(
        amd_per_file_dir,
        amd_by_year_dir,
        output_dir,
        working_csv_dir=working_csv_dir,
        force=force,
    )
