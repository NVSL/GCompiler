#!/usr/bin/env python

import argparse
import sys
import os
from lxml import etree
from ComponentCatalog import *
from mako.template import Template
import clang.cindex
import asciitree
import parseAST
# from itertools import chain


class GComponent(object):
    # __catalog_path = "../../Libraries/Components/Catalog/Components.cat"
    # __catalog = ComponentCatalog(__catalog_path)

    def __init__(self, e, catalog_path):
        self.is_class = True
        self.var_name = e.get("progname")
        self.type = e.get("type")
        self._catalog_path = catalog_path
        self._catalog = ComponentCatalog(self._catalog_path)
        self.linked_as = ""
        self.path = ""
        self.link_path = ""

        try:
            catalog_element = self._catalog.getItems()[self.type]
            class_element = catalog_element.find("API/arduino/class")
            if class_element != None:
                print self.type
                self.class_name = class_element.get("name")
                self.args = [arg.get("digitalliteral") if arg.get("analogliteral") == "None" else arg.get("analogliteral") for arg in e.findall("api/arg")]
                self.include_files = [os.path.splitext(include.get("file"))[0] for include in catalog_element.findall("API/arduino/include")]
                libdir = catalog_element.findall("API/arduino/libdirectory")
                if len(libdir) > 0:
                    self.linked_as = catalog_element.findall("API/arduino/libdirectory")[0].get("link-as")
                    self.path = catalog_element.findall("API/arduino/libdirectory")[0].get("path")
                    self.link_path = os.path.join(self.linked_as, self.path)
            else:
                self.is_class = False

        except Exception as e:
            print e
            sys.exit(-1)


def generate_header_file(header_name, g_components):

    mytemplate = Template(filename=os.path.dirname(os.path.realpath(__file__)) + '/headertemplate.txt')

    flatten_include_files = []
    for component in g_components:
        if component.is_class:
            for include in component.include_files:
                flatten_include_files.append(os.path.join(component.link_path, include + ".h"))

    flatten_include_files = list(set(flatten_include_files))

    class_names = []
    args = []
    var_names = []

    for component in g_components:
        if component.is_class:
            class_names.append(component.class_name)
            args.append(','.join(component.args))
            var_names.append(component.var_name)

    file_text =  mytemplate.render(header_name=header_name,
                                   include_files=flatten_include_files,
                                   class_names=class_names,
                                   var_names=var_names,
                                   args=args)

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


def generate_test_file(header_name, g_components):
    # setup_codes = []
    # loop_codes = []
    #
    # for component in g_components:
    #     class_name = component.class_name
    #     setup_template = Template(filename=os.path.dirname(os.path.realpath(__file__)) + '/' + class_name + '_setup.txt')
    #     setup_codes.append(setup_template.render(var=component.var_name))
    #     loop_template = Template(filename=os.path.dirname(os.path.realpath(__file__)) + '/' + class_name + '_loop.txt')
    #     loop_codes.append(loop_template.render(var=component.var_name))

    testtemplate = Template(filename=os.path.dirname(os.path.realpath(__file__)) + '/testtemplate.txt')
    # testcodes = testtemplate.render(header_name=header_name, component_setups=setup_codes, component_loops=loop_codes, components=g_components)
    testcodes = testtemplate.render(header_name=header_name, components=g_components)

    for component in g_components:
        for include in component.include_files:
            check_method(include + ".h")


    return testcodes


def check_method(header):
    clang.cindex.Config.set_library_path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib')
    index = clang.cindex.Index.create()
    print header
    translation_unit = index.parse(header, ['-x', 'c++', '-std=c++11', '-D__CODE_GENERATOR__'])

    print(asciitree.draw_tree(translation_unit.cursor, parseAST.node_children, parseAST.print_node))

    classes = parseAST.build_classes(translation_unit.cursor)

    for aClass in classes:
        print 'For class ' + aClass.name + ', public methods:'
        for aFunction in aClass.functions:
            print aFunction


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

    try:
        test_codes = generate_test_file(header_name, g_components)
        f = open(os.path.splitext(header_name)[0] + '_test.ino', 'w')
        f.write(test_codes)
        f.close()
    except Exception as e:
        print e

