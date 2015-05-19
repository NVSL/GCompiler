#!/usr/bin/env python

import argparse
import sys
import os
from testInoGenerator import *
from lxml import etree
from ComponentCatalog import *
from mako.template import Template
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
        # self.link_path = ""
        self.include_files = []
        self.required_files = []

        try:
            catalog_element = catalog.getItems()[self.type]
            class_element = catalog_element.find("API/arduino/class")
            if class_element is not None:
                # print self.type
                self.class_name = class_element.get("name")
                print("Connecting args for " + self.var_name)
                connection_names = component_element.findall("api/arg")
                self.args = get_args(self.var_name, catalog_element, connection_names)
                self.include_files = [include.get("file") for include in catalog_element.findall("API/arduino/include")]
                libdir = catalog_element.findall("API/arduino/libdirectory")
                if len(libdir) > 0:
                    self.linked_as = catalog_element.findall("API/arduino/libdirectory")[0].get("link-as")
                    self.path = catalog_element.findall("API/arduino/libdirectory")[0].get("path")
                    # self.link_path = os.path.join(self.linked_as, self.path)
                self.required_files = [r.get("file") for r in catalog_element.findall("API/arduino/required")]
            else:
                self.is_class = False

        except Exception as ex:
            print ex
            sys.exit(-1)


def get_args(var_name, catalog_element, connection_names):
    """
    :param class_name: The class name of the component
    :param catalog_element: The xml element in catalog of the component
    :param connection_names: The xml element of electrical section
    :return: A list of tuples of (ARG_NAME, ARG_VALUE)
    """
    # interfaces = catalog_element.find("electrical/interfaces")
    catalog_args = catalog_element.findall("API/arduino/class/arg")
    args = []
    for an_arg in catalog_args:
        arg_type = an_arg.get("type")
        arg_value = None
        arg_name = None
        if arg_type == "const":
            arg_name = None
            arg_value = an_arg.get("const")
        elif arg_type == "DigitalWireInterface" or arg_type == "SPIInterface" or arg_type == "PWMInterface":
            # Here I assume that if it is DigitalWireInterface, it can also be connected to AnalogWireInterface,
            # since analog pins on Arduino can be used identically as digital pins
            literal = get_net_literal(an_arg.get("net"), DIGITAL, connection_names)
            if literal == "None":
                literal = get_net_literal(an_arg.get("net"), ANALOG, connection_names)
            arg_name = (var_name + "_" + an_arg.get("net")).upper()
            arg_value = literal
        elif arg_type == "AnalogWireInterface":
            arg_name = (var_name + "_" + an_arg.get("net")).upper()
            arg_value = get_net_literal(an_arg.get("net"), ANALOG, connection_names)

        args.append((arg_name, arg_value))

    # print args
    return args
    # return [arg.get("digitalliteral") if check_interface(interfaces, arg) == DIGITAL else arg.get("analogliteral") for arg in connection_names]


def get_net_literal(arg_name, digital_or_analog, connection_names):
    # print("Getting net literal for " + arg_name)
    for c in connection_names:
        if c.get("arg") == arg_name:
            if digital_or_analog == DIGITAL:
                return c.get("digitalliteral")
            elif digital_or_analog == ANALOG:
                return c.get("analogliteral")

    return "None"


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
                # Check if the file exists
                include_header_path = os.path.join(sketchbook_path, component.linked_as, include)
                include_cpp_path = os.path.join(sketchbook_path, component.linked_as, os.path.splitext(include)[0] + ".cpp")
                if os.path.isfile(include_header_path):
                    flatten_include_files.append(os.path.join(component.linked_as, include))
                if os.path.isfile(include_cpp_path):
                    flatten_include_files.append(os.path.join(component.linked_as, os.path.splitext(include)[0] + ".cpp"))

    flatten_include_files = list(set(flatten_include_files))

    # class_names = []
    # args = []
    # var_names = []
    real_components = []

    for component in g_components:
        if component.is_class:
            real_components.append(component)
            # class_names.append(component.class_name)
            # var_names.append(component.var_name)
            # args.append(','.join(component.args))

    print args

    file_text = mytemplate.render(header_name=os.path.splitext(header_name)[0].upper() + "_H",
                                  include_files=flatten_include_files,
                                  components=real_components)

    return file_text


def create_header_file(header_name, g_components):
    file_text = generate_header_codes(header_name, g_components)
    file_handler = open(header_name, 'w')
    file_handler.write(file_text)
    file_handler.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tool for generating .h file for Arduino given .gspec file")
    parser.add_argument("-n", "--header", dest="header_name", required=True, help="The name of the header should be")
    parser.add_argument("-g", "--gspec", dest="gspec", required=True, help="The path to the gspec file")
    parser.add_argument("-c", "--catalog", dest="catalog", required=True, help="The path to the catalog file")
    parser.add_argument("-t", "--test", dest="test", action="store_true", help="Generate test .ino file")
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

    if args.test:
        generate_test_file(header_name, g_components)