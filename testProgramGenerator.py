#!/usr/bin/env python

__author__ = 'WeiPingLiao'

import os
from mako.template import Template
import clang.cindex
import parseAST
import asciitree
import headerSyn
import shutil
import sys
from subprocess import call

dir_name = os.path.dirname(os.path.abspath(__file__))
test_template_name = "test_template.mako"
clang.cindex.Config.set_library_path(dir_name)


def generate_test_codes(header_name, g_components):
    """
    :param header_name: The path to the header file
    :param g_components: The Component objects
    :return: The generated test codes
    """

    real_components = []

    for component in g_components:
        if component.is_class:
            should_add_test_codes = False
            for include in component.include_files:
                flag = validate_source_code(os.path.join(headerSyn.sketchbook_path, component.linked_as, include), component.class_name)
                if flag:
                    should_add_test_codes = True
            if should_add_test_codes:
                real_components.append(component)

    # Add in required files
    required_files = []
    for component in g_components:
        required_files.extend(component.required_files)

    required_files = list(set(required_files))

    testtemplate = Template(filename=os.path.join(dir_name, test_template_name))
    testcodes = testtemplate.render(header_name=header_name, components=real_components, required=required_files)

    return testcodes


def validate_source_code(header, class_name):
    """
    Checking whether both setup() and loop() methods are in the source code
    :param header: The path to header file
    :param class_name: The class name we're looking for
    :return: True if both setup() and loop() methods are in the source code
    """
    # print "Check method for " + header
    has_setup = False
    has_loop = False
    try:
        index = clang.cindex.Index.create()
        translation_unit = index.parse(header, ['-x', 'c++', '-std=c++11', '-D__CODE_GENERATOR__'])
        classes = parseAST.build_classes(translation_unit.cursor, header)
        # print(asciitree.draw_tree(translation_unit.cursor, parseAST.node_children, parseAST.print_node))
        for aClass in classes:
            if aClass.name == class_name:
                # print 'For class ' + aClass.name + ', public methods:'
                for aFunction in aClass.functions:
                    # print aFunction
                    if "setup" == aFunction.name:
                        has_setup = True
                    if "loop" == aFunction.name:
                        has_loop = True

    except Exception as e:
        print e
        return False

    return has_setup and has_loop


def generate_test_file(header_name, g_components, test_name=None):
    if test_name is None:
        test_name = os.path.splitext(header_name)[0] + '_test'
    try:
        test_dir_path = os.path.join(os.getcwd(), test_name)
        if os.path.exists(test_dir_path):
            shutil.rmtree(test_dir_path)
        os.makedirs(test_dir_path)
        test_codes = generate_test_codes(header_name, g_components)
        test_file_path = os.path.join(test_dir_path, test_name + ".ino")
        f = open(test_file_path, 'w')
        f.write(test_codes)
        f.close()
        # verify the generated test .ino file
        call(["arduino", "--verify", test_file_path])
    except Exception as e:
        print e


# if __name__ == "__main__":
#     print os.getcwd()
#     clang.cindex.Config.set_library_path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib')
#     index = clang.cindex.Index.create()
#     translation_unit = index.parse(sys.argv[1], ['-x', 'c++', '-std=c++11', '-D__CODE_GENERATOR__'])
#
#     print(asciitree.draw_tree(translation_unit.cursor, parseAST.node_children, parseAST.print_node))
#
#     classes = parseAST.build_classes(translation_unit.cursor)
#     print(classes)
#     generate_test_codes("LED.h", [])