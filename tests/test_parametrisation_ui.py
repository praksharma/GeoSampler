"""Real-renderer checks for explicit translation edits and reset lifecycle."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
import numpy as np

from geosampler.app import MainWindow
import test_shell

FIXTURE = Path(__file__).resolve().parents[1] / 'examples/geometries/cad/cylinder.brep'


class ParametrisationUiTest(unittest.TestCase):
    setUpClass = classmethod(test_shell.ShellTest.setUpClass.__func__)
    wait_for = test_shell.ShellTest.wait_for
    javascript = test_shell.ShellTest.javascript

    def diagnostics(self, window):
        return json.loads(self.javascript(window, 'JSON.stringify(window.geoViewer.diagnostics())'))

    def test_reset_edits_and_close_preserve_originals(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
            window = MainWindow(settings)
            window.show()
            try:
                self.wait_for(lambda: window.view.is_ready)
                window.load_geometry(FIXTURE)
                self.wait_for(lambda: window.import_process is None)
                self.assertIsNotNone(window.geometry)
                window.pick_entity(2, 1, False)
                window.sampling.count.setValue(16)
                window.sampling.label.setText('wall')
                window.sampling.start()
                self.wait_for(lambda: window.sampling.process is None)
                self.assertEqual(len(window.sampling.batches), 1)
                other = deepcopy(window.sampling.batches[0])
                other['label'] = 'other'
                other['colour'] = '#ffc857'
                window.sampling.batches.append(other)
                window.sampled_areas.set_area(other)
                window.sampled_areas.items['other'].setCheckState(0, Qt.CheckState.Unchecked)
                window.hide_faces([2])
                window.sampling.refresh_preview()
                self.wait_for(lambda: self.diagnostics(window)['sampleCount'] == 32)
                original_geometry = deepcopy(window.geometry)
                original_batches = deepcopy(window.sampling.batches)
                original_visibility = deepcopy(window.view.geometry_visibility)
                baseline = self.diagnostics(window)
                original_selection = window.selection.copy()

                for dismiss in ('close', 'escape'):
                    with self.subTest(dismiss=dismiss):
                        window.open_parametrisation()
                        dialog = window.parametrisation_dialog
                        with patch.object(window.sampling, 'start') as generate, patch(
                            'geosampler.parametrisation_panel.export_configuration'
                        ) as export:
                            dialog.offsets[0].setValue(2)
                            self.assertIn('Parameters changed', dialog.status.text())
                            self.assertIsNone(window.view.translation_preview)
                            dialog.preview()
                            self.wait_for(lambda: self.diagnostics(window)['geometryOffset'] == [2, 0, 0])
                            dialog.offsets[0].setValue(3)
                            dialog.scope.setCurrentIndex(dialog.scope.findData('regions'))
                            for i in range(dialog.regions.count()):
                                item = dialog.regions.item(i)
                                item.setCheckState(Qt.CheckState.Checked if item.text() == 'wall' else Qt.CheckState.Unchecked)
                            self.assertIn('previous preview', dialog.status.text())
                            self.assertEqual(self.diagnostics(window)['geometryOffset'], [2, 0, 0])
                            dialog.preview()
                            dialog.preview()
                            self.wait_for(lambda: self.diagnostics(window)['sampleOffsets']['wall'] == [3, 0, 0])
                            current = self.diagnostics(window)
                            self.assertEqual(current['geometryOffset'], [0, 0, 0])
                            self.assertEqual(current['sampleOffsets']['other'], [0, 0, 0])
                            dialog.reset_button.click()
                            self.assertEqual(dialog.setup(), {
                                'schema_version': 1, 'scope': 'domain', 'regions': [],
                                'translation': [0., 0., 0.], 'source_hash': window.geometry['source_hash']})
                            self.assertIsNone(window.view.translation_preview)
                            self.assertIn('Setup reset', dialog.status.text())
                            generate.assert_not_called()
                            export.assert_not_called()
                        self.wait_for(lambda: self.diagnostics(window)['sampleOffsets']['wall'] == [0, 0, 0])
                        # Export after reset must also evaluate the identity configuration.
                        path = Path(directory) / 'reset.npz'
                        with patch('geosampler.parametrisation_panel.QFileDialog.getSaveFileName',
                                   return_value=(str(path), 'NumPy archive (*.npz)')):
                            dialog.export_configuration()
                        with np.load(path, allow_pickle=False) as data:
                            np.testing.assert_array_equal(data['_gs_translation'], [0, 0, 0])
                            for batch in original_batches:
                                np.testing.assert_array_equal(data[batch['label']], batch['coordinates'])
                        # Dismiss an active preview through both real UI paths.
                        dialog.offsets[1].setValue(4)
                        dialog.preview()
                        if dismiss == 'close':
                            dialog.close()
                        else:
                            QTest.keyClick(dialog, Qt.Key.Key_Escape)
                        self.wait_for(lambda: window.parametrisation_dialog is None)
                        self.wait_for(lambda: self.diagnostics(window)['geometryOffset'] == [0, 0, 0])
                        window.open_parametrisation()
                        dialog = window.parametrisation_dialog
                        self.assertEqual(dialog.offsets[1].value(), 4)
                        self.assertIsNone(window.view.translation_preview)
                        dialog.reset_button.click()
                        dialog.close()
                        window.open_parametrisation()
                        dialog = window.parametrisation_dialog
                        self.assertEqual(dialog.setup()['translation'], [0, 0, 0])
                        self.assertEqual(dialog.setup()['regions'], [])
                        self.assertEqual(dialog.setup()['scope'], 'domain')
                        dialog.close()
                        current = self.diagnostics(window)
                        for key in ('visibleFaces', 'visibleEdges', 'visibleSampleCount', 'sampleColours'):
                            self.assertEqual(current[key], baseline[key])
                        self.assertEqual(window.geometry, original_geometry)
                        self.assertEqual(window.sampling.batches, original_batches)
                        self.assertEqual(window.view.geometry_visibility, original_visibility)
                        self.assertEqual(window.selection, original_selection)
                        self.assertEqual(window.sampled_areas.hidden_labels(), ['other'])
                        self.assertTrue(window.sampling.isEnabled())
                        self.assertTrue(window.open_action.isEnabled())
            finally:
                window.close()
