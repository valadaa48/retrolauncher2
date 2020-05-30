import re
import os
import shlex
from os import path as op
import urwid
from .common_widgets import PlainButton

app = None
browser = None


class ContextMenu(urwid.WidgetWrap):
    signals = ["close"]

    def __init__(self, browser, path):
        self.browser = browser
        self.path = path
        buttons = []
        for ctx in app.config["context_menu"]:
            pm = ctx.get("path", None)
            if pm and pm not in path:
                continue
            btn = PlainButton(ctx["name"])
            buttons.append(btn)
            urwid.connect_signal(btn, "click", self.item_chosen, ctx)

        lb = urwid.ListBox(urwid.SimpleFocusListWalker(buttons))
        fr = urwid.LineBox(lb, "Launch With...")
        self._w = fr

    def keypress(self, size, key):
        key = super().keypress(size, key)
        if key == "esc":
            self.browser.close_context_menu()

        return key

    def item_chosen(self, button, ctx):
        path = f'"{self.path}"'
        self.browser.close_context_menu()
        app.run_cmd(ctx["cmd"].format(path=path), ctx.get("term", False))


class FileWidget(urwid.TreeWidget):
    unexpanded_icon = urwid.AttrMap(
        urwid.TreeWidget.unexpanded_icon, "cm_dirmark", "cm_dirmark_focus"
    )
    expanded_icon = urwid.AttrMap(
        urwid.TreeWidget.expanded_icon, "cm_dirmark", "cm_dirmark_focus"
    )

    def __init__(self, node):
        super().__init__(node)
        self._w = urwid.AttrMap(self._w, "cm_normal", "cm_focus")

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key == "page down":
            return None
        elif key == "right":
            key = "page down"
        elif key == "left":
            key = "page up"
        elif key == "esc":
            key = "left"

        key = super().keypress(size, key)
        if key == "enter":
            browser.show_context_menu(self.get_node().get_value())
            return None
        return key

    def get_display_text(self):
        return self.get_node().get_key()


class DirWidget(FileWidget):
    def __init__(self, node):
        super().__init__(node)
        path = node.get_value()
        self.expanded = False
        self.update_expanded_icon()

    def keypress(self, size, key):
        if key == "enter" or key == "right":
            self.expanded = not self.expanded
            self.update_expanded_icon()
            return None

        return super().keypress(size, key)

    def get_display_text(self):
        node = self.get_node()
        if node.get_depth() == 0:
            return "/"
        else:
            return node.get_key()


class FileNode(urwid.TreeNode):
    def __init__(self, path, parent=None):
        depth = path.count("/")
        key = op.basename(path)
        super().__init__(path, key=key, parent=parent, depth=depth)

    def load_parent(self):
        parentname, myname = op.split(self.get_value())
        parent = DirectoryNode(parentname)
        parent.set_child_node(self.get_key(), self)
        return parent

    def load_widget(self):
        return FileWidget(self)


class DirectoryNode(urwid.ParentNode):
    def __init__(self, path, parent=None):
        if path == "/":
            depth = 0
            key = None
        else:
            depth = path.count("/")
            key = op.basename(path)
        super().__init__(path, key=key, parent=parent, depth=depth)

    def load_parent(self):
        parentname, myname = op.split(self.get_value())
        parent = DirectoryNode(parentname)
        parent.set_child_node(self.get_key(), self)
        return parent

    def load_child_keys(self):
        dirs = []
        files = []
        path = self.get_value()
        for f in sorted(os.listdir(path)):
            if op.isdir(op.join(path, f)):
                dirs.append(f)
            else:
                files.append(f)

        self.dir_count = len(dirs)
        keys = dirs + files
        return keys

    def load_child_node(self, key):
        index = self.get_child_index(key)
        path = op.join(self.get_value(), key)
        if index < self.dir_count:
            return DirectoryNode(path, parent=self)
        else:
            path = op.join(self.get_value(), key)
            return FileNode(path, parent=self)

    def load_widget(self):
        return DirWidget(self)


class Browser(urwid.WidgetWrap):
    def __init__(self, _app, start_dir):
        global app
        global browser
        app = _app
        browser = self
        header = urwid.AttrWrap(urwid.Text("File Browser", "center"), "title")
        main = urwid.Text(("hotkey", "Main"), "left")
        hcols = urwid.Columns([main, header, urwid.Text("")])

        tree = urwid.TreeListBox(urwid.TreeWalker(DirectoryNode(start_dir)))
        self._w = urwid.Frame(
            urwid.AttrWrap(tree, "cm_body"), header=hcols, footer=None,
        )

    def show_context_menu(self, path):
        cm = ContextMenu(self, path)
        overlay = urwid.Overlay(cm, self._w, "center", 40, "middle", 16)
        self._w = overlay

    def close_context_menu(self):
        self._w = self._w.bottom_w
        app.loop.draw_screen()

    def keypress(self, size, key):
        if key == "page up":
            app.root.original_widget = app.main_view
            return None
        return super().keypress(size, key)
