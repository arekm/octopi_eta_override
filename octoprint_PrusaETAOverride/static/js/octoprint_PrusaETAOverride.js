/*
 * View model for octoprint_PrusaETAOverride.js
 *
 * License: AGPLv3
 */
$(function () {
    function PrusaETAOverrideViewModel(parameters) {
        var self = this;

        // assign the injected parameters, e.g.:
        self.filesViewModel = parameters[0];
	self.printerStateViewModel = parameters[1];
	self.progress = 0;

	self.original_processProgressData = self.printerStateViewModel._processProgressData;
	self.printerStateViewModel._processProgressData = function(data) {
		if (self.progress == 0 && data.completion > 0) {
			data.completion = 0.1;
		} else {
			data.completion = self.progress;
		}
		self.original_processProgressData(data);
	};

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin != "PrusaETAOverride") {
                return;
            }

            if (data.hasOwnProperty("progress")) {
		self.progress = data["progress"];
            }
        };
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: PrusaETAOverrideViewModel,
        dependencies: ["filesViewModel", "printerStateViewModel"]
    });
});
