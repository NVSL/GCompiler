#!/usr/bin/env python

__author__ = 'WeiPingLiao'

import os
import shutil

import clang.cindex
import parseAST
from mako.template import Template

dir_name = os.path.dirname(os.path.abspath(__file__))
test_template_name = "test_template.mako"
clang.cindex.Config.set_library_path(dir_name)


def generate_test_codes(header_name, g_components):
    """
    :param header_name: The path to the header file
    :param g_components: The Component objects
    :return: The generated test codes
    """

    print "Generating test code"
    
    real_components = []

    for component in g_components:
        if component.is_class:
            real_components.append(component)

    # Add in required files
    required_files = []
    for component in g_components:
        required_files.extend(component.required_files)


    required_files = list(set(required_files))

    print "Making code"
    code = ""
    for component in g_components:
        print component.type, component.var_name, component.example_code
        if component.example_code is not None:
            code = code + 'Serial.println("Testing {}...");\n'.format(component.var_name);
            code = code + component.example_code.render(var_name=component.var_name)


    def indent(lines, amount, ch=' '):
        padding = amount * ch
        return padding + ('\n'+padding).join(lines.split('\n'))

    code = indent(code, 2)

    testtemplate = Template(filename=os.path.join(dir_name, "templates", test_template_name))

    testcodes = testtemplate.render(
                    header_name=header_name, 
                    components=real_components, 
                    required=required_files,
                    test_code=code
                )

    return testcodes


def validate_source_code(header, class_name):
    """
    Checking whether both setup() and loop() methods are in the source code
    :param header: The path to header file
    :param class_name: The class name we're looking for
    :return: True if both setup() and loop() methods are in the source code
    """
    print "Check method for " + header
    has_setup = False
    has_loop = False

    index = clang.cindex.Index.create()
    translation_unit = index.parse(header, ['-x', 'c++', '-std=c++11', '-D__CODE_GENERATOR__'])
    classes = parseAST.build_classes(translation_unit.cursor, header)
    #print(asciitree.draw_tree(translation_unit.cursor, parseAST.node_children, parseAST.print_node))
    for aClass in classes:
        if aClass.name == class_name:
            print 'For class ' + aClass.name + ', public methods:'
            for aFunction in aClass.functions:
                print aFunction
                if "setup" == aFunction.name:
                    has_setup = True
                if "loop" == aFunction.name:
                    has_loop = True

    return has_setup #and has_loop # we are just using setup now


def generate_test_file(header_name, g_components, test_name=None):
    if test_name is None:
        test_name = os.path.splitext(header_name)[0] + '_test'

    test_dir_path = os.path.join(os.getcwd(), test_name)
    if os.path.exists(test_dir_path):
        shutil.rmtree(test_dir_path)
    os.makedirs(test_dir_path)
    test_codes = generate_test_codes(header_name, g_components)
    test_file_path = os.path.join(test_dir_path, test_name + ".ino")
    print "Test code:"
    print test_codes
    print
    print "Opening "+test_file_path+" for writing"
    f = open(test_file_path, 'w')
    print "Writing"
    f.write(test_codes)
    f.close()
    # verify the generated test .ino file
    #print "Verifying"
    #call(["arduino", "--verify", test_file_path])
    print "Done"


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
