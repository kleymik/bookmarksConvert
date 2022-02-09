#!/usr/bin/env python
#
# wetRun => !dryRun
#     bookmarksToTree.py
#
# Way back in the mists of time, browser bookmarks and favourites were
# stored as individual files (e.g with a ".url" extension) in directory structures.
# They could be managed and searched just like other files. Now they tend to be stored in sqlite
# and exported into html or json. This program can convert any of these formats
# (back) into a file hierarchy.
#
# Convert bookmarks/favorites from source format (html, json, or sqlite)
# and create corresponding nested folders and files by depth-first-traversal ("dft")
# - file name is bookmark simplified name, with ".url" as extension
# - inside the file are the bookmark details:
#     - the exact name ('title') of the bookmark
#     - dates (added,modified,last_visited)
#     - any other details
# - bookmark last_visited date is used to set modification of file name
#   so that tools like "find" can be used (e.g. find ./ -name '*foo*' -mtime +100 )

import sys
import re
import os
import json
import sqlite3
import unicodedata as ud
import datetime as dt
from io import StringIO
from lxml import etree

from pathlib import Path
from see import see

# ------------------------------------------------------------------------- globals
#indntStr = "   "         # indentation string when writing to stdout in dry-run mode
indntStr = ""         # indentation string when writing to stdout in dry-run mode
stdoutVerbose = False    # show contents of generated files when writing stdout in dry-run mode

# ------------------------------------------------------------------------- utility funs
def cleanupDt(f, sio):
    '''remove spurious <DT>s from HTML to avoid which confusing traversal'''
    with open(f, 'r') as infile:
        for ln in infile:
            lnClean = re.sub(r'(\s+)<DT>', r'\1', ln);
            sio.write(lnClean)
    sio.seek(0)
    return sio

def cleanName(txt):
    '''derive a reasonable file name from the url name ("title")'''
    if txt:
        cleanTxt = re.sub(r"[^a-zA-Z0-9_\ ]", "", txt).strip().replace(" ","_")
        if len(cleanTxt)>0: return cleanTxt[:250] # file names can be atmost 255 chars long
        else:               return ""
    else:
        return ""


def unixEpochToIsoDateTime(unixEpochSeconds):
    return dt.datetime.fromtimestamp(unixEpochSeconds).strftime('%Y-%m-%dT%H:%M:%S')

def closeUrlFile(fileDscrptr, urlDate=None):
    '''close file and set its modified date to the url's add_date'''
    urlFileName = fileDscrptr.name
    if fileDscrptr!=sys.stdout:
        fileDscrptr.close()
        if urlDate:
            print("Closed", urlFileName, urlDate, unixEpochToIsoDateTime(urlDate)) # check date conversioning
            stat = os.stat(urlFileName)
            os.utime(urlFileName, times=(stat.st_atime, urlDate))         # utime must have two ints or floats (unix timestamps): (atime, mtime)


def makeBookmarkFile(wetRun, fldrPath, name, href, add_date=None, last_visited=None, last_modified=None, icon_uri=None, icon=None, last_charset=None, date_scaling=1):
    '''create a file named like the title or name associated with url
    add properties of the url into the file
    date_scaling should be either 1 or 1000000 depending on whether the epoch integer date time is in seconds or in microseconds
    '''
    global stdoutVerbose

    pageCleanName = cleanName(name)
    urlFileName   = fldrPath / Path(pageCleanName if pageCleanName!="" else "notitle").with_suffix('.url')
    print(urlFileName)

    if wetRun: outFile = open(urlFileName, 'w')   # file is not close in this function as it may need more writing to (in the html case)
    else:      outFile = sys.stdout

    if add_date: addDate = int(add_date)/date_scaling
    else:
        print("WARNING: No Date for", urlFileName, file=sys.stderr)
        addDate =0

    if outFile!=sys.stdout or stdoutVerbose:
        print(                  "TITLE:",         name,                                                    file=outFile)
        print(                  "URI:",           href,                                                    file=outFile)
        print(                  "DATE_ADDED:",    unixEpochToIsoDateTime(addDate),                         file=outFile)
        if last_modified: print("DATE_MODIFIED:", unixEpochToIsoDateTime(int(last_modified)/date_scaling), file=outFile)
        if last_visited:  print("DATE_VISITED:",  unixEpochToIsoDateTime(int(last_visited)/date_scaling),  file=outFile)
        if icon_uri:      print("ICON_URI:",      icon_uri,                                                file=outFile)
        if icon:          print("ICON:",          icon,                                                    file=outFile)
        if last_charset:  print("LAST_CHARSET:",  last_charset,                                            file=outFile)
    return outFile, addDate

def makeBookmarkFolderDir(wetRun, fldrPath, text):
    '''use mkdir to create folder path'''
    subFldrPath = fldrPath / cleanName(text)
    print(f"os.mkdir({subFldrPath})")
    if wetRun: os.makedirs(subFldrPath, exist_ok=True)
    return subFldrPath

# ------------------------------------------------------------------------- convert sqlite

def readSqliteBookmarks(dbFile):                                                    # convert hierarchy implict in table back into explicit one

    conn = sqlite3.connect(dbFile)
    cur = conn.cursor()
    allDict = {}

    sqry = '''SELECT mb.id, mb.title, mb.type, mb.parent, mb.dateAdded, mp.url
                FROM moz_bookmarks mb
           LEFT JOIN moz_places mp ON mb.fk=mp.id
            ORDER BY mb.id ASC'''
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

def dftSqliteDict(fldrPath, node, allDict, depth=0, wetRun=False):                  # depth first traversal of dict derived from moz_bookmakrs sqlite table

    global indntStr

    if 'children' in node:
        subFldrPath = makeBookmarkFolderDir(wetRun, fldrPath, node['name'])
        for c in node['children']: dftSqliteDict(subFldrPath, allDict[c], allDict, depth+1, wetRun)
    else:
        outFile, fileDate = makeBookmarkFile(wetRun, fldrPath, node['name'], node['url'], add_date=node['dateAdded'], date_scaling=1000000)
        closeUrlFile(outFile, fileDate)


# Note: typical sqlite moz_ tables structure
# sqlite moz tables:
# moz_bookmarks (id INTEGER PRIMARY KEY, type INTEGER, fk INTEGER DEFAULT NULL, parent INTEGER, position INTEGER, title LONGVARCHAR, keyword_id INTEGER, folder_type TEXT,
#                                  dateAdded INTEGER, lastModified INTEGER, guid TEXT, syncStatus INTEGER NOT NULL DEFAULT 0, syncChangeCounter INTEGER NOT NULL DEFAULT 1)
# moz_places    (id INTEGER PRIMARY KEY, url LONGVARCHAR, title LONGVARCHAR, rev_host LONGVARCHAR, visit_count INTEGER DEFAULT 0, hidden INTEGER DEFAULT 0 NOT NULL,
#                   typed INTEGER DEFAULT 0 NOT NULL, frecency INTEGER DEFAULT -1 NOT NULL, last_visit_date INTEGER , guid TEXT, foreign_count INTEGER DEFAULT 0 NOT NULL,
#                    url_hash INTEGER DEFAULT 0 NOT NULL , description TEXT, preview_image_url TEXT, origin_id INTEGER REFERENCES moz_origins(id))
#
# scrub the database of dodgy characters otherwise sqlite barfs, e.g.
#  sqlite3 firefox_places.sqlite '.dump' | string | sqlite3 firefox_places_clean.sqlite


# ------------------------------------------------------------------------- convert json

def readJsonBookmarks(infile):
    print("FILE", infile)
    with open(infile, 'r') as source: data = json.load(source)
    return data

def dftJson(fldrPath, jData, depth=0, wetRun=False):                            # depth first traversal of json
    global indntStr
    name = jData['name'] if 'name' in jData else jData['title']

    if jData['type']=='text/x-moz-place-container':
        print(indntStr*depth, name)
        subFldrPath = makeBookmarkFolderDir(wetRun, fldrPath, name)
        for c in jData['children']: dftJson(subFldrPath, c, depth+1)

    elif jData['type']=='text/x-moz-place' and jData['title'] not in ('Recently Bookmarked','Recent Tags', 'Most Visited'):
        if 'dateAdded' in jData:
            url = jData['url' if 'url' in jData else 'uri']                    # print(indntStr*depth, cleanName(name), "-------", url)
            outFile, fileDate = makeBookmarkFile(wetRun, fldrPath, name, url, add_date=jData['dateAdded'], last_modified=jData['lastModified'], date_scaling=1000000)
            closeUrlFile(outFile, fileDate)
        else:
            print(jData['type'], list(jData.items()), file=sys.stderr)
    else:
        print('skipped', jData['type'], jData['title'], file=sys.stderr)
        # print(jData, file=sys.stderr)

# Note: typical json structure:
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
#     'type': 'fodler'
#     'children':[.........]}  more same records


# ------------------------------------------------------------------------- convert html

def readHtmlBookmarks(inFile):
    sio = cleanupDt(inFile, StringIO(''))                                       # parse cleaned-up file using lxml eTree
    pTree = etree.parse(sio, etree.HTMLParser())
    sio.close()
    return pTree

def dftHtmlX(fldrPath, el, depth=0, wetRun=False):                               # depth first traversal to create fh (=file hierarchy)
    global stdoutVerbose

    if not wetRun: outFile=sys.stdout

    print("DEBUG0", len(el), el)
    for e in el:                                                                # typical keys: ['href', 'add_date', 'last_modified', 'icon_uri', 'icon', 'last_charset']
        print("DEBUG1", e.tag, e.text, e.keys()) # debug
        if (e.tag=='dd') or (e.tag=='a' and e.text and (e.get('add_date') or e.get('last_visit')) and not e.get('href').startswith('find')): # and not e.get('href').startswith('ftp')
            if e.tag=='a':
                try:
                    outFile, fileDate = makeBookmarkFile(wetRun, fldrPath, e.text, e.get('href'), add_date=e.get('add_date'), last_visited=e.get('last_visit'), icon_uri=e.get('icon_uri'), icon=e.get('icon'), last_charset=e.get('last_charset'))
                except Exception as e:
                    print(e)
                    print("FAILED ON", e.text)
                    print(e.keys())
                    closeUrlFile(outFile)
                    sys.exit()
            elif e.tag=='dd' and e.text.strip():                                # sometimes (rarely, but it happens) a <DT> is followed by a descriptive <DD> that should also be written into the url file
                if outFile!=sys.stdout or stdoutVerbose:
                    print(f"DESCRIPTION:{e.text.strip()}", file=outFile)          # so closing file (below) has to be delayed to after this check here

            if wetRun: closeUrlFile(outFile, fileDate)

        if e.tag=='h3':                                                       # create a subfolder
            print("DEBUG2", e.tag, e.text, e.keys()) # debug
            fldrPath = makeBookmarkFolderDir(wetRun, fldrPath, e.text)
            dftHtmlX(fldrPath, e, depth+1, wetRun=wetRun)

        else:
            print("OTHER", e.tag, file=sys.stderr,end='')                       # check stderr to see if anything got missed
            if e.text: print(" TEXT=", e.text, file=sys.stderr,end='')
            #for k in e.keys(): print(" KEY=", k, e.get(k), file=sys.stderr, end='')
            print('', file=sys.stderr)

            dftHtmlX(fldrPath, e, depth, wetRun=wetRun)


def dftHtml(fldrPath, el, depth=0, wetRun=False):                               # depth first traversal to create fh (=file hierarchy)
    global stdoutVerbose
    global indntStr

    if not wetRun: outFile=sys.stdout

    subFldr = ''
    for e in el:                                                                # typical keys: ['href', 'add_date', 'last_modified', 'icon_uri', 'icon', 'last_charset']
        # print(" "*4*depth, "DEBUG1", e.tag, e.text, e.keys(), f'chlds={len(e)}', fldrPath, file=sys.stderr) # debug
        if e.tag=='a' and e.text:                                               #print(indntStr*depth, fldrPath / cleanName(e.text)) #, e.get('href') print(indent*depth, e.tag, e.get('href'), e.text)
            try:
                outFile, fileDate = makeBookmarkFile(wetRun, fldrPath, e.text, e.get('href'), add_date=e.get('add_date'), last_visited=e.get('last_visit'), icon_uri=e.get('icon_uri'), icon=e.get('icon'), last_charset=e.get('last_charset'))
            except Exception as e:
                print(e)
                print(e.keys())
                print("FAILED ON", e.text)
                closeUrlFile(outFile)
                sys.exit()
        elif e.tag=='h3':
            subFldr = makeBookmarkFolderDir(wetRun, fldrPath, e.text).parts[-1]
        elif e.tag in ['dl','dt','dd','p','head','body']:
            if e.tag=='dd': print('WARNING: DD', e.text.strip())                 # sometimes (rarely, but it happens) a <DT> is followed by a descriptive <DD> that should also be written into the url file
            dftHtml(Path(fldrPath) / Path(subFldr), e, depth+1, wetRun=wetRun)   # dftPrint(e, path=path / Path(subFldr), depth=depth+1)


def dftPrint(el, path='', depth=0):                                              # depth first traversal - make file hierarchy
    global indntStr

    subFldr = ''
    for e in el:                                          # ['href', 'add_date', 'last_modified', 'icon_uri', 'icon', 'last_charset']
        print("DEBUG111", depth, e.tag, path, f'chlds={len(e)}')
        if   e.tag=='a':                                  print(indntStr*depth, Path(path) / cleanName(e.text)) #, e.get('href') print(indent*depth, e.tag, e.get('href'), e.text)
        elif e.tag=='h3':                                 subFldr = cleanName(e.text)
        elif e.tag in ['dl','p','dt','head','body','dd']: dftPrint(e, path=path / Path(subFldr), depth=depth+1) # only 'dl' and 'p' have children?


# Note: typical html structure
# html tag structure
# <DT>
#   <A HREF="https://www.microsoft.com/en-gb/software-download/windows10iso"
#      ADD_DATE="1635097118"
#      ICON="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAA..................">
#      Download Windows 10 Disc Image (ISO File)
#    </A>
# <DT>


# ------------------------------------------------------------------------------ main
if __name__ == "__main__":

    if len(sys.argv)<2:
        print("Usage: bmcTraverse.py bookmarks.[html|json|slqlite] [rootfolderWriteAreaPath] [W]")
        print()
        print("    bookmarks.[html|json|slqlite] - an input file containing bookmarks/favorites in one of these formats")
        print()
        print("    rootfolderWriteAreaPath - a path to a folder inside which the hierarchy of bookmarks will be created as subfolders and files")
        print()
        print("    W flag which must ='W' for files and folders to be created,")
        print("        otherwise bookmarks and folder information will be written to stdout as a dry-run and no files or folders will be created")
        print()
        print("For Example")
        print("        ./bmcTraverse.py bmArchive/html/bookmarks_20070817.html      ./testArea/html")
        print("        ./bmcTraverse.py bmArchive/json/bookmarks_20080907.json      ./testArea/json")
        print("        ./bmcTraverse.py bmArchive/sqlite/firefox_places_2021.sqlite ./testArea/sqlite W")
        print()
    else:
        inFile          = Path(sys.argv[1])
        rootWriteFolder = Path(sys.argv[2])

        wetRun = False                                                     # i.e. "dry run" is by default true
        if len(sys.argv)==4 and sys.argv[3]=='W': wetRun = True            # only create (many!) files and folders if 3rd arg="W"

        if wetRun: os.makedirs(rootWriteFolder, exist_ok=True)

        if   inFile.suffix=='.sqlite':
            pTreeDict = readSqliteBookmarks(inFile)
            dftSqliteDict(rootWriteFolder, pTreeDict[0], pTreeDict, wetRun=wetRun)
        elif inFile.suffix=='.json':
            pTreeObj = readJsonBookmarks(inFile)
            dftJson(rootWriteFolder, pTreeObj, wetRun=wetRun)
        elif inFile.suffix=='.html':
            pTreeObj = readHtmlBookmarks(inFile)
            dftHtml(rootWriteFolder, pTreeObj.getroot(), wetRun=wetRun)
            #dftHtmlX(Path("fooooo"), pTreeObj.getroot()[1], wetRun=wetRun)
            #dftPrint(pTreeObj.getroot(), path=Path('./foo/'))


