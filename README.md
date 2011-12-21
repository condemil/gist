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

Under the Packages/Gist sub-directory, edit the `Gist.sublime-settings` file:

*   `"create_public": false`

    This makes your gists be private instead of public.

*   `"username": YOUR_USERNAME`

    You need to enter your GitHub username here

*   `"password": YOUR_PASSWORD`

    You need to enter your GitHub password here

*   `"use_proxy": true/false`

    You need to enter proxy 'true' if you use a proxy
 
*   `"proxy": http://user:pass@proxy:port`

    You need to enter your proxy if use_proxy is true

   

Usage
-----
**Create a  gist:**

From menu items:

* Main menu: Tools -> Gist -> "Create Gist"
* Context menu: "Create Gist"

By command called "Gist: Create Gist from Selected Text".

There is a key bindings:

* Windows and Linux: "ctrl+k", "ctrl+i"
* OS X: "super+k", "super+i"

**Get gist list:**

From menu items:

* Main menu: Tools -> Gist -> "Get Gist List"

By command called "Gist: Get Gist List".

There is a key bindings:

* Windows and Linux: "ctrl+shift+g"
* OS X: "super+shift+g"

**The content of your selected gist will be copied into the clipboard**

Information
-----------

Source: https://github.com/condemil/Gist

Author: https://github.com/condemil/
