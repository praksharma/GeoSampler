"""Project menu actions and workspace restoration."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from PySide6.QtCore import Qt, QByteArray
from PySide6.QtWidgets import QFileDialog, QMessageBox
from .project import save_project, load_project


class ProjectActions:
    def project_busy(self):
        return self.sampling.process or self.import_process or self.parametrisation_dialog or self.boundary_dialog

    def refresh_project_actions(self):
        busy=bool(self.project_busy())
        self.open_project_action.setEnabled(not busy)
        self.save_project_action.setEnabled(not busy and self.geometry is not None)
        self.save_project_as_action.setEnabled(not busy and self.geometry is not None)

    def project_state(self, camera=None):
        panel=self.sampling
        return {'selection':[list(key) for key in sorted(self.selection)],
                'mode':self.view.mode,'geometry_visibility':deepcopy(self.view.geometry_visibility),
                'selected_area':self.selected_area,'isolate':self.isolate_action.isChecked(),
                'isolate_geometry':self.isolate_geometry_action.isChecked(),
                'show_points':panel.show_points.isChecked(),'through':panel.through.isChecked(),
                'point_size':panel.point_size.value(),'show_grid':self.view.show_grid,'show_axes':self.view.show_axes,
                'controls':{'method':panel.method.currentData(),'target':panel.target.currentData(),
                            'count':panel.count.value(),'seed':panel.seed.value(),'label':panel.label.text(),
                            'resolution':panel.resolution.currentData(),'compute_mode':panel.compute_mode.currentData(),
                            'cpu_threads':panel.cpu_threads.value()},
                'boundary_regions':deepcopy(self.boundary_regions),
                'parametrisation':deepcopy(self.parametrisation_setup),
                'layout':bytes(self.saveState()).hex(),'camera':camera}

    def save_project(self, save_as=False):
        if self.project_busy() or not self.geometry:
            return
        path=self.project_path if not save_as else None
        if not path:
            filename,_=QFileDialog.getSaveFileName(self,'Save GeoSampler project',self.geometry['name']+'.gsproj','GeoSampler project (*.gsproj)')
            if not filename:return
            path=Path(filename)
            if not path.suffix:path=path.with_suffix('.gsproj')
        def write(camera_json):
            try:
                camera=json.loads(camera_json) if camera_json else None
                areas=[(area,status,self.sampled_areas.items[label].checkState(0)==Qt.CheckState.Checked)
                       for label,(area,status) in self.sampled_areas.areas.items()]
                save_project(path,self.geometry,areas,self.project_state(camera))
                self.project_path=Path(path)
                self.setWindowTitle('GeoSampler — '+self.project_path.name)
                self.statusBar().showMessage('Project saved: '+str(path))
            except (ValueError,TypeError,OSError,KeyError) as error:
                QMessageBox.warning(self,'Could not save project',str(error))
        if self.view.is_ready:
            self.view.web.page().runJavaScript('JSON.stringify(window.geoViewer.cameraState())',write)
        else:write(None)

    def open_project(self):
        if self.project_busy():return
        filename,_=QFileDialog.getOpenFileName(self,'Open GeoSampler project','','GeoSampler project (*.gsproj)')
        if filename:self.load_project_file(filename)

    def load_project_file(self, filename):
        if self.project_busy():return
        cache=None
        try:
            manifest,source=load_project(filename)
            geometry=manifest['geometry']
            # Retain a valid original path for relative .geo dependencies; otherwise
            # restore the embedded main CAD source without extracting arbitrary paths.
            path=Path(geometry['source'])
            try:
                valid=path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==geometry['source_hash']
            except OSError:
                valid=False
            if self.project_cache and path.is_relative_to(self.project_cache.name):valid=False
            if not valid:
                cache=tempfile.TemporaryDirectory(prefix='geosampler-project-')
                path=Path(cache.name)/('model'+manifest['source_extension']);path.write_bytes(source)
            geometry['source']=str(path)
            for record in manifest['areas']:
                record['area']['source']=str(path)
            state=manifest['state']
            old_cache=self.project_cache
            self.show_geometry(geometry)
            self.boundary_regions = state.get('boundary_regions', [])
            self.refresh_boundary_regions()
            self.project_cache=cache
            self.project_path=Path(filename)
            if old_cache is not None:old_cache.cleanup()
            for record in manifest['areas']:
                area,status=record['area'],record['status']
                if status=='Generated':self.sampling.batches.append(area)
                self.sampled_areas.set_area(area,status)
                if status=='Generated' and not record['visible']:
                    self.sampled_areas.items[area['label']].setCheckState(0,Qt.CheckState.Unchecked)
            self.view.set_mode(state.get('mode','face'))
            self.selection_actions[self.view.mode].setChecked(True)
            self.selection={tuple(e) for e in state.get('selection',[])};self.update_selection()
            for key in ('geometry','faces','edges'):
                self.visibility_actions[key].setChecked(state['geometry_visibility'][key])
            self.view.set_geometry_visibility(state['geometry_visibility'])
            self.sampling.show_points.setChecked(state['show_points']);self.sampling.through.setChecked(state['through'])
            self.sampling.point_size.setValue(state['point_size'])
            self.set_visibility('show_grid',state['show_grid']);self.set_visibility('show_axes',state['show_axes'])
            for action,_ in self.icon_actions:
                if action.text()=='Grid':action.setChecked(state['show_grid'])
                if action.text()=='Axes':action.setChecked(state['show_axes'])
            controls=state['controls'];panel=self.sampling
            for field in ('method','target','resolution','compute_mode'):
                combo=getattr(panel,field)
                index=next((i for i in range(combo.count()) if combo.itemData(i)==controls[field]),0)
                combo.setCurrentIndex(index)
            for field in ('count','seed','cpu_threads'):getattr(panel,field).setValue(controls[field])
            panel.label.setText(controls['label'])
            self.parametrisation_setup=state.get('parametrisation')
            label=state.get('selected_area')
            if label in self.sampled_areas.items:
                self.sampled_areas.setCurrentItem(self.sampled_areas.items[label])
                self.isolate_geometry_action.setChecked(state['isolate_geometry'])
                self.isolate_action.setChecked(state['isolate'])
            self.sampling.refresh_preview()
            self.sampling.summary.setText(f'Restored {len(self.sampling.batches)} generated areas.')
            if state.get('layout'):self.restoreState(QByteArray.fromHex(state['layout'].encode()))
            if state.get('camera'):self.view.set_camera_state(state['camera'])
            self.setWindowTitle('GeoSampler — '+self.project_path.name)
            self.statusBar().showMessage('Project opened: '+str(filename))
            if not valid and manifest['source_extension']=='.geo':
                self.statusBar().showMessage('Project restored. Embedded .geo source is available; external Include/Merge dependencies may need restoring before regeneration.')
        except Exception as error:
            if cache is not None and cache is not self.project_cache:cache.cleanup()
            QMessageBox.warning(self,'Could not open project',str(error))

    def remap_parameter_label(self, old, new):
        if self.parametrisation_setup:
            self.parametrisation_setup['regions']=[new if label==old else label for label in self.parametrisation_setup.get('regions',[])]
