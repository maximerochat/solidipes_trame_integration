# Trame integration in Solidipes
This repo is a work in progress of potential solution to the pyvista deprecation of other backend than Trame

## TODO 
- make more warp fit to the different warp method (warp might be a vector or even a matrix)

- make a play animation button for multiframes



## Ideas
Main problem now able to set a select field dropdown that change when a new mesh is loaded. 
try spawning a child server 
````
`new_server = self.server.create_child_server()
````

- Add a request on the creation of the component in streamlit that specify the size it is allocated
- Add request to specify whether it's a sequence of images or not. If yes give size

Problems : 
- wireframe checkbox not propagating well when
- Scalar bar is showing on change when in local rendering mode

