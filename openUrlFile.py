#!/usr/bin/python3
# open a .url or desktop url file

import plistlib, sys, os
#from PyQt5.QtCore import QCoreApplication
#from PyKDE5.kdecore import KToolInvocation


print("ARGS=",len(sys.argv), sys.argv)

fl = sys.argv[1]
fd = open(fl,"rt")

for l in fd.readlines():
    print(l,end='')
    if l.startswith("URL"):
        print("Opening URL")
        url = "https://www.googe.com"
        os.system(f"xdg-open {url}")
        pass

# print(f"Found URL: {url}")
# sys.exec(f"xdg-open {extractedUrl")

#   kde-open
#   xdg-open



# .desktop gome
# [Desktop Entry]
# Encoding=UTF-8
# Name=Link to NETGEAR Router
# Type=Link
# URL=http://192.168.0.1/start.htm
# Icon=text-html


# .desktop
# https://wiki.archlinux.org/title/desktop_entries
#
# at (windows) .url file:
# [Desktop Entry]
# Icon=text-html
# Type=Link
# URL[$e]=https://superuser.com/questions/27490/create-a-desktop-shortcut-for-a-group-of-bookmarked-tabs-in-firefox
#
#


# https://wiki.archlinux.org/title/desktop_entries
#
# at (windows) .url file:
# [Desktop Entry]
# Icon=text-html
# Type=Link
# URL[$e]=https://superuser.com/questions/27490/create-a-desktop-shortcut-for-a-group-of-bookmarked-tabs-in-firefox
#

#  [Desktop Entry]
#  The type as listed above
#  Type=Application
#  # The version of the desktop entry specification to which this file complies
#  Version=1.0
#  # The name of the application
#  Name=jMemorize
#  # A comment which can/will be used as a tooltip
#  Comment=Flash card based learning tool
#  # The path to the folder in which the executable is run
#  Path=/opt/jmemorise
#  The executable of the application, possibly with arguments.
#  Exec=jmemorize
#  # The name of the icon that will be used to display this entry
#  Icon=jmemorize
#  # Describes whether this application needs to be run in a terminal or not
#  Terminal=false
#  # Describes the categories in which this entry should be shown
#  Categories=Education;Languages;Java;
