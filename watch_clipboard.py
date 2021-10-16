import json
import os

from . import clipboard
from anki.hooks import addHook, wrap
from aqt import dialogs, mw
from aqt.qt import *
import re

from configparser import ConfigParser

#  Globals
process = None
on = False
interval = 10  # ms
clean_text_breaks = True
keep_html_format = True

editor_local = None
main_path = os.path.dirname(__file__)
config_file_path = os.path.join(main_path, 'config.json')


def init_data():
    global on, interval, clean_text_breaks, keep_html_format
    with open(config_file_path) as f:
        try:
            data = json.load(f)
        except:
            save_configs()
            return

    on = data['on']
    interval = data['interval']
    clean_text_breaks = data['clean_text_breaks']
    keep_html_format = data['keep_html_format']


def save_configs():
    global on, interval, clean_text_breaks, keep_html_format
    with open(config_file_path, 'w') as f:
        data = {
            'on': on,
            "_NOTE": "...interval in ms...",
            'interval': interval,  # ms
            'clean_text_breaks': clean_text_breaks,
            'keep_html_format': keep_html_format
        }
        json.dump(data, f)


init_data()


def get_from_clipboard():
    global keep_html_format, clean_text_breaks
    if keep_html_format:
        try:
            t = clipboard.paste_html()
        except:
            try:
                t = clipboard.paste_text()
            except:
                t = ''
    else:
        try:
            t = clipboard.paste_text()
        except:
            t = ''

    if clean_text_breaks:
        t = t.encode("ascii", "ignore").decode().replace('\n', ' ').replace('\r', ' ').replace('<br>', ' ').replace(
            '<br/>', ' ').replace('<br />', ' ')
        t = '<pr>' + t + '</p>'
        t = re.sub(r'([^0-9])\. ', r"\1. <br />", t)
        t = re.sub(' +', ' ', t)
    return t


last_copied = get_from_clipboard()


def gc(arg, fail=False):
    conf = mw.addonManager.getConfig(__name__)
    if conf:
        return conf.get(arg, fail)
    return fail


def restore_add_window():
    for dclass, instance in dialogs._dialogs.values():
        if instance.windowTitle() == 'Add':
            mw.setWindowState(Qt.WindowMinimized)
            instance.setWindowState(Qt.WindowMinimized)
            instance.setWindowState((instance.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)


def select_all_text(editor):
    jscmd = "document.execCommand('selectAll');"
    editor.web.eval(jscmd)


def delete_all_text(editor):
    select_all_text(editor)
    remove_text = """
    var sel = getCurrentField().shadowRoot.getSelection();
    var r = sel.getRangeAt(0);
    var temp_rb_tag = document.createElement("span");
    document.execCommand('insertHTML', false, temp_rb_tag.innerHTML);
    saveNow(true);
    """
    editor.web.eval(remove_text)


def watch_clipboard(editor):
    global last_copied, process, on
    if last_copied != get_from_clipboard() and is_add_window():
        try:
            last_copied = get_from_clipboard()
            delete_all_text(editor)
            insert_text(editor, last_copied)
            restore_add_window()
        except:
            ...


def is_add_window():
    for dclass, instance in dialogs._dialogs.values():
        if instance and instance.windowTitle() == 'Add':
            return True
    return False


def insert_text(editor, text):
    delete_all_text(editor)
    editor.doPaste(text, internal=False, extended=True)


def get_editor_and_init(buttons, editor):
    global process, action, editor_local, on
    if editor_local:
        process.stop()
    editor_local = editor

    check_process()

    action.setChecked(on)

    b = editor.addButton(
        icon='',
        cmd=" ",
        func=lambda e=editor: toggle,
        keys=gc('shortcut')
    )
    buttons.append(b)
    return buttons


def check_process():
    global process, editor_local
    if on and editor_local:
        process = mw.progress.timer(interval, lambda e=editor_local: watch_clipboard(e), True)
    elif process:
        process.stop()


def toggle():
    global process, on, last_copied, action, editor_local
    if on:
        on = False
    else:
        last_copied = get_from_clipboard()
        on = True

    check_process()
    action.setChecked(on)
    save_configs()


action = QAction("Watch clipboard", mw)
action.setCheckable(True)
action.setChecked(on)
action.triggered.connect(toggle)
mw.form.menuTools.addAction(action)
addHook("setupEditorButtons", get_editor_and_init)
