"""Pandoc Export Pipeline

Features:
- Multi-format export (PDF, DOCX, LaTeX, HTML, ODT, EPUB)
- Journal template support (JAMA, NEJM, Lancet, etc.)
- Citation style application (CSL)
- Figure/table embedding
- PHI redaction in exports

This module is designed to be used by the worker service to convert markdown
manuscripts into a variety of publication-ready formats using Pandoc.

Design goals:
- Safe subprocess execution (no shell=True)
- Explicit temp directories and deterministic file handling
- Support for journal LaTeX templates and CSL citation styles
- Optional bibliography and metadata support
- Simple figure/table embedding helpers
- PHI redaction helper (regex-based)

Notes:
- PDF export typically requires a TeX engine (e.g., xelatex) available in the
  runtime image.
- Citation processing uses pandoc's built-in citeproc (Pandoc >= 2.11).
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Sequence, Tuple, Union

logger = logging.getLogger(__name__)


class PandocExportError(RuntimeError):
    """Raised when pandoc export fails."""


@dataclass
class PandocRunResult:
    args: List[str]
    returncode: int
    stdout: str
    stderr: str


class PandocExporter:
    """Export markdown content into multiple formats using Pandoc."""

    SUPPORTED_FORMATS = ["pdf", "docx", "latex", "html", "odt", "epub"]

    # Template map uses filenames within templates_dir.
    JOURNAL_TEMPLATES = {
        "jama": "jama.latex",
        "nejm": "nejm.latex",
        "lancet": "lancet.latex",
        "nature": "nature.latex",
        "plos": "plos.latex",
    }

    # Conservative default PHI patterns (can be overridden by caller).
    DEFAULT_PHI_PATTERNS = [
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",  # phone
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",  # email
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",  # dates (basic)
        r"\bMRN[:\s]*\d{6,12}\b",  # MRN-like
    ]

    def __init__(self, pandoc_path: str = "pandoc"):
        self.pandoc = pandoc_path
        self.templates_dir = Path(__file__).parent / "templates"

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def export(
        self,
        content: str,
        output_format: str,
        template: Optional[str] = None,
        csl_style: Optional[str] = None,
        bibliography: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Export markdown to the target format.

        Args:
            content: Markdown content.
            output_format: One of SUPPORTED_FORMATS.
            template: Optional journal template key (e.g., 'jama') or a filesystem
                path to a template file.
            csl_style: Optional CSL file path.
            bibliography: Optional bibliography file path (BibTeX, CSL JSON, etc.).
            metadata: Optional pandoc metadata dict.

        Returns:
            Bytes of the exported artifact.

        Raises:
            PandocExportError: On invalid args, missing pandoc, or pandoc failure.
        """

        fmt = (output_format or "").strip().lower()
        if fmt not in self.SUPPORTED_FORMATS:
            raise PandocExportError(
                f"Unsupported format '{output_format}'. Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        if not self.validate_pandoc_available():
            raise PandocExportError(
                "Pandoc is not available. Ensure 'pandoc' is installed and on PATH (or provide pandoc_path)."
            )

        # Prepare temp workspace
        with tempfile.TemporaryDirectory(prefix="pandoc_export_") as tmpdir:
            tmp = Path(tmpdir)
            input_md = tmp / "input.md"
            output_file = tmp / f"output.{self._default_ext_for_format(fmt)}"

            input_md.write_text(content or "", encoding="utf-8")

            # Metadata (optional)
            metadata_file: Optional[Path] = None
            if metadata:
                metadata_file = tmp / "metadata.json"
                metadata_file.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

            # Resolve template
            template_path = self._resolve_template_path(fmt, template)

            # Resolve CSL/Bibliography
            csl_path = self._resolve_optional_path(csl_style)
            bib_path = self._resolve_optional_path(bibliography)

            args = self._build_pandoc_args(
                input_path=input_md,
                output_path=output_file,
                output_format=fmt,
                template_path=template_path,
                csl_path=csl_path,
                bibliography_path=bib_path,
                metadata_json_path=metadata_file,
            )

            result = self._run_pandoc(args=args, cwd=tmp)
            if result.returncode != 0:
                raise PandocExportError(self._format_pandoc_error(result))

            if not output_file.exists():
                raise PandocExportError("Pandoc reported success but output file was not created.")

            return output_file.read_bytes()

    def embed_figures(self, content: str, figures: List[Dict[str, Any]]) -> str:
        """Embed figure references into markdown.

        Expects figure dicts with optional keys:
            - id: unique id
            - caption: caption text
            - path or url: image source
            - alt: alt text

        Strategy:
            - If content contains placeholder like [[FIGURE:id]], replace with a
              Pandoc-compatible image block.
            - Otherwise, append a Figures section at the end.
        """

        md = content or ""
        if not figures:
            return md

        def figure_md(fig: Dict[str, Any]) -> str:
            src = str(fig.get("path") or fig.get("url") or "").strip()
            caption = str(fig.get("caption") or "").strip()
            alt = str(fig.get("alt") or caption or "Figure").strip() or "Figure"
            if not src:
                # If no source, fall back to caption-only.
                return f"**Figure.** {caption}" if caption else "**Figure.**"
            # Pandoc markdown: ![alt](src){#fig:id}
            fig_id = str(fig.get("id") or "").strip()
            id_attr = f"{{#fig:{fig_id}}}" if fig_id else ""
            cap_suffix = f"\n\n*{caption}*" if caption else ""
            return f"![{alt}]({src}){id_attr}{cap_suffix}"

        replaced_any = False
        for fig in figures:
            fig_id = str(fig.get("id") or "").strip()
            if not fig_id:
                continue
            placeholder = f"[[FIGURE:{fig_id}]]"
            if placeholder in md:
                md = md.replace(placeholder, figure_md(fig))
                replaced_any = True

        if replaced_any:
            return md

        # Append section if no placeholders
        blocks = ["\n\n## Figures\n"]
        for idx, fig in enumerate(figures, start=1):
            blocks.append(f"\n### Figure {idx}\n\n{figure_md(fig)}\n")
        return md + "".join(blocks)

    def embed_tables(self, content: str, tables: List[Dict[str, Any]]) -> str:
        """Embed table data into markdown.

        Expects table dicts with keys:
            - id (optional)
            - caption (optional)
            - headers: List[str] (optional)
            - rows: List[List[Any]] (optional)

        Strategy:
            - Replace placeholder [[TABLE:id]] with a GitHub-style markdown table.
            - Otherwise append Tables section.
        """

        md = content or ""
        if not tables:
            return md

        def to_str(x: Any) -> str:
            if x is None:
                return ""
            return str(x)

        def table_md(tbl: Dict[str, Any]) -> str:
            caption = to_str(tbl.get("caption") or "").strip()
            headers = tbl.get("headers") or []
            rows = tbl.get("rows") or []

            # Normalize
            headers = [to_str(h) for h in headers]
            rows = [[to_str(c) for c in (r or [])] for r in rows]

            # If headers missing, infer from first row length
            if not headers:
                width = max((len(r) for r in rows), default=0)
                headers = [f"Col {i+1}" for i in range(width)]

            # Pad rows to header width
            width = len(headers)
            norm_rows: List[List[str]] = []
            for r in rows:
                r2 = (r + [""] * width)[:width]
                norm_rows.append(r2)

            # Build markdown table
            header_line = "| " + " | ".join(headers) + " |"
            sep_line = "| " + " | ".join(["---"] * width) + " |"
            row_lines = ["| " + " | ".join(r) + " |" for r in norm_rows]

            cap_line = f"\n\n*{caption}*\n" if caption else "\n"
            return "\n".join([header_line, sep_line, *row_lines]) + cap_line

        replaced_any = False
        for tbl in tables:
            tbl_id = str(tbl.get("id") or "").strip()
            if not tbl_id:
                continue
            placeholder = f"[[TABLE:{tbl_id}]]"
            if placeholder in md:
                md = md.replace(placeholder, table_md(tbl))
                replaced_any = True

        if replaced_any:
            return md

        blocks = ["\n\n## Tables\n"]
        for idx, tbl in enumerate(tables, start=1):
            blocks.append(f"\n### Table {idx}\n\n{table_md(tbl)}\n")
        return md + "".join(blocks)

    def apply_phi_redaction(self, content: str, phi_patterns: List[str]) -> str:
        """Redact PHI before export using regex patterns.

        Patterns are treated as regexes. Replacement uses a fixed token.

        Tips:
            - Provide specific patterns to reduce false positives.
            - Consider doing structured PHI detection upstream.
        """

        text = content or ""
        patterns = phi_patterns or []
        if not patterns:
            patterns = list(self.DEFAULT_PHI_PATTERNS)

        redacted = text
        for pat in patterns:
            try:
                redacted = re.sub(pat, "[REDACTED]", redacted, flags=re.IGNORECASE)
            except re.error as e:
                logger.warning("Invalid PHI regex pattern '%s': %s", pat, e)
                continue
        return redacted

    def validate_pandoc_available(self) -> bool:
        """Check if pandoc is installed and accessible."""

        try:
            proc = subprocess.run(
                [self.pandoc, "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode != 0:
                logger.warning("Pandoc not available: %s", (proc.stderr or proc.stdout).strip())
                return False
            return True
        except FileNotFoundError:
            logger.warning("Pandoc binary not found at '%s'", self.pandoc)
            return False
        except Exception as e:  # pragma: no cover
            logger.warning("Pandoc availability check failed: %s", e)
            return False

    # -------------------------------------------------------------------------
    # Internals
    # -------------------------------------------------------------------------

    def _default_ext_for_format(self, fmt: str) -> str:
        if fmt == "latex":
            return "tex"
        return fmt

    def _resolve_optional_path(self, p: Optional[str]) -> Optional[Path]:
        if not p:
            return None
        path = Path(p)
        if path.exists():
            return path
        # Allow relative paths from templates_dir and CWD.
        cand = (self.templates_dir / p)
        if cand.exists():
            return cand
        raise PandocExportError(f"File not found: {p}")

    def _resolve_template_path(self, fmt: str, template: Optional[str]) -> Optional[Path]:
        if not template:
            return None

        t = template.strip()

        # If a known journal key
        key = t.lower()
        if key in self.JOURNAL_TEMPLATES:
            filename = self.JOURNAL_TEMPLATES[key]
            path = self.templates_dir / filename
            if not path.exists():
                raise PandocExportError(
                    f"Journal template '{key}' was requested but not found at {path}."
                )
            return path

        # Otherwise treat as path
        path = Path(t)
        if path.exists():
            return path
        cand = self.templates_dir / t
        if cand.exists():
            return cand

        raise PandocExportError(f"Template not found: {template}")

    def _build_pandoc_args(
        self,
        input_path: Path,
        output_path: Path,
        output_format: str,
        template_path: Optional[Path],
        csl_path: Optional[Path],
        bibliography_path: Optional[Path],
        metadata_json_path: Optional[Path],
    ) -> List[str]:
        args: List[str] = [
            self.pandoc,
            str(input_path),
            "-f",
            "markdown",
            "-t",
            output_format,
            "-o",
            str(output_path),
            "--standalone",
        ]

        # Enable citeproc if CSL or bibliography provided.
        if csl_path or bibliography_path:
            args.append("--citeproc")

        if csl_path:
            args.extend(["--csl", str(csl_path)])

        if bibliography_path:
            args.extend(["--bibliography", str(bibliography_path)])

        # Use journal template for LaTeX/PDF when provided.
        if template_path:
            # Pandoc supports --template for a variety of formats
            args.extend(["--template", str(template_path)])

        # If metadata JSON provided, pass as metadata-file.
        if metadata_json_path:
            # Pandoc supports YAML/JSON metadata files.
            args.extend(["--metadata-file", str(metadata_json_path)])

        # PDF-specific niceties
        if output_format == "pdf":
            # Prefer xelatex for better unicode support if present in image.
            args.extend(["--pdf-engine", os.environ.get("PANDOC_PDF_ENGINE", "xelatex")])

        # HTML-specific: self-contained can be heavy; keep optional via env.
        if output_format == "html" and os.environ.get("PANDOC_HTML_SELF_CONTAINED") == "1":
            args.append("--self-contained")

        return args

    def _run_pandoc(self, args: Sequence[str], cwd: Optional[Path] = None) -> PandocRunResult:
        logger.info("Running pandoc: %s", " ".join(map(self._safe_arg_for_log, args)))

        proc = subprocess.run(
            list(args),
            cwd=str(cwd) if cwd else None,
            check=False,
            capture_output=True,
            text=True,
            timeout=int(os.environ.get("PANDOC_TIMEOUT_SECONDS", "120")),
        )

        return PandocRunResult(
            args=list(args),
            returncode=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )

    def _format_pandoc_error(self, result: PandocRunResult) -> str:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        lines = ["Pandoc export failed."]
        lines.append(f"Return code: {result.returncode}")
        if stderr:
            lines.append("stderr:")
            lines.append(stderr)
        if stdout:
            lines.append("stdout:")
            lines.append(stdout)
        return "\n".join(lines)

    def _safe_arg_for_log(self, arg: str) -> str:
        # Avoid logging extremely long strings; args are typically paths.
        if len(arg) > 300:
            return arg[:140] + "…" + arg[-140:]
        return arg


# -----------------------------------------------------------------------------
# Backwards-compatible helper (optional)
# -----------------------------------------------------------------------------


def export_with_pandoc(
    markdown: str,
    output_format: str,
    template: Optional[str] = None,
    csl_style: Optional[str] = None,
    bibliography: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    pandoc_path: str = "pandoc",
) -> bytes:
    """Convenience function for one-off exports."""

    exporter = PandocExporter(pandoc_path=pandoc_path)
    return exporter.export(
        content=markdown,
        output_format=output_format,
        template=template,
        csl_style=csl_style,
        bibliography=bibliography,
        metadata=metadata,
    )
