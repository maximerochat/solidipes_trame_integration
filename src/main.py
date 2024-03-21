import streamlit as st
import streamlit.components.v1 as components
from trame_viewer import MeshViewer
from MeshViewerComponent import MeshViewerComponent

import subprocess
import threading
import asyncio
import pyvista as pv

def main():
    st.title("Simple Streamlit App")

    # components.iframe("http://127.0.0.1:8080/index.html", width=600, height=400)
    value = st.number_input(label="frame number",value=0)
    formatted_num = "{:02d}".format(int(value))
    mesh_viewer = MeshViewerComponent(f"/home/maxime/Documents/EPFL/job/dataset/jtcam-data-10172/data/T3DE/Results/VTK/results_corr-%06d.vtk", 50)
    print(value)
    mesh_viewer.show()
    # start_server()

def start_server():
    mv = MeshViewer(plotter=pv.Plotter())
    mv.start_server()




if __name__ == "__main__":
    main()
