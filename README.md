Gist
====

[Sublime Text 2](http://www.sublimetext.com/) plugin for creating new Gists from selected text and get the gist list

Installation
-----------

Go to your Packages subdirectory under Sublime Text 2 data directory:

* Windows: %APPDATA%\Sublime Text 2
* OS X: ~/Library/Application Support/Sublime Text 2
* Linux: ~/.config/sublime-text-2
* Portable Installation: Sublime Text 2/Data

Then clone this repository:

    git clone git://github.com/condemil/Gist

Options
-------

If you're using OS X and have a keychain entry for github.com, no configuration is needed. Otherwise, copy the `Gist.sublime-settings` file from Packages/Gist to Packages/User sub-directory and edit:

*   `"username": ""`

    You need to enter your GitHub username here

*   `"password": ""`

    You need to enter your GitHub password here

*   `"https_proxy": http://user:pass@proxy:port`

    You can enter https proxy here
    Format: "http://user:pass@proxy:port"

Usage
-----
**Create a public gist:**

From menu items:

* Main menu: Tools -> Gist -> "Create Public Gist"
* Context menu: "Create Public Gist"

By command called "Gist (public): Create from Selected Text"

There is a key bindings:

* Windows and Linux: "ctrl+k", "ctrl+i"
* OS X: "super+k", "super+i"

**Create a private gist:**

From menu items:

* Main menu: Tools -> Gist -> "Create Private Gist"
* Context menu: "Create Private Gist"

By command called "Gist (private): Create from Selected Text".

There is a key bindings:

* Windows and Linux: "ctrl+k", "ctrl+l"
* OS X: "super+k", "super+l"

**Get gist list:**

From menu items:

* Main menu: Tools -> Gist -> "Get Gist List"

By command called "Gist: Get Gist List".

There is a key bindings:

* Windows and Linux: "ctrl+shift+g"
* OS X: "super+shift+g"

**The content of the selected gist will be copied into the clipboard**

Information
-----------

Source: https://github.com/condemil/Gist

Author: https://github.com/condemil/
