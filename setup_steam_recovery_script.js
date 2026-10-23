(function() {
	if (window._rimdeckSteamRecovery) {
		return;
	}
	window._rimdeckSteamRecovery = true;

	function maybeReload(msg) {
		if (!msg || msg.indexOf('Failed to fetch dynamically imported module') < 0) {
			return;
		}
		if (sessionStorage.getItem('rimdeck_steam_reload')) {
			return;
		}
		sessionStorage.setItem('rimdeck_steam_reload', '1');
		location.reload();
	}

	window.addEventListener('unhandledrejection', function(event) {
		var message = event.reason && event.reason.message;
		maybeReload(message);
	});
})();
