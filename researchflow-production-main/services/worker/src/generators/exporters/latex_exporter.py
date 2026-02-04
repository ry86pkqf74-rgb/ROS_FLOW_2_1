"""LaTeX exporter using a small Jinja2 template."""

from __future__ import annotations

from ..imrad_assembler import ManuscriptBundle


class LatexExporter:
    format: str = "latex"

    def export(self, bundle: ManuscriptBundle) -> str:
        try:
            from jinja2 import Template
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"jinja2 not available: {e}")

        tpl = Template(
            r"""\\documentclass[11pt]{article}
\\usepackage[margin=1in]{geometry}
\\usepackage{hyperref}
\\title{{{{ title }}}}
\\date{}
\\begin{document}
\\maketitle

\\section*{{{{ abstract_heading }}}}
{{{{ abstract }}}}

\\section*{{{{ methods_heading }}}}
{{{{ methods }}}}

\\section*{{{{ results_heading }}}}
{{{{ results }}}}

\\section*{{{{ discussion_heading }}}}
{{{{ discussion }}}}

\\section*{{{{ references_heading }}}}
{{{{ references }}}}

\\end{document}
"""
        )

        def sec(key: str) -> str:
            s = bundle.sections.get(key)  # type: ignore[arg-type]
            return (s.text if s else "") or ""

        def head(key: str) -> str:
            s = bundle.sections.get(key)  # type: ignore[arg-type]
            return (s.heading if s and s.heading else key.capitalize())

        return tpl.render(
            title=bundle.title,
            abstract_heading=head("abstract"),
            abstract=sec("abstract"),
            methods_heading=head("methods"),
            methods=sec("methods"),
            results_heading=head("results"),
            results=sec("results"),
            discussion_heading=head("discussion"),
            discussion=sec("discussion"),
            references_heading=head("references"),
            references=sec("references"),
        )
