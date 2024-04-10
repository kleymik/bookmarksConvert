#!/usr/bin/python3
#
# open a .url, .webloc, or .desktop url-containing file
#
# Script to open the small files that are used to keep urls
#
# There are no firm standards, these are the most common
#   ".webloc"  - Nextcloud link editor offers which apparently is an Apple-ism
#                xml so that seems expandable, e.g. even to keep the entire web-page too.
#   ".url"     - which is kind-of a microsoft-ism?
#   ".desktop" - linuxy used with mimtypes
#   ".html"    - an actual web-page instead of a link to a page
#

import os
import sys
import re
import argparse
import configparser                               # for .url, .desktop
import plistlib                                   # for .webloc xml
import subprocess
import datetime
from glob import glob
from os.path import expanduser

dt             = str(datetime.datetime.now())
logDir         = f"{expanduser('~')}/history"                         # folder to keep history log of urls opened
defaultBrowser = ['xdg-open', 'firefox', 'chromium', 'konqueror'][1]  # could add command line options, such as --new-tab [url]?
stderrFile     = f"{logDir}/openUrlFileLast.stderr"
browseLogFile  = f"{logDir}/openUrlFileBrowseLog_{dt[:6]}.log"        # logfile for each month


def get_url_file(file_path):
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    url = None

    if ext=='.url':                               # check for sections, without sections, configparser doesn't work
        config = configparser.ConfigParser()
        if args.verbose:                          # for k,v in config.items(): print('config',k,v)
            print(config)
        config.read(file_path)
        url = config.get('InternetShortcut', 'URL')

    elif ext=='.desktop':
        config = configparser.ConfigParser(strict=False)
        config.read(file_path)
        urlKys = [ k for k in config['Desktop Entry'] if k.upper()[:3]=='URL']  # sometimes the "URL" key has funky qualifiers, e.g. url[$e]=https://ww...
        if len(urlKys)==1: url = config.get('Desktop Entry', urlKys[0])

    elif ext=='.webloc':
        with open(file_path, 'rb') as f: url = plistlib.load(f).get('URL')

    elif ext=='.html':
        firstLine = open(fl).readline()
        if firstLine.startswith('<html><head><meta http-equiv="refresh"'):
            # for example: <html><head><meta http-equiv="refresh" content="0; url=https://www.ft.com/content/f9cf6d1a-0313-4c1f-aeb2-df1f64bd5d3e" /></head></html>
            mtch = re.search(r'url=(.+)"', firstLine)                 # from url=http.....to end double-quote
            if mtch: url = mtch.groups()[0]                           # <re.Match object; span=(0, 3), match='012'>
            else:    url = file_path                                  # just pass the file path to the browser    (n.b. an html file with one url in it works automaticaly with firefox)

    else:
        print(f'Unsupported file type: {ext}')
    return url



if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='openUrlFile',
        description='open url embedded in file',
        epilog='-------- openUrlFile.py --------')

    parser.add_argument('file|folder|glob', nargs="+")                # positional argument
    parser.add_argument('-t',  '--type',      action='store_true')    # type out the file containing the url
    parser.add_argument('-u',  '--url',       action='store_true')    # print the url
    parser.add_argument('-l',  '--list',      action='store_true')    # for folders/globs: list the files
    parser.add_argument('-v',  '--verbose',   action='store_true')    # be verbose
    parser.add_argument('-bf', '--firefox',   action='store_true')    # browse with firefox
    parser.add_argument('-bc', '--chromium',  action='store_true')    # browse with chromium
    parser.add_argument('-bk', '--konqueror', action='store_true')    # browse with konqueror
    parser.add_argument('-bo', '--xdgopen',   action='store_true')    # browse with xdg-open - beware of infinte recursion xdg-open may decide to use this srcipt !
    parser.add_argument('-nl', '--noLog',     action='store_true')    # log (append) to given log file

    args = parser.parse_args()                                        # print(args.filename, args.verbose)
    if args.verbose: print("parsed args", args)

    pth = vars(args)['file|folder|glob']

    if    args.firefox:   browser='firefox'
    elif  args.chromium:  browser='chromium'
    elif  args.konqueror: browser='konqueror'
    elif  args.xdgopen:   browser='xdg-open'
    else:                 browser=defaultBrowser
    if args.verbose: print("selected browser", browser)

    if args.verbose: print("determine file or files")
    if len(pth)==1 and os.path.isdir(pth[0]): files = glob(expanduser(pth[0])+'/*')  # if it's a folder path get (glob) all files in the folder
    elif os.path.isfile(pth[0]):              files = pth
    else:
        print(f"failed to interpret {pth}")
        sys.exit(1)

    for fl in [expanduser(f) for f in files]:
      if args.list:                                                   # type out the name of the file
        print(fl)
      elif args.type:                                                 # type out the contents of the file
        print("---",fl)
        for l in open(fl): print(l, end='')
        print()
      elif args.url:                                                  # print the embedded url
        print("---",fl)
        print("URL=", get_url_file(fl))
      else:
        url = get_url_file(fl)
        print(fl, ":URL=", url)
        if not args.noLog:
          with open(browseLogFile, 'a') as blf:
            print(f"DATE={dt}, ", file=blf, end='')
            print(f"URL={url}, ", file=blf, end='')
            print(f"FILE={fl}",   file=blf, end='')
            print(f"",            file=blf)
        subprocess.run([browser, url], check=True, stderr=open(stderrFile, 'w'), text=True)
      # print(f"DATE={dt}, URL={url}")

# TBD inspect first lines for:  "<!doctype html><html..."
# TBD - if it's a folder open all bookmark files in the folder!
# See also https://benchdoos.github.io/
#          https://gitlab.com/claderoki/QuickCut


