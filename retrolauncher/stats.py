import json
import time
import os
from os import path as op
from subprocess import check_output
from cachetools import TTLCache, cached
from humanize import naturalsize

BATTERY_CAPACITY = "/sys/class/power_supply/battery/capacity"
BATTERY_STATUS = "/sys/class/power_supply/battery/status"
BATTERY_CURRENT = "/sys/class/power_supply/battery/current_now"

GPU_GOV = "/sys/devices/platform/ff400000.gpu/devfreq/ff400000.gpu/governor"
DMC_GOV = "/sys/devices/platform/dmc/devfreq/dmc/governor"
CPU_GOV = "/sys/devices/system/cpu/cpufreq/policy0/scaling_governor"



def get_file_value(path, default="", strip=True):
    val = default
    if op.exists(path):
        val = open(path).read()
        if strip:
            val = val.strip()
    return val


@cached(TTLCache(1, ttl=5))
def get_battery_stats():
    return (
        int(get_file_value(BATTERY_CAPACITY, 0)),
        get_file_value(BATTERY_STATUS),
        int(get_file_value(BATTERY_CURRENT, 0)),
    )


@cached(TTLCache(1, ttl=5))
def get_time(fmt):
    return time.strftime(fmt)


def get_gov():
    return (
        get_file_value(CPU_GOV),
        get_file_value(GPU_GOV),
        get_file_value(DMC_GOV),
    )


@cached(TTLCache(1, ttl=5))
def get_ip():
    ssid = check_output("iwgetid -r || true", shell=True).decode().strip()
    j = json.loads(check_output("ip -j addr", shell=True).decode())
    for iface in j:
        if iface["ifname"] == "wlan0":
            for ai in iface["addr_info"]:
                if ai["family"] == "inet":
                    return ssid, ai["local"]
    return "", ""

@cached(TTLCache(1, ttl=60))
def get_kernel():
    return check_output("uname -r", shell=True).decode().strip()


@cached(TTLCache(1, ttl=5))
def get_disk(path):
    s = os.statvfs(path)
    return (
        s.f_bavail * s.f_frsize,
        s.f_blocks * s.f_frsize
    )
