import difflib
import logging
import sys
from collections.abc import Iterable
from pathlib import Path

import click

from lktk.formatter import fmt
from lktk.logger import logger


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    default="WARNING",
)
def run(log_level: str) -> None:
    level = getattr(logging, log_level)
    logging.basicConfig(level=level)


@click.command()
@click.option(
    "--check",
    is_flag=True,
    help="Don't update files. Instead, exit with status code 1 if any file should be modefied.",  # noqa: #501
)
@click.argument("file", type=click.Path(exists=True, path_type=Path), nargs=-1)
def format(check: bool, file: list[Path]) -> None:
    """Format LookML file(s).

    FILE is the LookML file(s) to format (directory is also OK).
    Files which does not end with `.lkml` will be ignored.
    """
    modified: list[bool] = []

    for f in filter_lkml(file):
        logger.debug(f"formatting {f}")
        before = f.read_text()
        after = fmt(before)

        if before != after:
            click.echo(f"{f} is modified")
            modified.append(True)
        else:
            click.echo(f"{f} is skipped")
            modified.append(False)

        if check:
            print_diff(before, after)
        else:
            f.write_text(after)

    # https://stackoverflow.com/questions/12765833/counting-the-number-of-true-booleans-in-a-python-list
    n_modified = modified.count(True)
    n_skipped = len(modified) - n_modified
    click.echo(f"{n_modified} files are modified, {n_skipped} files are skipped.")

    if n_modified > 0 and check:
        sys.exit(1)


run.add_command(format)


# TODO ignore files listed in .gitignore
def filter_lkml(files: Iterable[Path]) -> Iterable[Path]:
    res = []

    for f in files:
        if f.is_dir():
            for child in filter_lkml(f.iterdir()):
                res.append(child)
        elif f.suffix == ".lkml":  # foo.view.lkml is ok
            res.append(f)

    return res


def print_diff(a: str, b: str) -> None:
    diffs = difflib.unified_diff(a.splitlines(), b.splitlines())

    # skip --- filename +++ filename
    for _ in range(2):
        next(diffs)

    for d in diffs:
        fg = None
        if len(d) == 0:
            pass
        elif d[0] == "+":
            fg = "green"
        elif d[0] == "-":
            fg = "red"
        click.echo(click.style(d, fg=fg))
