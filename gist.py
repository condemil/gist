import sublime
import sublime_plugin
import os
import json
import urllib2
import base64

DEFAULT_CREATE_PUBLIC_VALUE = 'false'
_selectedText = ''
_fileName = ''

def create_gist(description):
	settings = sublime.load_settings('Gist.sublime-settings')

	url = 'https://api.github.com/gists'

	data = json.dumps({ 'description': description,
						'public': settings.get('create_public', DEFAULT_CREATE_PUBLIC_VALUE),
						'files': {
							_fileName: {'content': _selectedText}
						}})

	headers = { 'Authorization': 'Basic ' + base64.urlsafe_b64encode("%s:%s" % (settings.get('username'), settings.get('password'))),
				'Accept': 'application/json',
				'Content-Type': 'application/json',
				'Content-Length': len(data)}

	request = urllib2.Request(url, data, headers)
	response = urllib2.urlopen(request)

	result = json.loads(response.read())
	sublime.set_clipboard(result['html_url'])

class PromptGistCommand(sublime_plugin.WindowCommand):
	def run(self):
		fileName = os.path.basename(self.window.active_view().file_name()) if self.window.active_view().file_name() else ''
		self.window.show_input_panel('File name: (optional):', fileName, self.on_done_input_file_name, None, None)

	def on_done_input_file_name(self, fileName):
		global _fileName
		_fileName = fileName
		self.window.show_input_panel('Description (optional):', '', self.on_done_input_description, None, None)

	def on_done_input_description(self, description):
		create_gist(description)

class GistCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		for selectedRegion in self.view.sel():
			if not selectedRegion.empty():
				global _selectedText
				_selectedText = self.view.substr(selectedRegion)
				self.view.window().run_command('prompt_gist')
			else:
				_selectedText = self.view.substr(sublime.Region(0, self.view.size()))
				self.view.window().run_command('prompt_gist')
