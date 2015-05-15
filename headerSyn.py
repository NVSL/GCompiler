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

sketchbook_path = "../../Designs/GadgetronSketchBook/libraries"
dir_name = os.path.dirname(os.path.realpath(__file__))
DIGITAL = "D"
ANALOG = "A"


class GComponent(object):
    def __init__(self, component_element, catalog):
        self.is_class = True
        self.var_name = component_element.get("progname")
        self.type = component_element.get("type")
        self.linked_as = ""
        self.path = ""
        self.link_path = ""
        self.include_files = []

        try:
            catalog_element = catalog.getItems()[self.type]
            class_element = catalog_element.find("API/arduino/class")
            if class_element is not None:
                # print self.type
                self.class_name = class_element.get("name")
                connection_names = component_element.findall("api/arg")
                self.args = get_args(catalog_element, connection_names)
                self.include_files = [os.path.splitext(include.get("file"))[0] for include in catalog_element.findall("API/arduino/include")]
                libdir = catalog_element.findall("API/arduino/libdirectory")
                if len(libdir) > 0:
                    self.linked_as = catalog_element.findall("API/arduino/libdirectory")[0].get("link-as")
                    self.path = catalog_element.findall("API/arduino/libdirectory")[0].get("path")
                    self.link_path = os.path.join(self.linked_as, self.path)
            else:
                self.is_class = False

        except Exception as ex:
            print ex
            sys.exit(-1)


def get_args(catalog_element, connection_names):
    print("Connecting args...")
    interfaces = catalog_element.find("electrical/interfaces")
    catalog_args = catalog_element.findall("API/arduino/class/arg")
    args = []
    for an_arg in catalog_args:
        arg_type = an_arg.get("type")
        if arg_type == "const":
            args.append(an_arg.get("const"))
        elif arg_type == "DigitalWireInterface":
            args.append(get_net_literal(an_arg.get("net"), DIGITAL, connection_names))
        elif arg_type == "AnalogWireInterface":
            args.append(get_net_literal(an_arg.get("net"), ANALOG, connection_names))

    return args
    # return [arg.get("digitalliteral") if check_interface(interfaces, arg) == DIGITAL else arg.get("analogliteral") for arg in connection_names]


def get_net_literal(arg_name, digital_or_analog, connection_names):
    print("Getting net literal for " + arg_name)
    for c in connection_names:
        if c.get("arg") == arg_name:
            if digital_or_analog == DIGITAL:
                return c.get("digitalliteral")
            elif digital_or_analog == ANALOG:
                return c.get("analogliteral")

    return None


# def check_interface(interfaces, arg_name):
#     for i in interfaces:
#         # print i.get("net")
#         if i.get("net") == arg_name.get("net"):
#             if i.get("type") == "DigitalWireInterface":
#                 return DIGITAL
#             elif i.get("type") == "AnalogWireInterface":
#                 return ANALOG
#
#     return None


def generate_header_codes(header_name, g_components):

    mytemplate = Template(filename=dir_name + '/headertemplate.txt')

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

    file_text =  mytemplate.render(header_name="HEADER",
                                   include_files=flatten_include_files,
                                   class_names=class_names,
                                   var_names=var_names,
                                   args=args)

    return file_text


def generate_test_codes(header_name, g_components):
    # setup_codes = []
    # loop_codes = []
    #
    # for component in g_components:
    #     class_name = component.class_name
    #     setup_template = Template(filename=os.path.dirname(os.path.realpath(__file__)) + '/' + class_name + '_setup.txt')
    #     setup_codes.append(setup_template.render(var=component.var_name))
    #     loop_template = Template(filename=os.path.dirname(os.path.realpath(__file__)) + '/' + class_name + '_loop.txt')
    #     loop_codes.append(loop_template.render(var=component.var_name))

    clang.cindex.Config.set_library_path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib')
    index = clang.cindex.Index.create()

    real_components = []

    for component in g_components:
        for include in component.include_files:
            flag = check_method(os.path.join(sketchbook_path, component.linked_as, include + ".h"), index)
            if flag:
                real_components.append(component)

    testtemplate = Template(filename=os.path.dirname(os.path.realpath(__file__)) + '/testtemplate.txt')
    # testcodes = testtemplate.render(header_name=header_name, component_setups=setup_codes, component_loops=loop_codes, components=g_components)
    testcodes = testtemplate.render(header_name=header_name, components=real_components)

    return testcodes


def check_method(header, index):
    print header
    flag = True
    try:
        translation_unit = index.parse(header, ['-x', 'c++', '-std=c++11', '-D__CODE_GENERATOR__'])
        # print(asciitree.draw_tree(translation_unit.cursor, parseAST.node_children, parseAST.print_node))
        classes = parseAST.build_classes(translation_unit.cursor)
        for aClass in classes:
            # print 'For class ' + aClass.name + ', public methods:'
            # for aFunction in aClass.functions:
            #     print aFunction
            if "setup" not in aClass.functions:
                flag = False

            if "loop" not in aClass.functions:
                flag = False

    except Exception as e:
        print e
        flag = False

    return flag


def create_header_file(header_name, g_components):
    file_text = generate_header_codes(header_name, g_components)
    file_handler = open(header_name, 'w')
    file_handler.write(file_text)
    file_handler.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tool for generating .h file for Arduino given .gspec file")
    parser.add_argument("-n", dest="header_name", required=True, help="The name of the header should be")
    parser.add_argument("-g", dest="gspec", required=True, help="The path to the gspec file")
    parser.add_argument("-c", dest="catalog", required=True, help="The path to the catalog file")
    args = parser.parse_args()

    gspec_path = args.gspec
    catalog_path = args.catalog
    header_name = args.header_name
    tree = etree.parse(gspec_path)
    gspec_root = tree.getroot()

    # purified_gadget_name = "_".join(root.findtext("name").split())

    g_components = []
    catalog = ComponentCatalog(catalog_path)

    for component_element in gspec_root.iter("component"):
        g_components.append(GComponent(component_element, catalog))

    create_header_file(header_name, g_components)

    try:
        test_codes = generate_test_codes(header_name, g_components)
        f = open(os.path.splitext(header_name)[0] + '_test.ino', 'w')
        f.write(test_codes)
        f.close()
    except Exception as e:
        print e

