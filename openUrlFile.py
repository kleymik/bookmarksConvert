#!/usr/bin/python3
#
# open a .url, .webloc, or .desktop url file
#
# Script (started by GPT) to open the small files that are used to keep urls
# There are no firm standards, these are the most common
#   Nextcloud link editor offers ".webloc" which apparently is an Apple-ism
#   or ".url" which is kind-of a microsoft-ism?
#   .webloc are xml, so that seems expandable, e.g even to keep the entire web-page too.

import os
import sys
import configparser                    # for .url, .desktop
import argparse
import plistlib                        # for .webloc xml
import subprocess


chosenBrowser = ['xdg-open', 'firefox', 'chromium', 'konqueror'][1]  #  could add command line options, such as --new-tab

def get_url_file(file_path):
    _, ext = os.path.splitext(file_path)
    url = None

    ext = ext.lower()
    if ext=='.url':
        config = configparser.ConfigParser()
        config.read(file_path)
        url = config.get('InternetShortcut', 'URL')
    elif ext=='.desktop':
        config = configparser.ConfigParser(strict=False)
        config.read(file_path)
        urlKys = [ k for k in config['Desktop Entry'] if k.upper()[:3]=='URL'] # sometimes the "URL" key has funky qualifiers, e.g. url[$e]=https://ww...
        if len(urlKys)==1:
            url = config.get('Desktop Entry', urlKys[0])
    elif ext=='.webloc':
        with open(file_path, 'rb') as f:
            plist_data = plistlib.load(f)
            url = plist_data.get('URL')
    return url



if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='openUrlFile',
        description='open url embedded in file',
        epilog='-------- openUrlFile.py --------')

    parser.add_argument('filename')             # positional argument
    # parser.add_argument('-c', '--count')      # option that takes a value
    parser.add_argument('-t', '--type',    action='store_true')    # type out the file
    parser.add_argument('-u', '--url',     action='store_true')    # print the url
    parser.add_argument('-v', '--verbose', action='store_true')    # on/off flag
    parser.add_argument('-bf', '--verbose', action='store_true')    # browse with firefox
    parser.add_argument('-bc', '--verbose', action='store_true')    # on/off flag
    parser.add_argument('-bk', '--verbose', action='store_true')    # on/off flag

    args = parser.parse_args()
    print(args.filename, args.verbose)

    if args.type:
        for l in open(args.filename): print(l,end='')
    elif args.url:
        url = get_url_file(file_path)
        print(url)
    else:
        url = get_url_file(file_path)
        subprocess.run([chosenBrowser, url], check=True, stderr="/home/kleyn/openUrlFile.stderr")

    if False:  # junk

        if len(sys.argv) != 2:
            print(f'Usage: {sys.argv[0]} <file>', file=sys.stderr)
            sys.exit(1)

        open_url_file(sys.argv[1])

        if url:
            print(f'Found url: {url}', file=sys.stderr)
            print(f"subprocess.run([{chosenBrowser}, {url}], check=True)")
        elif :
            print(f'Unsupported file type: {ext}', file=sys.stderr)

# TBD add an optional logger to record browsing history!
# The ArgumentParser.add_argument() method attaches individual argument
# specifications to the parser. It supports positional arguments, options that accept values, and on/off flags:

#The ArgumentParser.parse_args() method runs the parser and places the extracted data in a argparse.Namespace object:


# .lnk (Windows Shortcut): On Windows systems, .lnk files are used as shortcuts and may contain URLs. These files are commonly created when a user creates a shortcut to a website on their desktop.

# .website: Some Windows systems use .website files to store links to websites. These files are essentially XML files containing information about the associated URL.

# .desktop (Generic): While .desktop files are commonly associated with Linux desktop environments, they can also be used on other platforms. These files are often used to create shortcuts or launchers, and they may contain URLs.

# .uri or .url: Some systems may use .uri as an alternative extension for files containing URLs. Additionally, files with the extension .url may be used on various platforms.

# .htm or .html (HTML Files): Simple HTML files can be used to store a URL. Users might create small HTML files with a link to a website.

# .link: The .link extension is sometimes used to indicate files containing links or shortcuts.
