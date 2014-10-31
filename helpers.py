# -*- coding: utf-8 -*-

import os
import sys
import re

PY3 = sys.version >= '3'
#ST3 = sys.version >= '3'
#ST3 = int(sublime.version()) >= 3000

if PY3:
    from .settings import *
else:
    from settings import *


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
    description = gist.get('description')

    if description and settings.get('prefer_filename') is False:
        title = description
    else:
        title = list(gist['files'].keys())[0]

    if settings.get('show_authors'):
        return [title, gist.get('user').get('login')]
    else:
        return [title]


def gists_filter(all_gists):
    
    # Set variable for further reuse
    sort_type = settings.get('sort_gists')
    prefix = settings.get('gist_prefix')
    if prefix:
        prefix_len = len(prefix)

    if settings.get('gist_tag'):
        tag_prog = re.compile('(^|\s)#' + re.escape(settings.get('gist_tag')) + '($|\s)')
    else:
        tag_prog = False

    gists = []
    gists_names = []
    gists_filenames = []

    for gist in all_gists:

        name = gist_title(gist)

        if not gist['files']:
            continue

        if prefix:
            if name[0][0:prefix_len] == prefix:
                name[0] = name[0][prefix_len:] # remove prefix from name
            else:
                continue

        if tag_prog:
            match = re.search(tag_prog, name[0])

            if match:
                name[0] = name[0][0:match.start()] + name[0][match.end():]
            else:
                continue

        if sort_type:

            # Set the extra data for sorting
            sorted_data = set_sort_data(sort_type, gist, name)
            
            if not sorted_data is None:
                gist = sorted_data[0]

            if sort_type == 'extension' or sort_type == 'ext':
                gists_filenames.append([sorted_data[1][0], sorted_data[1][1]])
        
        gists.append(gist)
        gists_names.append(name)

    # Sort block
    if sort_type:

        # Custom sort the data alphabetically
        sorted_results = sort_gists_data(sort_type, gists, gists_names, gists_filenames)
        gists          = sorted_results[0]
        gists_names    = sorted_results[1]
        

    return [gists, gists_names]


def set_syntax(view, file_data):
    if not "language" in file_data:
        return

    language = file_data['language']

    if language is None:
        return

    if language == 'C':
        new_syntax = os.path.join('C++', "{0}.tmLanguage".format(language))
    else:
        new_syntax = os.path.join(language, "{0}.tmLanguage".format(language))

    if PY3:
        new_syntax_path = os.path.join('Packages', new_syntax)

        if os.name == 'nt':
            new_syntax_path = new_syntax_path.replace('\\', '/')
    else:
        new_syntax_path = os.path.join(sublime.packages_path(), new_syntax)

    try:
        #print(new_syntax_path)
        view.set_syntax_file(new_syntax_path)
    except:
        pass

def set_sort_data(sort_type, gist, name):
    
    # Set the gist description to the filename at element 0
    # Same process that gist_title does for the title variable
    if sort_type == 'description' and gist['description'] == "":
        #print('Description')
        gist['description'] = list(gist['files'].keys())[0]
        return [gist]

    # For sorting by extension lets add the extension to the gist list
    if sort_type == 'extension' or sort_type == 'file extension' or sort_type == 'ext':
        #print('Ext')
        ext = list(gist['files'].keys())[0].split('.')
        if 1 < len(ext):
            gist['extension'] = ext[1]
        else:
            # This it to place gists without filenames at the end of the context list
            gist['extension'] = '[No Filename]'

        # Add to extensions name list
        filename = [name[0], gist['extension']]
        return [gist, filename]

def sort_gists_data(sort_type, gists, gists_names, gists_filenames):

    if sort_type == 'description':
        #print('Debug: Sort by description')
        
        # Check for the filename to appear to determine how to sort
        if not settings.get('prefer_filename'):
            gists = sorted(gists, key=lambda k: k['description'].lower())
        else:
            gists = sorted(gists, key=lambda k: list(k['files'].keys())[0].lower())

        gists_names = sorted(gists_names,key=lambda k: k[0].lower())
        
    elif sort_type == 'extension' or sort_type == 'ext':
        #print('Sort by file extension')
        
        gists = sorted(gists, key=lambda k: (k['extension'] == "[No Filename]", k['extension'].lower()))
        gists_names = sorted(gists_filenames, key=lambda k: (k[1] == "[No Filename]", k[1].lower()))

    return [gists, gists_names]
