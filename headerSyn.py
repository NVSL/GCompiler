#!/usr/bin/env python

import argparse
import sys
import os
from lxml import etree
from ComponentCatalog import *
from mako.template import Template
# from itertools import chain


class GComponent(object):
    # __catalog_path = "../../Libraries/Components/Catalog/Components.cat"
    # __catalog = ComponentCatalog(__catalog_path)

    def __init__(self, e, catalog_path):
        self.var_name = e.get("progname")
        self.type = e.get("type")
        self._catalog_path = catalog_path
        self._catalog = ComponentCatalog(self._catalog_path)

        try:
            catalog_element = self._catalog.getItems()[self.type]
            self.class_name = catalog_element.find("API/arduino/class").get("name")
            self.include_files = [include.get("file") for include in catalog_element.findall("API/arduino/include")]
        except Exception as e:
            print e
            sys.exit(-1)


def generate_header_file(header_name, g_components):

    mytemplate = Template(filename=os.path.dirname(os.path.realpath(__file__)) + '/headertemplate.txt')

    flatten_include_files = []
    for component in g_components:
        for include in component.include_files:
            flatten_include_files.append(include)

    flatten_include_files = list(set(flatten_include_files))

    class_names = [component.class_name for component in g_components]
    var_names = [component.var_name for component in g_components]

    file_text =  mytemplate.render(header_name=header_name,
                                   include_files=flatten_include_files,
                                   class_names=class_names,
                                   var_names=var_names)

    return file_text

    # print("a file has been written to " + header_name)

    # string = ""
    #
    # for headers in include_files:
    #     for h in headers:
    #         string += "#include \"" + h + "\"\n"
    #
    # string += "\n"
    #
    # for idx, var in enumerate(var_names):
    #     string += class_names[idx] + " " + var_names[idx] + " = new " + class_names[idx] + "()\n"
    #
    # print string

    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tool for generating .h file for Arduino given .gspec file")
    parser.add_argument("header_name")
    parser.add_argument("gspec")
    parser.add_argument("catalog")
    args = parser.parse_args()

    gspec_path = args.gspec
    catalog_path = args.catalog
    header_name = args.header_name
    tree = etree.parse(gspec_path)
    root = tree.getroot()

    # purified_gadget_name = "_".join(root.findtext("name").split())

    g_components = []

    for element in root.iter("component"):
        g_components.append(GComponent(element, catalog_path))

    file_text = generate_header_file(header_name, g_components)
    f = open(header_name, 'w')
    f.write(file_text)
    f.close()