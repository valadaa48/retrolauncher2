import shlex
import urwid


class StatsView(urwid.WidgetWrap):
    def __init__(self, app):
        self._app = app
        self._w = urwid.Terminal(shlex.split("conky"), main_loop=self._app.loop)

    def keypress(self, size, key):
        if key == "page down":
            self._w.terminate()
            self._app.root.original_widget = self._app.main_view
            return None
        return super().keypress(size, key)


