from minipy3dr import App

app = App(title="はじめての 3D")
cube = app.cube(position=(0, 0, -5), size=2, color=(220, 120, 80))
app.light()

def update(app, delta):
    app.rotate(cube, y=delta)

app.run(update=update)