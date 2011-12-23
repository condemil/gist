import sublime
import sublime_plugin
import os
import json
import urllib2
import base64

DEFAULT_CREATE_PUBLIC_VALUE = 'false'
DEFAULT_USE_PROXY_VALUE = 'false'
_selectedText = ''
_fileName = ''
_gistsUrls = []
settings = sublime.load_settings('Gist.sublime-settings')
url = 'https://api.github.com/gists'

def create_gist(description):
	data = json.dumps({ 'description': description,
						'public': settings.get('create_public', DEFAULT_CREATE_PUBLIC_VALUE),
						'files': {
							_fileName: {'content': _selectedText}
						}})

	result = api_request(url, data)

	sublime.set_clipboard(result['html_url'])

def get_gist(url_gist):
	gists = api_request(url_gist)

	for gist in gists['files']:
		sublime.set_clipboard(gists['files'][gist]['content'])

def get_gists():
	gists = api_request(url)

	gistsNames = []

	for gist in gists:
		if(gist['description'] != ''):
			gistsNames.append([gist['description']])
		else:
			gistsNames.append(['[No Name]'])

		_gistsUrls.append([gist['url']])

	return gistsNames

def api_request(url_api, data = ''):
	request = urllib2.Request(url_api)
	request.add_header('Authorization', 'Basic ' + base64.urlsafe_b64encode("%s:%s" % (settings.get('username'), settings.get('password'))))
	request.add_header('Accept', 'application/json')
	request.add_header('Content-Type', 'application/json')

	if len(data)>0:
		request.add_data(data)

	if settings.get('use_proxy', DEFAULT_USE_PROXY_VALUE) == 'true':
		use_proxy(urllib2)

	response = urllib2.urlopen(request)

	return json.loads(response.read())

def use_proxy(urllib2):
    opener = urllib2.build_opener(
            urllib2.HTTPHandler(),
            urllib2.HTTPSHandler(),
            urllib2.ProxyHandler({'https': settings.get('proxy')})
            )

    return urllib2.install_opener(opener)


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

class GistlistCommand(sublime_plugin.WindowCommand):
	def run(self):
		self.window.show_quick_panel(get_gists(), self.on_done)

	def on_done(self, num):
		get_gist(_gistsUrls[num][0])
