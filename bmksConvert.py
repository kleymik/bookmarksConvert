#!/usr/bin/env python
# Way back in the mist of time, browser bookmarks and favourites were
# stored as individual files (e.g with a ".url" extension) in directory structures.
# They could be managed just like other files. Now they tend to be stored in sqlite
# and exported into html or json. This program can convert any of these formats
# (back) into a file hierarchy.
#
# Convert bookmarks/favorites from source format (html, json, or sqlite)
# and create corresponding nested folders and files by depth-first-traversal ("dft")
# - file name is bookmark simplified name, with ".url" as extension
# - inside the file are the bookmark details:
#     - the exact name ('tiltle') of the bookmark
#     - the last visited
#     - any other details
# - bookmark last_visited date is used to set modification of file name
#   so that tools like find can be used (for find ./ -name '*foo*' -mtime +100 )

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
#from see import see

# ------------------------------------------------------------------------- pass in indent string as a global
indntStr = "   "
# ------------------------------------------------------------------------- utility funs
def cleanupDt(f, sio):                  # remove spurious <DT>s which confuses traversal of HTML
    with open(f, 'r') as infile:
        for ln in infile:
            lnClean = re.sub(r'(\s+)<DT>', r'\1', ln);
            sio.write(lnClean)
    sio.seek(0)
    return sio

def cleanName(txt):                     # derive a reasonable file name from the url name ('title')
    if txt:
        cleanTxt = re.sub(r"[^a-zA-Z0-9_\ ]", "", txt).strip().replace(" ","_")
        if len(cleanTxt)>0: return cleanTxt
        else:               return "noName"
    else:
        return "noName"


def unixEpochToIsoDateTime(unixDateAsInt):
    # return (dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(unixIntDateAsStr))).strftime('%Y-%m-%dT%H:%M:%S')     print(unixDateAsInt)
    isoDt = dt.datetime.fromtimestamp(unixDateAsInt).strftime('%Y-%m-%dT%H:%M:%S')
    return isoDt

def closeUrlFile(fileDscrptr, urlMtime= None):
    urlFileName = fileDscrptr.name
    if fileDscrptr!=sys.stdout:
        fileDscrptr.close()
        print("Closed", urlFileName, urlMtime, unixEpochToIsoDateTime(str(urlMtime)))
        stat = os.stat(urlFileName)                                     # times must have two ints or floats (unix timestamps): (atime, mtime)
        os.utime(urlFileName, times=(stat.st_atime, urlMtime))


def makeBookmarkFile(wetRun, fldrPath, name, href, add_date=None, last_visited=None, last_modified=None, icon_uri=None, icon=None, last_charset=None):

    pageCleanName = cleanName(name)

    urlFileName   = fldrPath / Path(pageCleanName).with_suffix('.url')
    print(urlFileName)

    if wetRun: outFile = open(urlFileName, 'w')
    else:      outFile = sys.stdout

    if True:
        print(                  "TITLE:",         name,                                  file=outFile)
        print(                  "URI:",           href,                                  file=outFile)
        print(                  "DATE_ADDED:",    unixEpochToIsoDateTime(add_date),      file=outFile)
        if last_modified: print("DATE_MODIFIED:", unixEpochToIsoDateTime(last_modified), file=outFile)
        if last_modified: print("DATE_VISITED:",  unixEpochToIsoDateTime(last_visited),  file=outFile)
        if icon_uri:      print("ICON_URI:",      icon_uri,                              file=outFile)
        if icon:          print("ICON:",          icon,                                  file=outFile)
        if last_charset:  print("LAST_CHARSET:",  last_charset,                          file=outFile)
    return outFile

def makeBookmarkFolderDir(wetRun, fldrPath, text):
    fldrCleanName = cleanName(text)
    subFldrPath = fldrPath / fldrCleanName
    print(f"os.mkdir({subFldrPath})")
    if wetRun: os.makedirs(subFldrPath, exist_ok=True)
    return subFldrPath

# ------------------------------------------------------------------------- convert sqlite

def readSqliteBookmarks(dbFile):                                                # convert hierarchy implict in table back into explicit one
    conn = sqlite3.connect(dbFile)
    cur = conn.cursor()
    allDict = {}

    sqry = '''SELECT mb.id, mb.title, mb.type, mb.parent, mb.dateAdded, mp.url
                FROM moz_bookmarks mb
           LEFT JOIN moz_places mp ON mb.fk=mp.id
            ORDER BY mb.id ASC'''
    cur.execute(sqry)
    for (id, title, type, parent, dateAdded, url) in cur.fetchall():            # print(id, cleanName(title), parent)
        allDict[id] = {'id':        id,
                       'name':      title,
                       'url':       url,
                       'type':      type,
                       'parent':    parent,
                       'dateAdded': dateAdded}
    conn.close()

    allDict[0] = {'id':0, 'name':'root', 'children':[1]}                                                 # make tree by getting each parent to point to children
    for id in allDict:
        # print(id, [ (k, allDict[id][k]) for k in allDict[id] if k!='children' ] )
        if 'parent' in allDict[id]:
            prnt = allDict[id]['parent']
            if prnt in allDict:
                if 'children' not in allDict[prnt]: allDict[prnt]['children'] = []
                allDict[prnt]['children'] += [id] # print(prnt,allDict[prnt]['children'])
            else:
                print('Failed to find parent with id=', prnt, file=sys.stderr)
    allDict[1]['name'] = 'subroot'
    return allDict

def dftSqliteDict(fldrPath, node, allDict, depth=0, wetRun=False):                        # depth first traversal of dict derived from moz_bookmakrs sqlite table
    global indntStr
    if 'children' in node:
        subFldrPath = makeBookmarkFolderDir(wetRun, fldrPath, node['name'])
        for c in node['children']: dftSqliteDict(subFldrPath, allDict[c], allDict, depth+1, wetRun)
    else:
        #if 'name' in node and 'url' in node: print(indntStr*depth, node['name'], "-------", node['url'])
        #else:                                print("Partial record", node.keys(), file=sys.stderr)
        dateInSeconds = int(node['dateAdded']/1000000)
        outFile = makeBookmarkFile(wetRun, fldrPath, node['name'], node['url'], )
        closeUrlFile(outFile, dateinSeconds)

# Note: typical sqlite moz places structure
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
    with open(infile, 'r') as source:
        data = json.load(source)
    return data

def dftJson(fldrPath, jData, depth=0, wetRun=False):                            # depth first traversal of json
    global indntStr
    if jData['type']=='folder':
        print(indntStr*depth, jData['title'])
        subFldrPath = makeBookmarkFolderDir(wetRun, fldrPath, jData['name'])
        for c in jData['children']: dftJson(subFldrPath, c, depth+1)

    elif jData['type']=='folder':
        if 'uri' in jData:
            print(indntStr*depth, cleanName(jData['name']), "-------", jData['url'])
            outFile = makeBookmarkFileqy(wetRun, fldrPath, jData['name'], jData['url'], add_date=jData['date_added'])
            closeUrlFile(outFile, , int(jData['date_added']))
    else:
        print('unrecognized type', jData['type'], file=sys.stderr)
        print(jData, file=sys.stderr)

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

def dftHtml(fldrPath, el, depth=0, wetRun=False):                               # depth first traversal to create fh (=file hierarchy)

    if not wetRun: outFile=sys.stdout
    for e in el.getchildren():                                                  # typical keys: ['href', 'add_date', 'last_modified', 'icon_uri', 'icon', 'last_charset']
                                                                                # print("DEBUG", e.tag, e.text, e.get('href'), e.keys()) # debug
        if (e.tag=='dd') or (e.tag=='a' and e.text and (e.get('add_date') or e.get('last_visit')) and not e.get('href').startswith('find')): # and not e.get('href').startswith('ftp')
            if e.tag=='a':
                try:
                    print(cleanName(e.text))
                    outFile = makeBookmarkFile(wetRun, fldrPath, e.text, e.get('href'), e.get('add_date'), e.get('last_visit'), e.get('icon_uri'), e.get('icon'), e.get('last_charset'))
                except Exception as e:
                    print(e)
                    print("FAILED ON", e.text)
                    print(e.keys())
                    closeUrlFile(outFile)
                    sys.exit()
            elif e.tag=='dd' and e.text.strip():                                # sometimes (rarely, but it happens) a <DT> is followed by a descriptive <DD> that should also be written into the url file
                print(f"DESCRIPTION:{e.text.strip()}", file=outFile)            # so closing file (below) has to be delayed to after this check here

            if wetRun:
                closeUrlFile(outFile, int(e.get('add_date'), e.get('last_visit'))

        elif e.tag=='h3':                                                       # create a subfolder
            subFldrPath = makeBookmarkFolderDir(wetRun, fldrPath, e.text)

        else:
            print("OTHER", e.tag, file=sys.stderr,end='')                       # check stderr to see if anything got missed
            if e.text: print(" TEXT=", e.text, file=sys.stderr,end='')
            for k in e.keys(): print(" KEY=", k, e.get(k), file=sys.stderr, end='')
            print('', file=sys.stderr)

        dftHtml(subFldrPath, e, depth+1, wetRun=wetRun)


def dftPrint(el, depth=0):                                                      # depth first traversal - make file hierarchy
    global indntStr
    for e in el.getchildren():                                                  # ['href', 'add_date', 'last_modified', 'icon_uri', 'icon', 'last_charset']
        if   e.tag=='a':  print(indntStr*depth, cleanName(e.text), e.get('href')) # print(indent*depth, e.tag, e.get('href'), e.text)
        elif e.tag=='h3': print(indntStr*depth, ' ', cleanName(e.text))           # print(indent*depth, e.tag, e.text)
        elif e.tag=='dd': print("DD", e.text, file=sys.stderr)
        elif e.tag not in ['dl','p','dt']: print("OTHER",e.tag, file=sys.stderr)
        dftPrint(e, depth=depth+1)

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
            dftHtml(rootWriteFolder, pTreeObj, wetRun=wetRun)


