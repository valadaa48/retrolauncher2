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


class InputPipe:
    repeat_mask = { e.BTN_DPAD_UP, e.BTN_DPAD_DOWN, e.BTN_DPAD_LEFT, e.BTN_DPAD_RIGHT }

    def __init__(self, fd, repeat_rate=0.05, poll_freq=0.01):
        self._fd = fd
        self.repeat_rate = repeat_rate
        self.poll_freq = poll_freq

    def start(self):
        self._t = threading.Thread(target=self._loop)
        self._t.setDaemon(True)
        self._active = True
        self._t.start()

    def stop(self):
        self._active = False
        self._t.join()

    def _loop(self):
        dev = InputDevice("/dev/input/by-path/platform-odroidgo2-joypad-event-joystick")
        last_repeat = time.time()

        while self._active:
            ev = dev.read_one()
            active = set(dev.active_keys())
            if e.BTN_TRIGGER_HAPPY5 in active:
                time.sleep(self.poll_freq)
                continue

            if ev:
                last_repeat = time.time() + self.repeat_rate * 5
                if ev.value == 1:
                    self._write(ev.code)
            else:
                now = time.time()
                if now - last_repeat >= self.repeat_rate:
                    last_repeat = now
                    active_mask = active & InputPipe.repeat_mask
                    if active_mask:
                        for k in active_mask:
                            self._write(k)
            time.sleep(self.poll_freq)

    def _write(self, code):
        try:
            msg = {"code": code}
            os.write(self._fd, str.encode(json.dumps(msg)))
        except:
            pass
