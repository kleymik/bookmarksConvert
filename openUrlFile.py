import os
import sys
import urllib.parse

# 20231128_09:44:11 from GPT

def open_url_file(file_path):
    with open(file_path, 'r') as file:
        # Read the first line of the file
        first_line = file.readline()

        # Check if it contains 'URL=' (for .url files)
        if first_line.startswith('URL='):
            url = first_line[4:].strip()

        # Check if it contains 'URL=' (for .desktop files)
        elif first_line.startswith('Exec=xdg-open '):
            url = first_line[15:].strip()

        # Check if it contains 'URL=' (for .webloc files)
        elif first_line.startswith('<?xml version'):
            for line in file:
                if '<string>' in line and '</string>' in line:
                    url = line.strip().replace('<string>', '').replace('</string>', '')
                    break

        else:
            print(f"Unsupported file format: {file_path}")
            return

    # Unquote the URL in case it's percent-encoded
    url = urllib.parse.unquote(url)

    # Open the URL using xdg-open
    os.system(f"xdg-open '{url}'")

if __name__ == "__main__":
    # Check if a file path is provided as a command-line argument
    if len(sys.argv) != 2:
        print("Usage: python open_url_file.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    # Invoke the function to open the URL from the file
    open_url_file(file_path)


# .lnk (Windows Shortcut): On Windows systems, .lnk files are used as shortcuts and may contain URLs. These files are commonly created when a user creates a shortcut to a website on their desktop.

# .website: Some Windows systems use .website files to store links to websites. These files are essentially XML files containing information about the associated URL.

# .desktop (Generic): While .desktop files are commonly associated with Linux desktop environments, they can also be used on other platforms. These files are often used to create shortcuts or launchers, and they may contain URLs.

# .uri or .url: Some systems may use .uri as an alternative extension for files containing URLs. Additionally, files with the extension .url may be used on various platforms.

# .htm or .html (HTML Files): Simple HTML files can be used to store a URL. Users might create small HTML files with a link to a website.

# .link: The .link extension is sometimes used to indicate files containing links or shortcuts.

