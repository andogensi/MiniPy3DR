from minipy3dr import App

app = App()
sphere = app.obj("assets/sphere.obj", position=(0, 0, -5), color=(120, 200, 255))
app.light()
app.run()