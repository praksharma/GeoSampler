"""Create overlapping regions, sample them, preserve snapshots and reopen a project."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import xarray as xr
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor
from geosampler.app import MainWindow
from geosampler.export import export_samples
import test_shell

FIXTURE = Path(__file__).resolve().parents[1] / 'examples/geometries/cfdbench/annulus_unstructured.geo'


class RegionsUiTest(unittest.TestCase):
    setUpClass = classmethod(test_shell.ShellTest.setUpClass.__func__)
    wait_for = test_shell.ShellTest.wait_for
    javascript = test_shell.ShellTest.javascript

    def test_edit_sample_persist_and_reimport(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'annulus.geo'; source.write_bytes(FIXTURE.read_bytes())
            settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
            window = MainWindow(settings); window.show()
            try:
                self.wait_for(lambda: window.view.is_ready)
                window.load_geometry(source); self.wait_for(lambda: window.import_process is None)
                window.set_selection_mode('edge')
                window.pick_entity(1,1,False); window.pick_entity(1,2,True)
                window.boundary_button.click(); dialog = window.boundary_dialog
                self.assertIsNotNone(dialog)
                self.assertFalse(window.save_project_action.isEnabled())
                dialog.label.setText('inner / 壁')
                with patch('geosampler.regions_panel.QColorDialog.getColor', return_value=QColor('#ffc857')):
                    dialog.colour_button.click()
                dialog.save_button.click()
                first = deepcopy(window.boundary_regions[0])
                self.assertEqual(first['entities'], [[1,1],[1,2]])
                dialog.new_button.click()
                dialog.label.setText('shared')
                dialog.set_members([[1,2],[1,3]])
                dialog.colour = '#123456'; dialog.save_button.click()
                dialog.close()
                self.assertIsNone(window.boundary_dialog)
                window.clear_selection()
                self.wait_for(lambda: self.javascript(window, 'window.geoViewer.diagnostics().entityColours["1:2"]') == '#ffc857')
                self.assertEqual(self.javascript(window, 'window.geoViewer.diagnostics().entityColours["1:3"]'), '#123456')
                index = next(i for i in range(window.sampling.target.count())
                             if window.sampling.target.itemData(i) == {'region_id': first['id']})
                window.sampling.target.setCurrentIndex(index)
                window.sampling.label.setText('training'); window.sampling.count.setValue(32)
                window.sampling.start(); self.wait_for(lambda: window.sampling.process is None)
                batch = deepcopy(window.sampling.batches[0])
                self.assertEqual(batch['boundary_region'], first)
                self.assertEqual(batch['label'], 'training')
                self.assertEqual(batch['entities'], [[1,1],[1,2]])
                self.assertEqual(set(batch['entity_tags']), {1,2})
                for suffix in ('nc','npz'):
                    path = export_samples([batch], Path(directory) / ('regions.' + suffix))
                    if suffix == 'nc':
                        with xr.open_dataset(path, engine='scipy') as data:
                            metadata = json.loads(data.attrs['metadata_json'])
                    else:
                        with np.load(path, allow_pickle=False) as data:
                            metadata = json.loads(data['_gs_metadata'].item())
                    self.assertEqual(metadata['datasets'][0]['metadata']['boundary_region'], first)
                window.open_boundary_regions(); dialog = window.boundary_dialog
                dialog.regions.setCurrentRow(0)
                self.assertEqual(dialog.identity, first['id'])
                dialog.label.setText('renamed'); dialog.set_members([[1,1],[1,4]])
                dialog.save_button.click(); dialog.select_button.click()
                self.assertEqual(window.selection, {(1,1),(1,4)})
                dialog.close()
                self.assertEqual(window.sampling.batches[0], batch)
                self.assertEqual(window.boundary_regions[0]['id'], first['id'])
                self.assertIn('renamed', window.properties.text())
                project = Path(directory) / 'regions.gsproj'
                with patch('geosampler.project_ui.QFileDialog.getSaveFileName', return_value=(str(project),'GeoSampler project (*.gsproj)')):
                    window.save_project()
                    self.wait_for(project.exists)
                expected = deepcopy(window.boundary_regions)
                source.unlink()
                window.load_project_file(project)
                self.assertEqual(window.boundary_regions, expected)
                self.assertEqual(window.sampling.batches[0]['boundary_region'], first)
                self.assertTrue(Path(window.geometry['source']).is_file())
                self.assertEqual(window.sampling.target.currentData(), {'region_id': first['id']})
                # Deleting assignments keeps generated datasets and unlabelled entities.
                window.open_boundary_regions(); dialog = window.boundary_dialog
                dialog.regions.setCurrentRow(0); dialog.delete_button.click()
                dialog.close()
                self.assertEqual(window.sampling.target.currentData(), 'selection')
                self.assertEqual(window.sampling.batches[0]['boundary_region'], first)
                window.set_selection_mode('edge'); window.pick_entity(1,1,False)
                self.assertEqual(window.selection, {(1,1)})
                # A failed import preserves assignments and samples; a successful one clears assignments.
                before = deepcopy(window.boundary_regions)
                bad = Path(directory) / 'bad.geo'; bad.write_text('not valid CAD')
                with patch('geosampler.app.QMessageBox.warning') as warning:
                    window.load_geometry(bad); self.wait_for(lambda: window.import_process is None)
                    warning.assert_called_once()
                self.assertEqual(window.boundary_regions, before)
                self.assertEqual(window.sampling.batches[0]['boundary_region'], first)
                window.load_geometry(FIXTURE); self.wait_for(lambda: window.import_process is None)
                self.assertEqual(window.boundary_regions, [])
                self.assertEqual(window.sampling.batches, [])
            finally:
                window.close()
