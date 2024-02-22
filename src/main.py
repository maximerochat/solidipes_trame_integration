import streamlit as st
import streamlit.components.v1 as components
from trame_viewer import MeshViewer
import subprocess
import threading
import asyncio
import pyvista as pv

def main():
    st.title("Simple Streamlit App")

    components.iframe("http://127.0.0.1:8080/index.html", width=600, height=400)


    # start_server()

def start_server():
    mv = MeshViewer(plotter=pv.Plotter())
    mv.start_server()




if __name__ == "__main__":
    main()