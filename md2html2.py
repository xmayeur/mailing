"""
https://github.com/trentm/python-markdown2?tab=readme-ov-file
"""

import markdown2

with open("input/page.md", "r") as f:
    data = f.read()
converter = markdown2.Markdown(extras=["tables", "header-ids", "cuddled-lists"])  # <-- here
html = converter.convert(data)


with open("input/page.html", "w") as f:
    f.write(html)
