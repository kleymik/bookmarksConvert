#!/usr/bin/python3
#
# open a .url, .webloc, or .desktop url file
#
# Script (started by GPT) to open the small files that are used to keep urls
# There are no firm standards, these are the most common
#   Nextcloud link editor offers ".webloc" which apparently is an Apple-ism
#   or ".url" which is kind-of a microsoft-ism?
#   .webloc are xml, so that seems for expandle, e.g to keep the entire web-page too.

import os
import sys
import configparser                    # for .url, .desktop
import plistlib                        # for .webloc xml
import subprocess

chosenBrowser = ['xdg-open', 'firefox', 'chromium', 'konqueror'][1]  #  --new-tab

def open_url_file(file_path):
    _, ext = os.path.splitext(file_path)
    url = None

    ext = ext.lower()
    if ext=='.url':
        config = configparser.ConfigParser()
        config.read(file_path)
        url = config.get('InternetShortcut', 'URL')
    elif ext=='.webloc':
        with open(file_path, 'rb') as f:
            plist_data = plistlib.load(f)
            url = plist_data.get('URL')
    elif ext=='.desktop':
        config = configparser.ConfigParser(strict=False)
        config.read(file_path)
        urlKys = [ k for k in config['Desktop Entry'] if k.upper()[:3]=='URL'] # sometimes the "URL" key has funky qualifiers, e.g. url[$e]=https://ww...
        if len(urlKys)==1:
            url = config.get('Desktop Entry', urlKys[0])

    if url:
        print(f'Found url: {url}', file=sys.stderr)
        print(f"subprocess.run([{chosenBrowser}, {url}], check=True)")
        subprocess.run([chosenBrowser, url], check=True)
    else:
        print(f'Unsupported file type: {ext}', file=sys.stderr)


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} <file>', file=sys.stderr)
        sys.exit(1)

    open_url_file(sys.argv[1])

# TBD add optional logger!



# .lnk (Windows Shortcut): On Windows systems, .lnk files are used as shortcuts and may contain URLs. These files are commonly created when a user creates a shortcut to a website on their desktop.

# .website: Some Windows systems use .website files to store links to websites. These files are essentially XML files containing information about the associated URL.

# .desktop (Generic): While .desktop files are commonly associated with Linux desktop environments, they can also be used on other platforms. These files are often used to create shortcuts or launchers, and they may contain URLs.

# .uri or .url: Some systems may use .uri as an alternative extension for files containing URLs. Additionally, files with the extension .url may be used on various platforms.

# .htm or .html (HTML Files): Simple HTML files can be used to store a URL. Users might create small HTML files with a link to a website.

# .link: The .link extension is sometimes used to indicate files containing links or shortcuts.

