#!/usr/bin/python3
#
# open a .url, .webloc, or .desktop url file
#
# Script (started by GPT) to open the small files that are used to keep urls
# There are no firm standards, these are the most common
#   ".webloc"  - Nextcloud link editor offers which apparently is an Apple-ism
#                xml so that seems expandable, e.g. even to keep the entire web-page too.
#   ".url"     - which is kind-of a microsoft-ism?
#   ".desktop" -
#   ".html"    - an actual web-page instead of a link to a page

import os
import sys
import argparse
import configparser                    # for .url, .desktop
import plistlib                        # for .webloc xml
import subprocess
import datetime
chosenBrowser = ['xdg-open', 'firefox', 'chromium', 'konqueror'][1]  #  could add command line options, such as --new-tab
stderrFile    = "/home/kleyn/openUrlFile.stderr"

dt = str(datetime.datetime.now())
brosweLogFile = f"/home/kleyn/history/browseLog_{dt[:6]}.log"  # logfile for each month

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
    elif ext=='.html':
        # TBD
        pass
    return url


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='openUrlFile',
        description='open url embedded in file',
        epilog='-------- openUrlFile.py --------')

    parser.add_argument('filename')                                # positional argument
    parser.add_argument('-t', '--type',       action='store_true')   # type out the file containing the url
    parser.add_argument('-u', '--url',        action='store_true')   # print the url
    parser.add_argument('-v', '--verbose',    action='store_true')   # be verbose
    parser.add_argument('-bf', '--firefox',   action='store_true')   # browse with firefox
    parser.add_argument('-bc', '--chromium',  action='store_true')   # browse with chromium
    parser.add_argument('-bk', '--konqueror', action='store_true')   # browse with konqueror
    parser.add_argument('-bo', '--xdg-open',  action='store_true')   # browse with xdg-open - beware of infinte recursion xdg-open may decide to use this srcipt !
    parser.add_argument('-nl', '--nolog',     action='store_true')   # log (append) to given log file

    args = parser.parse_args()
    #print(args.filename, args.verbose)

    if args.type:
        for l in open(args.filename): print(l,end='')
    elif args.url:
        url = get_url_file(args.filename)
        print("URL=", url)
    else:
        url = get_url_file(args.filename)
        print("URL=", url)
        subprocess.run([chosenBrowser, url], check=True, stderr=open(stderrFile, 'w'), text=True)
        # if successfull log URL in browsing history
        if not args.noLog
        bh = open(browseLogFile, 'a')
        print(f"DATE={dt}, URL={url}", file=bh)

    if False:  # junk

        if len(sys.argv) != 2:
            print(f'Usage: {sys.argv[0]} <file>', file=sys.stderr)
            sys.exit(1)

        open_url_file(sys.argv[1])

        if url:
            print(f'Found url: {url}', file=sys.stderr)
            print(f"subprocess.run([{chosenBrowser}, {url}], check=True)")
        elif False:
            print(f'Unsupported file type: {ext}', file=sys.stderr)





