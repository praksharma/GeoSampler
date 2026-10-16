"""Screen-space selection checks against the offline renderer and WebChannel."""
import json
import math
from pathlib import Path
import tempfile
import unittest
from PySide6.QtCore import QSettings
from PySide6.QtTest import QSignalSpy
from geosampler.app import MainWindow
import test_shell


def face(tag, size, z):
    return {'dimension':2, 'tag':tag, 'type':'Plane', 'boundary':[], 'groups':[],
            'positions':[-size,-size,z, size,-size,z, size,size,z,
                         -size,-size,z, size,size,z, -size,size,z]}


def edge(tag, start, end):
    return {'dimension':1, 'tag':tag, 'type':'Line', 'boundary':[], 'groups':[],
            'positions':list(start)+list(end)}


class PickingUiTest(unittest.TestCase):
    setUpClass = classmethod(test_shell.ShellTest.setUpClass.__func__)
    wait_for = test_shell.ShellTest.wait_for
    javascript = test_shell.ShellTest.javascript

    def show(self, window, entities):
        window.show_geometry({'document':'picking-fixture', 'name':'Selection test',
                              'source':'selection.geo', 'source_hash':'fixture', 'dimension':3,
                              'groups':[], 'entities':entities})
        self.javascript(window, 'true')

    def camera(self, window, depth):
        window.view.set_camera_state({'position':[0,0,depth], 'target':[0,0,0],
                                      'up':[0,1,0], 'near':.1, 'far':100})
        self.javascript(window, 'true')

    def click(self, window, point, depth, offset=(0,0)):
        width,height=json.loads(self.javascript(window,'JSON.stringify([innerWidth,innerHeight])'))
        scale=height/(2*(depth-point[2])*math.tan(math.radians(19)))
        x=width/2+point[0]*scale+offset[0]; y=height/2-point[1]*scale+offset[1]
        spy=QSignalSpy(window.view.picked)
        self.javascript(window, f"""(()=>{{const c=document.querySelector('canvas');
            for(const type of ['pointerdown','pointerup'])c.dispatchEvent(new PointerEvent(type,
            {{clientX:{x},clientY:{y},button:0,pointerId:1,pointerType:'mouse',bubbles:true}}));return true;}})()""")
        self.wait_for(lambda: spy.count()>0)
        return window.selection.copy()

    def test_zoom_tolerance_occlusion_and_visibility(self):
        with tempfile.TemporaryDirectory() as directory:
            window=MainWindow(QSettings(str(Path(directory)/'settings.ini'),QSettings.Format.IniFormat))
            window.show()
            try:
                self.wait_for(lambda:window.view.is_ready)
                self.show(window,[face(1,.5,0),edge(1,(-.8,0,-.02),(.8,0,-.02))])
                window.set_selection_mode('edge'); self.camera(window,5)
                self.assertEqual(self.click(window,(0,0,-.02),5),set())
                self.assertEqual(self.click(window,(.7,0,-.02),5),{(1,1)})
                window.visibility_actions['faces'].setChecked(False)
                self.assertEqual(self.click(window,(0,0,-.02),5),{(1,1)})
                window.visibility_actions['faces'].setChecked(True)
                self.assertEqual(self.click(window,(0,0,-.02),5),set())
                window.hide_faces([1])
                self.assertEqual(self.click(window,(0,0,-.02),5),{(1,1)})
                window.visibility_actions['edges'].setChecked(False)
                self.assertEqual(self.click(window,(0,0,-.02),5),set())
                window.visibility_actions['edges'].setChecked(True)
                # A six-pixel tolerance must not grow or shrink with camera distance.
                self.show(window,[face(1,.5,-1),edge(1,(-.8,0,0),(.8,0,0))])
                window.set_selection_mode('edge')
                for depth in (3,10,30):
                    with self.subTest(depth=depth):
                        self.camera(window,depth)
                        self.assertEqual(self.click(window,(0,0,0),depth,(0,5)),{(1,1)})
                        self.assertEqual(self.click(window,(0,0,0),depth,(0,8)),set())
                # Nearest projected edge wins, even if another edge is closer in depth.
                self.show(window,[face(1,.5,-1),edge(1,(-.8,0,0),(.8,0,0)),
                                  edge(2,(-.8,.04,.5),(.8,.04,.5))])
                window.set_selection_mode('edge'); self.camera(window,10)
                self.assertEqual(self.click(window,(0,0,0),10),{(1,1)})
                # Edges entirely behind the camera are ineligible.
                self.show(window,[face(1,.5,-1),edge(1,(-.8,0,12),(.8,0,12))])
                window.set_selection_mode('edge'); self.camera(window,5)
                self.assertEqual(self.click(window,(0,0,0),5),set())
                # Face mode picks the visible part of a partially occluded rear face.
                self.show(window,[face(1,.5,0),face(2,1,-.2)])
                window.set_selection_mode('face'); self.camera(window,5)
                self.assertEqual(self.click(window,(0,0,0),5),{(2,1)})
                self.assertEqual(self.click(window,(.8,0,-.2),5),{(2,2)})
                window.hide_faces([1])
                self.assertEqual(self.click(window,(0,0,-.2),5),{(2,2)})
                window.visibility_actions['geometry'].setChecked(False)
                self.assertEqual(self.click(window,(0,0,-.2),5),set())
            finally:window.close()
