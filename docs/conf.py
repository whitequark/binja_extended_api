#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os
import sphinx_rtd_theme
from mock import Mock as MagicMock

# Configure our load path
sys.path.insert(0, os.path.abspath('..'))

# Mock out C dependencies for readthedocs
class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
            return MagicMock()

MOCK_MODULES = ['PyQt5', 'PyQt5.QtCore']
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

# Configure Sphinx
extensions = ['sphinx.ext.autosummary', 'sphinx.ext.autodoc', 'sphinx.ext.viewcode']
templates_path = ['_templates']
autosummary_generate = True
source_suffix = '.rst'
master_doc = 'index'
project = 'Binary Ninja Extended API'
author = 'whitequark'
copyright = '2018, whitequark'
pygments_style = 'sphinx'
html_theme = 'sphinx_rtd_theme'
