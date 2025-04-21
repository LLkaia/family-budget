import sys
from pathlib import Path


sys.path.insert(0, str(Path("..", "app").resolve()))


project = "Family budget"
copyright = "2025, Illia Kaialainien"
author = "Illia Kaialainien"
release = "0.0.1"

extensions = ["sphinx.ext.viewcode", "sphinx.ext.todo", "sphinx.ext.autodoc", "sphinx_autodoc_typehints", "myst_parser"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["static"]
