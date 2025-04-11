# SayoDevice O3C Screen Reader

> Allows you to stream the screen of your **O3C** HID to your PC and output it in a separate window, which can be captured by OBS/Streamlabs/etc.<br>
> *Useful for streaming/showcasing*.

## OpenGL (Recommended)

Musthave update. Fast realtime render, NEW ICON OMG.

![image](Static/Showcase%20-%20OpenGL.png)
![image](Static/Showcase%20-%20OpenGL2.png)

## Tkinter

I don't like TKinter overall, it is quite slow, which is the reason why I dropped it and moved towards OpenGL.

![image](Static/Showcase%20-%20Tkinter.png)

## Build

For building the project I used the [PyInstaller](https://pypi.org/project/pyinstaller/).<br>
**WARNING**: Pyinstaller does not automatically collect the *GLFW.dll*, so you will need to include it manually.

```bash

pyinstaller --onefile --add-binary "...\Python\Python312\Lib\site-packages\glfw\glfw3.dll;." --hidden-import=glfw main_opengl.py
```
<br>

## Known issues, which I will never address (probably)

* Window dragging causes the render to stop (it will continue after drag stop).
    * _Don't drag it :skull:_
* Window hiding (minimizing) may hide the window from recognition by OBS/etc.
    * In this case, please unhide the window. The visibility doesn't matter, it depends only on window state. <br>
    _You can still open/put anything over the window. It will still be rendered successfully!_

