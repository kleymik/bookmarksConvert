#!/usr/bin/env python
import sys
import re
import os
from io import StringIO
from lxml import etree
from see import see
from datetime import datetime as dt
from pathlib import Path

def cleanupDt(f, sio):
    with open(f, 'r') as infile:
        for ln in infile:
            lnClean = re.sub(r'(\s+)<DT>', r'\1', ln);        # print("BBBBBB",len(ln),ln[:200]); print("AAAAAA",len(lnClean),lnClean[:200])
            sio.write(lnClean)
    sio.seek(0)
    return sio

def unixEpochToIsoDateTime(unixIntDateAsStr):
    return dt.fromtimestamp(int(unixIntDateAsStr)).strftime('%Y-%m-%dT%H:%M:%S')

def dftFh(el, fldrPath="/tmp/bmc", wetRun=False):             # depth first traversal create fh (=file hierarchy)

    if not wetRun: outFile=sys.stdout
    for e in el.getchildren():                                # ['href', 'add_date', 'last_modified', 'icon_uri', 'icon', 'last_charset']

        # print("DEBUG", e.tag, e.text, e.get('href'), e.keys()) # debug

        if (e.tag=='dd') or (e.tag=='a' and e.text and (e.get('add_date') or e.get('last_visit')) and not e.get('href').startswith('find')): # and not e.get('href').startswith('ftp')
            if e.tag=='a':
                try:
                    pageCleanName = re.sub(r"[^a-zA-Z0-9_\ ]", "", e.text).strip().replace(" ","_")[:200]   # limit file name size
                    urlFileName = fldrPath+"/"+pageCleanName+'.url'
                    urlMtime = int(e.get('add_date') or e.get('last_visit'))
                    if wetRun: outFile = open(urlFileName, 'w')
                    print(pageCleanName)
                    if False:
                        print(                          "TITLE:",          e.text,                                         file=outFile)
                        print(                          "URI:",            e.get('href'),                                  file=outFile)
                        print(                          "DATE_ADDED:",     unixEpochToIsoDateTime(e.get('add_date')),      file=outFile)
                        if e.get('last_modified'): print("DATE_MODIFIED:", unixEpochToIsoDateTime(e.get('last_modified')), file=outFile)
                        if e.get('icon_uri'):      print("ICON_URI:",      e.get('icon_uri'),                              file=outFile)
                        if e.get('icon'):          print("ICON:",          e.get('icon'),                                  file=outFile)
                        if e.get('last_charset'):  print("LAST_CHARSET:",  e.get('last_charset'),                          file=outFile)

                except Exception as e:
                    print(e)
                    print("FAILED ON", e.text)
                    print(e.keys())
                    if wetRun: outFile.close()
                    sys.exit()
            elif e.tag=='dd' and e.text:                      # sometimes (rarely but it happens, at <DT> is followed by adecriptive <DD> that should also be written into the file
                print("DESCRIPTION:", e.text, file=outFile)

            #print("DEBUG:Closing")
            if wetRun:
                print("Closing", urlFileName, urlMtime, unixEpochToIsoDateTime(str(urlMtime)))
                outFile.close()
                stat = os.stat(urlFileName)                  # times must have two ints or floats (unix timestamps): (atime, mtime)
                os.utime(urlFileName, times=(stat.st_atime, urlMtime))

        elif e.tag=='h3':                                   # create a subfolder

            fldrCleanName = re.sub(r"[^a-zA-Z0-9_\ ]", "", e.text).strip().replace(" ","_")
            print(fldrCleanName)
            fldrPath += '/'+fldrCleanName
            print(f"os.mkdir({fldrPath})")
            if wetRun:
                os.makedirs(fldrPath,exist_ok=True)

        #elif e.tag not in ['dl','p','dt']:

            # print("OTHER-TAG ", e.tag, e.text, e.keys(), file=sys.stderr)

        else:

            print("OTHER", e.tag, e.text, e.keys(), file=sys.stderr)
            for k in e.keys(): print("TAG", k, e.get(k), file=sys.stderr)

        dftFh(e, fldrPath=fldrPath, wetRun=wetRun)


def dftPrint(el, depth=0):                                    # depth first traversal - make file hierarchy
    indent = ["   ","*"][0]
    for e in el.getchildren():                                # ['href', 'add_date', 'last_modified', 'icon_uri', 'icon', 'last_charset']
        if e.tag=='a':
            pageCleanName = re.sub(r"[^a-zA-Z0-9_\ ]", "", e.text).strip().replace(" ","_")
            print(indent*depth, pageCleanName, e.get('href')) # print(indent*depth, e.tag, e.get('href'), e.text)
        elif e.tag=='h3':
            fldrCleanName = re.sub(r"[^a-zA-Z0-9_\ ]", "", e.text).strip().replace(" ","_")
            print(indent*depth, ' ', fldrCleanName)           # print(indent*depth, e.tag, e.text)
        elif e.tag=='dd':
            print("DD", e.text, file=sys.stderr)
        elif e.tag not in ['dl','p','dt']:
            print("OTHER",e.tag, file=sys.stderr)
        dftPrint(e, depth=depth+1)


print("len(sys.argv)=", len(sys.argv), file=sys.stderr)

if len(sys.argv)<2:
    print("Usage: bmTraverse.py bookmarks.html [folderWriteArea]")
else:
    testArea    = "/home/kleyn/projects/bookmarkMerge/testArea"
    wetRun      = False
    inFile      = Path(sys.argv[1])

    sio = cleanupDt(inFile, StringIO(''))             # parse cleaned-up file using lxml eTree
    tr = etree.parse(sio, etree.HTMLParser())
    sio.close()

    if len(sys.argv)==3 and sys.argv[2]=='W': wetRun = True
    if wetRun: os.makedirs(testArea+'/'+inFile.stem, exist_ok=True)
    dftFh(tr.getroot(), fldrPath=testArea+"/"+inFile.stem, wetRun=wetRun)

#else:        dftPrint(tr.getroot())


#if __name__ == "__main__":
# a https://wiki.python.org/jython/
# {'href': 'https://wiki.python.org/jython/',
# 'add_date': '1636306593',
# 'icon': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACN0lEQVQ4jWWTP2gUQRSHv907zSVRxIBiIjaCTRobKwuLQLARosKBtqKNoqnTCIKFIEI6IxY2wSaFGJSIIioGMaeetkbEGKNJxJPjLrszO/Nm1uJ2zSYZeAzMfL/3fvPnBWwaI7dePrCJOead6RObIMYgidJG67u12xfHAA24nA83J3BOTj4eG+5zYnHW4sXivauAvwwcACpFfmsCazl+bRondj2szbf7gZ4iXwYYGZ+96q09aIwKjFaTRrXKouOSM4Zwe1c1TX3OdwGlDQlOj7957pwd8k4IvCcgpVTe3kGDEk5skSddrC57G2lJoptdg69uhD51Qx2rZqPtLPIhuj0DWCQmdKpSTtUlYKCcg74g8oVzp6nXLole1O+N3flTHx5GFEhM6FUf0F/eILaWZK0583Nu+v5S/VkTECAFzOLr4cHdvTKKU+BikBiguywm0V5sxYlFtRpTtYkrk+2F0TM93YdOhU5V/sMSkVdHFF60BoJQRBZy679qTx9GP0Yv7Oh1Z0NfFMcFcQxOE8fpO8CEXkcTYox2YlmqP2r2VNyJdUFBVBADfJxPngDtIPtZ/cB+IEmXz9Vy+Pdqcyr0UYpTYBU4BcCX7/bT0fONt8C3MmCAFaAFpMVqe3dJFXHgLIglOLIyBKwBKuMbIeCzhQbw19tYd6wW4vA8Pk119iLLwNdsjrf0QtRqVa2OPngT6dyJnRv4PPteXwcsEGcFLZAGmxNkd7IH2AfsBLZlLttZ1VU6LQ3AP75vsPXueofxAAAAAElFTkSuQmCC'}

# import string
#"".join(filter(lambda char: char in string.printable, s))
#bad_chars = [';', ':', '!', "*"]

