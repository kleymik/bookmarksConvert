#!/usr/bin/env python3
#
#
#     bookmarks converter:  bkmksConvert.py
#
#
import sys
import re
import os
import argparse
import subprocess
import json
import sqlite3
import unicodedata as ud
import datetime as dt

from glob import glob
from io import StringIO
from lxml import etree
from pathlib import Path

# ------------------------------------------------------------------------- utility functions

def cleanupTags(f, sio):
    """try to normalise the structure of the HTML by adding closing </tags> to match opening ones
       or remove spurious tags entirely. So that lxml has a better chance of a sane parse.
    """

    with open(f, 'r') as infile:
        for ln in infile:
            lnClean = re.sub(r'(\s+)<DT>', r'\1', ln);
            if lnClean.startswith('<DD>'): lnClean+='</DD>'           # close unclosed <DD>s
            lnClean = lnClean.replace('<p>','<p></p>')                # close unclosed <p>s
            sio.write(lnClean)
    sio.seek(0)
    return sio


def cleanName(txt):
    """derive a reasonable file name, free of weird characters, from the url name or title
    """

    if txt:
        cleanTxt = re.sub(r"[^a-zA-Z0-9_\ ]", "", txt).strip().replace(" ","_")
        if len(cleanTxt)>0: return cleanTxt[:200]                      # file *paths* can be at most 255? chars long - in nextCloud?
        else:               return ""
    else:
        return ""


def unixEpochToIsoDateTime(unixEpochSeconds):
    return dt.datetime.fromtimestamp(unixEpochSeconds).strftime('%Y-%m-%dT%H:%M:%S')


def closeUrlFile(fileDscrptr, urlDate=None):
    """close file and set its modified date to the url's add_date
    """

    urlFileName = fileDscrptr.name
    if fileDscrptr!=sys.stdout:
        fileDscrptr.close()
        if urlDate:
            if args.verbose: print("Closed", urlFileName, urlDate, unixEpochToIsoDateTime(urlDate)) # check date conversioning
            stat = os.stat(urlFileName)
            os.utime(urlFileName, times=(stat.st_atime, urlDate))     # utime must have two ints or floats (unix timestamps): (atime, mtime)

# ------------------------------------------------------------------------- functions to create files and folders

def makeBookmarkFile(depth, name, href, outFmt, add_date=None, last_visited=None, last_modified=None, icon_uri=None, icon=None, last_charset=None, date_scaling=1, fldrPath=None):
    """create a file named like the name or title associated with url and add the details of the url into the file
       date_scaling should be either 1 or 1000000 depending on whether the epoch integer date time is in seconds or in microseconds
    """

    pageCleanName = cleanName(name)
    if args.verbose: print("+ ", name)                                                     # print("*"*(depth+1), name)

    if fldrPath is None:
        outFile = sys.stdout
    else:
        urlFileName   = fldrPath / Path(pageCleanName if pageCleanName!="" else "notitle").with_suffix(outFmt)
        outFile = open(urlFileName, 'w', encoding='utf-8')                                 # file is not closed in this function as it may need more writing to (in the html parsing case)


    if add_date: addDate = int(add_date)/date_scaling
    else:
        print("WARNING: No Date for", name, file=sys.stderr)
        addDate = 0


    if outFmt=='.org' or outFile==sys.stdout:                                              # format as org-mode named list entries
        print(                  f" - TITLE ::{name}",                                                            file=outFile)
        print(                  f" - URL ::{href}",                                                              file=outFile)
        print(                  f" - DATE_ADDED ::{unixEpochToIsoDateTime(addDate)}",                            file=outFile)
        if last_modified: print(f" - DATE_MODIFIED ::{unixEpochToIsoDateTime(int(last_modified)/date_scaling)}", file=outFile)
        if last_visited:  print(f" - DATE_VISITED ::{unixEpochToIsoDateTime(int(last_visited)/date_scaling)}",   file=outFile)
        if icon_uri:      print(f" - ICON_URI ::{icon_uri}",                                                     file=outFile)
        if icon:          print(f" - ICON ::{icon}",                                                             file=outFile)
        if last_charset:  print(f" - LAST_CHARSET ::{last_charset}",                                             file=outFile)
        print(                   "",                                                                             file=outFile) # add terminating newline

    elif outFmt=='.url':                                                                   # format as window shortcut .url
        print(                   "[InternetShortcut]", file=outFile)
        print(                  f"TITLE={name}",                                                            file=outFile)
        print(                  f"URL={href}",                                                              file=outFile)
        print(                  f"DATE_ADDED={unixEpochToIsoDateTime(addDate)}",                            file=outFile)
        if last_modified: print(f"DATE_MODIFIED={unixEpochToIsoDateTime(int(last_modified)/date_scaling)}", file=outFile)
        if last_visited:  print(f"DATE_VISITED={unixEpochToIsoDateTime(int(last_visited)/date_scaling)}",   file=outFile)
        if icon_uri:      print(f"ICON_URI={icon_uri}",                                                     file=outFile)
        if icon:          print(f"ICON={icon}",                                                             file=outFile)
        if last_charset:  print(f"LAST_CHARSET={last_charset}",                                             file=outFile)
        print(                   "",                                                                        file=outFile) # add terminating newline

    elif outFmt=='.html':                                                                  # create ".html" file like the .html one Firefox extension "QC Save Link" makes, i.e.
        print( "<html>",                                                    file=outFile)
        print( "  <head>",                                                  file=outFile)
        print(f'    <meta http-equiv="refresh" content="0; url={href}" />', file=outFile)
        print( "  </head>",                                                 file=outFile)
        print( "</html>",                                                   file=outFile)
        print( "",                                                          file=outFile)  # add terminating newline

    elif outFmt=='.webloc':
        print( '<?xml version="1.0" encoding="UTF-8"?>',                                                                 file=outFile)
        print( '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">', file=outFile)  # optional?
        print( '<plist version="1.0">',                                                                                  file=outFile)
        print( '  <dict>',                                                                                               file=outFile)
        print(f'    <key>URL</key> <string>{href}</string>',                                                             file=outFile)
        print(f'    <key>DATE_ADDED</key> <string>{unixEpochToIsoDateTime(addDate)}</string>',                           file=outFile)  # non-standard additional info
        print( '  </dict>',                                                                                              file=outFile)
        print( '</plist>',                                                                                               file=outFile)
        print( "",                                                                                                       file=outFile)  # add details terminating newline

    return outFile, addDate


def makeBookmarkFolderDir(depth, text, fldrPath=None):
    """use mkdir to create folder path
    """

    clnName = cleanName(text)
    print("*"*depth, clnName)

    if fldrPath is None:
        subFldrPath = None
    else:
        subFldrPath = fldrPath / clnName
        os.makedirs(subFldrPath, exist_ok=True)

    return subFldrPath

# ------------------------------------------------------------------------- convert sqlite

def readSqliteBookmarks(dbFile):
    """convert hierarchy implict in table back into explicit one
    """

    conn = sqlite3.connect(dbFile)
    cur = conn.cursor()
    allDict = {}

    sqry = """SELECT mb.id, mb.title, mb.type, mb.parent, mb.dateAdded, mp.url
                FROM moz_bookmarks mb
           LEFT JOIN moz_places mp ON mb.fk=mp.id
            ORDER BY mb.id ASC"""
    cur.execute(sqry)
    for (id, title, type, parent, dateAdded, url) in cur.fetchall():                # print(id, cleanName(title), parent)
        allDict[id] = {'id':        id,
                       'name':      title,
                       'url':       url,
                       'type':      type,
                       'parent':    parent,
                       'dateAdded': dateAdded}
    conn.close()

    allDict[0] = {'id':0, 'name':'root', 'children':[1]}                            # make tree by getting each parent to point to children
    for id in allDict:                                                              # print(id, [ (k, allDict[id][k]) for k in allDict[id] if k!='children' ] )
        if 'parent' in allDict[id]:
            prnt = allDict[id]['parent']
            if prnt in allDict:
                if 'children' not in allDict[prnt]: allDict[prnt]['children'] = []
                allDict[prnt]['children'] += [id]                                   # print(prnt,allDict[prnt]['children'])
            else:
                print('Failed to find parent with id=', prnt, file=sys.stderr)
    allDict[1]['name'] = 'subroot'

    return allDict

def dftSqliteDict(fldrPath, node, allDict, outFmt, depth=0):
    """depth first traversal of dict derived from moz_bookmarks sqlite tables
    """

    if 'children' in node:
        subFldrPath = makeBookmarkFolderDir(depth, node['name'], fldrPath=fldrPath)
        for c in node['children']: dftSqliteDict(subFldrPath, allDict[c], allDict, outFmt, depth+1)
    else:
        outFile, fileDate = makeBookmarkFile(depth, node['name'], node['url'], outFmt, add_date=node['dateAdded'], date_scaling=1000000, fldrPath=fldrPath)
        closeUrlFile(outFile, fileDate)


# Notes: typical sqlite moz_ tables structure
# sqlite moz tables:
# moz_bookmarks (id INTEGER PRIMARY KEY, type INTEGER, fk INTEGER DEFAULT NULL, parent INTEGER, position INTEGER, title LONGVARCHAR, keyword_id INTEGER, folder_type TEXT,
#                                  dateAdded INTEGER, lastModified INTEGER, guid TEXT, syncStatus INTEGER NOT NULL DEFAULT 0, syncChangeCounter INTEGER NOT NULL DEFAULT 1)
# moz_places    (id INTEGER PRIMARY KEY, url LONGVARCHAR, title LONGVARCHAR, rev_host LONGVARCHAR, visit_count INTEGER DEFAULT 0, hidden INTEGER DEFAULT 0 NOT NULL,
#                   typed INTEGER DEFAULT 0 NOT NULL, frecency INTEGER DEFAULT -1 NOT NULL, last_visit_date INTEGER , guid TEXT, foreign_count INTEGER DEFAULT 0 NOT NULL,
#                    url_hash INTEGER DEFAULT 0 NOT NULL , description TEXT, preview_image_url TEXT, origin_id INTEGER REFERENCES moz_origins(id))
#
# scrub the database of dodgy characters otherwise sqlite barfs, e.g.
#  sqlite3 firefox_places.sqlite '.dump' | strings | sqlite3 firefox_places_clean.sqlite


# ------------------------------------------------------------------------- convert json

def readJsonBookmarks(infile):
    print("reading FILE", infile, file=sys.stderr)
    with open(infile, 'r') as source: data = json.load(source)
    return data

def dftJson(fldrPath, jData, outFmt, depth=0):
    """depth first traversal of json
    """
    name = jData['name'] if 'name' in jData else jData['title']

    if jData['type']=='text/x-moz-place-container':
        subFldrPath = makeBookmarkFolderDir(depth, name, fldrPath=fldrPath)
        for c in jData['children']: dftJson(subFldrPath, c, outFmt, depth+1)

    elif jData['type']=='text/x-moz-place' and jData['title'] not in ('Recently Bookmarked','Recent Tags', 'Most Visited'):
        if 'dateAdded' in jData:
            url = jData['url' if 'url' in jData else 'uri']
            outFile, fileDate = makeBookmarkFile(depth, name, url, outFmt, add_date=jData['dateAdded'], last_modified=jData['lastModified'], date_scaling=1000000, fldrPath=fldrPath)
            closeUrlFile(outFile, fileDate)
        else:
            print(jData['type'], list(jData.items()), file=sys.stderr)
    else:
        print('skipped', jData['type'], jData['title'], file=sys.stderr)
        # print(jData, file=sys.stderr)


# Notes: typical json structure:
# json record typical fields
#   links:
#    {'date_added': '0',
#     'guid': '7f6a3a6a-d375-4500-8010-2af013a3d12d',
#     'id': '5',
#     'name': 'Community',
#     'type': 'url',
#     'url': 'https://community.linuxmint.com/'}
#   folders:
#    {'date_added': '13276128414300148',
#     'date_modified': '0'
#     'guid': ''ba62c54f-d6c8-4943-867b-0d83f30da76f',
#     'id': '9',
#     'name': 'Goog',
#     'type': 'folder'
#     'children':[.........]}  more same records


# ------------------------------------------------------------------------- convert html

def readHtmlBookmarks(inFile):
    sio = cleanupTags(inFile, StringIO(''))                                         # parse cleaned-up file using lxml eTree
    pTree = etree.parse(sio, etree.HTMLParser())
    sio.close()
    return pTree

def dftHtml(fldrPath, el, outFmt, depth=0):
    """depth first traversal to create fh (=file hierarchy)
    """

    if not fldrPath: outFile = sys.stdout

    subFldr  = ''
    numChlds = len(el)
    for ei,e in enumerate(el):                                                     # typical keys: ['href', 'add_date', 'last_modified', 'icon_uri', 'icon', 'last_charset']         # print(" "*4*depth, "DEBUG", e.tag, e.text, e.keys(), f'chlds={len(e)}', fldrPath) # debug

        if e.tag=='a' and e.text:                                                  # print(indntStr*depth, fldrPath / cleanName(e.text)) #, e.get('href') print(indent*depth, e.tag, e.get('href'), e.text)

            try:
                outFile, fileDate = makeBookmarkFile(depth, e.text, e.get('href'), outFmt, add_date=e.get('add_date'), last_visited=e.get('last_visit'), icon_uri=e.get('icon_uri'), icon=e.get('icon'), last_charset=e.get('last_charset'), fldrPath=fldrPath)
            except Exception as e:
                print(e)
                print(e.keys())
                print("FAILED ON", e.text)
                closeUrlFile(outFile)
                sys.exit()
            if ei+1<numChlds-1 and el[ei+1].tag=='dd':                             # lookahead in case there is a further DESCRIPTON of the anchor, right after it
                if outFile!=sys.stdout:
                    print('DESCRIPTION:', el[ei+1].text.strip(), file=outFile)     # sometimes (rarely, but it happens) a <DT> is followed by a descriptive <DD> that should also be written into the url file
            if fldrPath: closeUrlFile(outFile, fileDate)

        elif e.tag=='h3':

            maybePath = makeBookmarkFolderDir(depth, e.text, fldrPath=fldrPath)
            if maybePath: subFldr = maybePath.parts[-1]

        elif e.tag in ['dl','dt','p','head','body']:                               # keep recursing down

            if fldrPath: subpath = Path(fldrPath) / Path(subFldr)
            else:        subpath = None
            dftHtml(subpath, e, outFmt, depth+1)

# ------------------------------------------------------------------------- other html functions

def compareHtmlFiles(htmlDir, lim=100):
    """independent function to give a measure of how similar pairs of html bookmark files are
    """
    allFiles = glob(htmlDir+"/*.html")[:lim]
    for ai,fa in enumerate(allFiles):
        for bi in range(ai+1, len(allFiles)):
            fb = allFiles[bi]
            os.system(f"sed 's/^[ \t]*//g' {fa} | sort -u > /tmp/t1")
            fas = int(subprocess.getoutput(f'wc -l /tmp/t1').split()[0])
            os.system(f"sed 's/^[ \t]*//g' {fb} | sort -u > /tmp/t2")
            fbs = int(subprocess.getoutput(f'wc -l /tmp/t2').split()[0])
            result = int(subprocess.getoutput(f'comm -12 /tmp/t1 /tmp/t2 | wc -l'))
            if result>0: print(f"{float(result/max(fas,fbs)):5.4f} {result:5d} {fas:5d} {fbs:5d} ", fa, fb)

# ------------------------------------- GLOBAL VAR
indntStr = "   "       # indentation string when writing to stdout

def dftPrint(el, path='', depth=0):
    """depth first traversal - print file hierarchy without creating it
    """
    global indntStr

    subFldr = ''
    numChlds = len(el)
    for ei,e in enumerate(el):                                                     # print(depth, "DEBUG", e.tag, path, f'chlds={len(e)}', e.keys())

        if e.tag=='a':
            print(depth, indntStr*depth, "A", ei, cleanName(e.text), end='')       # e.get('href') print(indent*depth, e.tag, e.get('href'), e.text) Path(path) /
            if ei+1<numChlds-1 and el[ei+1].tag=='dd': print(' DD>', depth, ei+1, el[ei+1].text.strip(), '<DD') # lookahead in case there is a further DESCRIPTON of the anchor, right after it
            else:                                      print('')

        elif e.tag=='h3':
            subFldr = cleanName(e.text)

        if e.tag in ['dl','dt','p','head','body']:
            dftPrint(e, path=path / Path(subFldr), depth=depth+1)                  # only 'dl' and 'p' have children?


# Notes: typical html structure
# html tag structure:
#  <DT>
#    <A HREF="https://www.microsoft.com/en-gb/software-download/windows10iso"
#       ADD_DATE="1635097118"
#       ICON="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAA..................">
#       Download Windows 10 Disc Image (ISO File)
#     </A>
#  <DT>
# hence typical  lxml element keys:
#   ['href', 'add_date', 'last_modified', 'icon_uri', 'icon', 'last_charset']


# ------------------------------------------------------------------------------ main
if __name__ == "__main__":


    descrip = '''
     bookmarks.[html|json|slqlite] - an input file containing bookmarks/favorites in one of these formats

     rootWriteFldrAreaPath - a path to a directory inside which the hierarchy of bookmarks will be created as subfolders and files
         if omitted, the bookmark data will be printed to stdout in org-mode format (no files or folders will be created)

     For example:
       ./bmksConvert.py bmArchive/html/bookmarks_20070817.html
       ./bmksConvert.py bmArchive/json/bookmarks_20080907.json      ./testArea/json
       ./bmksConvert.py bmArchive/sqlite/firefox_places_2021.sqlite ./testArea/sqlite
    '''

    parser = argparse.ArgumentParser(
        prog='bkmksConvert.py',
        description='convert file [.sqlite|.html|.json] containing bookmarks into file hierarchy of single-bookmark files [.html|.url|.webloc|..]',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=descrip)

    parser.add_argument('file',                                   type=str, help="file containing urls")                                                 # Add required positional argument
    parser.add_argument('writeFolder', nargs='?', default=None,   type=str, help="path to folder inside which (many!) folder & files hierarchy will be created") # Add optional positional
    parser.add_argument('-v',  '--verbose',  action='store_true')     # be verbose

    exclsve_grp = parser.add_mutually_exclusive_group(required=True)  # Create mutually exclusive group
    exclsve_grp.add_argument('-ow', '--webloc',   action='store_true', help='write url files in .webloc format')
    exclsve_grp.add_argument('-oh', '--html',     action='store_true', help='write url files in .html format')
    exclsve_grp.add_argument('-ou', '--url',      action='store_true', help='write url files in .url format')
    exclsve_grp.add_argument('-oo', '--orgmode',  action='store_true', help='write urls in one  .org format file')

    args = parser.parse_args()                                       # print(args.filename, args.verbose)


    if args.verbose: print("DEBUG: parsed args", args)
    if args.verbose: print("DEBUG: determine file or files")

    inFile        = Path(vars(args)['file'])
    rootWriteFldr = vars(args)['writeFolder']
    if not rootWriteFldr: print("DEBUG: no write folder given, output to stdout in org-mode format")

    if not rootWriteFldr: outFmt = ".org"                             # default, implies to stdout
    elif args.webloc:     outFmt = ".webloc"
    elif args.html:       outFmt = ".html"
    elif args.url:        outFmt = ".url"
    else:                 outFmt = ".org"                             # default, implies to stdout
    if args.verbose: print("DEBUG: output files format =", outFmt)

    if  rootWriteFldr: os.makedirs(rootWriteFldr, exist_ok=True)

    if   inFile.suffix=='.sqlite':
        pTreeDict = readSqliteBookmarks(inFile)
        dftSqliteDict(rootWriteFldr, pTreeDict[0], pTreeDict, outFmt)
    elif inFile.suffix=='.json':
        pTreeObj = readJsonBookmarks(inFile)
        dftJson(rootWriteFldr, pTreeObj, outFmt)
    elif inFile.suffix=='.html':
        pTreeObj = readHtmlBookmarks(inFile)
        dftHtml(rootWriteFldr, pTreeObj.getroot(), outFmt)


