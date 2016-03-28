import os
import re

import sublime


def gistify_view(view, gist, gist_filename):
    statusline_string = "Gist: " + gist_title(gist)[0]

    if not view.file_name():
        view.set_name(gist_filename)
    elif os.path.basename(view.file_name()) != gist_filename:
        statusline_string = "%s (%s)" % (statusline_string, gist_filename)

    view.settings().set('gist_html_url', gist["html_url"])
    view.settings().set('gist_description', gist['description'])
    view.settings().set('gist_url', gist["url"])
    view.settings().set('gist_filename', gist_filename)
    view.set_status("Gist", statusline_string)


def ungistify_view(view):
    view.settings().erase('gist_html_url')
    view.settings().erase('gist_description')
    view.settings().erase('gist_url')
    view.settings().erase('gist_filename')
    view.erase_status("Gist")


def gist_title(gist):
    settings = sublime.load_settings('Gist.sublime-settings')
    description = gist.get('description')

    if description and settings.get('prefer_filename') is False:
        title = description
    else:
        title = list(gist['files'].keys())[0]

    if settings.get('show_authors'):
        return [title, gist.get('owner').get('login')]
    else:
        return [title]


def gists_filter(all_gists):
    settings = sublime.load_settings('Gist.sublime-settings')
    prefix = settings.get('gist_prefix')
    if prefix:
        prefix_len = len(prefix)

    if settings.get('gist_tag'):
        tag_prog = re.compile('(^|\s)#' + re.escape(settings.get('gist_tag')) + '($|\s)')
    else:
        tag_prog = False

    gists = []
    gists_names = []

    for gist in all_gists:
        if not gist['files']:
            continue

        name = gist_title(gist)

        if prefix:
            if name[0][0:prefix_len] == prefix:
                name[0] = name[0][prefix_len:]  # remove prefix from name
            else:
                continue

        if tag_prog:
            match = re.search(tag_prog, name[0])

            if match:
                name[0] = name[0][0:match.start()] + name[0][match.end():]
            else:
                continue

        gists.append(gist)
        gists_names.append(name)

    return [gists, gists_names]


def set_syntax(view, file_data):
    if "language" not in file_data:
        return

    language = file_data['language']

    if language is None:
        return

    if language == 'C':
        new_syntax = os.path.join('C++', "{0}.tmLanguage".format(language))
    else:
        new_syntax = os.path.join(language, "{0}.tmLanguage".format(language))

    new_syntax_path = os.path.join('Packages', new_syntax)

    if os.name == 'nt':
        new_syntax_path = new_syntax_path.replace('\\', '/')

    try:
        # print(new_syntax_path)
        view.set_syntax_file(new_syntax_path)
    except:
        pass
