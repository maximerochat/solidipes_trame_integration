import pyvista as pv
from pyvista import examples
from pyvista.trame.ui import plotter_ui
from trame.app import get_server
from trame.ui.vuetify3 import VAppLayout
from trame.widgets import vuetify3 as vuetify
from trame.widgets import html


class MeshViewer:

    def __init__(self, mesh=None, plotter=None):
        pv.OFF_SCREEN = True

        self.server = get_server()
        self.state, self.ctrl = self.server.state, self.server.controller
        self.state.is_full_screen = False
        if mesh is None:
            mesh = examples.load_random_hills()
        self.mesh = mesh
        self.pl = pv.Plotter()
        self.pl.add_mesh(self.mesh)

    def start_server(self):
        with VAppLayout(self.server) as layout:
            with layout.root:
                with html.Div(ref="container", style="height: 100vh; width:100vw"):
                    view = plotter_ui(self.pl)
                    vuetify.VBtn(click=self.request_full, style="position: absolute; bottom:25px; right:25px;")
        self.server.start()

    def request_full(self):
        print("clicked");
        if not self.state.is_full_screen:
            self.server.js_call("container", "requestFullscreen")
        else:
            self.server.js_call("container", "webkitExitFullscreen")
        self.state.is_full_screen = not self.state.is_full_screen

if __name__ == "__main__":
    mv = MeshViewer()
    mv.start_server()