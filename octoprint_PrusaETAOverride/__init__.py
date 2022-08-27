from __future__ import absolute_import, unicode_literals

import logging
import re
import time

import octoprint.plugin
from octoprint.printer.estimation import PrintTimeEstimator


class PrusaETAPrintTimeEstimator(PrintTimeEstimator):
    def __init__(self, job_type):
        super(PrusaETAPrintTimeEstimator, self).__init__(job_type)
        self._logger = logging.getLogger("octoprint.plugins.PrusaETAOverride")
        self.last_update = time.time()
        self.estimated_time = -1

    def estimate(self, *args, **kwargs):
        if self.estimated_time < 0:
            self._logger.debug(
                "self.estimated_time < 0: {}, calling default PrintTimeEstimator".format(
                    self.estimated_time
                )
            )
            return PrintTimeEstimator.estimate(self, *args, **kwargs)
        eta = self.estimated_time - (int(time.time() - self.last_update)), "estimate"
        self._logger.debug(
            "New eta calculated: {} (self.estimated_time: {}, self.last_update: {}".format(
                eta, self.estimated_time, self.last_update
            )
        )
        return eta


class PrusaetaoverridePlugin(octoprint.plugin.AssetPlugin):
    def __init__(self):
        self._logger = logging.getLogger("octoprint.plugins.PrusaETAOverride")

        self._estimator = None
        self.m73_mode = None

        # do not match lines with negative progress ("... Percent done: -1; ...")
        self.m73_pattern = re.compile(
            r"(?P<mode>\w+) MODE: Percent done: (?P<progress>\d+); print time remaining in mins: (?P<eta>\d+)(?:; Change in mins: (?P<eta_change>-?\d+))?"
        )
        self.m114_pattern = re.compile(r"^X:\d+\.\d+ Y:\d+\.\d+ Z:(?P<z>\d+\.\d+) ")

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {"js": ["js/octoprint_PrusaETAOverride.js"]}

    def set_progress(self, progress):
        if self._printer.is_printing():
            self._plugin_manager.send_plugin_message(
                self._identifier, dict(progress=int(progress))
            )

    def parse_line(self, comm, line, *args, **kwargs):
        if not self._estimator:
            self._logger.debug("Estimator not ready yet")
            return line

        m = self.m73_pattern.search(line)
        if m:

            mode = m.group("mode")

            # lock into first MODE we will see
            if self.m73_mode is None:
                self.m73_mode = mode

            # but switch to NORMAL if we see it. SILENT will be properly choosen once fixed
            # in prusa firmware: https://github.com/prusa3d/Prusa-Firmware/pull/2735
            if self.m73_mode != mode and mode == "NORMAL":
                self._logger.debug(
                    "Switching from mode {} to mode NORMAL".format(self.m73_mode)
                )
                self.m73_mode = "NORMAL"

            if mode != self.m73_mode:
                return line

            self._estimator.estimated_time = int(m.group("eta")) * 60
            self._estimator.last_update = int(time.time())
            progress = int(m.group("progress"))
            self.set_progress(progress)
            self._logger.debug(
                "Parsed updates for mode {} - time: {}s, progress: {}%".format(
                    mode, self._estimator.estimated_time, progress
                )
            )
            comm._sendCommand("M114")
            return line

        z = self.m114_pattern.search(line)
        if z:
            newZ = float(z.group("z"))
            comm._callback.on_comm_z_change(newZ)
            self._logger.debug("Parsed Z update: {}".format(newZ))
            return line

        return line

    def estimator_factory(self, *args, **kwargs):
        def factory(*args, **kwargs):
            self._estimator = PrusaETAPrintTimeEstimator(*args, **kwargs)
            return self._estimator

        return factory

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
                pip="https://github.com/kanocz/octopi_eta_override/archive/{target_version}.zip",
            )
        )


__plugin_name__ = "Prusa ETA override Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PrusaetaoverridePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.received": __plugin_implementation__.parse_line,
        "octoprint.printer.estimation.factory": __plugin_implementation__.estimator_factory,
    }
