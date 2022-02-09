#!/usr/bin/env python
import sys
import re
import os
from io import StringIO
from lxml import etree
from see import see


def cleanupDt(f, sio):
    with open(f, 'r') as infile:
        for ln in infile:
            lnClean = re.sub(r'(\s+)<DT>', r'\1', ln);                          # print("BBBBBB",len(ln),ln[:200]); print("AAAAAA",len(lnClean),lnClean[:200])
            sio.write(lnClean)
    sio.seek(0)
    return sio

def dftFh(el, fldrPath="/tmp/bmc"):                                                    # depth first traversal
    indent = [" ","*"][0]
    depth = (len(fldrPath) - len("/home/kleyn/projects/bookmarkMerge/testArea"))//2
    for e in el.getchildren():                                                # ['href', 'add_date', 'last_modified', 'icon_uri', 'icon', 'last_charset']
        # with open(fldPth+"/"+pageCleanName+'.url', 'w') as foo:
        if e.tag=='a' and e.text:
            try:
                pageCleanName = re.sub(r"[^a-zA-Z0-9_\ ]", "", e.text).strip().replace(" ","_")
                if True:
                    print(indent*depth, pageCleanName)   # print(indent*depth, e.tag, e.get('href'), e.text)
                    #print(indent*depth, "  TITLE::", e.text)
                    #print(indent*depth, "  URI:",    e.get('href'))
                    #print(indent*depth, "  DATE:",   e.get('add_date'))
                    #print(indent*depth, "  DATE:",   e.get('last_modified'))
                    #print(indent*depth, "  ICON_URI:", e.get('icon_uri'))
                    #print(indent*depth, "  ICON:", e.get('icon'))
                    #print(indent*depth, "  DICT:",   e.keys())
                    # if e.get('last_charset'): print(indent*depth, "  LAST_CHARSET:",   e.get('last_charset'))
            except:
                print("FAILED ON", e.text)
                sys.exit()
        elif e.tag=='dd':                        #needs to happen beforr mkdir
            if e.text:
                # print(indent*depth, "DD  DESCRIPTION:",   e.text)
                pass
        else:
            if e.tag=='h3':
                fldrCleanName = re.sub(r"[^a-zA-Z0-9_\ ]", "", e.text).strip().replace(" ","_")
                print(indent*depth, '   ', fldrCleanName)
                # fldrPath += '/'+fldrCleanName
                fldrPath += '/d'
                print(f"os.mkdir({fldrPath})")
            elif e.tag not in ['dl','p','dt']:
                print("OTHER", e.tag, file=sys.stderr)


        dftFh(e, fldrPath=fldrPath)


def dftPrint(el, depth=0):                                                       # depth first traversal - make file hierarchy
    indent = ["   ","*"][0]
    for e in el.getchildren():                                                # ['href', 'add_date', 'last_modified', 'icon_uri', 'icon', 'last_charset']
        if   e.tag=='a':
            print(indent*depth, e.text, e.get('href'))                        # print(indent*depth, e.tag, e.get('href'), e.text)
        elif e.tag=='h3':
            print(indent*depth, ' ', e.text)                    # print(indent*depth, e.tag, e.text)
        elif e.tag=='dd':
            print("DD", e.text, file=sys.stderr)
        elif e.tag not in ['dl','p','dt']:
            print("OTHER",e.tag, file=sys.stderr)
        dftPrint(e, depth=depth+1)


print("len(sys.argv)=", len(sys.argv), file=sys.stderr)
testArea = "/home/kleyn/projects/bookmarkMerge/testArea"
if len(sys.argv)<2:
    print("Usage: bmTraverse.py bookmarks.html [folderWriteArea]")
else:
    sio = cleanupDt(sys.argv[1], StringIO(''))
    tr = etree.parse(sio, etree.HTMLParser())
    sio.close()
    if len(sys.argv)==3:
        folderWriteArea=sys.argv[2]
        # os.mkdir(testArea+'/'+folderWriteArea)
        dftFh(tr.getroot(), fldrPath=testArea+"/"+folderWriteArea)
    else:
        dftPrint(tr.getroot())


#    soup = BeautifulSoup(htmlFd)
#    print(soup.prettify())
#if __name__ == "__main__":
# a https://wiki.python.org/jython/
# {'href': 'https://wiki.python.org/jython/',
# 'add_date': '1636306593',
# 'icon': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACN0lEQVQ4jWWTP2gUQRSHv907zSVRxIBiIjaCTRobKwuLQLARosKBtqKNoqnTCIKFIEI6IxY2wSaFGJSIIioGMaeetkbEGKNJxJPjLrszO/Nm1uJ2zSYZeAzMfL/3fvPnBWwaI7dePrCJOead6RObIMYgidJG67u12xfHAA24nA83J3BOTj4eG+5zYnHW4sXivauAvwwcACpFfmsCazl+bRondj2szbf7gZ4iXwYYGZ+96q09aIwKjFaTRrXKouOSM4Zwe1c1TX3OdwGlDQlOj7957pwd8k4IvCcgpVTe3kGDEk5skSddrC57G2lJoptdg69uhD51Qx2rZqPtLPIhuj0DWCQmdKpSTtUlYKCcg74g8oVzp6nXLole1O+N3flTHx5GFEhM6FUf0F/eILaWZK0583Nu+v5S/VkTECAFzOLr4cHdvTKKU+BikBiguywm0V5sxYlFtRpTtYkrk+2F0TM93YdOhU5V/sMSkVdHFF60BoJQRBZy679qTx9GP0Yv7Oh1Z0NfFMcFcQxOE8fpO8CEXkcTYox2YlmqP2r2VNyJdUFBVBADfJxPngDtIPtZ/cB+IEmXz9Vy+Pdqcyr0UYpTYBU4BcCX7/bT0fONt8C3MmCAFaAFpMVqe3dJFXHgLIglOLIyBKwBKuMbIeCzhQbw19tYd6wW4vA8Pk119iLLwNdsjrf0QtRqVa2OPngT6dyJnRv4PPteXwcsEGcFLZAGmxNkd7IH2AfsBLZlLttZ1VU6LQ3AP75vsPXueofxAAAAAElFTkSuQmCC'}

# import string
#"".join(filter(lambda char: char in string.printable, s))
#bad_chars = [';', ':', '!', "*"]

