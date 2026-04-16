from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Genera notebooks y HTML ENAHO Exposure por año.")
    parser.add_argument("--project-root", type=Path, default=project_root)
    parser.add_argument("--start-year", type=int, default=2019)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--skip-execute", action="store_true")
    parser.add_argument("--skip-html", action="store_true")
    return parser.parse_args()


def run(cmd: list[str], cwd: Path) -> None:
    print(">", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def resolve_existing_path(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    workspace_root = project_root.parent
    presentation_root = project_root.parent if project_root.name == "_interno" else project_root
    generator = project_root / "scripts" / "build_enaho_exposure_notebook.py"
    notebooks_dir = presentation_root / "notebooks"
    html_dir = project_root / "notebooks_html"
    base_dir = resolve_existing_path(
        project_root / "bases" / "intermedias" / "enaho_complete_years",
        project_root / "data" / "intermediate" / "enaho_complete_years",
    )

    notebooks_dir.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)

    for year in range(args.start_year, args.end_year + 1):
        base_csv = base_dir / f"ENAHO_complete_{year}.csv"
        notebook_path = notebooks_dir / f"ia_empleo_peru_{year}.ipynb"

        run(
            [
                "python",
                str(generator),
                "--project-root",
                str(project_root),
                "--base-csv",
                str(base_csv),
                "--year",
                str(year),
                "--output",
                str(notebook_path),
            ],
            cwd=workspace_root,
        )

        if not args.skip_execute:
            run(
                [
                    "jupyter",
                    "nbconvert",
                    "--to",
                    "notebook",
                    "--execute",
                    "--inplace",
                    str(notebook_path),
                ],
                cwd=workspace_root,
            )

        if not args.skip_html:
            run(
                [
                    "jupyter",
                    "nbconvert",
                    "--to",
                    "html",
                    "--output-dir",
                    str(html_dir),
                    str(notebook_path),
                ],
                cwd=workspace_root,
            )


if __name__ == "__main__":
    main()
