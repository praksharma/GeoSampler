"""Launch file classification and main's use of the normal document loaders."""
from contextlib import ExitStack, redirect_stderr
import io
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from jorvik import app
from jorvik.cli import launch_document
from jorvik.project import create_empty_project


class CliTest(unittest.TestCase):
    def run_main(self, path, error=None):
        with ExitStack() as stack:
            stack.enter_context(patch('sys.argv', ['jorvik', str(path)]))
            for name in ('configure_graphics', 'configure_theme', 'install_window_controls', 'QSettings'):
                stack.enter_context(patch('jorvik.app.' + name))
            stack.enter_context(patch('jorvik.shutdown.SignalShutdown'))
            application = stack.enter_context(patch('jorvik.app.QApplication')).return_value
            application.exec.return_value = 0
            window = stack.enter_context(patch('jorvik.app.MainWindow')).return_value
            window.load_project_file.side_effect = error
            stderr = io.StringIO()
            with redirect_stderr(stderr), self.assertRaises(SystemExit) as exit:
                app.main()
            return exit.exception.code, window, application, stderr.getvalue()

    def test_project_and_geometry_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            for extension in ('.jorvik', '.JORVIK', '.gsproj', '.GSPROJ'):
                project = create_empty_project(Path(directory) / ('space in name' + extension))
                code, window, application, _ = self.run_main(project)
                self.assertEqual(code, 0)
                window.load_project_file.assert_called_once_with(project.resolve(), raise_errors=True)
                window.load_geometry.assert_not_called()
                application.exec.assert_called_once()
            for extension in ('geo', 'step', 'stp', 'brep', 'iges', 'igs'):
                path = Path(directory) / ('model.' + extension); path.touch()
                self.assertEqual(launch_document(path), ('geometry', path.resolve()))
                code, window, _, _ = self.run_main(path)
                self.assertEqual(code, 0)
                self.assertEqual(window.load_geometry.call_args.args, (path.resolve(),))
                self.assertTrue(callable(window.load_geometry.call_args.kwargs['on_error']))
                window.load_project_file.assert_not_called()

    def test_failures_are_nonzero_and_preserve_files(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, contents, message in [('missing.jorvik', None, 'does not exist'),
                                             ('unsupported.stl', b'original', 'Unsupported file'),
                                             ('corrupt.jorvik', b'invalid zip', 'Could not open project')]:
                path = Path(directory) / name
                if contents is not None: path.write_bytes(contents)
                if name == 'corrupt.jorvik':
                    from jorvik.project import load_project
                    try: load_project(path)
                    except Exception as error: load_error = error
                    code, window, application, stderr = self.run_main(path, load_error)
                    application.exec.assert_not_called()
                    window.close.assert_called_once()
                else:
                    code, window, _, stderr = self.run_main(path)
                    window.load_geometry.assert_not_called()
                    window.load_project_file.assert_not_called()
                self.assertNotEqual(code, 0)
                self.assertIn(message, stderr)
                if contents is not None: self.assertEqual(path.read_bytes(), contents)
                else: self.assertFalse(path.exists())


class CliProcessTest(unittest.TestCase):
    def test_real_launch_projects_and_failures(self):
        from jorvik.geometry import load_geometry
        from jorvik.project import save_project
        from test_project import FIXTURE, state
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            environment = dict(os.environ, XDG_CONFIG_HOME=str(directory / 'config'),
                               XDG_CACHE_HOME=str(directory / 'cache'), XDG_DATA_HOME=str(directory / 'data'))
            empty = create_empty_project(directory / 'empty.jorvik')
            populated = directory / 'populated.jorvik'
            saved_state = state(); saved_state['selected_area'] = None
            save_project(populated, load_geometry(FIXTURE), [], saved_state)
            # Exercise the real entry point and normal loader; only schedule an
            # automatic close so the process test does not require human input.
            code = """import json,sys
from PySide6.QtCore import QTimer
from jorvik import app
original = app.MainWindow.load_project_file
def loaded(window, filename, **kwargs):
    result = original(window, filename, **kwargs)
    print(json.dumps({'path': str(window.project_path), 'empty': window.geometry is None}), flush=True)
    QTimer.singleShot(100, window.close)
    return result
app.MainWindow.load_project_file = loaded
app.main()
"""
            legacy_empty = directory / 'empty.gsproj'; legacy_empty.write_bytes(empty.read_bytes())
            legacy_populated = directory / 'populated.gsproj'; legacy_populated.write_bytes(populated.read_bytes())
            for path, is_empty in [(empty, True), (populated, False),
                                   (legacy_empty, True), (legacy_populated, False)]:
                before = path.read_bytes()
                result = subprocess.run([sys.executable, '-c', code, '--software-rendering', str(path)],
                                        env=environment, capture_output=True, text=True, timeout=25)
                self.assertEqual(result.returncode, 0, result.stderr)
                record = json.loads(result.stdout.strip().splitlines()[-1])
                self.assertEqual(record, {'path': str(path), 'empty': is_empty})
                self.assertEqual(path.read_bytes(), before)
            for name, contents, message in [('missing.jorvik', None, 'does not exist'),
                                             ('bad.jorvik', b'not a zip', 'Could not open project'),
                                             ('bad.step', b'not CAD', 'Could not open geometry'),
                                             ('bad.stl', b'not supported', 'Unsupported file')]:
                path = directory / name
                if contents is not None: path.write_bytes(contents)
                result = subprocess.run([sys.executable, '-m', 'jorvik', '--software-rendering', str(path)],
                                        env=environment, capture_output=True, text=True, timeout=25)
                self.assertNotEqual(result.returncode, 0, result.stderr)
                self.assertIn(message, result.stderr)
                if contents is not None: self.assertEqual(path.read_bytes(), contents)
                else: self.assertFalse(path.exists())
