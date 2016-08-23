#!/usr/bin/env python

import argparse

import Gadgetron.ComponentCatalog
from lxml import etree
import Gadgetron.GtronLogging as log
import GCompiler.MakeLibraryLink
from GCompiler.testProgramGenerator import generate_test_file
import os
import shutil
from mako.template import Template

sketchbook_path = "../../Designs/GadgetronSketchBook/libraries"
library_template_name = "header_template.mako"
DIGITAL = "D"
ANALOG = "A"


class GComponent(object):
    """
    This class holds the programming information for a gadget component.
    The information is taken from the catalog file.
    """

    def __init__(self, component_element, catalog):
        log.debug("Making new GComponent")
        self.is_class = True
        self.var_name = component_element.get("progname")
        self.type = component_element.get("type")
        self.linked_as = ""
        self.path = ""
        # self.link_path = ""
        self.include_files = []
        self.required_files = []
        self.example_code = None

        catalog_element = catalog.find_component(self.type)
        class_element = catalog_element.et.find("API/arduino/class")

        if class_element is not None:
            # print self.type
            self.class_name = class_element.get("name")
            log.debug("name:", self.class_name)

            log.debug("Connecting args for " + self.var_name)
            connection_names = component_element.findall("api/arg")
            Gadgetron.ComponentCatalog.ET.dump(component_element)
            log.debug("Connection names:", connection_names)

            # print
            # print etree.dump(catalog_element)
            # print

            self.args = get_args(self.var_name, catalog_element, connection_names)
            log.debug("Args:")
            for a in self.args:
                log.debug(str(a))

            self.include_files = [include.get("file") for include in catalog_element.et.findall("API/arduino/include")]
            log.debug("Include files:", self.include_files)
            libdir = catalog_element.et.findall("API/arduino/libdirectory")
            log.debug("libdir:", libdir)

            if len(libdir) > 0:
                self.linked_as = catalog_element.et.findall("API/arduino/libdirectory")[0].get("link-as")
                self.path = catalog_element.et.findall("API/arduino/libdirectory")[0].get("path")

                log.debug("Finding example code for", self.type)
                if len(catalog_element.et.findall("API/arduino/example")) > 0:
                    log.debug(self.type, "example code:", catalog_element.et.findall("API/arduino/example")[0].text)
                    self.example_code = Template(catalog_element.et.findall("API/arduino/example")[0].text)

            self.required_files = [r.get("file") for r in catalog_element.et.findall("API/arduino/required")]

        else:
            self.is_class = False
            log.debug("No class")


class GArg(object):
    def __init__(self, var_name, arg_element, connection_names):
        self.element = arg_element
        self.type = self.element.get("type")
        self.value = None
        self.name = None
        self.preprocess = None

        log.debug("Making GArg")
        log.debug(etree.dump(self.element))
        log.debug("End tree")

        log.debug("Type:", self.type)

        if self.type == "const":
            self.value = self.element.get("const")

        elif self.type == "DigitalWireInterface" \
                or self.type == "SPIInterface" \
                or self.type == "PWMInterface" \
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
            assert self.value is not None
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

        log.debug(self.type is not None)
        assert (self.type is not None) and (self.name is not None) and (self.value is not None) and (
            self.preprocess is not None), str(self)

    def __str__(self):
        string = "GArg{" + "type: " + str(self.type) + ", value: " + str(self.value) + ", name: " + str(
            self.name) + ", preprocess: " + str(self.preprocess) + " }"
        return string


def get_args(var_name, catalog_element, connection_names):
    """
    :param var_name: The var name of the component
    :param catalog_element: The xml element in catalog of the component
    :param connection_names: The xml element of electrical section
    :return: A list of GArg objects
    """
    catalog_args = catalog_element.et.findall("API/arduino/class/arg")
    args = []
    for an_arg in catalog_args:
        args.append(GArg(var_name, an_arg, connection_names))
    return args


def get_net_literal(arg_name, digital_or_analog, connection_names):
    log.debug("Getting net literal for " + arg_name)
    log.debug("connection_names:", connection_names)

    for c in connection_names:
        if c.get("arg") == arg_name:  # find the right connection for the arg
            if digital_or_analog == DIGITAL:
                return c.get("digitalliteral")
            elif digital_or_analog == ANALOG:
                return c.get("analogliteral")
            else:
                assert False, "Digital or analog error: " + str(arg_name) + ", " + str(digital_or_analog) + ", " + str(
                    connection_names)
        else:
            # this happens when we don't have the right one
            continue
            # assert False, "Could not get net literal: " + str(arg_name) + " not equal to " + str(c.get("arg"))
    assert False, "Could not find sutable connections: " + str(connection_names)


def generate_header_codes(header_name, g_components):
    log.debug("Generating header codes")
    log.debug("\tLoading template")

    header_template = Template(
        filename=os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates", library_template_name))

    flatten_include_files = []

    log.debug("Components:")
    for c in g_components:
        log.debug(c.__dict__)

    for component in g_components:
        if component.is_class:
            for include in component.include_files:
                # Check if the file exists
                flatten_include_files.append(include)

    flatten_include_files = list(set(flatten_include_files))

    real_components = []

    for component in g_components:
        if component.is_class:
            real_components.append(component)

    log.debug("Real components:", [c.var_name for c in real_components])

    file_text = header_template.render(header_name=os.path.splitext(header_name)[0].upper() + "_H",
                                       include_files=flatten_include_files,
                                       components=real_components)

    log.debug(file_text)
    # exit(-1)

    return file_text


def create_header_file(header_name, g_components, test_name):
    log.debug("Creating header file")
    file_text = generate_header_codes(header_name, g_components)

    if test_name is not None:
        test_header_name = os.path.join(test_name, header_name)
        log.debug("Saving test header as", test_header_name)

        test_file = open(test_header_name, 'w')
        test_file.write(file_text)
        test_file.close()
        # link_header_file(test_header_name)

    log.debug("Opening header")
    file_handler = open(header_name, 'w')
    file_handler.write(file_text)
    file_handler.close()
    # link_header_file(header_name)


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
    GCompiler.MakeLibraryLink.create_link(source, destination_path, sketchbook_path)


def main():
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

    log.debug("Making catalog")
    catalog = Gadgetron.ComponentCatalog.ComponentCatalog(catalog_path)

    log.debug("api gspec:", )
    log.debug("G Components:", gspec_path)
    for component_element in gspec_root.iter("component"):
        Gadgetron.ComponentCatalog.ET.dump(component_element)
        g_components.append(GComponent(component_element, catalog))
        if g_components[-1].is_class:
            log.debug("component:", g_components[-1].var_name)

    test_name = os.path.splitext(header_name)[0] + '_test'
    log.debug("Making test program")
    if args.test:
        log.debug("Generating test program")
        generate_test_file(header_name, g_components, test_name=test_name)

    create_header_file(header_name, g_components, test_name=test_name)


if __name__ == "__main__":
    main()
