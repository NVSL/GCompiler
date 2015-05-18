#!/usr/bin/env python

__author__ = 'WeiPingLiao'

import os
from mako.template import Template
import clang.cindex
import parseAST
import asciitree
from headerSyn import sketchbook_path
import shutil

dir_name = os.path.dirname(os.path.abspath(__file__))


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

    clang.cindex.Config.set_library_path(dir_name)
    index = clang.cindex.Index.create()

    real_components = []

    for component in g_components:
        for include in component.include_files:
            flag = check_method(os.path.join(sketchbook_path, component.linked_as, include), index)
            if flag:
                real_components.append(component)

    testtemplate = Template(filename=os.path.join(dir_name, 'testtemplate.txt'))
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


def generate_test_file(header_name, g_components, test_name=None):
    if test_name is None:
        test_name = os.path.splitext(header_name)[0] + '_test'
    try:
        test_dir_path = os.path.join(os.getcwd(), test_name)
        if os.path.exists(test_dir_path):
            shutil.rmtree(test_dir_path)
        os.makedirs(test_dir_path)
        test_codes = generate_test_codes(header_name, g_components)
        f = open(os.path.join(test_dir_path, test_name + ".ino"), 'w')
        f.write(test_codes)
        f.close()
    except Exception as e:
        print e