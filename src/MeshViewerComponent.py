import os

import streamlit as st
import streamlit.components.v1 as components
import requests
import json


class MeshViewerComponent:

    def __init__(self, mesh_path: str = None, sequence_size=1):
        if sequence_size != 1:
            self.mesh_array = []
            for i in range(sequence_size):
                path = mesh_path % i
                if not os.path.exists(path):
                    print("Error, the path specified does not exist")
                    return
        elif not os.path.exists(mesh_path):
            print("invalid mesh file path")
            return
        
        self.sequence_size = sequence_size
        self.mesh_path = mesh_path
        self.width = 800
        self.height = 900
        self.set_mesh()


    def set_mesh(self):
        url = "http://127.0.0.1:8080/select_mesh"
        data = {
            "mesh_path": self.mesh_path,
            "nbr_frames": self.sequence_size,
            "width": self.width,
            "height": self.height
                }

        headers = {"Content-Type": "application/json"}
        print("send request")
        response = requests.get(url, data=json.dumps(data), headers=headers)
        resp_body = response.json()
        if "request_space" in resp_body:
            self.height = resp_body["request_space"]
    def show(self):
        components.iframe("http://127.0.0.1:8080/index.html", width=self.width, height=self.height) # , scrolling=True
