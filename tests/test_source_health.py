# -*- coding: utf-8 -*-
"""The module source compiles cleanly, warnings included.

A JavaScript regex inside a Python f-string ("/\\D/g") is an invalid escape
sequence: today a SyntaxWarning, an error in a future Python, and the whole
website controller would stop loading.
"""
import os
import warnings

from odoo.tests.common import TransactionCase, tagged
from odoo.tools.misc import file_path


@tagged('post_install', '-at_install', 'vehicle_source')
class TestSourceHealth(TransactionCase):

    def test_python_files_compile_without_warnings(self):
        root = file_path('vehicle_rental')
        for folder, _dirs, files in os.walk(root):
            for name in files:
                if not name.endswith('.py'):
                    continue
                path = os.path.join(folder, name)
                with open(path, encoding='utf-8') as source, warnings.catch_warnings():
                    warnings.simplefilter('error')
                    try:
                        compile(source.read(), path, 'exec')
                    except SyntaxError as error:
                        self.fail(f'{os.path.relpath(path, root)}: {error.msg} (line {error.lineno})')
