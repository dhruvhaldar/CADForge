# Viewer refresh and rendering choice

The current renderer remains NiceGUI's browser scene, controlled entirely from Python.

## Refresh behavior

The previous implementation dispatched GLB creation and immediately marked the result Ready. The updated pipeline reports Loading preview, waits for NiceGUI's browser-side object readiness, swaps in the replacement, and refreshes the canvas size/projection before reporting Ready. The previous successful mesh remains visible while the asset loads. Edits during preview loading invalidate that replacement, just as edits during CAD generation invalidate a worker result.

The scene targets 60 FPS. Fit on update is optional and off by default, preserving the user's camera for repeated edits of the same model. Static lighting and axes remain in the scene instead of being deleted with each mesh.

Regression tests cover updates without viewport interaction, camera preservation, delayed GLB delivery, and edits during preview loading. Testing uses Chrome; the original interaction-dependent symptom was not reproduced in headless Chrome, but the asynchronous readiness gap was confirmed in the implementation and addressed. The embedded browser should be reloaded to pick up the new viewer.

## VTK assessment

Python VTK with Trame is a viable future viewer backend. Trame exposes both local browser rendering and remote server rendering from Python VTK pipelines. Local rendering transfers geometry to the browser; remote rendering sends images and adds server-side rendering requirements. See [Kitware's VTK tutorial](https://kitware.github.io/trame/guide/tutorial/vtk.html) and [trame-vtk](https://github.com/Kitware/trame-vtk).

For the current six-model CAD preview, switching backends would add a second visualization integration without resolving the application-level handoff by itself. Keep NiceGUI for this release. Reconsider VTK/Trame when the product needs scientific scalar fields, clipping/contouring pipelines, or significantly larger datasets. OpenCascade/build123d should remain the authoritative CAD geometry engine in either case. No VTK dependency or custom JavaScript frontend has been added.
