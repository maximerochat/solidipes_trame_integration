# Trame integration in Solidipes
This repo is a work in progress of potential solution to the pyvista deprecation of other backend than Trame

## TODO 
- make more warp fit to the different warp method (warp might be a vector or even a matrix)




## Ideas
Main problem now able to set a select field dropdown that change when a new mesh is loaded. 
try spawning a child server 
````
new_server = self.server.create_child_server()
````

- Add a request on the creation of the component in streamlit that specify the size it is allocated
- Add request to specify whether it's a sequence of images or not. If yes give size

Problems : 
- wireframe checkbox not propagating well when
- Scalar bar is showing on change when in local rendering mode


Idea : 
replace handle reload of the ui ? 


Planning : 

- Faire une API pour streamlit:
  - qunad on start avec select mesh return la width et height que streamlit doit lui allouer
  
- le warp voir comment géré les différente taille de scalaire/vecteur/tenseur

- Add min-max fields to manually select min max of scalar bar and add a button to automatically compute min-max 
- Warp can be done on 1 input only and use pyvista scale by scalar, scale by vector,
- Enable possibility to warp a field and show another one
- choose components of the vector field to show
- add a radio field that allow to choose sepcific function computed on the scalar field 
  

- Client side rendering, detect when local and disable option to play 




Paraview library :
https://github.com/Kitware/trame-vtk