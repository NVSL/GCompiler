import sys
import asciitree
import clang.cindex


class Function(object):
    def __init__(self, cursor):
        self.name = cursor.spelling
        self.params = []
        self.get_params(cursor)

    def __str__(self):
        return self.name + str(self.params)


    def get_params(self, cursor):
        for t in cursor.type.argument_types():
            canonical = t.get_canonical()
            # print 'Parameter type: ' + canonical.kind.name
            type_kind_name = canonical.kind.name
            if canonical.kind == clang.cindex.TypeKind.POINTER:
                pointee = canonical.get_pointee()
                type_displayname = pointee.get_declaration().displayname
                # print pointee.get_declaration().displayname
            elif canonical.kind == clang.cindex.TypeKind.RECORD:
                # print canonical.get_declaration().displayname
                type_displayname = canonical.get_declaration().displayname
            else:
                # print canonical.kind.spelling
                type_displayname = canonical.kind.spelling

            self.params.append((type_kind_name, type_displayname))

            # declaration_cursor = t.get_declaration()
            # if declaration_cursor.kind == clang.cindex.CursorKind.NO_DECL_FOUND:
            #     print t.kind.name
            # elif t.kind == clang.cindex.TypeKind.POINTER:
            #     print 'something'
            # else:
            #     print declaration_cursor.displayname
            # print c.spelling
            # print c.type.get_declaration()
            # a = c.type.get_canonical()
            # print a.get_declaration()

            # for type in c.get_children():
            #     print type.displayname

            # if (c.kind == clang.cindex.CursorKind.PARM_DECL):
            #     print c.spelling
            #     print c.type.kind.name
                # for type in c.get_children():
                #     if (type.kind == clang.cindex.CursorKind.TYPE_REF):
                #         print type.spelling


class Class(object):
    def __init__(self, cursor):
        self.name = cursor.spelling
        self.functions = []

        for c in cursor.get_children():
            if (c.kind == clang.cindex.CursorKind.CXX_METHOD and
                c.access_specifier == clang.cindex.AccessSpecifier.PUBLIC):
                f = Function(c)
                self.functions.append(f)


def build_classes(cursor):
    result = []
    for c in cursor.get_children():
        if (c.kind == clang.cindex.CursorKind.CLASS_DECL
            and c.location.file.name == sys.argv[1]):
            a_class = Class(c)
            result.append(a_class)
        # elif c.kind == clang.cindex.CursorKind.NAMESPACE:
        #     child_classes = build_classes(c)
        #     result.extend(child_classes)

    return result


def node_children(node):
    return (c for c in node.get_children() if c.location.file.name == sys.argv[1])


def print_node(node):
    text = node.spelling or node.displayname
    kind = str(node.kind)[str(node.kind).index('.')+1:]
    return '{} {}'.format(kind, text)


if __name__ == "__main__":
    clang.cindex.Config.set_library_path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib')
    index = clang.cindex.Index.create()
    translation_unit = index.parse(sys.argv[1], ['-x', 'c++', '-std=c++11', '-D__CODE_GENERATOR__'])

    print(asciitree.draw_tree(translation_unit.cursor, node_children, print_node))

    classes = build_classes(translation_unit.cursor)

    for aClass in classes:
        print 'For class ' + aClass.name + ', public methods:'
        for aFunction in aClass.functions:
            print aFunction