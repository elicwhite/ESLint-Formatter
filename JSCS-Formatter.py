import sublime
import sublime_plugin
import json
import re
from os.path import dirname, realpath, join, splitext

try:
    # Python 2
    from node_bridge import node_bridge
except:
    from .node_bridge import node_bridge

# monkeypatch `Region` to be iterable
sublime.Region.totuple = lambda self: (self.a, self.b)
sublime.Region.__iter__ = lambda self: self.totuple().__iter__()

# BIN_PATH = join(sublime.packages_path(), dirname(realpath(__file__)), 'jscs-passthrough.js')
# BIN_PATH = join(sublime.packages_path(), dirname(realpath(__file__)), 'node_modules/.bin/jscs')
BIN_PATH = 'jscs'
SETTINGS_FILE = 'JSCS-Formatter.sublime-settings'


settings = sublime.load_settings(SETTINGS_FILE)

def plugin_loaded():
    global settings
    settings = sublime.load_settings(SETTINGS_FILE)

class FormatJavascriptCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if not self.has_selection():
            region = sublime.Region(0, self.view.size())
            originalBuffer = self.view.substr(region)
            formated = self.jscs(originalBuffer, self.get_scope(region))
            if formated:
                self.view.replace(edit, region, formated)
            return
        # handle selections
        for region in self.view.sel():
            if region.empty():
                continue
            originalBuffer = self.view.substr(region)
            formated = self.jscs(originalBuffer, self.get_scope(region))
            if formated:
                self.view.replace(edit, region, formated)

    def get_scope(self, region):
        return self.view.scope_name(region.begin()).rpartition('.')[2].strip()

    def jscs(self, data, scope):
        try:
            # grab the cwd
            if self.view.file_name():
                cdir = dirname(self.view.file_name())
            else:
                cdir = "/"

            return node_bridge(data, BIN_PATH, cdir, ['--fix'])
        except Exception as e:
            msg = "The formatting failed please check the console for more details."
            # Seach for the line number in case of a js error
            t = re.search('Error: Line [0-9]+: (.*)', str(e), flags=re.MULTILINE)
            if t:
                msg += '\n' + t.string[t.start():t.end()]

            sublime.error_message(msg)

            print('\n\nJSCS ==>\n%s\n\n' % e)

    def has_selection(self):
        for sel in self.view.sel():
            start, end = sel
            if start != end:
                return True
        return False