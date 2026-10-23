import json
import re
from pathlib import Path

from app.utils.steam.steambrowser.browser import (
    BadgeState,
    build_web_channel_script,
    resolve_workshop_page_mode,
)


class TestResolveWorkshopPageMode:
    def test_hub_main_workshop_page(self) -> None:
        url = "https://steamcommunity.com/app/294100/workshop/"
        assert resolve_workshop_page_mode(url) == "hub"

    def test_browse_grid_page(self) -> None:
        url = (
            "https://steamcommunity.com/app/294100/workshop/"
            "?browsefilter=trend&section=readytouseitems"
        )
        assert resolve_workshop_page_mode(url) == "browse"

    def test_browse_path(self) -> None:
        url = "https://steamcommunity.com/workshop/browse/?appid=294100"
        assert resolve_workshop_page_mode(url) == "browse"

    def test_myworkshopfiles_is_browse(self) -> None:
        url = (
            "https://steamcommunity.com/profiles/76561197984862442/"
            "myworkshopfiles/?appid=294100"
        )
        assert resolve_workshop_page_mode(url) == "browse"

    def test_detail_mod_page(self) -> None:
        url = "https://steamcommunity.com/sharedfiles/filedetails/?id=12345"
        assert resolve_workshop_page_mode(url) == "detail"


class TestWebChannelScriptSubstitute:
    def test_build_script_does_not_raise_on_modid_template_literals(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3] / "setup_web_channel_script.js"
        )
        result = build_web_channel_script(
            installed_mods=["123"],
            added_mods=["456"],
            page_mode="browse",
            script_path=template_path,
        )
        assert "${modId}" in result
        assert "@installed_mods@" not in result
        assert "@badge_state_js@" not in result
        assert "@page_mode@" not in result
        assert "@inject_delay_ms@" not in result
        assert "KeyError" not in result

    def test_build_script_embeds_inject_delay_ms(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3] / "setup_web_channel_script.js"
        )
        result = build_web_channel_script(
            installed_mods=[],
            added_mods=[],
            page_mode="hub",
            script_path=template_path,
            inject_delay_ms=3000,
        )
        assert "const INJECT_DELAY_MS = 3000;" in result

    def test_build_script_embeds_mod_lists_and_page_mode(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3] / "setup_web_channel_script.js"
        )
        result = build_web_channel_script(
            installed_mods=["111"],
            added_mods=["222"],
            page_mode="hub",
            script_path=template_path,
        )
        assert json.dumps(["111"]) in result
        assert json.dumps(["222"]) in result
        assert "const PAGE_MODE = 'hub';" in result
        assert BadgeState.INSTALLED.value in result

    def test_tile_selectors_exclude_panel_class(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3] / "setup_web_channel_script.js"
        )
        raw = template_path.read_text(encoding="utf-8")
        assert (
            "const TILE_SELECTORS = ['.workshopItem', '[data-publishedfileid]'];" in raw
        )
        assert "function rimdeckBrowseTileFromLink" in raw

    def test_deferred_workshop_setup_wrapper(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3] / "setup_web_channel_script.js"
        )
        raw = template_path.read_text(encoding="utf-8")
        assert "function rimdeckScheduleWorkshopSetup" in raw
        assert "INJECT_DELAY_MS" in raw
        assert "setTimeout(run, INJECT_DELAY_MS)" in raw
        assert "setupRimDeckWorkshopBridge(@installed_mods@" not in raw

    def test_qwebchannel_wait_helper(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3] / "setup_web_channel_script.js"
        )
        raw = template_path.read_text(encoding="utf-8")
        assert "function rimdeckWaitForQWebChannel" in raw
        assert "qt.webChannelTransport" in raw

    def test_hub_add_button_injection_helpers(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3] / "setup_web_channel_script.js"
        )
        raw = template_path.read_text(encoding="utf-8")
        assert "function rimdeckInjectHubAddButtons" in raw
        assert "svg.SVGIcon_MagnifyingGlass" in raw
        assert "insertAdjacentElement" in raw
        assert "rimdeck-hub-add-btn" in raw

    def test_hub_update_path_and_dedupe_helpers(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3] / "setup_web_channel_script.js"
        )
        raw = template_path.read_text(encoding="utf-8")
        assert "function rimdeckUpdateHubAddButton" in raw
        assert "function rimdeckFindHubAddButton" in raw
        assert "function rimdeckCleanupHubLegacyBadges" in raw
        assert "data-mod-id" in raw
        assert "if (PAGE_MODE === 'hub') {" in raw
        assert "rimdeckUpdateHubAddButton(modId, status);" in raw
        assert "return;" in raw

    def test_hub_add_button_has_margin(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3] / "setup_web_channel_script.js"
        )
        raw = template_path.read_text(encoding="utf-8")
        assert "margin-left: 6px;" in raw
        assert "margin-right: 6px;" in raw
        assert "margin-bottom: 6px;" in raw


class TestSteamRecoveryScript:
    def test_recovery_script_one_time_reload(self) -> None:
        recovery_path = (
            Path(__file__).resolve().parents[3] / "setup_steam_recovery_script.js"
        )
        raw = recovery_path.read_text(encoding="utf-8")
        assert "window._rimdeckSteamRecovery" in raw
        assert "Failed to fetch dynamically imported module" in raw
        assert "sessionStorage.getItem('rimdeck_steam_reload')" in raw
        assert "location.reload()" in raw


class TestSsrBrowseInjectHelpers:
    def test_ssr_browse_snippet_fixture_exists(self) -> None:
        snippet_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "steam"
            / "ssr_browse_snippet.html"
        )
        assert snippet_path.exists()
        content = snippet_path.read_text(encoding="utf-8")
        assert "filedetails/?id=" in content
        assert "aspectratio_16x9" in content
        assert "workshopItem" not in content

    def test_browse_script_includes_ssr_helpers(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3] / "setup_web_channel_script.js"
        )
        raw = template_path.read_text(encoding="utf-8")
        assert "function rimdeckBrowseTileFromLink" in raw
        assert "function rimdeckCollectBrowseModEntries" in raw
        assert "function rimdeckModTitleFromBrowseTile" in raw
        assert "function rimdeckFindBrowseTitleElement" in raw
        assert "rimdeckCollectBrowseModEntries().forEach" in raw
        assert "link.closest('.aspectratio_16x9')" in raw

    def test_observer_root_falls_back_to_body(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3] / "setup_web_channel_script.js"
        )
        raw = template_path.read_text(encoding="utf-8")
        assert "|| document.body" in raw
        assert ".workshopBrowseItems" in raw

    def test_history_url_sync_helper(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3] / "setup_web_channel_script.js"
        )
        raw = template_path.read_text(encoding="utf-8")
        assert "function rimdeckInstallHistoryUrlSync" in raw
        assert "wrapHistory('pushState')" in raw
        assert "wrapHistory('replaceState')" in raw
        assert "browserBridge.on_url_changed" in raw
        assert "rimdeckInstallHistoryUrlSync();" in raw

    def test_hub_status_prefers_sets(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3] / "setup_web_channel_script.js"
        )
        raw = template_path.read_text(encoding="utf-8")
        assert "function rimdeckSyncModListsFromSets" in raw
        assert "function rimdeckRecordModStatus" in raw
        assert "rimdeckRecordModStatus(modId, status);" in raw
        assert "rimdeckSyncModListsFromSets();" in raw
        assert "installedSet.has(modId)" in raw
        assert "addedSet.has(modId)" in raw


class TestClassicMyWorkshopFilesFixture:
    def test_classic_myworkshopfiles_snippet(self) -> None:
        snippet_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "steam"
            / "classic_myworkshopfiles_snippet.html"
        )
        content = snippet_path.read_text(encoding="utf-8")
        assert 'class="workshopItem"' in content
        assert "data-publishedfileid=" in content
        assert "workshopItemTitle" in content
        assert "filedetails/?id=" in content
        assert 'data-publishedfileid="3748351639"' in content
        ids = re.findall(r"filedetails/\?id=(\d+)", content)
        assert "3748351639" in ids
        assert "3746459582" in ids


class TestSteamBrowserProfile:
    def test_chrome_user_agent_constant(self) -> None:
        from app.utils.steam.steambrowser.browser import CHROME_USER_AGENT

        assert "Chrome/" in CHROME_USER_AGENT
        assert "QtWebEngine" not in CHROME_USER_AGENT
