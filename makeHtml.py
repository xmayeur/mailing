#!/usr/bin/env python
# coding: utf-8

import os
import urllib.parse
import argparse
from bs4 import BeautifulSoup


def file_to_base64(filepath):
    """
    Returns the content of a file as a Base64 encoded string.
    :param filepath: Path to the file.
    :type filepath: str
    :return: The file content, Base64 encoded.
    :rtype: str
    """
    import base64

    with open(filepath, "rb") as f:
        encoded_str = base64.b64encode(f.read())
    return encoded_str.decode("utf-8")


def guess_type(filepath):
    """
    Return the mimetype of a file, given its path.
    This is a wrapper around two alternative methods - Unix 'file'-style
    magic which guesses the type based on file content (if available),
    and simple guessing based on the file extension (eg .jpg).
    :param filepath: Path to the file.
    :type filepath: str
    :return: Mimetype string.
    :rtype: str
    """
    try:
        import magic  # python-magic

        return magic.from_file(filepath, mime=True)
    except ImportError:
        import mimetypes

        return mimetypes.guess_type(filepath)[0]


def make_html_images_inline(in_filepath, out_filepath=None) -> str:
    """
    Takes an HTML file and writes a new version with inline Base64 encoded
    images.
    :param in_filepath: Input file path (HTML)
    :type in_filepath: str
    :param out_filepath: Output file path (HTML) - if None, return the data
    :type out_filepath: str
    :returns the html data with inline images
    """
    basepath = os.path.split(in_filepath.rstrip(os.path.sep))[0]
    soup = BeautifulSoup(open(in_filepath, "r"), "html.parser")
    for img in soup.find_all("img"):
        img_path = urllib.parse.unquote(os.path.join(basepath, img.attrs["src"]))
        mimetype = guess_type(img_path)
        if ";base64," not in img_path:
            img.attrs["src"] = "data:%s;base64,%s" % (
                mimetype,
                file_to_base64(img_path),
            )
        else:
            # TODO Change by a regex to ensure the string start with data:.*?;base64...
            img.attrs["src"] = img_path[6:]

    if out_filepath is not None:
        with open(out_filepath, "w") as of:
            of.write(str(soup))
    return str(soup)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", help="HTML file to ocnvert", required=True)
    parser.add_argument("-o", "--output", help="Output file", required=True)
    args = parser.parse_args()
    make_html_images_inline(args.input, args.output)
