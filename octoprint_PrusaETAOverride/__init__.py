from __future__ import absolute_import, unicode_literals

import re
import time

import octoprint.plugin
from octoprint.printer.estimation import PrintTimeEstimator


class PrusaETAPrintTimeEstimator(PrintTimeEstimator):
    def __init__(self, job_type):
        super(PrusaETAPrintTimeEstimator, self).__init__(job_type)
        self._logger = None
        self.last_update = time.time()
        self.estimated_time = -1

    def estimate(self, *args, **kwargs):
        if self.estimated_time < 0:
            if self._logger:
                self._logger.debug(
                    "self.estimated_time < 0: {}, calling default PrintTimeEstimator".format(
                        self.estimated_time
                    )
                )
            return PrintTimeEstimator.estimate(self, *args, **kwargs)
        eta = self.estimated_time - (int(time.time() - self.last_update)), "estimate"
        if self._logger:
            self._logger.debug(
                "New eta calculated: {} (self.estimated_time: {}, self.last_update: {}".format(
                    eta, self.estimated_time, self.last_update
                )
            )
        return eta


class PrusaetaoverridePlugin(octoprint.plugin.AssetPlugin):
    def __init__(self):
        self._estimator = None
        self.m73_mode = None

        self.m73_patterns = [
            # Prusa Firmware 3.3.0+
            re.compile(
                r"(?P<mode>\w+) MODE: Percent done: (?P<progress>-?\d+); print time remaining in mins: (?P<eta>-?\d+)(?:; Change in mins: (?P<eta_interaction>-?\d+))?"
            ),
            # Marlin 2.1.2+ (>= 20221208)
            re.compile(
                r"M73 Progress:\s+(?P<progress>\d+(?:\.\d+)?)%;(?: Time left:\s+(?P<eta>\d+(?:\.\d+)?)m;)?(?: Change:\s+(?P<eta_interaction>\d+(?:\.\d+)?)m;)?"
            ),
        ]
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

    def parse_line_m73(self, line):
        for r in self.m73_patterns:
            m = r.search(line)
            if m:
                return dict(
                    filter(lambda item: item[1] is not None, m.groupdict().items())
                )
        return None

    def parse_line_m114(self, line):
        m = self.m114_pattern.search(line)
        return m.groupdict() if m else None

    def parse_line(self, comm, line, *args, **kwargs):
        m = self.parse_line_m73(line)
        if m:

            # Prusa firmware supports different modes
            if "mode" in m:
                mode = m["mode"]

                # lock into first MODE we will see
                if self.m73_mode is None:
                    self.m73_mode = mode

                # but switch to NORMAL if we see it. SILENT will be properly chosen once fixed
                # in prusa firmware: https://github.com/prusa3d/Prusa-Firmware/pull/2735
                if self.m73_mode != mode and mode == "NORMAL":
                    self._logger.debug(
                        "Switching from mode {} to mode NORMAL".format(self.m73_mode)
                    )
                    self.m73_mode = "NORMAL"

                if mode != self.m73_mode:
                    return line

                self._logger.debug("Parsed update for mode: {}".format(mode))

            if "eta" in m:
                if not self._estimator:
                    self._logger.debug("Estimator not ready yet")
                    return line

                eta = int(m["eta"])
                if eta >= 0:
                    self._estimator.estimated_time = eta * 60
                    self._estimator.last_update = int(time.time())
                    self._logger.debug(
                        "Parsed eta update: {}s".format(self._estimator.estimated_time)
                    )

            if "progress" in m:
                progress = int(m["progress"])
                if progress >= 0:
                    self.set_progress(progress)
                    self._logger.debug("Parsed progress update: {}%".format(progress))

            comm._sendCommand("M114")
            return line

        z = self.parse_line_m114(line)
        if z:
            newZ = float(z["z"])
            comm._callback.on_comm_z_change(newZ)
            self._logger.debug("Parsed Z update: {}".format(newZ))
            return line

        return line

    def estimator_factory(self, *args, **kwargs):
        def factory(*args, **kwargs):
            self._estimator = PrusaETAPrintTimeEstimator(*args, **kwargs)
            self._estimator._logger = self._logger
            return self._estimator

        return factory

    def get_update_information(self):
        return dict(
            PrusaETAOverride=dict(
                displayName="Slicer M73 ETA override Plugin (Prusa; Marlin 2)",
                displayVersion=self._plugin_version,
                # version check: github repository
                type="github_release",
                user="arekm",
                repo="octopi_eta_override",
                current=self._plugin_version,
                # update method: pip
                pip="https://github.com/arekm/octopi_eta_override/archive/{target_version}.zip",
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
