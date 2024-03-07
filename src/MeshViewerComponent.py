import os

import streamlit as st
import streamlit.components.v1 as components
import requests
import json


class MeshViewerComponent:

    def __init__(self, mesh_path: str = None, sequence_size=None):
        if sequence_size is not None:
            self.mesh_array = []
            for i in range(sequence_size):
                path = mesh_path % i
                if not os.path.exists(path):
                    print("Error, the path specified does not exist")
                    return
        elif not os.path.exists(mesh_path):
            print("invalid mesh file path")
            return

        self.mesh_path = mesh_path
        self.set_mesh()


    def set_mesh(self):
        url = "http://127.0.0.1:8080/select_mesh"  # replace with your URL
        data = {"mesh_path": self.mesh_path}  # replace with your data

        headers = {"Content-Type": "application/json"}
        print("send request")
        response = requests.get(url, data=json.dumps(data), headers=headers)
    def show(self):
        components.iframe("http://127.0.0.1:8080/index.html", width=900, height=800)
