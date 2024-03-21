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
import numpy as np
import time, threading
import asyncio

from typing import Dict

from MeshViewerComponent import MeshViewerComponent




@TrameApp()
class MeshViewer:

    def __init__(self, mesh=None, plotter=None, server=None):

        pv.OFF_SCREEN = True
        self.scalar_bar_exist = None
        if server is None:
            self.server = get_server()
        else:
            self.server = server
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
        p = "/home/mrochat/dataset/jtcam-data-10172/data/T3DE/Results/VTK/results_corr-%06d.vtk"

        self.mesh_array = [pv.read(p % i) for i in range(self.sequence_bounds[1])]
        #
        # self.state.options = m.array_names.copy()
        # self.state.options.insert(0, "None")
        self.state.options = [None]
        self.actor = None
        self.width = 800
        self.height = 900
        self.ui = self.build_ui()

    def setup_pl(self) -> pv.Plotter:
        pl = pv.Plotter()
        pl.background_color = self.style["background-color"]
        pl.theme.font.color = self.style["font-color"]
        self.bounds_scalar = None
        self.scalar_bar_exist = False
        self.scalar_bar_mapper = None
        return pl

    def setup_state(self):
        self.state.is_full_screen = False
        self.state.mesh_representation = self.state.options[0] if self.state.options is not None else None

        self.state.warp_input = 0
        self.state.wireframe_on = True
        self.state.slider_value = 0
        self.state.play_pause_icon = "mdi-play"
        self.prev_bar_repr = self.state.mesh_representation
        self.prev_wrap = "0"

    def setup_timer(self):
        self.timeout = 0.25
        self.timer = threading.Thread(target=self.timer_callback)
        self.sequence_bounds = [0, 70]

    @change("mesh_representation")
    def update_mesh_representation(self, mesh_representation, **kwargs):

        if self.mesh is not None and self.mesh.active_scalars is not None:
            self.pl.remove_scalar_bar()

        self.prev_bar_repr = mesh_representation

        if mesh_representation == "None":
            self.state.mesh_representation = None
        for i in range(self.sequence_bounds[1]):
            self.mesh_array[i].set_active_scalars(self.state.mesh_representation)
        # self.replace_mesh(self.mesh)



        self.update_mesh_from_index(self.state.slider_value)
        self.ui = self.build_ui()
        # self.update_mesh_from_index(1)

    @change("warp_input")
    def update_warp_input(self, **kwargs):

        try:

            new_warp = float(self.state.warp_input)

            min_v, max_v = self.bounds_scalar.get(self.state.mesh_representation, (0, 0))

            offset = (max_v - min_v) / 0.01

            if new_warp > float(self.prev_wrap):
                new_warp = float(self.state.warp_input) + offset
                self.state.warp_input = str(float(self.prev_wrap) + offset)
            elif new_warp < float(self.prev_wrap):
                new_warp = float(self.state.warp_input) - offset
                self.state.warp_input = str(float(self.prev_wrap) - offset)
            dim = self.mesh.point_data.get_array(self.state.mesh_representation).ndim  # 1 if scalar, 2 if vector
            if dim == 1:
                new_pyvista_mesh = self.clean_mesh.warp_by_scalar(self.state.mesh_representation,
                                                                  factor=new_warp)
            else:
                new_pyvista_mesh = self.clean_mesh.warp_by_vector(self.state.mesh_representation,
                                                                  factor=new_warp)

            self.prev_wrap = self.state.warp_input
            self.replace_mesh(new_pyvista_mesh)
        except ValueError as e:
            print(e)
            pass
        except Exception as e:
            print(e)
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
            self.clean_mesh = self.mesh_array[idx]
            self.replace_mesh(self.mesh_array[idx])

    def handle_new_mesh(self, mesh_path, seq_len):
        self.mesh_array = []
        if seq_len == 1:
            self.mesh_array.append(pv.read(mesh_path))
            return

        for i in range(self.sequence_bounds[1]):
            path = self.path % i
            if not os.path.exists(path):
                print("Error, the path specified does not exist")
                return
            self.mesh_array.append(pv.read(path))


    async def change_mesh(self, request):

        request_body: Dict[str, str] = await request.json()
        self.path = request_body.get("mesh_path", None)
        self.width = request_body.get("width", self.width)
        self.height = request_body.get("height", self.height)
        self.sequence_bounds[1] = request_body.get("nbr_frames", self.sequence_bounds[1])

        if self.path is None:
            print("Error : No filepath found in the change mesh request")
            return

        self.handle_new_mesh(self.path, self.sequence_bounds[1])

        # self.mesh_array = []
        # for i in range(self.sequence_bounds[1]):
        #     path = self.path % i
        #     if not os.path.exists(path):
        #         print("Error, the path specified does not exist")
        #         return
        #     self.mesh_array.append(pv.read(path))
        self.state.mesh_representation = None
        self.replace_mesh(self.mesh_array[0])

        self.state.options = self.mesh_array[0].array_names.copy()
        self.state.options.insert(0, "None")

        print(self.state.options)
        self.computes_bounds_scalar()
        self.update_ui()
        response_body = {}
        if self.height - self.estimate_controller_height()[1] < 700:
            response_body["request_space"] = 1.65*self.height

        self.pl.reset_camera()
        return web.json_response(response_body, status=200)

    def compute_field_interval(self, field=None):
        if field is None:
            field = self.state.mesh_representation
        if field is None or field == "None":
            field = self.state.options[1]
        max_bound = -np.inf
        min_bound = np.inf
        for i in range(self.sequence_bounds[1]):
            l_max = self.mesh_array[i].get_array(field).max()
            l_min = self.mesh_array[i].get_array(field).min()
            if l_max > max_bound:
                max_bound = l_max
            if l_min < min_bound:
                min_bound = l_min
        return min_bound, max_bound

    def show_scalar_bar(self, field=None):
        if self.mesh_array is None:
            return
        if field is None:
            field = self.state.mesh_representation
        if field is None:
            return

        if self.bounds_scalar is None:
            self.computes_bounds_scalar()

        bounds = self.bounds_scalar.get(field, None)
        if bounds is not None:
            self.pl.mapper.lookup_table.SetTableRange(bounds[0], bounds[1])
            self.pl.add_scalar_bar(self.state.mesh_representation)

        return self.pl.mapper

    def computes_bounds_scalar(self):
        if self.state.options is None:
            return

        # store bounds and mapper for all the fields available except "None" which is the first one of the options array
        self.bounds_scalar = {}

        for field in self.state.options[1:]:
            self.bounds_scalar[field] = self.compute_field_interval(field)
        print(self.bounds_scalar)

    def replace_mesh(self, new_mesh):
        if new_mesh is None:
            return

        # set custom style
        kwargs_plot = {}
        if self.state.wireframe_on:
            kwargs_plot["style"] = "wireframe"

        # update mesh and set its active scalar field, as well as adding the scalar bar
        self.mesh = new_mesh

        # Set the active scalar and create it's scalar bar if it does not exist
        self.mesh.set_active_scalars(self.state.mesh_representation)

        self.pl.mapper = self.show_scalar_bar(self.state.mesh_representation)

        # Replace actor with the new mesh (automatically update the actor because they have the same name)
        self.actor = self.pl.add_mesh(self.mesh, style="wireframe" if self.state.wireframe_on else None,
                                      name="displayed_mesh", show_scalar_bar=True, scalar_bar_args={"mapper": self.pl.mapper})

    def start_server(self):
        try:
            self.server.start()
        except KeyboardInterrupt:
            # Stop the thread that manage the play of the mesh sequence
            self.timer.join()  # Wait for the timer thread to finish

    def update_ui(self):
        self.ui = self.build_ui()

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
            vuetify.VSlider(
                ref="slider",
                label="",
                min=self.sequence_bounds[0],
                max=self.sequence_bounds[1]-1,
                v_model=("slider_value", 8),
                step=1
            )
        return row

    @controller.set("play_button")
    def play_button(self):
        if self.sequence_bounds[1] <= 1:
            print("Impossible to start the sequence since it's a unique mesh")
            return

        # Invert the state of the play button and if it's playing start the timer updating frame at a fixed interval
        self.slider_playing = not self.slider_playing
        if self.slider_playing and not self.timer.is_alive():
            self.state.play_pause_icon = "mdi-pause"
            self.timer.start()
        else:
            self.state.play_pause_icon = "mdi-play"

    def build_warper(self):
        warper = vuetify.VCol(cols="6")
        with warper:
            if self.state.mesh_representation != "None" and self.state.mesh_representation is not None:
                ndim = self.mesh_array[0].get_array(self.state.mesh_representation).shape[1]
                for i in range(ndim):
                    vuetify.VTextField(type="number", label="warp",
                                       v_model=("warp_input", 0.0),
                                       ref=f"warp-{i}"
                                       )

        return warper

    def build_mesh_control_layout(self):
        layout = html.Div()
        with (layout):
            with vuetify.VRow(dense=True):
                with vuetify.VCol(cols="6"):
                    if self.state.options[0] is not None:
                        self.option_dropdown()
                self.build_warper()
            vuetify.VCheckbox(v_model=("wireframe_on",), label="Wireframe on")
            if self.sequence_bounds[1] != 1:
                self.build_slider()

            with vuetify.VBtn(click=self.request_full, style="position: absolute; bottom:25px; right:25px;", icon=True):
                vuetify.VIcon("mdi-fullscreen" if not self.state.is_full_screen else "mdi-fullscreen-exit")
        return layout

    def estimate_controller_height(self):
        if self.mesh_array is not None and self.state.mesh_representation is not None:
            ndim = self.mesh_array[0].get_array(self.state.mesh_representation).shape[1]
            return  30 * ndim, 9*30
        return 0.2*self.height, 9*30



    def build_ui(self):
        control_height = self.estimate_controller_height()[0]
        if not self.state.is_full_screen:
            plotter_height = self.height - control_height
            plotter_height = f"{plotter_height}px"
            width = f"{self.width}px"


        else:
            plotter_height = "100%"
            width = "100%"

        print(self.height)

        with VAppLayout(self.server) as layout:
            with layout.root:
                with html.Div(
                              style=f"height: {self.height}px ;width:{width}"):  # add the following arg: style="height: 100vh; width:100vw" to have the plotter taking all screen
                    with html.Div(ref="container", style=f"height:{plotter_height};padding: 0;"):
                        with vuetify.VCol(style=f"height:{plotter_height};padding: 0;"):
                            plotter_ui(self.pl, default_server_rendering=True, style="width: 100%; height:100%;background-color: black;")

                    with vuetify.VCol(style=f"height:{control_height}px;padding: 0;width:100%;"):
                        self.build_mesh_control_layout()
            return layout

    def on_server_bind(self, wslink_server):
        wslink_server.app.add_routes(self.my_routes)



    def request_full(self):
        self.server.js_call("container", "requestFullscreen")
        # if not self.state.is_full_screen:
        #     self.server.js_call("container", "requestFullscreen")
        # else:
        #     self.server.js_call("", "exitFullscreen()")
        self.state.is_full_screen = not self.state.is_full_screen
        self.update_ui()


if __name__ == "__main__":
    mv = MeshViewer()
    mv.start_server()
    # sm = ServerManager()
    # sm.start_server()
