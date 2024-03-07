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

        self.server = get_server()

        # self.state, self.ctrl = self.server.state, self.server.controller
        self.state.welcome = "hello"
        self.state.is_full_screen = False
        if mesh is None:
            mesh = examples.load_random_hills()

        self.counter = 30
        formatted_num = "{:02d}".format(self.counter)
        print()
        self.mesh = pv.read(
            f"/home/mrochat/dataset/jtcam-data-10172/data/T3DE/Results/VTK/results_corr-0000{formatted_num}.vtk")
        print(self.mesh.array_names)
        self.clean_mesh = self.mesh.copy()
        self.options = self.mesh.array_names.copy()
        self.options.insert(0, "None")
        self.style = {
            "background-color": "black",
            "font-color": "white"
        }
        self.pl = pv.Plotter()
        self.pl.background_color = self.style["background-color"]
        self.pl.theme.font.color = self.style["font-color"]

        kwargs_plot = {}
        self.mesh.set_active_scalars(None)
        kwargs_plot["style"] = "wireframe"
        setattr(self, "on_server_bind", self.server.controller.add("on_server_bind")(self.on_server_bind))
        self.actor = self.pl.add_mesh(self.mesh, **kwargs_plot)
        self.my_routes = [
            web.get("/select_mesh", self.change_mesh),
        ]
        self.state.mesh_representation = self.options[1]
        self.state.warp_input = 0
        self.state.wireframe_on = True
        self.state.slider_value = 0
        self.slider_playing = False
        self.timeout = 0.25
        self.timer = threading.Thread(target=self.timer_callback)
        self.sequence_bounds = [0, 70]



        self.loop = asyncio.get_event_loop()

        self.mesh_array = [
            pv.read("/home/mrochat/dataset/jtcam-data-10172/data/T3DE/Results/VTK/results_corr-0000{:02d}.vtk".format(
                slider_value)) for slider_value in range(self.sequence_bounds[1])
        ]

        self.build_ui()

    @change("mesh_representation")
    def update_mesh_representation(self, mesh_representation, **kwargs):
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
        # new_mesh = pv.read("/home/mrochat/dataset/jtcam-data-10172/data/T3DE/Results/VTK/results_corr-0000{:02d}.vtk".format())
        # self.replace_mesh(self.mesh_array[slider_value])
        self.update_mesh_from_index(int(slider_value))
        print(f"Slider is changing slider_value to {slider_value}")

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    def timer_callback(self):
        print("timer")
        print(self.slider_playing)
        while self.slider_playing:
            self.state.slider_value = (self.state.slider_value + 1) % self.sequence_bounds[1]
            print(self.state.slider_value)
            # self.update_mesh_from_index(self.state.slider_value)

            self.loop.call_soon_threadsafe(self.update_mesh_from_index, self.state.slider_value)
            self.loop.call_soon_threadsafe(self.server.js_call, ["slider", "setAttribute", ["aria-valuenow", str(self.state.slider_value)]])

            time.sleep(0.25)

        self.timer = threading.Thread(target=self.timer_callback)

    def update_mesh_from_index(self, idx):
        self.replace_mesh(self.mesh_array[idx])

    async def change_mesh(self, request):
        # print((await request.json())["test"])
        request_body: Dict[str, str] = await request.json()
        path = request_body.get("mesh_path", None)
        if path is None:
            print("Error : No filepath found in the change mesh request")
            return

        if not os.path.exists(path):
            print("Error, the path specified does not exist")
            return

        self.counter += 10
        formatted_num = "{:02d}".format(self.counter)

        print(path)
        mesh = pv.read(
            path)
        self.replace_mesh(mesh)

        self.state.welcome = "updated from request"
        # print("new handler")
        return web.json_response(status=200)

    def replace_mesh(self, new_mesh):
        # set custom style
        kwargs_plot = {}
        if self.state.wireframe_on:
            kwargs_plot["style"] = "wireframe"

        # update mesh and set its active scalar field, as well as adding the scalar bar
        self.mesh = new_mesh
        self.mesh.set_active_scalars(self.state.mesh_representation)
        # self.pl.add_scalar_bar(self.state.mesh_representation)
        tmp_act = self.pl.add_mesh(self.mesh,**kwargs_plot)
        # remove old mesh and add the new one
        self.pl.remove_actor(self.actor)
        self.actor = tmp_act



    @controller.set("reset_resolution")
    def reset_resolution(self):
        self.state.welcome = str(self.counter)

    def start_server(self):
        self.server.start()

    def option_dropdown(self):
        return vuetify.VSelect(
            # Representation
            v_model=("mesh_representation", "None"),
            items=("fields", self.options),
            label="Representation",
            hide_details=True,
            dense=True,
            outlined=True,
            classes="pt-1",
        )

    def build_slider(self):
        slider = vuetify.VSlider(
            ref="slider",
            label="Example",
            min=self.sequence_bounds[0],
            max=self.sequence_bounds[1],
            v_model=("slider_value", 8),
            step=1
        )
        return slider

    @controller.set("play_button")
    def play_button(self):

        self.slider_playing = not self.slider_playing
        print("clicked")
        print(self.slider_playing)
        if self.slider_playing and not self.timer.is_alive():
            self.timer.start()

    def build_ui(self):
        with VAppLayout(self.server) as layout:
            with layout.root:
                with vuetify.VRow(dense=True):
                    vuetify.VBtn(
                        icon=True,
                        click=self.play_button
                    )
                    self.build_slider()
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
