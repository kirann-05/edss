"""Builds the final course project report (PDF) from docs/technical.

    cd backend && uv run --with markdown python ../scripts/build_report.py

Needs the web app's Playwright browser (pnpm install in frontend). Writes
docs/report/EDSS-Final-Report.pdf. Images are the UML PNGs under docs/technical/uml/png.
"""

import pathlib
import re
import subprocess
import tempfile

import markdown

ROOT = pathlib.Path(__file__).resolve().parent.parent
TECH = ROOT / "docs" / "technical"
OUT = ROOT / "docs" / "report"

TEAM = [
    ("Kiran Patil", "01FE24BCI407", "256"),
    ("Mohammed Mudassir", "01FE23BCI089", "263"),
    ("Sakshi Manvi", "01FE23BCI013", "162"),
    ("Nazreen Syed", "01FE23BCI026", "209"),
]
ORDER = [
    "README.md", "01-requirements.md", "02-design-principles.md", "03-architecture.md",
    "04-design-patterns.md", "05-api.md", "06-database.md", "07-detailed-design.md",
    "08-implementation.md", "09-tools.md", "10-testing.md", "11-traceability.md", "12-deployment.md",
]  # fmt: skip
CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font: 10.5pt/1.5 -apple-system, "Helvetica Neue", Arial, sans-serif; color: #111; }
h1 { font-size: 20pt; border-bottom: 2px solid #222; padding-bottom: 4px; page-break-before: always; }
h2 { font-size: 14pt; margin-top: 18px; } h3 { font-size: 11.5pt; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 8px 0; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th, td { border: 1px solid #999; padding: 3px 6px; text-align: left; vertical-align: top; }
th { background: #eee; }
code { font: 9pt Menlo, monospace; background: #f3f3f3; padding: 0 2px; }
pre { background: #f6f6f6; padding: 8px; overflow-wrap: anywhere; white-space: pre-wrap; font-size: 8.5pt; }
img { max-width: 100%; max-height: 220mm; }
.cover { text-align: center; padding-top: 70mm; } .cover h1 { border: 0; page-break-before: avoid; font-size: 28pt; }
.cover table { width: auto; margin: 24px auto; font-size: 11pt; }
"""


def body(name: str) -> str:
    text = (TECH / name).read_text()
    text = re.sub(r"\]\((?:\./)?([\w./-]+\.md)(#[\w-]+)?\)", r"](#\1)", text)  # no dead file links
    html = markdown.markdown(text, extensions=["tables", "fenced_code"])
    return html.replace('src="uml/', f'src="{TECH.as_uri()}/uml/').replace(
        'src="results/', f'src="{TECH.as_uri()}/results/'
    )


def main() -> None:
    rows = "".join(f"<tr><td>{n}</td><td>{u}</td><td>{r}</td><td>B</td></tr>" for n, u, r in TEAM)
    cover = (
        '<div class="cover"><h1>Executive Decision Support System</h1>'
        "<p><b>Final course project report</b><br>Agentic AI, KLE Technological University, VII Semester</p>"
        "<p><b>Team B1 (VII Sem) EDSS</b></p>"
        f"<table><tr><th>Name</th><th>USN</th><th>Roll no.</th><th>Division</th></tr>{rows}</table>"
        "<p>Worklet 15, Chapter 15 of the Agentic AI build book<br>Repository: Team B1 (VII Sem) EDSS</p></div>"
    )
    parts = [body(name) for name in ORDER if (TECH / name).exists()]
    html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{cover}{''.join(parts)}</body></html>"
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        page = pathlib.Path(tmp) / "report.html"
        page.write_text(html)
        script = pathlib.Path(tmp) / "pdf.mjs"
        pdf = OUT / "EDSS-Final-Report.pdf"
        script.write_text(
            f"import {{ chromium }} from '{(ROOT / 'frontend/node_modules/@playwright/test/index.mjs').as_uri()}';"
            "const b = await chromium.launch(); const p = await b.newPage();"
            f"await p.goto('{page.as_uri()}'); await p.waitForLoadState('load');"
            f"await p.pdf({{ path: '{pdf}', format: 'A4', printBackground: true, displayHeaderFooter: true,"
            " headerTemplate: '<span></span>', footerTemplate: '<div style=\"font-size:8px;width:100%;text-align:center\">"
            'Team B1 (VII Sem) EDSS &nbsp; <span class="pageNumber"></span></div>\','
            " margin: { top: '18mm', bottom: '18mm', left: '16mm', right: '16mm' } });"
            "await b.close();"
        )
        subprocess.run(["node", str(script)], check=True, cwd=ROOT / "frontend")
    print(f"wrote {OUT / 'EDSS-Final-Report.pdf'}")


if __name__ == "__main__":
    main()
