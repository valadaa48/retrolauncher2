import os
import time
import threading
import json
from evdev import InputDevice, ecodes as e


def inputdevice_close(self):
    if self.fd > -1:
        try:
            os.close(self.fd)
        finally:
            self.fd = -1


InputDevice.close = inputdevice_close


class InputPipe(object):
    def __init__(self, fd):
        self._fd = fd

    def start(self):
        self._t = threading.Thread(target=self._loop)
        self._t.setDaemon(True)
        self._active = True
        self._t.start()

    def stop(self):
        self._active = False
        self._t.join()

    def _loop(self):
        hotkey_on = False
        dev = InputDevice("/dev/input/by-path/platform-odroidgo2-joypad-event-joystick")
        while self._active:
            ev = dev.read_one()
            if ev:
                if ev.code == e.BTN_TRIGGER_HAPPY3:
                    hotkey_on = bool(ev.value)
                if ev.value == 1 and not hotkey_on:
                    msg = {"code": ev.code}
                    try:
                        os.write(self._fd, str.encode(json.dumps(msg)))
                    except:
                        pass
            time.sleep(0.01)
