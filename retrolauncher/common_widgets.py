import shlex
import urwid


class PlainButton(urwid.Button):
    def __init__(self, caption):
        super(PlainButton, self).__init__("")
        self._w = urwid.AttrMap(
            urwid.SelectableIcon(caption, 0), "button", "button_focus"
        )


class RLTerm(urwid.WidgetWrap):
    def __init__(self, cmd, app):
        self._app = app
        self._ow = app.root.original_widget

        btn = urwid.Button("Close")
        w = urwid.AttrMap(btn, "term_close_button", "term_close_button_focus")
        urwid.connect_signal(btn, "click", self.exit)

        footer = urwid.GridFlow([w], 9, 1, 1, "center")

        self.cmd = cmd

        self.header = urwid.Text(
            ("term_header", f"Running: {self.cmd}" + " " * 200), wrap="clip"
        )

        cmd2 = f"bash -c '{cmd}'"
        term = urwid.Terminal(shlex.split(cmd2), main_loop=app.loop)
        self._term = term
        self.frame = urwid.Frame(term, self.header, footer, focus_part="body")
        self._w = self.frame
        urwid.connect_signal(term, "closed", self.done)

    def done(self, *args, **kwargs):
        self.header.set_text(("term_header", f"Finished: {self.cmd}" + " " * 200))
        self.frame.set_focus("footer")

    def exit(self, *args, **kwargs):
        self._app.root.original_widget = self._ow
