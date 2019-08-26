# coding=utf-8
from __future__ import absolute_import
import octoprint.plugin
import re
import time
from octoprint.printer.estimation import PrintTimeEstimator
from octoprint.events import eventManager, Events

eta = 0
oldZ = 0.0

ts = int(time.time())
r = re.compile(
    r'NORMAL MODE: Percent done: \d+; print time remaining in mins: (\d+)')
p = re.compile(
    r'^X:\d+\.\d+ Y:\d+\.\d+ Z:(\d+\.\d+) ')


def pETAeveryLine(comm, line, *args, **kwargs):
    global eta, r, ts, oldZ
    m = r.search(line)
    if m:
        eta = int(m.group(1)) * 60
        ts = int(time.time())
        comm._sendCommand("M114")
    z = p.search(line)
    if z:
        newZ = float(z.group(1))
        if newZ != oldZ:
            eventManager().fire(Events.Z_CHANGE, {"new": newZ, "old": oldZ})
            oldZ = newZ
    return line


class PrusaetaoverridePlugin(octoprint.plugin.OctoPrintPlugin):

    def get_update_information(self):
        return dict(
            PrusaETAOverride=dict(
                displayName="Prusa ETA override Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="kanocz",
                repo="octopi_eta_override",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/kanocz/octopi_eta_override/archive/{target_version}.zip"
            )
        )


class pETAPrintTimeEstimator(PrintTimeEstimator):
    def __init__(self, job_type):
        super(pETAPrintTimeEstimator, self).__init__(job_type)

    def estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType):
        return eta - (int(time.time()) - ts), "estimate"


def pETAfactory(*args, **kwargs):
    return pETAPrintTimeEstimator


__plugin_name__ = "Prusa ETA override Plugin"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PrusaetaoverridePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.received": pETAeveryLine,
        "octoprint.printer.estimation.factory": pETAfactory
    }
