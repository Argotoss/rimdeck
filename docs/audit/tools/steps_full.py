from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMenu, QMessageBox, QWidget


def mw(c):
    return c.main_window


def mp(c):
    return c.main_window.main_content_panel.mods_panel


def close_popups(c):
    for w in QApplication.topLevelWidgets():
        if w is c.main_window or not w.isVisible():
            continue
        if isinstance(w, QMessageBox):
            w.reject()
        else:
            w.close()


def first_red_row(lst):
    for i in range(lst.count()):
        item = lst.item(i)
        w = lst.itemWidget(item)
        if w is not None and "red" in (w.styleSheet() + str(item.foreground().color().name())).lower():
            return i
    return 7


def select(row, which="active"):
    def f(c):
        close_popups(c)
        lst = mp(c).active_mods_list if which == "active" else mp(c).inactive_mods_list
        lst.setCurrentRow(row)
        lst.scrollToItem(lst.item(row))
    return f


def search(text):
    def f(c):
        mp(c).active_mods_search.setText(text)
    return f


def clear_search(c):
    mp(c).active_mods_search.setText("")


def tab(i):
    def f(c):
        close_popups(c)
        mw(c).tab_widget.setCurrentIndex(i)
    return f


def settings_tab(i):
    def f(c):
        d = c.settings_dialog
        if not d.isVisible():
            d.show()
        d.tab_widget.setCurrentIndex(i)
    return f


def close_settings(c):
    c.settings_dialog.hide()
    mw(c).tab_widget.setCurrentIndex(0)


def press_sort(c):
    mw(c).sort_button.setDown(True)


def release_sort(c):
    mw(c).sort_button.setDown(False)


def do_sort(c):
    mw(c).sort_button.click()


def rule_editor(c):
    close_popups(c)
    c.main_window.menu_bar.rule_editor_action.trigger()


def context_menu(c):
    close_popups(c)
    lst = mp(c).active_mods_list
    lst.setCurrentRow(5)
    rect = lst.visualItemRect(lst.item(5))
    pos = lst.viewport().mapToGlobal(rect.center())
    # The list builds its menu on customContextMenuRequested; fall back to a no-op
    try:
        QTimer.singleShot(0, lambda: lst.customContextMenuRequested.emit(rect.center()))
    except Exception:
        pass
    _ = pos


def theme(name):
    def f(c):
        close_popups(c)
        c.theme_controller.apply_selected_theme(True, name)
    return f


def no_theme(c):
    c.theme_controller.apply_selected_theme(False, "")


def small(c):
    close_popups(c)
    c.theme_controller.apply_selected_theme(True, "RimPy")
    mw(c).resize(1280, 760)


def menubar(c):
    pass


STEPS = [
    ("02_main_clean", 3, close_popups),
    ("03_mod_selected", 2, select(4)),
    ("04_mod_selected_warn", 2, select(5)),
    ("05_mod_selected_err", 2, select(6)),
    ("06_inactive_selected", 2, select(1, "inactive")),
    ("07_search", 2, search("royalty")),
    ("08_search_clear", 1, clear_search),
    ("09_btn_pressed", 1, press_sort),
    ("10_btn_released", 1, release_sort),
    ("11_tab_acf", 2, tab(1)),
    ("12_tab_playerlog", 2, tab(2)),
    ("13_tab_filesearch", 2, tab(3)),
    ("14_tab_troubleshoot", 2, tab(4)),
    ("15_set_locations", 2, settings_tab(0)),
    ("16_set_launch", 1, settings_tab(1)),
    ("17_set_databases", 1, settings_tab(2)),
    ("18_set_sorting", 1, settings_tab(3)),
    ("19_set_dbbuilder", 1, settings_tab(4)),
    ("20_set_internal", 1, settings_tab(5)),
    ("21_set_external", 1, settings_tab(6)),
    ("22_set_appearance", 1, settings_tab(7)),
    ("23_set_advanced", 1, settings_tab(8)),
    ("24_after_settings", 1, close_settings),
    ("25_sort", 5, do_sort),
    ("26_rule_editor", 4, rule_editor),
    ("27_context_menu", 2, context_menu),
    ("28_theme_modern", 2, theme("Modern")),
    ("29_theme_nature", 2, theme("Nature")),
    ("30_theme_sunset", 2, theme("SunSet")),
    ("31_theme_wood", 2, theme("Wood")),
    ("32_theme_off", 2, no_theme),
    ("33_small_window", 3, small),
]
