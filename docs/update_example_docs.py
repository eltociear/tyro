"""Helper script for updating the auto-generated examples pages in the documentation."""

from __future__ import annotations

import dataclasses
import pathlib
import shlex
import shutil
from typing import Iterable

import m2r2

import tyro


@dataclasses.dataclass
class ExampleMetadata:
    index: str
    index_with_zero: str
    source: str
    title: str
    usages: Iterable[str]
    description: str

    @staticmethod
    def from_path(path: pathlib.Path) -> ExampleMetadata:
        # 01_functions -> 01, _, functions.
        index, _, title = path.stem.partition("_")

        # 01 -> 1.
        index_with_zero = index
        index = str(int(index))

        # functions -> Functions.
        title = title.replace("_", " ").title()

        source = path.read_text().strip()

        docstring = source.split('"""')[1].strip()
        assert "Usage:" in docstring
        description, _, usage_text = docstring.partition("Usage:")
        example_usages = map(
            lambda x: x[1:-1],
            filter(
                lambda line: line.startswith("`") and line.endswith("`"),
                usage_text.split("\n"),
            ),
        )
        return ExampleMetadata(
            index=index,
            index_with_zero=index_with_zero,
            source=source[3:].partition('"""')[2].strip(),
            title=title,
            usages=example_usages,
            description=description,
        )


def get_example_paths(examples_dir: pathlib.Path) -> Iterable[pathlib.Path]:
    return filter(
        lambda p: not p.name.startswith("_"), sorted(examples_dir.glob("*.py"))
    )


REPO_ROOT = pathlib.Path(__file__).absolute().parent.parent


def main(
    examples_dir: pathlib.Path = REPO_ROOT / "examples",
    sphinx_source_dir: pathlib.Path = REPO_ROOT / "docs" / "source",
) -> None:
    example_doc_dir = sphinx_source_dir / "examples"
    shutil.rmtree(example_doc_dir)
    example_doc_dir.mkdir()

    for path in get_example_paths(examples_dir):
        ex = ExampleMetadata.from_path(path)
        path_for_sphinx = pathlib.Path("..") / ".." / path.relative_to(REPO_ROOT)

        usage_lines = []
        for usage in ex.usages:
            args = shlex.split(usage)
            python_index = args.index("python")
            sphinx_usage = shlex.join(
                args[:python_index]
                + ["python", path_for_sphinx.as_posix()]
                + args[python_index + 2 :]
            )

            # Note that :kbd: in Sphinx does unnecessary stuff we want to avoid, see:
            # https://github.com/sphinx-doc/sphinx/issues/7530
            #
            # Instead, we just use raw HTML.
            assert "../../examples/" in sphinx_usage
            command = sphinx_usage.replace("../../examples/", "")
            usage_lines += [
                "------------",
                "",
                ".. raw:: html",
                "",
                f"        <kbd>{command}</kbd>",
                "",
                f".. program-output:: {sphinx_usage}",
                "",
            ]

        (
            example_doc_dir
            / f"{ex.index_with_zero}_{ex.title.lower().replace(' ', '_')}.rst"
        ).write_text(
            "\n".join(
                [
                    (
                        ".. Comment: this file is automatically generated by"
                        " `update_example_docs.py`."
                    ),
                    "   It should not be modified manually.",
                    "",
                    f"{ex.index}. {ex.title}",
                    "==========================================",
                    "",
                    m2r2.convert(ex.description),
                    "",
                    "",
                    ".. code-block:: python",
                    "        :linenos:",
                    "",
                    "",
                    "\n".join(
                        f"        {line}".rstrip() for line in ex.source.split("\n")
                    ),
                    "",
                ]
                + usage_lines
            )
        )


if __name__ == "__main__":
    tyro.cli(main, description=__doc__)
