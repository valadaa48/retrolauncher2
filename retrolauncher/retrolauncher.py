#!/usr/bin/env python

import urwid
import json
import sys
import os
import time
import toml
import shutil
import shlex
from evdev import ecodes as e
from importlib import resources
from subprocess import Popen, call, check_output, PIPE
from os import path as op
from .input import InputPipe
from .stats_view import StatsView, StatsViewConky
from .browse import Browser
from .common_widgets import PlainButton, RLTerm

USER_CONFIG = op.expanduser("~/.config/retrolauncher/retrolauncher.toml")
THEME_PATH = op.expanduser("~/.config/retrolauncher/themes")

urwid.set_encoding("utf8")


def load_config():
    config = None
    with resources.path("retrolauncher.config", "retrolauncher.toml") as f:
        config = toml.load(f)
        if not op.exists(USER_CONFIG):
            os.makedirs(op.dirname(USER_CONFIG), exist_ok=True)
            shutil.copy(f, USER_CONFIG)
    try:
        user_config = toml.load(USER_CONFIG)
        config = {**config, **user_config}
    except:
        pass

    return config


def load_theme(name):
    with resources.path("retrolauncher.themes", "default.toml") as f:
        try:
            return toml.load(f"{THEME_PATH}/{name}.toml")
        except:
            return toml.load(f)


app = None
config = load_config()
theme = load_theme(config["theme"])


class AppMenu(urwid.WidgetWrap):
    def __init__(self):
        self.apps = config["apps"]
        body = [urwid.Divider()]
        for c in self.apps:
            if "cmd" not in c:
                button = urwid.Text(c["name"])
            else:
                button = PlainButton(c["name"])
                urwid.connect_signal(button, "click", self.item_chosen, c)
            body.append(button)
        lb = urwid.ListBox(urwid.SimpleFocusListWalker(body))
        self._w = urwid.Padding(lb, left=2, right=2)

    def item_chosen(self, button, c):
        app.run_cmd(c["cmd"], c.get("term", False))


class Header(urwid.WidgetWrap):
    def __init__(self):
        stats = urwid.AttrMap(urwid.Text("Stats", "left"), "hotkey")
        browser = urwid.AttrMap(urwid.Text("Browser", "right"), "hotkey")
        title = urwid.AttrMap(
            urwid.Text(config.get("title", "Retro Roller"), "center"), "title"
        )
        self._w = urwid.Columns([stats, title, browser])


class FixedText(urwid.Text):
    def __init__(self, name, width, *args, **kw):
        super(FixedText, self).__init__(name[:width], *args, **kw)
        self._width = width

    def pack(self, size=None, focus=False):
        return (self._width, None)


class MainView(urwid.WidgetWrap):
    def __init__(self):
        self.header = Header()

        self.app_menu = AppMenu()
        self.stats = StatsView()

        cols = urwid.Columns([("fixed", 30, self.app_menu), self.stats], dividechars=2)
        frame = urwid.Frame(cols, header=self.header, footer=self.footer())
        self._w = frame

    def footer(self):
        s = config["shortcuts"]
        w = []
        w.append(self.fixed_text(7, "f1", s, align="left"))
        w.append(self.fixed_text(10, "f2", s, align="left"))
        w.append((4, urwid.Text("", align="center", wrap="space")))
        w.append(self.fixed_text(9, "f3", s))
        w.append(self.fixed_text(9, "f4", s))
        w.append((4, urwid.Text("", align="center", wrap="space")))
        w.append(self.fixed_text(10, "f5", s, align="right"))
        w.append(self.fixed_text(7, "f6", s, align="right"))
        cols = urwid.Columns(w)
        return cols

    def fixed_text(self, width, f, s, align="center"):
        return (width, urwid.Text((f"{f}", s[f]["name"][:width]), align=align))

    def keypress(self, size, key):
        if key == "page down":
            app.root.original_widget = Browser(app, "/roms")
            return None
        elif key == "page up":
            app.root.original_widget = StatsViewConky(app)

            return None
        return super().keypress(size, key)

    def tick(self):
        self.stats.tick()


BUTTON_MAP = {
    e.BTN_DPAD_UP: "up",
    e.BTN_DPAD_DOWN: "down",
    e.BTN_DPAD_RIGHT: "right",
    e.BTN_DPAD_LEFT: "left",
    e.BTN_EAST: "enter",
    e.BTN_SOUTH: "esc",
    e.BTN_NORTH: "ctrl n",
    e.BTN_WEST: "ctrl p",
    e.BTN_TL: "page up",
    e.BTN_TR: "page down",
}


class App:
    def __init__(self):
        self.main_view = MainView()
        self.root = urwid.WidgetPlaceholder(self.main_view)
        self.loop = urwid.MainLoop(
            self.root,
            handle_mouse=False,
            unhandled_input=self.unhandled_input,
            palette=theme["palette"],
        )

        self.inputfd = self.loop.watch_pipe(self._input_reader)
        self._inputpipe = InputPipe(self.inputfd)

        self.start()

    def run_cmd(self, cmd, term=False):
        if term:
            self.root.original_widget = RLTerm(cmd, self)
        else:
            orig = self.root.original_widget
            self.root.original_widget = urwid.SolidFill(" ")
            self.stop()
            with open(config["log_file"], "a") as f:
                f.write(f"\nRetrolauncher: {cmd}\n\n")
            cmd_log = f"bash -c '{cmd}' &>> /tmp/retrolauncher.log"
            call(cmd_log, shell=True)
            self.root.original_widget = orig
            self.start()

    def _update_stats(self, loop, user_data):
        self.main_view.tick()
        self.loop.set_alarm_in(1, self._update_stats)

    def unhandled_input(self, key):
        if key == "q":
            raise urwid.ExitMainLoop()

    def start(self):
        self._stats_handle = self.loop.set_alarm_in(0, self._update_stats)
        self.loop.start()
        if self._inputpipe:
            self._inputpipe.start()

    def stop(self):
        self.loop.stop()
        self.loop.remove_alarm(self._stats_handle)
        if self._inputpipe:
            self._inputpipe.stop()

    def handle_shortcut(self, code):
        fkey = f"f{code - e.BTN_TRIGGER_HAPPY1 + 1}"
        sc = config["shortcuts"][fkey]
        action = sc.get("action", None)
        if action == "quit":
            raise urwid.ExitMainLoop()
        elif "cmd" in sc:
            self.run_cmd(sc["cmd"], sc.get("term", False))

    def _input_reader(self, data):
        try:
            j = json.loads(data.decode())
            code = j["code"]
            if code >= e.BTN_TRIGGER_HAPPY1 and code <= e.BTN_TRIGGER_HAPPY6:
                self.handle_shortcut(code)
            else:
                key = BUTTON_MAP.get(code)
                if key:
                    self.loop.process_input([key])
        except urwid.ExitMainLoop:
            raise
        except:
            pass


def main():
    global app
    urwid.escape.SHOW_CURSOR = ""
    app = App()
    app.config = config
    app.theme = theme
    app.loop.run()


if __name__ == "__main__":
    main()
