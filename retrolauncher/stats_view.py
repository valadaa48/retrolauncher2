import shlex
import urwid
from . import stats
from humanize import naturalsize


class StatsItem(urwid.WidgetWrap):
    def __init__(self, title, widget=None):
        self.title = urwid.Text(("stats_title", f"{title}:"), "right")
        if widget is None:
            widget = urwid.Text(("stats_value", ""))

        self.value = widget

        col1 = ("weight", 0.35, self.title)
        col2 = ("weight", 1.0, self.value)
        self._w = urwid.Columns([col1, col2], dividechars=1)

    def set_text(self, value):
        self.value.set_text(("stats_value", value))


class DiskStatus(urwid.ProgressBar):
    def __init__(self, path, *args, **kwargs):
        super(DiskStatus, self).__init__(*args, **kwargs)

        self.path = path
        self.tick()

    def get_text(self):
        return f"{naturalsize(self.avail, gnu=True)} Free"

    def tick(self):
        self.avail, self.total = stats.get_disk(self.path)
        self.set_completion((self.total - self.avail) / self.total * 100.0)


class BatteryStatus(urwid.ProgressBar):
    def __init__(self, normal, complete, *args, **kwargs):
        super(BatteryStatus, self).__init__(normal, complete, *args, **kwargs)
        self.tick()

    def get_text(self):
        return self.text

    def tick(self):
        cap, status, current = stats.get_battery_stats()
        current /= 1000.0
        self.set_completion(cap)
        self.text = f"{cap}% {current}mA"


class StatsViewConky(urwid.WidgetWrap):
    def __init__(self, app):
        self._app = app
        self._w = urwid.Terminal(shlex.split("conky"), main_loop=self._app.loop)

    def keypress(self, size, key):
        if key == "page down":
            self._w.terminate()
            self._app.root.original_widget = self._app.main_view
            return None
        return super().keypress(size, key)

class StatsView(urwid.WidgetWrap):
    def __init__(self):
        self.ip = StatsItem("IP")
        self.ssid = StatsItem("ssid")
        self.bat = StatsItem("Bat", BatteryStatus("bat_normal", "bat_complete"))
        self.cpu_freq = StatsItem("Freq")
        self.cpu = StatsItem("CPU")
        self.gpu = StatsItem("GPU")
        self.dmc = StatsItem("DMC")
        self.kernel = StatsItem("Kernel")

        self.root_disk = StatsItem("/", DiskStatus("/", "bat_normal", "bat_complete"))

        self._w = urwid.ListBox(
            [
                urwid.Divider(),
                self.ip,
                self.ssid,
                urwid.Divider(),
                self.bat,
                urwid.Divider(),
                self.cpu_freq,
                self.cpu,
                self.gpu,
                self.dmc,
                urwid.Divider(),
                self.root_disk,
                urwid.Divider(),
                self.kernel,
            ]
        )

        self._w._selectable = False

    def tick(self):
        ssid, ip = stats.get_ip()
        self.ip.set_text(ip)
        self.ssid.set_text(ssid)

        self.cpu_freq.set_text(f"{stats.get_cpu_freq() / 1000.0} MHz")
        cpu, gpu, dmc = stats.get_gov()
        self.cpu.set_text(cpu)
        self.gpu.set_text(gpu)
        self.dmc.set_text(dmc)

        self.root_disk.value.tick()
        self.bat.value.tick()

        self.kernel.set_text(stats.get_kernel())
