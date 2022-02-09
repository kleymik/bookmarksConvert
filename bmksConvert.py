#!/usr/bin/env python
#
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
from io import StringIO
from lxml import etree
from datetime import datetime as dt
from pathlib import Path
from see import see

# ------------------------------------------------------------------------- utility funs
def cleanupDt(f, sio):                  # remove spurious <DT>s which confuses traversal of HTML
    with open(f, 'r') as infile:
        for ln in infile:
            lnClean = re.sub(r'(\s+)<DT>', r'\1', ln);
            sio.write(lnClean)
    sio.seek(0)
    return sio

def cleanName(txt):                     # derive a reasonable file name from the url name ('title')
    return re.sub(r"[^a-zA-Z0-9_\ ]", "", txt).strip().replace(" ","_")

def unixEpochToIsoDateTime(unixIntDateAsStr):
    return dt.fromtimestamp(int(unixIntDateAsStr)).strftime('%Y-%m-%dT%H:%M:%S')

def makeBookmarkFile(wetRun=False, fldrPath, name, href, add_date=None, last_visit=None, icon_uri=None, icon=None, last_charset=None):
    pageCleanName = cleanName()
    urlFileName   = fldrPath / pageCleanName+'.url'
    if wetRun:
        outFile       = open(urlFileName, 'w')
    else:
        outFile = sys.stdout
        print(urlFileName, file=outFile)
    print(                  "TITLE:",         name,                                  file=outFile)
    print(                  "URI:",           href,                                  file=outFile)
    print(                  "DATE_ADDED:",    unixEpochToIsoDateTime(add_date),      file=outFile)
    if last_modified: print("DATE_MODIFIED:", unixEpochToIsoDateTime(last_modified), file=outFile)
    if icon_uri:      print("ICON_URI:",      icon_uri,                              file=outFile)
    if icon:          print("ICON:",          icon,                                  file=outFile)
    if last_charset:  print("LAST_CHARSET:",  last_charset,                          file=outFile)
    return outFile

def makeBookmarkFolderDir(fldrPath, text, wetRun=False):
    fldrCleanName = cleanName(text)
    print(fldrCleanName)
    subFldrPath = fldrPath / fldrCleanName
    print(f"os.mkdir({subFldrPath})")
    if wetRun: os.makedirs(subFldrPath, exist_ok=True)
    return subFldrPath

# ------------------------------------------------------------------------- convert sqlite
def readSqliteBookmarks(dbFile):                                                # convert hierarchy implict in table back into explicit one
    conn = sqlite3.connect(dbFile)
    cur = conn.cursor()
    allDict = {}
    for (id, title, type, parent, dateAdded, url) in cur.execute(''''SELECT mb.id, mb.title, mb.type, mb.parent, mb.dateAdded, mp.url
                                                                       FROM moz_bookmarks mb
                                                                            JOIN moz_places mp ON mb.fk=mp.id
                                                                   ORDER BY mb.parent ASC'''):
        allDict[i] = {'id':        i,
                      'name':      title,
                      'url':       url,
                      'type':      type,
                      'parent':    parent,
                      'children':  [],
                      'dateAdded': dateAdded}
    conn.close()

    allDict[1]['title'] ='root'                                                 # make tree by getting each parent to point to children
    for id in allDict:
        prnt = allDict[id]['parent']
        if prnt in allDict: allDict[prnt]['children'] += [id]
        else:               print('Fail to find parent with id=', prnt)
    return allDict

def dftSqliteDict(fldrPath, dct, depth=0, wetRun=False):                        # depth first traversal of dict derived from moz_bookmakrs sqlite table
    if 'children' in dct:
        print("---"*depth, dct['name'])
        subFldrPath = makeBookmarkFolderDir(wetRun, fldrPath, dct['name'])
        for c in dct['children']: dftSqliteDict(subFldrPath, c, depth+1)
    else:
        print("--"*depth, dct['name'], "-------", dct['url'])
        if wetRun:
            outFile = makeBookmarkFile(wetRun, fldrPath, dct['name'], dct['url'], dct['dateAdded'])
            if outFile!=sys.stdout: outFile.close()

# ------------------------------------------------------------------------- convert json
def readJsonBookmarks(infile):
    print("FILE", infile)
    with open(infile, 'r') as source:
        data = json.load(source)
    return data

def dftJson(fldrPath, jData, depth=0, wetRun=False):                            # depth first traversal of json
    if 'children' in jData:
        print("---"*depth, jData['title'])
        subFldrPath = makeBookmarkFolderDir(fldrPath, jData['title'], wetRun)
        for c in jData['children']: dftJson(subFldrPath, c, depth+1)
    else:
        if 'uri' in jData:
            print("---"*depth, cleanName(jData['title']), "-------", jData['uri'])
            if wetRun:
                outFile = makeBookmarkFile(fldrPath, jData['title'], jData['uri'], add_date=None, last_visit=None, icon_uri=None, icon=None, last_charset=None)
                outFile.close()

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
                    if wetRun: outFile = makeBookmarkFile(fldrPath, e.text, e.get('add_date'), e.get('last_visit'), e.get('href'), e.get('icon_uri'), e.get('icon'),e.get('last_charset'))
                except Exception as e:
                    print(e)
                    print("FAILED ON", e.text)
                    print(e.keys())
                    if wetRun: outFile.close()
                    sys.exit()
            elif e.tag=='dd' and e.text.strip():                                # sometimes (rarely, but it happens) a <DT> is followed by a descriptive <DD> that should also be written into the url file
                print(f"DESCRIPTION:{e.text.strip()}", file=outFile)            # so closing file (below) has to be delayed to after this check here

            if wetRun:
                urlMtime = int(e.get('add_date'), e.get('last_visit'))
                print("Closing", urlFileName, urlMtime, unixEpochToIsoDateTime(str(urlMtime)))
                outFile.close()
                stat = os.stat(urlFileName)                                     # times must have two ints or floats (unix timestamps): (atime, mtime)
                os.utime(urlFileName, times=(stat.st_atime, urlMtime))

        elif e.tag=='h3':                                                       # create a subfolder
            subFldrPath = makeBookmarkFolderDir(fldrPath, e.text, wetRun)

        else:
            print("OTHER", e.tag, file=sys.stderr,end='')                       # check stderr to see if anything got missed
            if e.text: print(" TEXT=", e.text, file=sys.stderr,end='')
            for k in e.keys(): print(" KEY=", k, e.get(k), file=sys.stderr, end='')
            print('', file=sys.stderr)

        dftHtml(subFldrPath, e, depth+1, wetRun=wetRun)


def dftPrint(el, depth=0):                                                      # depth first traversal - make file hierarchy
    indent = ["   ","*"][0]
    for e in el.getchildren():                                                  # ['href', 'add_date', 'last_modified', 'icon_uri', 'icon', 'last_charset']
        if   e.tag=='a':  print(indent*depth, cleanName(e.text), e.get('href')) # print(indent*depth, e.tag, e.get('href'), e.text)
        elif e.tag=='h3': print(indent*depth, ' ', cleanName(e.text))           # print(indent*depth, e.tag, e.text)
        elif e.tag=='dd': print("DD", e.text, file=sys.stderr)
        elif e.tag not in ['dl','p','dt']: print("OTHER",e.tag, file=sys.stderr)
        dftPrint(e, depth=depth+1)

if __name__ == "__main__":

    if len(sys.argv)<2:
        print("Usage: bmcTraverse.py bookmarks.[html|json|slqlite] [rootfolderWriteArea] [W]")
    else:
        inFile          = Path(sys.argv[1])
        rootWriteFolder = Path(sys.argv[2])

        wetRun = False                                                     # i.e. "dry run" is by default true
        if len(sys.argv)==4 and sys.argv[3]=='W': wetRun = True            # only create (many!) files and folders if 3rd arg="W"

        if wetRun: os.makedirs(rootWriteFolder, exist_ok=True)

        if   inFile.suffix=='.sqlite':
            pTreeDict = readSqliteBookmarks(inFile)
            dftSqliteDict(rootWriteFolder, pTreeDict, wetRun=wetRun)
        elif inFile.suffix=='.json':
            pTreeObj = readJsonBookmarks(inFile)
            dftJson(rootWriteFolder, pTreeObj, wetRun=wetRun)
        elif inFile.suffix=='.html':
            pTreeObj = readHtmlBookmarks(inFile)
            dftHtml(rootWriteFolder, pTreeObj, wetRun=wetRun)


