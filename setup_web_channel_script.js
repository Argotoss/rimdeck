const BadgeState = @badge_state_js@;
const PAGE_MODE = '@page_mode@';
const INJECT_DELAY_MS = @inject_delay_ms@;

const TILE_SELECTORS = ['.workshopItem', '[data-publishedfileid]'];

function rimdeckBrowseTileFromLink(link) {
	const aspect = link.closest('.aspectratio_16x9');
	if (aspect) {
		const panel = aspect.closest('.Panel');
		if (panel) {
			return panel;
		}
	}
	return link.closest('.workshopItem')
		|| link.closest('[data-publishedfileid]')
		|| link.closest('.Panel');
}

function rimdeckModTitleFromBrowseTile(tile, modId) {
	if (!tile) {
		return modId;
	}
	const legacyTitle = tile.querySelector('.workshopItemTitle');
	if (legacyTitle && legacyTitle.textContent.trim()) {
		return legacyTitle.textContent.trim();
	}
	const links = tile.querySelectorAll('a[href*="filedetails/?id="]');
	for (const link of links) {
		const text = link.textContent.trim();
		if (text) {
			return text;
		}
	}
	const img = tile.querySelector('img[alt]');
	if (img && img.alt) {
		return img.alt;
	}
	return modId;
}

function rimdeckFindBrowseTitleElement(tile) {
	if (!tile) {
		return null;
	}
	const legacyTitle = tile.querySelector('.workshopItemTitle');
	if (legacyTitle) {
		return legacyTitle;
	}
	const links = tile.querySelectorAll('a[href*="filedetails/?id="]');
	for (const link of links) {
		if (link.textContent.trim()) {
			return link;
		}
	}
	return null;
}

function rimdeckCollectBrowseModEntries() {
	const entries = [];
	const seenModIds = new Set();
	document.querySelectorAll('a[href*="filedetails/?id="]').forEach(function(link) {
// jscpd:ignore-start
		const match = link.href.match(/id=(\d+)/);
		if (!match) {
			return;
		}
		const modId = match[1];
		if (seenModIds.has(modId)) {
			return;
		}
// jscpd:ignore-end
		const tile = rimdeckBrowseTileFromLink(link);
		if (!tile) {
			return;
		}
		seenModIds.add(modId);
		entries.push({ modId: modId, tile: tile });
	});
	return entries;
}

function rimdeckModStatus(installedMods, addedMods, modId) {
	const installedSet = window._rimdeckInstalledSet;
	const addedSet = window._rimdeckAddedSet;
	if (installedSet && installedSet.has(modId)) {
		return BadgeState.INSTALLED;
	}
	if (addedSet && addedSet.has(modId)) {
		return BadgeState.ADDED;
	}
	if (installedMods.includes(modId)) {
		return BadgeState.INSTALLED;
	}
	if (addedMods.includes(modId)) {
		return BadgeState.ADDED;
	}
	return BadgeState.DEFAULT;
}

function findModTile(modId) {
	for (const selector of TILE_SELECTORS) {
		const tiles = document.querySelectorAll(selector);
		for (const tile of tiles) {
			const link = tile.querySelector(`a[href*="id=${modId}"]`);
			if (link) {
				return tile;
			}
		}
	}
	const directLink = document.querySelector(`a[href*="id=${modId}"]`);
	if (directLink) {
		return rimdeckBrowseTileFromLink(directLink);
	}
	return null;
}

function rimdeckFindQuickViewButtons() {
	return [...document.querySelectorAll(
		'div.Panel[role="button"] svg.SVGIcon_MagnifyingGlass'
	)].map(function(svg) {
		return svg.closest('div.Panel[role="button"]');
	}).filter(Boolean);
}

// jscpd:ignore-start
function rimdeckModIdFromHubCard(quickViewEl) {
	let el = quickViewEl;
	for (let depth = 0; depth < 12 && el; depth++) {
		const link = el.querySelector('a[href*="filedetails/?id="]');
		if (link) {
			const match = link.href.match(/id=(\d+)/);
// jscpd:ignore-end
			if (match) {
				return match[1];
			}
		}
		el = el.parentElement;
	}
	return null;
}

function rimdeckModTitleFromHubCard(quickViewEl, modId) {
	let el = quickViewEl;
	for (let depth = 0; depth < 12 && el; depth++) {
		const link = el.querySelector('a[href*="filedetails/?id="]');
		if (link) {
			return link.getAttribute('title') || link.textContent.trim() || modId;
		}
		el = el.parentElement;
	}
	return modId;
}

function rimdeckApplyHubButtonState(btn, status) {
	btn.classList.remove('rimdeck-hub-installed', 'rimdeck-hub-added', 'rimdeck-hub-default');
	if (status === BadgeState.INSTALLED) {
		btn.classList.add('rimdeck-hub-installed');
		btn.title = 'Already installed';
		btn.textContent = '✓';
	} else if (status === BadgeState.ADDED) {
		btn.classList.add('rimdeck-hub-added');
		btn.title = 'Preparing to download';
		btn.textContent = '-';
	} else {
		btn.classList.add('rimdeck-hub-default');
		btn.title = 'Add to list';
		btn.textContent = 'Add to list';
	}
}

// jscpd:ignore-start
function rimdeckHubCardRoot(quickViewEl) {
	let el = quickViewEl;
	for (let depth = 0; depth < 12 && el; depth++) {
		const link = el.querySelector('a[href*="filedetails/?id="]');
		if (link) {
			return el;
// jscpd:ignore-end
		}
		el = el.parentElement;
	}
	return null;
}

function rimdeckFindHubAddButton(modId, quickViewEl) {
	const card = rimdeckHubCardRoot(quickViewEl);
	if (!card) {
		return null;
	}
	return card.querySelector('.rimdeck-hub-add-btn[data-mod-id="' + modId + '"]');
}

function rimdeckFindHubAddButtonByModId(modId) {
	return document.querySelector('.rimdeck-hub-add-btn[data-mod-id="' + modId + '"]');
}

function rimdeckCleanupHubLegacyBadges(card) {
	if (!card) {
		return;
	}
	card.querySelectorAll('.rimdeck-modstatus-badge').forEach(function(badge) {
		badge.remove();
	});
}

function rimdeckSyncModListsFromSets() {
	if (window._rimdeckInstalledSet) {
		window._rimdeckInstalledMods = Array.from(window._rimdeckInstalledSet);
	}
	if (window._rimdeckAddedSet) {
		window._rimdeckAddedMods = Array.from(window._rimdeckAddedSet);
	}
}

function rimdeckRecordModStatus(modId, status) {
	if (!window._rimdeckInstalledSet) {
		window._rimdeckInstalledSet = new Set(window._rimdeckInstalledMods || []);
	}
	if (!window._rimdeckAddedSet) {
		window._rimdeckAddedSet = new Set(window._rimdeckAddedMods || []);
	}
	if (status === BadgeState.INSTALLED) {
		window._rimdeckInstalledSet.add(modId);
		window._rimdeckAddedSet.delete(modId);
	} else if (status === BadgeState.ADDED) {
		window._rimdeckAddedSet.add(modId);
	} else {
		window._rimdeckAddedSet.delete(modId);
	}
	rimdeckSyncModListsFromSets();
}

function rimdeckUpdateHubAddButton(modId, status) {
	rimdeckRecordModStatus(modId, status);

	const existingBtn = rimdeckFindHubAddButtonByModId(modId);
	if (existingBtn) {
		rimdeckApplyHubButtonState(existingBtn, status);
		const card = rimdeckHubCardRoot(existingBtn);
		rimdeckCleanupHubLegacyBadges(card);
		return;
	}

	if (typeof window.rimdeckInjectHubAddButtons === 'function') {
		window.rimdeckInjectHubAddButtons();
	}
}
window.rimdeckUpdateHubAddButton = rimdeckUpdateHubAddButton;

function rimdeckCreateHubAddButton(modId, status, modTitleText) {
	const btn = document.createElement('div');
	btn.className = 'rimdeck-hub-add-btn Panel';
	btn.setAttribute('role', 'button');
	btn.tabIndex = 0;
	btn.dataset.modId = modId;
	rimdeckApplyHubButtonState(btn, status);

	btn.addEventListener('click', function() {
		if (!window.browserBridge) {
			return;
		}
		btn.classList.add('pressed');
		setTimeout(function() {
			btn.classList.remove('pressed');
		}, 150);

		if (btn.classList.contains('rimdeck-hub-default')) {
			rimdeckRecordModStatus(modId, BadgeState.ADDED);
			window.browserBridge.add_mod_from_js(modId, modTitleText);
		} else if (btn.classList.contains('rimdeck-hub-added')) {
			rimdeckRecordModStatus(modId, BadgeState.DEFAULT);
			window.browserBridge.remove_mod_from_js(modId);
		}
	});

	return btn;
}

function rimdeckInjectHubAddButtons() {
	const installedMods = window._rimdeckInstalledMods || [];
	const addedMods = window._rimdeckAddedMods || [];
	const installedSet = window._rimdeckInstalledSet || new Set(installedMods);
	const addedSet = window._rimdeckAddedSet || new Set(addedMods);
	window._rimdeckInstalledSet = installedSet;
	window._rimdeckAddedSet = addedSet;

	for (const quickViewEl of rimdeckFindQuickViewButtons()) {
		const modId = rimdeckModIdFromHubCard(quickViewEl);
		if (!modId) {
			continue;
		}

		const card = rimdeckHubCardRoot(quickViewEl);
		rimdeckCleanupHubLegacyBadges(card);

		const status = rimdeckModStatus(installedMods, addedMods, modId);
		const existingBtn = rimdeckFindHubAddButton(modId, quickViewEl);
		if (existingBtn) {
			rimdeckApplyHubButtonState(existingBtn, status);
			continue;
		}

		const modTitleText = rimdeckModTitleFromHubCard(quickViewEl, modId);
		quickViewEl.insertAdjacentElement(
			'afterend',
			rimdeckCreateHubAddButton(modId, status, modTitleText)
		);
	}
}
window.rimdeckInjectHubAddButtons = rimdeckInjectHubAddButtons;

function rimdeckFindBadgeObserverRoot() {
	return document.querySelector('.workshopBrowseRow')
		|| document.querySelector('.workshopBrowseItems')
		|| document.querySelector('#BrowseResultContainer')
		|| document.querySelector('main')
		|| document.body
		|| null;
}

function rimdeckMutationIsRimDeck(mutation) {
	const target = mutation.target;
	if (target instanceof Element && target.closest('.rimdeck-modstatus-badge, .rimdeck-hub-add-btn')) {
		return true;
	}
	for (const node of mutation.addedNodes) {
		if (!(node instanceof Element)) {
			continue;
		}
		if (
			node.classList.contains('rimdeck-modstatus-badge')
			|| node.classList.contains('rimdeck-hub-add-btn')
			|| node.querySelector('.rimdeck-modstatus-badge, .rimdeck-hub-add-btn')
		) {
			return true;
		}
	}
	return false;
}

function rimdeckSetupPageObserver(callback) {
	if (window._rimdeckObserver) {
		return;
	}
	const root = rimdeckFindBadgeObserverRoot();
	if (!root) {
		return;
	}

	let observerDebounce = null;
	window._rimdeckObserver = new MutationObserver(function(mutations) {
		if (window._rimdeckUpdatingBadges) {
			return;
		}
		if (mutations.every(rimdeckMutationIsRimDeck)) {
			return;
		}
		if (observerDebounce) {
			clearTimeout(observerDebounce);
		}
		observerDebounce = setTimeout(callback, 500);
	});
	window._rimdeckObserver.observe(root, { childList: true, subtree: true });
}

function rimdeckWaitForQWebChannel(callback, attempt) {
	if (attempt === undefined) {
		attempt = 0;
	}
	if (typeof QWebChannel !== 'undefined' && typeof qt !== 'undefined' && qt.webChannelTransport) {
		callback();
		return;
	}
	if (attempt >= 20) {
		console.error("QWebChannel is not defined. Cannot setup bridge.");
		return;
	}
	setTimeout(function() {
		rimdeckWaitForQWebChannel(callback, attempt + 1);
	}, 50);
}

function rimdeckInstallHistoryUrlSync() {
	if (window._rimdeckHistoryUrlSync) {
		return;
	}
	window._rimdeckHistoryUrlSync = true;

	const notify = function() {
		if (!window.browserBridge || typeof window.browserBridge.on_url_changed !== 'function') {
			return;
		}
		window.browserBridge.on_url_changed(window.location.href);
	};

	const wrapHistory = function(methodName) {
		const original = history[methodName];
		if (typeof original !== 'function') {
			return;
		}
		history[methodName] = function() {
			const result = original.apply(this, arguments);
			notify();
			return result;
		};
	};

	wrapHistory('pushState');
	wrapHistory('replaceState');
	window.addEventListener('popstate', notify);
	notify();
}

function setupRimDeckWorkshopBridge(installedMods, addedMods) {
	window._rimdeckInstalledMods = installedMods;
	window._rimdeckAddedMods = addedMods;
	window._rimdeckInstalledSet = new Set(installedMods);
	window._rimdeckAddedSet = new Set(addedMods);

	if (window._rimdeckBridgeReady) {
		rimdeckInstallHistoryUrlSync();
		if (PAGE_MODE === 'browse' && typeof window.updateAllModBadges === 'function') {
			window.updateAllModBadges();
		} else if (PAGE_MODE === 'hub') {
			window.rimdeckInjectHubAddButtons();
		}
		return;
	}

	new QWebChannel(qt.webChannelTransport, function(channel) {
		window.browserBridge = channel.objects.browserBridge;
		window._rimdeckBridgeReady = true;
		console.log("QWebChannel bridge to Python ready!");
		rimdeckInstallHistoryUrlSync();

		window.updateModBadge = function(modId, status) {
			if (PAGE_MODE === 'hub') {
				rimdeckUpdateHubAddButton(modId, status);
				return;
			}

			rimdeckRecordModStatus(modId, status);

			const tile = findModTile(modId);
			if (!tile) {
				console.log(`Mod tile for ${modId} not found.`);
				return;
			}

			let modStatusBadge = tile.querySelector('.rimdeck-modstatus-badge');

			if (!modStatusBadge) {
				modStatusBadge = document.createElement('div');
				modStatusBadge.className = 'rimdeck-modstatus-badge';

				let modTitleContainer = null;
				const collectionItemParent = tile.parentElement;
				if (collectionItemParent && collectionItemParent.classList.contains('collectionItem')) {
					modTitleContainer = collectionItemParent.querySelector('.collectionItemDetails');
				} else {
					modTitleContainer = tile;
				}

				const modTitleText = rimdeckModTitleFromBrowseTile(tile, modId);

				const tileMouseoverHandler = function() {
					tile.classList.add('rimdeck-tile-hovered');
					if (modStatusBadge.classList.contains('rimdeck-mod-default') && PAGE_MODE !== 'browse') {
						modStatusBadge.style.opacity = '1';
						modStatusBadge.style.visibility = 'visible';
					}
				};
				const tileMouseoutHandler = function() {
					tile.classList.remove('rimdeck-tile-hovered');
					if (modStatusBadge.classList.contains('rimdeck-mod-default') && PAGE_MODE !== 'browse') {
						modStatusBadge.style.opacity = '0';
						modStatusBadge.style.visibility = 'hidden';
					}
				};
				tile.addEventListener('mouseover', tileMouseoverHandler);
				tile.addEventListener('mouseout', tileMouseoutHandler);

				const badgeMouseoverHandler = function() {
					modStatusBadge.classList.add('rimdeck-badge-hovered');
				};
				const badgeMouseoutHandler = function() {
					modStatusBadge.classList.remove('rimdeck-badge-hovered');
				};
				modStatusBadge.addEventListener('mouseover', badgeMouseoverHandler);
				modStatusBadge.addEventListener('mouseout', badgeMouseoutHandler);

				const badgeClickHandler = function() {
					if (!window.browserBridge) {
						return;
					}

					modStatusBadge.classList.add('pressed');
					setTimeout(function() {
						modStatusBadge.classList.remove('pressed');
					}, 150);

					if (modStatusBadge.classList.contains('rimdeck-mod-default')) {
						rimdeckRecordModStatus(modId, BadgeState.ADDED);
						window.browserBridge.add_mod_from_js(modId, modTitleText);
					} else if (modStatusBadge.classList.contains('rimdeck-mod-added')) {
						rimdeckRecordModStatus(modId, BadgeState.DEFAULT);
						window.browserBridge.remove_mod_from_js(modId);
					}
				};

				modStatusBadge.addEventListener('click', badgeClickHandler);

				tile.style.position = 'relative';
				tile.appendChild(modStatusBadge);
			}

			if (status === BadgeState.INSTALLED) {
				modStatusBadge.title = 'Already installed';
				modStatusBadge.innerHTML = '✓';
				modStatusBadge.classList.remove('rimdeck-mod-added', 'rimdeck-mod-default');
				modStatusBadge.classList.add('rimdeck-mod-installed');
				const modTitleElement = rimdeckFindBrowseTitleElement(tile);
				if (modTitleElement) {
					modTitleElement.style.color = '#4CAF50';
				}
				modStatusBadge.style.opacity = '1';
				modStatusBadge.style.visibility = 'visible';
			} else if (status === BadgeState.ADDED) {
				modStatusBadge.title = 'Preparing to download';
				modStatusBadge.innerHTML = '-';
				modStatusBadge.classList.remove('rimdeck-mod-installed', 'rimdeck-mod-default');
				modStatusBadge.classList.add('rimdeck-mod-added');
				const modTitleElement = rimdeckFindBrowseTitleElement(tile);
				if (modTitleElement) {
					modTitleElement.style.color = '';
				}
				modStatusBadge.style.opacity = '1';
				modStatusBadge.style.visibility = 'visible';
			} else {
				modStatusBadge.title = 'Add to list';
				modStatusBadge.innerHTML = 'Add to list';
				modStatusBadge.classList.remove('rimdeck-mod-installed', 'rimdeck-mod-added');
				modStatusBadge.classList.add('rimdeck-mod-default');
				const modTitleElement = rimdeckFindBrowseTitleElement(tile);
				if (modTitleElement) {
					modTitleElement.style.color = '';
				}
				if (PAGE_MODE === 'browse' || tile.classList.contains('rimdeck-tile-hovered')) {
					modStatusBadge.style.opacity = '1';
					modStatusBadge.style.visibility = 'visible';
				} else {
					modStatusBadge.style.opacity = '0';
					modStatusBadge.style.visibility = 'hidden';
				}
			}

			if (modStatusBadge.matches(':hover')) {
				modStatusBadge.classList.add('rimdeck-badge-hovered');
			} else {
				modStatusBadge.classList.remove('rimdeck-badge-hovered');
			}
		};

		window._rimdeckUpdatingBadges = false;
		window.updateAllModBadges = function() {
			if (PAGE_MODE !== 'browse') {
				return;
			}
			if (window._rimdeckUpdatingBadges) {
				return;
			}
			window._rimdeckUpdatingBadges = true;
			try {
				const seenModIds = new Set();
				const installedSet = window._rimdeckInstalledSet || new Set();
				const addedSet = window._rimdeckAddedSet || new Set();

				rimdeckCollectBrowseModEntries().forEach(function(entry) {
					if (seenModIds.has(entry.modId)) {
						return;
					}
					seenModIds.add(entry.modId);
					if (installedSet.has(entry.modId)) {
						window.updateModBadge(entry.modId, BadgeState.INSTALLED);
					} else if (addedSet.has(entry.modId)) {
						window.updateModBadge(entry.modId, BadgeState.ADDED);
					} else {
						window.updateModBadge(entry.modId, BadgeState.DEFAULT);
					}
				});

				for (const selector of TILE_SELECTORS) {
					const tiles = document.querySelectorAll(selector);
					tiles.forEach(function(tile) {
						const link = tile.querySelector('a[href*="id="]');
						if (!link) {
							return;
						}
						const match = link.href.match(/id=(\d+)/);
						if (!match) {
							return;
						}
						const modId = match[1];
						if (seenModIds.has(modId)) {
							return;
						}
						seenModIds.add(modId);

						if (installedSet.has(modId)) {
							window.updateModBadge(modId, BadgeState.INSTALLED);
						} else if (addedSet.has(modId)) {
							window.updateModBadge(modId, BadgeState.ADDED);
						} else {
							window.updateModBadge(modId, BadgeState.DEFAULT);
						}
					});
				}
			} finally {
				window._rimdeckUpdatingBadges = false;
			}
		};

		if (PAGE_MODE === 'browse') {
			document.body.classList.add('rimdeck-grid-page');
			window.updateAllModBadges();
			rimdeckSetupPageObserver(function() {
				window.updateAllModBadges();
			});
		} else if (PAGE_MODE === 'hub') {
			window.rimdeckInjectHubAddButtons();
			rimdeckSetupPageObserver(function() {
				window.rimdeckInjectHubAddButtons();
			});
		}
	});
}

function rimdeckScheduleWorkshopSetup(installed, added) {
	const run = function() {
		rimdeckWaitForQWebChannel(function() {
			setupRimDeckWorkshopBridge(installed, added);
		});
	};
	const schedule = function() {
		if (INJECT_DELAY_MS <= 0) {
			run();
			return;
		}
		setTimeout(run, INJECT_DELAY_MS);
	};
	if (document.readyState === 'complete') {
		schedule();
	} else {
		window.addEventListener('load', schedule, { once: true });
	}
}

rimdeckScheduleWorkshopSetup(@installed_mods@, @added_mods@);

if (!document.getElementById('rimdeck-workshop-badge-style')) {
	const style = document.createElement('style');
	style.id = 'rimdeck-workshop-badge-style';
	style.textContent = `
    .rimdeck-modstatus-badge {
        position: absolute;
        top: 5px;
        right: 5px;
        color: white;
        width: auto;
        min-width: 32px;
        height: 32px;
        padding: 0 8px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 12px;
        box-shadow: 0 0 4px black;
        cursor: default;
        user-select: none;
        transition: transform 0.1s ease, box-shadow 0.1s ease, opacity 0.2s ease, visibility 0.2s ease;
    }

    .rimdeck-modstatus-badge.rimdeck-badge-hovered {
        transform: scale(1.05);
        box-shadow: 0 0 8px rgba(0,0,0,0.4);
    }

    .rimdeck-modstatus-badge.pressed {
        transform: scale(0.9);
    }

    .rimdeck-mod-installed {
        background-color: #4CAF50;
    }

    .rimdeck-mod-added {
        background-color: #FFA500;
        cursor: pointer;
    }

    .rimdeck-mod-default {
        background-color: #2196F3;
        cursor: pointer;
    }

    body.rimdeck-grid-page .rimdeck-mod-default {
        opacity: 1;
        visibility: visible;
    }

    .rimdeck-mod-default:not(body.rimdeck-grid-page .rimdeck-mod-default) {
        opacity: 0;
        visibility: hidden;
    }

    .rimdeck-hub-add-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 32px;
        height: 32px;
        padding: 0 10px;
        margin-left: 6px;
        margin-right: 6px;
        margin-bottom: 6px;
        border-radius: 6px;
        color: white;
        font-weight: bold;
        font-size: 12px;
        box-shadow: 0 0 4px black;
        user-select: none;
        cursor: default;
        transition: transform 0.1s ease, box-shadow 0.1s ease;
    }

    .rimdeck-hub-add-btn.rimdeck-hub-default,
    .rimdeck-hub-add-btn.rimdeck-hub-added {
        cursor: pointer;
    }

    .rimdeck-hub-add-btn.rimdeck-hub-installed {
        background-color: #4CAF50;
    }

    .rimdeck-hub-add-btn.rimdeck-hub-added {
        background-color: #FFA500;
    }

    .rimdeck-hub-add-btn.rimdeck-hub-default {
        background-color: #2196F3;
    }

    .rimdeck-hub-add-btn.pressed {
        transform: scale(0.9);
    }
`;
	document.head.appendChild(style);
}
