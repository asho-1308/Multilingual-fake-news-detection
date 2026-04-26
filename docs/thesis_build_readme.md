Thesis build instructions

This folder contains a LaTeX draft for the Tamil fake-news classification thesis.

Build PDF (requires a LaTeX toolchain such as TeX Live or MikTeX):

```bash
cd docs
pdflatex tamil_thesis.tex
pdflatex tamil_thesis.tex
```

If you prefer to convert to PDF from Markdown, you can copy contents into a Markdown document and use pandoc.

Notes:
- The draft uses repository artifacts and placeholders for dataset statistics and evaluation metrics. Replace placeholders with evaluated numbers after running training or evaluation.
