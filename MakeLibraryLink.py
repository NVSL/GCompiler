#!/usr/bin/env python

import argparse
import os
from contextlib import contextmanager
from lxml import etree

__author__ = 'WeiPingLiao'

@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tool for making symbolic link for library of a component")
    parser.add_argument("-s", dest="sketch_lib_path", required=True, help="The path to libraries folder in SketchBook for Arduino IDE")
    parser.add_argument("-g", dest="gcom", required=True, nargs="+", help="The path to the gcom files")
    args = parser.parse_args()

    sketch_lib_path = args.sketch_lib_path
    sketch_lib_path_abs = os.path.abspath(sketch_lib_path)

    for gcom in args.gcom:
        gcom_path = gcom

        #parse gcom file
        tree = etree.parse(gcom_path)
        gcom_root = tree.getroot()

        lib_element = gcom_root.find(".//libdirectory")
        if lib_element is not None:
            linked_as = lib_element.get("link-as")
            path = lib_element.get("path")
            gcom_dir_path = os.path.dirname(gcom_path)
            lib_path = os.path.join(gcom_dir_path, path)
            lib_path_abs = os.path.abspath(lib_path)
            lib_path_relative = os.path.relpath(lib_path_abs, sketch_lib_path_abs)

            with cd(sketch_lib_path_abs):
                try:
                    print "Creating link for: " + lib_path_abs
                    os.symlink(lib_path_relative, linked_as)
                except OSError as error:
                    print gcom + " has error " + str(error)

            # print "lib_path = " + lib_path_abs
            # print "sketch_path = " + sketch_lib_path_abs
            # print "relative_path = " + lib_path_relative