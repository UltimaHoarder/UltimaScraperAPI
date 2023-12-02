# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os  # type: ignore
import sys  # type: ignore

# sys.path.insert(0, os.path.abspath('../..'))
project = "UltimaScraperAPI"
copyright = "2022, UltimaHoarder"
author = "UltimaHoarder"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "autoapi.extension",
    "sphinx_rtd_theme",
]

autoapi_type = "python"
autoapi_dirs = ["../../apis", "../../classes", "../../database", "../../helpers"]
autoapi_ignore = ["*database*"]
# autoapi_keep_files = True

autosummary_generate = True  # Turn on sphinx.ext.autosummary

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
