# Gist

A [Sublime Text 2](http://www.sublimetext.com/) plugin for creating and editing Gists.

# Installation

## Package Control

Install [Package Control](http://wbond.net/sublime_packages/package_control). Gist will show up in the package list. This is the recommended installation method.

## Manual installation

Go to the "Packages" directory (`Preferences` / `Browse Packages…`). Then clone this repository:

    git clone git://github.com/condemil/Gist

# Generating Access Token

Currently, the only way to create a Gist Access Token is to curl the authorize API from Github. Here's the command you can run from your terminal to do so:

    curl -v -u USERNAME -X POST https://api.github.com/authorizations --data "{\"scopes\":[\"gist\"]}"

Where USERNAME is your Github username. Save the token generated and paste it in the settings section under the token option.

# Options

If you're using OS X and have a keychain entry for github.com, no configuration is needed. Otherwise, edit the settings file (it should open automatically the first time you use a Gist command). Note you must specifiy either username AND password or token.

*   `"username": ""`

    You can enter your GitHub username here

*   `"password": ""`

    You can enter your GitHub password here

*   `"https_proxy": http://user:pass@proxy:port`

    You can enter https proxy here
    Format: "http://user:pass@proxy:port"

*   `"enterprise": false`

    Set this to true if you want to use a enterprise version of github instead of github.com

*   `"url": ""`

    Set the url of the enterprise version of github you want to use. Leave this blank if the enterprise option is set to false.

*   `"max_gists": 100`

    Set the maximum number of Gists that can will fetched by the plugin. It can't be higher than 100, because of GitHub API limitations.

* `"gist_prefix": ""`

    Limit the Gists displayed in the `Open Gist` list by prefix. Leave blank to display all Gists. Example: `"gist_prefix": "Snippet:"` will only list Gists with names starting with the text **Snippet:**.

# Usage

All functionality of the plugin is available in the `Tools` / `Gist` menu and in the command pallette.

## Creating Gists

Use the `Gist` / `Create Public Gist` or `Gist` / `Create Private Gist` commands. If you don't have anything selected, a Gist will be created with contents of current file, URL of that Gist will be copied to the clipboard and then the file will switch to Gist editing mode. If you have selected some text, a Gist will be created using only that text and then immediately opened for editing. In case of multiple selections, you'll get one Gist with multiple files.

## Editing existing Gists

Use the `Gist` / `Open Gist` command to see a list of your Gists. Selecting one will open the files from that Gist in new tabs. You can then edit the files normally and use `Gist` / `Update File` to update the Gist, or use other commands to change Gist description, remove or rename files, or delete the Gist.

## Adding new files to existing Gists

Use the `Gist` / `Add File To Gist` command to see a list of your Gists. Selecting one will add contents of current file as a new file to that Gist and switch the file to Gist editing mode.

# Default key bindings:

## Create Public Gist

* Windows and Linux: `Ctrl+K` `Ctrl+I`
* OS X: `Super+K` `Super+I`

## Create Private Gist

* Windows and Linux: `Ctrl+K` `Ctrl+P`
* OS X: `Super+K` `Super+P`

## Update File

* Windows and Linux: `Ctrl+K` `Ctrl+S`
* OS X: `Super+K` `Super+S`

## Open Gist

* Windows and Linux: `Ctrl+K` `Ctrl+O`
* OS X: `Super+K` `Super+O`

## Insert Gist

* Windows and Linux: `Ctrl+K` `Ctrl+[`
* OS X: `Super+K` `Super+[`

## Add File

* Windows and Linux: `Ctrl+K` `Ctrl+]`
* OS X: `Super+K` `Super+]`

# Information

Source: https://github.com/condemil/Gist

Authors: [Dmitry Budaev](https://github.com/condemil/), [Alexey Ermakov](https://github.com/technocoreai)
