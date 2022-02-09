#!/usr/bin/env python
#
# TBD
# take out stdoutVerbose
# wetRun => !dryRun
# refine org-mode format?
#
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
from glob import glob
import subprocess
import json
import sqlite3
import unicodedata as ud
import datetime as dt
from io import StringIO
from lxml import etree

from pathlib import Path
from see import see

# ------------------------------------------------------------------------- GLOBALS
indntStr = "   "       # indentation string when writing to stdout in dry-run mode

# ------------------------------------------------------------------------- utility funs
def cleanupDt(f, sio):
    '''try to normalise the structure of the HTML by adding closing </tags> to match opening ones
      or remove spurious tags entirely. So that lxml has a better chance of a sane parse'''
    with open(f, 'r') as infile:
        for ln in infile:
            lnClean = re.sub(r'(\s+)<DT>', r'\1', ln);
            if lnClean.startswith('<DD>'): lnClean+='</DD>'  # close unclosed <DD>s
            lnClean = lnClean.replace('<p>','<p></p>')       # close unclosed <p>s
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


def makeBookmarkFile(depth, wetRun, fldrPath, name, href, add_date=None, last_visited=None, last_modified=None, icon_uri=None, icon=None, last_charset=None, date_scaling=1):
    '''create a file named like the title or name associated with url
    add properties of the url into the file
    date_scaling should be either 1 or 1000000 depending on whether the epoch integer date time is in seconds or in microseconds
    '''

    pageCleanName = cleanName(name)
    urlFileName   = fldrPath / Path(pageCleanName if pageCleanName!="" else "notitle").with_suffix('.url')
    #print("*"*(depth+1), name)
    print("+ ", name)

    if wetRun: outFile = open(urlFileName, 'w')   # file is not close in this function as it may need more writing to (in the html case)
    else:      outFile = sys.stdout

    if add_date: addDate = int(add_date)/date_scaling
    else:
        print("WARNING: No Date for", urlFileName, file=sys.stderr)
        addDate =0

    if outFile!=sys.stdout: prefix, pstfix = "",   ":"     # vanilla key-value notation
    else:                   prefix, pstfix = " - ", " ::"   # format of org-mode named list entries

    print(                  f"{prefix}TITLE{pstfix}",          name,                                                    file=outFile)
    print(                  f"{prefix}URI{pstfix}",            href,                                                    file=outFile)
    print(                  f"{prefix}DATE_ADDED{pstfix}",     unixEpochToIsoDateTime(addDate),                         file=outFile)
    if last_modified: print(f"{prefix}DATE_MODIFIED{pstfix}",  unixEpochToIsoDateTime(int(last_modified)/date_scaling), file=outFile)
    if last_visited:  print(f"{prefix}DATE_VISITED{pstfix}",   unixEpochToIsoDateTime(int(last_visited)/date_scaling),  file=outFile)
    if icon_uri:      print(f"{prefix}ICON_URI{pstfix}",       icon_uri,                                                file=outFile)
    if icon:          print(f"{prefix}ICON{pstfix}",           icon,                                                    file=outFile)
    if last_charset:  print(f"{prefix}LAST_CHARSET{pstfix}",   last_charset,                                            file=outFile)
    print(                   "",                                                                                        file=outFile) # add terminating newline
    return outFile, addDate

def makeBookmarkFolderDir(depth, wetRun, fldrPath, text):
    '''use mkdir to create folder path'''
    clnName = cleanName(text)
    print("*"*depth, clnName)
    subFldrPath = fldrPath / clnName
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
        subFldrPath = makeBookmarkFolderDir(depth, wetRun, fldrPath, node['name'])
        for c in node['children']: dftSqliteDict(subFldrPath, allDict[c], allDict, depth+1, wetRun)
    else:
        outFile, fileDate = makeBookmarkFile(depth, wetRun, fldrPath, node['name'], node['url'], add_date=node['dateAdded'], date_scaling=1000000)
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
        subFldrPath = makeBookmarkFolderDir(depth, wetRun, fldrPath, name)
        for c in jData['children']: dftJson(subFldrPath, c, depth+1)

    elif jData['type']=='text/x-moz-place' and jData['title'] not in ('Recently Bookmarked','Recent Tags', 'Most Visited'):
        if 'dateAdded' in jData:
            url = jData['url' if 'url' in jData else 'uri']                    # print(indntStr*depth, cleanName(name), "-------", url)
            outFile, fileDate = makeBookmarkFile(depth, wetRun, fldrPath, name, url, add_date=jData['dateAdded'], last_modified=jData['lastModified'], date_scaling=1000000)
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

def compareHtmlFiles(lim):
    allFiles = glob("/home/kleyn/projects/bookmarksToTree/archiveArea/*.html")[:lim]
    for ai,fa in enumerate(allFiles):
        for bi in range(ai+1, len(allFiles)):
            fb = allFiles[bi]
            os.system(f"sed 's/^[ \t]*//g' {fa} | sort -u > /tmp/t1")
            os.system(f"sed 's/^[ \t]*//g' {fb} | sort -u > /tmp/t2")
            result = int(subprocess.getoutput(f'diff -iwB /tmp/t1 /tmp/t2 | wc -l'))
            if result<100:
                print(f"{result:5d}", fa, fb)

def dftHtml(fldrPath, el, depth=0, wetRun=False):                                  # depth first traversal to create fh (=file hierarchy)
    global indntStr

    if not wetRun: outFile = sys.stdout

    subFldr  = ''
    numChlds = len(el)
    for ei,e in enumerate(el):                                                     # typical keys: ['href', 'add_date', 'last_modified', 'icon_uri', 'icon', 'last_charset']         # print(" "*4*depth, "DEBUG", e.tag, e.text, e.keys(), f'chlds={len(e)}', fldrPath) # debug

        if e.tag=='a' and e.text:                                                  # print(indntStr*depth, fldrPath / cleanName(e.text)) #, e.get('href') print(indent*depth, e.tag, e.get('href'), e.text)

            try:
                outFile, fileDate = makeBookmarkFile(depth, wetRun, fldrPath, e.text, e.get('href'), add_date=e.get('add_date'), last_visited=e.get('last_visit'), icon_uri=e.get('icon_uri'), icon=e.get('icon'), last_charset=e.get('last_charset'))
            except Exception as e:
                print(e)
                print(e.keys())
                print("FAILED ON", e.text)
                closeUrlFile(outFile)
                sys.exit()
            if ei+1<numChlds-1 and el[ei+1].tag=='dd':                             # lookahead in case there is a further DESCRIPTON of the anchor, right after it
                if outFile!=sys.stdout:
                    print('DESCRIPTION:', el[ei+1].text.strip(), file=outFile)     # sometimes (rarely, but it happens) a <DT> is followed by a descriptive <DD> that should also be written into the url file
            if wetRun: closeUrlFile(outFile, fileDate)

        elif e.tag=='h3':

            subFldr = makeBookmarkFolderDir(depth, wetRun, fldrPath, e.text).parts[-1]

        elif e.tag in ['dl','dt','p','head','body']: #,'dd']:                      # keep recursing down

            dftHtml(Path(fldrPath) / Path(subFldr), e, depth+1, wetRun=wetRun)     # dftPrint(e, path=path / Path(subFldr), depth=depth+1)


def dftPrint(el, path='', depth=0):                                                # depth first traversal - make file hierarchy
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


# Note: typical html structure
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
    elif False:
        compareHtmlFiles(int(sys.argv[1]))
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
            #dftPrint(pTreeObj.getroot(), path=Path('./foo/'))


