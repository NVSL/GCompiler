#!/usr/bin/env python

import argparse
import sys
import os
from testProgramGenerator import *
from lxml import etree
from ComponentCatalog import *
from mako.template import Template
# from itertools import chain
import MakeLibraryLink
import shutil

sketchbook_path = "../../Designs/GadgetronSketchBook/libraries"
dir_name = os.path.dirname(os.path.realpath(__file__))
library_template_name = "header_template.mako"
DIGITAL = "D"
ANALOG = "A"


class GComponent(object):
    """
    This class holds the programming information for a gadget component.
    The information is taken from the catalog file.
    """
    def __init__(self, component_element, catalog):
        print
        print
        print "Making new GComponent"
        self.is_class = True
        self.var_name = component_element.get("progname")
        self.type = component_element.get("type")
        self.linked_as = ""
        self.path = ""
        # self.link_path = ""
        self.include_files = []
        self.required_files = []
        self.example_code = None

        catalog_element = catalog.getItems()[self.type]
        class_element = catalog_element.find("API/arduino/class")

        if class_element is not None:
            # print self.type
            self.class_name = class_element.get("name")
            print "name:", self.class_name

            print "Connecting args for " + self.var_name
            connection_names = component_element.findall("api/arg")

            print 
            print etree.dump(catalog_element)
            print

            self.args = get_args(self.var_name, catalog_element, connection_names)
            print "Args:"
            for a in self.args:
                print str(a)

            self.include_files = [include.get("file") for include in catalog_element.findall("API/arduino/include")]
            libdir = catalog_element.findall("API/arduino/libdirectory")
            
            if len(libdir) > 0:
                self.linked_as = catalog_element.findall("API/arduino/libdirectory")[0].get("link-as")
                self.path = catalog_element.findall("API/arduino/libdirectory")[0].get("path")

                print
                print "Finding example code for", self.type
                if len(catalog_element.findall("API/arduino/example")) > 0:
                    print self.type, "example code:", catalog_element.findall("API/arduino/example")[0].text
                    self.example_code = Template(catalog_element.findall("API/arduino/example")[0].text)

            self.required_files = [r.get("file") for r in catalog_element.findall("API/arduino/required")]
        
        else:
            self.is_class = False
            print "No class"


class GArg (object):
    def __init__(self, var_name, arg_element, connection_names):
        self.element = arg_element
        self.type = self.element.get("type")
        self.value = None
        self.name = None
        self.preprocess = None

        print "Making GArg"
        print etree.dump(self.element)
        print "End tree"

        print "Type:", self.type

        if self.type == "const":
            self.value = self.element.get("const")

        elif self.type == "DigitalWireInterface" \
                or self.type == "SPIInterface" \
                or self.type == "PWMInterface"\
                or self.type == "SerialInterface":

            literal = get_net_literal(self.element.get("net"), DIGITAL, connection_names)

            if literal == "None":
                literal = get_net_literal(self.element.get("net"), ANALOG, connection_names)

            self.name = (var_name + "_" + self.element.get("net")).upper()
            self.value = literal
            self.preprocess = "define"

        elif self.type == "AnalogWireInterface":
            self.name = (var_name + "_" + self.element.get("net")).upper()
            self.value = get_net_literal(self.element.get("net"), ANALOG, connection_names)
            self.preprocess = "define"

        elif self.type == "pointer" or self.type == "object":
            self.name = (var_name + "_" + self.element.get("class")).upper()
            self.class_name = self.element.get("class")
            self.factory_method = self.element.get("factory")
            self.preprocess = "factory"
            self.sub_args = []
            sub_arg_elements = self.element.findall("arg")
            
            for a in sub_arg_elements:
                self.sub_args.append(GArg(var_name, a, connection_names))

        else:
            assert False, "Unknown GArg type: " + str(self.type)

        print self.type is not None
        assert (self.type is not None) or (self.name is not None) or (self.value is not None) or (self.preprocess is not None), str(self)

    def __str__ (self):
        string = "GArg{" + "type: " + str(self.type) + ", value: " + str(self.value) + ", name: " + str(self.name) + ", preprocess: " + str(self.preprocess) + " }"
        return string

def get_args(var_name, catalog_element, connection_names):
    """
    :param var_name: The var name of the component
    :param catalog_element: The xml element in catalog of the component
    :param connection_names: The xml element of electrical section
    :return: A list of GArg objects
    """
    catalog_args = catalog_element.findall("API/arduino/class/arg")
    args = []
    for an_arg in catalog_args:
        args.append(GArg(var_name, an_arg, connection_names))
    return args


def get_net_literal(arg_name, digital_or_analog, connection_names):
    # print("Getting net literal for " + arg_name)
    for c in connection_names:
        if c.get("arg") == arg_name: # find the right connection for the arg
            if digital_or_analog == DIGITAL:
                return c.get("digitalliteral")
            elif digital_or_analog == ANALOG:
                return c.get("analogliteral")
            else:
                assert False, "Digital or analog error: " + str(arg_name) + ", " + str(digital_or_analog) + ", " + str(connection_names)
        else:
            # this happens when we don't have the right one
            continue
            #assert False, "Could not get net literal: " + str(arg_name) + " not equal to " + str(c.get("arg"))


def generate_header_codes(header_name, g_components):
    print "Generating header codes"
    print "\tLoading template"
    header_template = Template(filename=os.path.join(dir_name, library_template_name))

    flatten_include_files = []

    print "Component:", g_components[0].__dict__

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

    real_components = []

    for component in g_components:
        if component.is_class:
            real_components.append(component)

    print "Args:", args

    file_text = header_template.render(header_name=os.path.splitext(header_name)[0].upper() + "_H",
                                       include_files=flatten_include_files,
                                       components=real_components)

    return file_text


def create_header_file(header_name, g_components):
    print "Creating header file"
    file_text = generate_header_codes(header_name, g_components)
    
    print "Opening header"
    file_handler = open(header_name, 'w')
    file_handler.write(file_text)
    file_handler.close()
    link_header_file(header_name)


def link_header_file(header_name):
    """
    This function creates a sym link in GadgetronSketchBook directory
    :param header_name: The path to the generated header file
    :return:
    """
    source = header_name
    dir_name = os.path.splitext(source)[0]
    dir_path = os.path.join(sketchbook_path, dir_name)
    destination_name = source
    destination_path = os.path.join(dir_path, destination_name)
    if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
    os.makedirs(dir_path)
    MakeLibraryLink.create_link(source, destination_path, sketchbook_path)


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

    g_components = []
    
    print "Making catalog"
    catalog = ComponentCatalog(catalog_path)

    print
    print "api gspec:", 
    print "G Components:", gspec_path
    for component_element in gspec_root.iter("component"):
        g_components.append(GComponent(component_element, catalog))
        if g_components[-1].is_class:
            print "component:", g_components[-1].var_name

    create_header_file(header_name, g_components)

    print "Making test program"
    if args.test:
        print "Generating test program"
        generate_test_file(header_name, g_components)