# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sublime, sublime_plugin
import platform
import os, sys, subprocess, codecs, webbrowser
from subprocess import Popen, PIPE

try:
  import commands
except ImportError:
  pass

PLUGIN_FOLDER = os.path.dirname(os.path.realpath(__file__))
SETTINGS_FILE = "JSCSFormatter.sublime-settings"
KEYMAP_FILE = "Default ($PLATFORM).sublime-keymap"

IS_WINDOWS = platform.system() == 'Windows'

class FormatJavascriptCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    # Save the current viewport position to scroll to it after formatting.
    previous_selection = list(self.view.sel()) # Copy.
    previous_position = self.view.viewport_position()

    # Save the already folded code to refold it after formatting.
    # Backup of folded code is taken instead of regions because the start and end pos
    # of folded regions will change once formatted.
    folded_regions_content = [self.view.substr(r) for r in self.view.folded_regions()]

    # Get the current text in the buffer and save it in a temporary file.
    # This allows for scratch buffers and dirty files to be linted as well.
    entire_buffer_region = sublime.Region(0, self.view.size())
    text_selection_region = self.view.sel()[0]

    buffer_text = self.get_buffer_text(entire_buffer_region)

    output = self.run_script_on_text(buffer_text)

    # If the prettified text length is nil, the current syntax isn't supported.
    if output == None or len(output) < 1:
      return

    # Replace the text only if it's different.
    if output != buffer_text:
      self.view.replace(edit, entire_buffer_region, output)

    self.refold_folded_regions(folded_regions_content, output)
    self.view.set_viewport_position((0, 0), False)
    self.view.set_viewport_position(previous_position, False)
    self.view.sel().clear()

    # Restore the previous selection if formatting wasn't performed only for it.
    # if not is_formatting_selection_only:
    for region in previous_selection:
      self.view.sel().add(region)

  def get_buffer_text(self, region):
    buffer_text = self.view.substr(region)
    return buffer_text

  def run_script_on_text(self, data):
    try:
      node_path = PluginUtils.get_node_path()
      script_path = PluginUtils.get_cmd_path('jscs')

      if script_path == False:
        sublime.error_message('JSCS could not be found on your path')
        return;

      cmd = [node_path, script_path, '--fix']

      if self.view.file_name():
          cdir = os.path.dirname(self.view.file_name())
      else:
          cdir = "/"

      output = PluginUtils.get_output(cmd, cdir, data)

      return output;

    except:
      # Something bad happened.
      msg = str(sys.exc_info()[1])
      print("Unexpected error({0}): {1}".format(sys.exc_info()[0], msg))
      sublime.error_message(msg)

  def refold_folded_regions(self, folded_regions_content, entire_file_contents):
    self.view.unfold(sublime.Region(0, len(entire_file_contents)))
    region_end = 0

    for content in folded_regions_content:
      region_start = entire_file_contents.index(content, region_end)
      if region_start > -1:
        region_end = region_start + len(content)
        self.view.fold(sublime.Region(region_start, region_end))

class JscsFormatterEventListeners(sublime_plugin.EventListener):
  @staticmethod
  def on_pre_save(view):
    if PluginUtils.get_pref("format_on_save"):
      view.run_command("format_javascript")

class JscsFormatterSetPluginOptionsCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    PluginUtils.open_sublime_settings(self.view.window())

class JscsFormatterSetKeyboardShortcutsCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    PluginUtils.open_sublime_keymap(self.view.window(), {
      "windows": "Windows",
      "linux": "Linux",
      "osx": "OSX"
    }.get(sublime.platform()))

class JscsFormatterSetNodePathCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    PluginUtils.open_sublime_settings(self.view.window())

class PluginUtils:
  @staticmethod
  def get_pref(key):
    return sublime.load_settings(SETTINGS_FILE).get(key)

  @staticmethod
  def open_sublime_settings(window):
    window.open_file(PLUGIN_FOLDER + "/" + SETTINGS_FILE)

  @staticmethod
  def open_sublime_keymap(window, platform):
    window.open_file(PLUGIN_FOLDER + "/" + KEYMAP_FILE.replace("$PLATFORM", platform))

  @staticmethod
  def get_cmd_path(cmd):
    # Can't search the path if a directory is specified.
    assert not os.path.dirname(cmd)
    path = os.environ.get("PATH", "").split(os.pathsep)
    extensions = os.environ.get("PATHEXT", "").split(os.pathsep)

    path += ['/usr/local/bin']

    # For each directory in PATH, check if it contains the specified binary.
    for directory in path:
      base = os.path.join(directory, cmd)
      options = [base] + [(base + ext) for ext in extensions]
      for filename in options:
        if os.path.exists(filename):
          return filename

    return False

  @staticmethod
  def get_node_path():
    platform = sublime.platform()
    node = PluginUtils.get_pref("node_path").get(platform)
    print("Using node.js path on '" + platform + "': " + node)
    return node

  @staticmethod
  def get_output(cmd, cdir, data):
    try:
      p = Popen(cmd,
        stdout=PIPE, stdin=PIPE, stderr=PIPE,
        cwd=cdir, shell=IS_WINDOWS)
    except OSError:
      raise Exception('Couldn\'t find Node.js. Make sure it\'s in your $PATH by running `node -v` in your command-line.')
    stdout, stderr = p.communicate(input=data.encode('utf-8'))
    stdout = stdout.decode('utf-8')
    stderr = stderr.decode('utf-8')

    if stderr:
      raise Exception('Error: %s' % stderr)
    else:
      return stdout
