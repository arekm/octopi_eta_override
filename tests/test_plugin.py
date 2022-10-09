import logging

import pytest

from octoprint_PrusaETAOverride import PrusaetaoverridePlugin

_logger = logging.getLogger("octoprint.plugins.PrusaETAOverride")
_logger.setLevel(logging.DEBUG)


@pytest.fixture
def plugin():
    p = PrusaetaoverridePlugin()
    p._logger = logging.getLogger(__name__)
    return p


# test MODE switch and lock
def test_mode(plugin):
    assert plugin.m73_mode is None
    plugin.parse_line(
        comm=None,
        line="SILENT MODE: Percent done: -1; print time remaining in mins: -1; Change in mins: -1",
    )
    assert plugin.m73_mode == "SILENT"
    plugin.parse_line(
        comm=None,
        line="NORMAL MODE: Percent done: -1; print time remaining in mins: -1; Change in mins: -1",
    )
    assert plugin.m73_mode == "NORMAL"
    plugin.parse_line(
        comm=None,
        line="SILENT MODE: Percent done: -1; print time remaining in mins: -1; Change in mins: -1",
    )
    assert plugin.m73_mode == "NORMAL"


# other tests


@pytest.mark.parametrize(
    "val,expected",
    [
        # Prusa
        (
            "NORMAL MODE: Percent done: 100; print time remaining in mins: 0; Change in mins: -1",
            {"mode": "NORMAL", "progress": "100", "eta": "0", "eta_interaction": "-1"},
        ),
        (
            "NORMAL MODE: Percent done: 50; print time remaining in mins: 3; Change in mins: 23",
            {"mode": "NORMAL", "progress": "50", "eta": "3", "eta_interaction": "23"},
        ),
        (
            "SILENT MODE: Percent done: 3; print time remaining in mins: 60; Change in mins: -1",
            {"mode": "SILENT", "progress": "3", "eta": "60", "eta_interaction": "-1"},
        ),
        (
            "SILENT MODE: Percent done: -1; print time remaining in mins: -1; Change in mins: -1",
            {"mode": "SILENT", "progress": "-1", "eta": "-1", "eta_interaction": "-1"},
        ),
        (
            "SILENT MODE: Percent done: -1; print time remaining in mins: -1",
            {"mode": "SILENT", "progress": "-1", "eta": "-1"},
        ),
        # Marlin, with M73_REPORT_PRUSA
        (
            "echo:  M73 Percent done: 10; Print time remaining in mins: 20; Change in mins: 7;",
            {"progress": "10", "eta": "20", "eta_interaction": "7"},
        ),
        (
            "echo:  M73 Percent done: 10; Print time remaining in mins: 20;",
            {"progress": "10", "eta": "20"},
        ),
        (
            "echo:  M73 Percent done: 10; Change in mins: 7;",
            {"progress": "10", "eta_interaction": "7"},
        ),
        (
            "echo:  M73 Percent done: 10;",
            {"progress": "10"},
        ),
        (
            "echo:  M73 Percent done:   5; Print time remaining in mins: 10; Change in mins: 3;",
            {"progress": "5", "eta": "10", "eta_interaction": "3"},
        ),
        (
            "echo:  M73 Percent done:   7.0; Print time remaining in mins: 10; Change in mins: 3;",
            {"progress": "7.0", "eta": "10", "eta_interaction": "3"},
        ),
        (
            "echo:  M73 Percent done:   7.0; Print time remaining in mins: 10.0; Change in mins: 3.0;",
            {"progress": "7.0", "eta": "10.0", "eta_interaction": "3.0"},
        ),
        # Marlin, without M73_REPORT_PRUSA
        (
            "echo:  M73 Progress: 10%; Time left: 20m; Change: 7m",
            {"progress": "10", "eta": "20", "eta_interaction": "7"},
        ),
        (
            "echo:  M73 Progress: 10%; Time left: 20m",
            {"progress": "10", "eta": "20"},
        ),
        (
            "echo:  M73 Progress: 10%; Change: 7m",
            {"progress": "10", "eta_interaction": "7"},
        ),
        (
            "echo:  M73 Progress: 10%;",
            {"progress": "10"},
        ),
        (
            "echo:  M73 Progress:   5%; Time left: 10m; Change: 3m",
            {"progress": "5", "eta": "10", "eta_interaction": "3"},
        ),
        (
            "echo:  M73 Progress:   7.0%; Time left: 10m; Change: 3m",
            {"progress": "7.0", "eta": "10", "eta_interaction": "3"},
        ),
        (
            "echo:  M73 Progress:   7.0%; Time left: 10.0m; Change: 3.0m",
            {"progress": "7.0", "eta": "10.0", "eta_interaction": "3.0"},
        ),
    ],
)
def test_parse_line_m73(plugin, val, expected):
    assert plugin.parse_line_m73(val) == expected


@pytest.mark.parametrize(
    "val,expected",
    [
        (
            "X:147.15 Y:97.24 Z:9.60 E:26.74 Count X: 140.92 Y:76.96 Z:9.84 E:25.82",
            {"z": "9.60"},
        ),
        (
            "X:119.59 Y:104.77 Z:5.60 E:50.03 Count X: 119.89 Y:107.02 Z:9.88 E:50.26",
            {"z": "5.60"},
        ),
        (
            "X:102.27 Y:97.54 Z:3.40 E:52.70 Count X: 122.35 Y:98.51 Z:9.87 E:51.51",
            {"z": "3.40"},
        ),
    ],
)
def test_parse_line_m114(plugin, val, expected):
    assert plugin.parse_line_m114(val) == expected
