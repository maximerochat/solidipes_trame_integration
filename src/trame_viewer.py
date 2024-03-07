import pyvista as pv
from pyvista import examples
from pyvista.trame.ui import plotter_ui
from trame.app import get_server
from trame.ui.vuetify3 import VAppLayout
from trame.widgets import vuetify3 as vuetify
from trame.widgets import html
from aiohttp import web
from trame.decorators import TrameApp, change, controller

import os
import time, threading
import asyncio

from typing import Dict


class Representation:
    Points = 0
    Wireframe = 1
    Surface = 2
    SurfaceWithEdges = 3


FIELD_NAMES = ["field1", "field2", "field3"]


@TrameApp()
class MeshViewer:

    def __init__(self, mesh=None, plotter=None):

        pv.OFF_SCREEN = True
        self.scalar_bar_exist = None
        self.server = get_server()
        self.slider_playing = False
        self.path = None

        self.mesh = None
        self.clean_mesh = None

        self.style = {
            "background-color": "black",
            "font-color": "white"
        }

        self.pl = self.setup_pl()

        setattr(self, "on_server_bind", self.server.controller.add("on_server_bind")(self.on_server_bind))

        # self.replace_mesh(mesh)
        self.my_routes = [
            web.get("/select_mesh", self.change_mesh),
        ]

        self.setup_state()

        self.setup_timer()

        self.loop = asyncio.get_event_loop()

        self.mesh_array = None
        m = pv.read("/home/mrochat/dataset/jtcam-data-10172/data/T3DE/Results/VTK/results_corr-000000.vtk")

        self.state.options = m.array_names.copy()
        self.state.options.insert(0, "None")
        # self.state.options = [None]

        self.build_ui()

    def setup_pl(self) -> pv.Plotter:
        pl = pv.Plotter()
        pl.background_color = self.style["background-color"]
        pl.theme.font.color = self.style["font-color"]
        self.scalar_bar_exist = False
        return pl

    def setup_state(self):
        self.state.is_full_screen = False
        self.state.mesh_representation = self.state.options[0] if self.state.options is not None else None

        self.state.warp_input = 0
        self.state.wireframe_on = True
        self.state.slider_value = 0
        self.state.play_pause_icon = "mdi-play"
        self.prev_bar_repr = self.state.mesh_representation

    def setup_timer(self):
        self.timeout = 0.25
        self.timer = threading.Thread(target=self.timer_callback)
        self.sequence_bounds = [0, 70]

    @change("mesh_representation")
    def update_mesh_representation(self, mesh_representation, **kwargs):
        if self.mesh is not None and self.scalar_bar_exist and self.prev_bar_repr is not None and self.prev_bar_repr != "None":
            self.pl.remove_scalar_bar(self.prev_bar_repr)

        self.prev_bar_repr = mesh_representation
        print(mesh_representation)
        if mesh_representation == "None":
            self.state.mesh_representation = None
        self.replace_mesh(self.mesh)

    @change("warp_input")
    def update_warp_input(self, **kwargs):

        try:
            new_warp = float(self.state.warp_input)
            dim = self.mesh.point_data.get_array(self.state.mesh_representation).ndim  # 1 if scalar, 2 if vector
            if dim == 1:
                new_pyvista_mesh = self.clean_mesh.warp_by_scalar(self.state.mesh_representation,
                                                                  factor=new_warp)

            else:
                new_pyvista_mesh = self.clean_mesh.warp_by_vector(self.state.mesh_representation,
                                                                  factor=new_warp)

            self.replace_mesh(new_pyvista_mesh)
        except ValueError as e:
            print(e)
            pass
        finally:
            return

    @change("wireframe_on")
    def update_wireframe_on(self, **kwargs):
        self.replace_mesh(self.mesh)


    @change("slider_value")
    def slider_value_change(self, slider_value, **kwargs):
        self.update_mesh_from_index(int(slider_value))

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    def timer_callback(self):
        print("timer")
        print(self.slider_playing)
        while self.slider_playing and self.server.running:
            self.state.slider_value = (self.state.slider_value + 1) % self.sequence_bounds[1]

            # self.update_mesh_from_index(self.state.slider_value)

            self.loop.call_soon_threadsafe(self.update_mesh_from_index, self.state.slider_value)
            self.loop.call_soon_threadsafe(self.server.force_state_push, "slider_value")
            time.sleep(0.25)

        self.timer = threading.Thread(target=self.timer_callback)

    def update_mesh_from_index(self, idx):
        if self.mesh_array is not None:
            self.replace_mesh(self.mesh_array[idx])

    async def change_mesh(self, request):

        request_body: Dict[str, str] = await request.json()
        self.path = request_body.get("mesh_path", None)
        if self.path is None:
            print("Error : No filepath found in the change mesh request")
            return

        self.mesh_array = []
        for i in range(self.sequence_bounds[1]):
            path = self.path % i
            if not os.path.exists(path):
                print("Error, the path specified does not exist")
                return
            self.mesh_array.append(pv.read(path))

        self.update_mesh_from_index(0)

        self.server.force_state_push("options")
        self.server = self.server.create_child_server()
        self.server.force_state_push("options")

        # self.setup_pl()
        # self.build_ui()
        return web.json_response(status=200)

    def replace_mesh(self, new_mesh):
        if new_mesh is None:
            return

        # set custom style
        kwargs_plot = {}
        if self.state.wireframe_on:
            kwargs_plot["style"] = "wireframe"
        print("here 1")
        # update mesh and set its active scalar field, as well as adding the scalar bar
        self.mesh = new_mesh
        print("here 2")
        self.mesh.set_active_scalars(self.state.mesh_representation)
        print("here 3")
        # Replace actor with the new mesh (automatically update the actor because they have the same name)
        self.pl.add_mesh(self.mesh, style="wireframe" if self.state.wireframe_on else "surface", name="displayed_mesh",
                         silhouette=False)

        print("here 4")
        if self.state.options != new_mesh.array_names:
            self.state.options = new_mesh.array_names.copy()


        if not self.slider_playing:
            self.pl.add_scalar_bar(self.state.mesh_representation)
            self.scalar_bar_exist = True

    @controller.set("reset_resolution")
    def reset_resolution(self):
        self.state.welcome = str(self.counter)

    def start_server(self):
        try:
            self.server.start()
        except KeyboardInterrupt:
            self.stop_event.set()  # Set the stop event when an interrupt signal is received
            self.timer.join()  # Wait for the timer thread to finish

    def option_dropdown(self):

        return vuetify.VSelect(
            v_model=("mesh_representation", "None"),
            items=("fields", self.state.options),

            label="Representation",
            hide_details=True,
            dense=True,
            outlined=True,
            classes="pt-1",
        )

    def build_slider(self):
        row = html.Div(style='display:flex;justify-content:center;align-content:center;gap:20px;')
        with row:
            with vuetify.VBtn(
                    icon=True,
                    click=self.play_button
            ):
                vuetify.VIcon("{{ play_pause_icon }}")

            html.Div("{{ slider_value }}")
            slider = vuetify.VSlider(
                ref="slider",
                label="",
                min=self.sequence_bounds[0],
                max=self.sequence_bounds[1],
                v_model=("slider_value", 8),
                step=1
            )
        return row

    @controller.set("play_button")
    def play_button(self):

        self.slider_playing = not self.slider_playing
        print("clicked")
        print(self.slider_playing)
        if self.slider_playing and not self.timer.is_alive():
            self.state.play_pause_icon = "mdi-pause"
            self.timer.start()
        else:
            self.state.play_pause_icon = "mdi-play"

    def build_ui(self):
        with VAppLayout(self.server) as layout:
            with layout.root:
                with html.Div(ref="container",
                              style="height: 600px; width:1200px"):  # add the following arg: style="height: 100vh; width:100vw" to have the plotter taking all screen
                    plotter_ui(self.pl, default_server_rendering=False)
                    with vuetify.VRow(dense=True):
                        with vuetify.VCol(cols="6"):
                            self.option_dropdown()

                        with vuetify.VCol(cols="6"):
                            vuetify.VTextField(type="number", label="warp",
                                               v_model=("warp_input", 0.0)
                                               )
                    vuetify.VCheckbox(v_model=("wireframe_on",), label="Wireframe on")
                    self.build_slider()
                    html.Div("{{ welcome }}")
                    vuetify.VBtn(icon=True, click=self.ctrl.reset_resolution)
                    vuetify.VBtn(click=self.request_full, style="position: absolute; bottom:25px; right:25px;")

    def on_server_bind(self, wslink_server):
        print("server ready")
        wslink_server.app.add_routes(self.my_routes)

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
