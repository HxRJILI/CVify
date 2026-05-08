import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


def _copy_photo_assets(latex_source: str, destination_dir: Path):
    source_match = re.search(r"^%\s*CVIFY_PHOTO_SOURCE:\s*(.+)$", latex_source, re.MULTILINE)
    target_match = re.search(r"^%\s*CVIFY_PHOTO_TARGET:\s*(.+)$", latex_source, re.MULTILINE)
    if not source_match or not target_match:
        return

    source_path = Path(source_match.group(1).strip())
    target_name = Path(target_match.group(1).strip()).name
    if not source_path.exists() or not target_name:
        return

    destination_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_dir / target_name)


def _find_pdflatex() -> str:
    pdflatex_path = shutil.which("pdflatex")
    if pdflatex_path:
        return pdflatex_path

    local_appdata = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", "")

    candidates = [
        Path(local_appdata) / "Programs/MiKTeX/miktex/bin/x64/pdflatex.exe",
        Path(local_appdata) / "Programs/MiKTeX/miktex/bin/pdflatex.exe",
        Path(program_files) / "MiKTeX/miktex/bin/x64/pdflatex.exe",
        Path(program_files) / "MiKTeX/miktex/bin/pdflatex.exe",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return str(candidate)
    return ""


def compile_latex_to_pdf(latex_source: str, job_title: str = "Job") -> str:
    """Compile LaTeX to PDF, or return the .tex path if compilation is unavailable."""
    documents_dir = Path(os.path.expanduser("~/Documents/CVify"))
    documents_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in job_title if c.isalnum() or c in " _-").strip().replace(" ", "_")
    output_filename = f"CVify_{safe_title}_{timestamp}"

    final_tex_path = documents_dir / f"{output_filename}.tex"
    final_pdf_path = documents_dir / f"{output_filename}.pdf"

    final_tex_path.write_text(latex_source, encoding="utf-8")
    _copy_photo_assets(latex_source, documents_dir)

    pdflatex_cmd = _find_pdflatex()
    if not pdflatex_cmd:
        return str(final_tex_path)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        temp_tex_path = temp_dir_path / "cv.tex"
        temp_tex_path.write_text(latex_source, encoding="utf-8")
        _copy_photo_assets(latex_source, temp_dir_path)

        try:
            for _ in range(2):
                subprocess.run(
                    [pdflatex_cmd, "-interaction=nonstopmode", "cv.tex"],
                    cwd=temp_dir,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

            temp_pdf_path = temp_dir_path / "cv.pdf"
            if temp_pdf_path.exists():
                shutil.copy2(temp_pdf_path, final_pdf_path)
                return str(final_pdf_path)
            return str(final_tex_path)
        except subprocess.CalledProcessError as e:
            error_log = e.stdout.decode("utf-8", errors="ignore") + "\n" + e.stderr.decode("utf-8", errors="ignore")
            temp_pdf_path = temp_dir_path / "cv.pdf"
            if temp_pdf_path.exists():
                shutil.copy2(temp_pdf_path, final_pdf_path)
                print("LaTeX reported a non-zero exit code, but a PDF was generated. Returning PDF.")
                return str(final_pdf_path)
            print(f"LaTeX compilation failed due to syntax errors.\nCompiler Log snippet: {error_log[-500:]}")
            return str(final_tex_path)
