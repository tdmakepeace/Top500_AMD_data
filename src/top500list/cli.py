from pathlib import Path

import click

from top500list import phase0_download, phase1_convert, phase2_amd_by_year, phase2_amd_tables, phase3_pdf_report
from top500list.paths import (
    OUTPUT_DIR,
    RAW_DIR,
    WORKING_AMD_BY_YEAR_DIR,
    WORKING_AMD_PER_FILE_DIR,
    WORKING_CSV_DIR,
)


def _printHeader(title: str) -> None:
    click.echo("")
    click.echo(f"=== {title} ===")


@click.group()
def cli() -> None:
    """Phased TOP500 AMD analysis pipeline."""


@cli.command("phase0")
@click.option(
    "--list-type",
    type=click.Choice(["TOP500", "GREEN500"], case_sensitive=False),
    default=None,
    help="Which list to download. Prompts when omitted.",
)
@click.option(
    "--years",
    type=int,
    default=None,
    help="Number of calendar years to fetch (current year plus prior years). Default: 4.",
)
@click.option("--raw-dir", type=click.Path(path_type=Path), default=RAW_DIR, show_default=True)
@click.option("--force", is_flag=True, help="Re-download files even when they already exist.")
@click.option(
    "--skip-clean",
    is_flag=True,
    help="Do not clear data/raw and working folders before downloading.",
)
def phase0(list_type: str | None, years: int | None, raw_dir: Path, force: bool, skip_clean: bool) -> None:
    """Download TOP500 or Green500 Excel files from top500.org into data/raw/."""
    _printHeader("Phase 0: Download List Files")
    if list_type is None:
        list_type = click.prompt(
            "List type",
            type=click.Choice(["TOP500", "Green500"]),
            default="TOP500",
        )
    if years is None:
        years = click.prompt("Number of years", type=int, default=4)

    try:
        paths = phase0_download.runPhase0(
            list_type=phase0_download.normalizeListType(list_type),
            years=years,
            raw_dir=raw_dir,
            force=force,
            clean=not skip_clean,
        )
    except phase0_download.ListDownloadError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Downloaded or reused {len(paths)} file(s) in {raw_dir}.")


@cli.command("phase1")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=RAW_DIR, show_default=True)
@click.option("--working-csv-dir", type=click.Path(path_type=Path), default=WORKING_CSV_DIR, show_default=True)
@click.option("--force", is_flag=True, help="Re-run even when working files are up to date.")
def phase1(raw_dir: Path, working_csv_dir: Path, force: bool) -> None:
    """Convert raw TOP500 files in data/raw to CSV in working/csv."""
    _printHeader("Phase 1: Convert to CSV")
    paths = phase1_convert.runPhase1(raw_dir=raw_dir, working_csv_dir=working_csv_dir, force=force)
    click.echo(f"Converted or reused {len(paths)} CSV file(s).")


@cli.command("phase2-1")
@click.option("--working-csv-dir", type=click.Path(path_type=Path), default=WORKING_CSV_DIR, show_default=True)
@click.option(
    "--amd-per-file-dir",
    type=click.Path(path_type=Path),
    default=WORKING_AMD_PER_FILE_DIR,
    show_default=True,
)
@click.option("--force", is_flag=True, help="Re-run even when working files are up to date.")
def phase2_1(working_csv_dir: Path, amd_per_file_dir: Path, force: bool) -> None:
    """Build AMD server tables per converted CSV file."""
    _printHeader("Phase 2.1: AMD Servers per File")
    paths, manifest = phase2_amd_tables.runPhase2_1(
        working_csv_dir=working_csv_dir,
        amd_per_file_dir=amd_per_file_dir,
        force=force,
    )
    click.echo(f"Wrote or reused {len(paths)} AMD table(s).")
    click.echo(f"Total AMD servers across files: {int(manifest['amd_server_count'].sum())}")


@cli.command("phase2-2")
@click.option(
    "--amd-per-file-dir",
    type=click.Path(path_type=Path),
    default=WORKING_AMD_PER_FILE_DIR,
    show_default=True,
)
@click.option(
    "--amd-by-year-dir",
    type=click.Path(path_type=Path),
    default=WORKING_AMD_BY_YEAR_DIR,
    show_default=True,
)
@click.option(
    "--reference-year",
    type=int,
    default=None,
    help="Anchor year for the 4-year window (defaults to current year).",
)
@click.option("--force", is_flag=True, help="Re-run even when working files are up to date.")
def phase2_2(
    amd_per_file_dir: Path,
    amd_by_year_dir: Path,
    reference_year: int | None,
    force: bool,
) -> None:
    """Filter AMD servers to build years: Y, Y-1, Y-2, Y-3."""
    _printHeader("Phase 2.2: AMD Servers by Build Year")
    frame = phase2_amd_by_year.runPhase2_2(
        amd_per_file_dir=amd_per_file_dir,
        amd_by_year_dir=amd_by_year_dir,
        reference_year=reference_year,
        force=force,
    )
    click.echo(f"AMD servers in recent build-year window: {len(frame)}")


@cli.command("phase2-3")
@click.option(
    "--amd-per-file-dir",
    type=click.Path(path_type=Path),
    default=WORKING_AMD_PER_FILE_DIR,
    show_default=True,
)
@click.option(
    "--amd-by-year-dir",
    type=click.Path(path_type=Path),
    default=WORKING_AMD_BY_YEAR_DIR,
    show_default=True,
)
@click.option("--output-dir", type=click.Path(path_type=Path), default=OUTPUT_DIR, show_default=True)
@click.option("--force", is_flag=True, help="Re-run even when output PDF is up to date.")
def phase2_3(amd_per_file_dir: Path, amd_by_year_dir: Path, output_dir: Path, force: bool) -> None:
    """Build PDF report with graphs from phase 2 outputs."""
    _printHeader("Phase 2.3: PDF Report")
    output_path = phase3_pdf_report.runPhase2_3(
        amd_per_file_dir=amd_per_file_dir,
        amd_by_year_dir=amd_by_year_dir,
        output_dir=output_dir,
        force=force,
    )
    click.echo(f"Report written to {output_path}")


def _runPhase2(ctx: click.Context, force: bool, reference_year: int | None) -> None:
    ctx.invoke(phase2_1, force=force)
    ctx.invoke(phase2_2, force=force, reference_year=reference_year)
    ctx.invoke(phase2_3, force=force)


@cli.command("run-phase2")
@click.option("--force", is_flag=True, help="Re-run all phase 2 steps.")
@click.option(
    "--reference-year",
    type=int,
    default=None,
    help="Anchor year for the 4-year window in phase 2.2 (defaults to current year).",
)
@click.pass_context
def run_phase2(ctx: click.Context, force: bool, reference_year: int | None) -> None:
    """Run phases 2.1, 2.2, and 2.3 using existing working/csv files."""
    _runPhase2(ctx, force=force, reference_year=reference_year)


@cli.command("run-all")
@click.option("--force", is_flag=True, help="Re-run all phases.")
@click.option(
    "--skip-phase1",
    is_flag=True,
    help="Skip phase 1 and use existing CSV files in working/csv/.",
)
@click.option(
    "--reference-year",
    type=int,
    default=None,
    help="Anchor year for the 4-year window in phase 2.2 (defaults to current year).",
)
@click.pass_context
def run_all(
    ctx: click.Context,
    force: bool,
    skip_phase1: bool,
    reference_year: int | None,
) -> None:
    """Run phases 1, 2.1, 2.2, and 2.3 in order. Does not run phase 0 (download)."""
    if not skip_phase1:
        ctx.invoke(phase1, force=force)
    _runPhase2(ctx, force=force, reference_year=reference_year)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
