import clang.cindex

from common import includePathArgs, occtBasePath, ocIncludeStatements, ocIncludePaths
from filters.enums import filter_enum
from filters.typedefs import filter_typedef
from wasm_gen.common import ignore_duplicate_typedef


def get_includes(path: str):
    index = clang.cindex.Index.create()
    translation_unit = index.parse(
        path,
        ["-x", "c++", "-stdlib=libc++", "-d__emscripten__"] + includePathArgs,
    )
    return list(translation_unit.get_includes())


def parse(additional_cpp_code=""):
    index = clang.cindex.Index.create()
    translation_unit = index.parse(
        "myMain.h",
        ["-x", "c++", "-stdlib=libc++", "-d__emscripten__"] + includePathArgs,
        [["myMain.h", ocIncludeStatements + "\n" + additional_cpp_code]],
    )
    
    if len(translation_unit.diagnostics) > 0:
        print("diagnostic messages:")
        for d in translation_unit.diagnostics:
            print("  " + d.format())

    return translation_unit


def template_typedef_generator(tu):
    return list(
        filter(
            lambda x: (
                x.kind == clang.cindex.CursorKind.TYPEDEF_DECL
                and not (x.get_definition() is None or not x == x.get_definition())
                and filter_typedef(x)
                and x.type.get_num_template_arguments() != -1
                and not ignore_duplicate_typedef(x)
            ),
            tu.cursor.get_children(),
        )
    )


def typedef_generator(tu: clang.cindex.TranslationUnit):
    return list(
        filter(
            lambda x: x.kind == clang.cindex.CursorKind.TYPEDEF_DECL,
            tu.cursor.get_children(),
        )
    )


def all_children_generator(tu: clang.cindex.TranslationUnit):
    return list(tu.cursor.get_children())


def enum_generator(tu: clang.cindex.TranslationUnit):
    return list(
        filter(
            lambda x: x.kind == clang.cindex.CursorKind.ENUM_DECL and filter_enum(x),
            tu.cursor.get_children(),
        )
    )


def class_dict(tu: clang.cindex.TranslationUnit):
    d = dict()
    for x in tu.cursor.get_children():
        if (
            x.kind == clang.cindex.CursorKind.CLASS_DECL
            or x.kind == clang.cindex.CursorKind.STRUCT_DECL
        ) and not (x.get_definition() is None or not x == x.get_definition()):
            if x.spelling not in d:
                # original code didn't handle duplicate names, that seems bad?
                d[x.spelling] = x
    return d

def includes_generator(tu: clang.cindex.TranslationUnit):
    return list(
        filter(
            lambda x: x.kind == clang.cindex.CursorKind.INCLUSION_DIRECTIVE,
            tu.cursor.get_children(),
        )
    )

def underlying_dict(items: list, check_occt_base_path: bool):
    d = dict()
    for x in items:
        if check_occt_base_path and not x.location.file.name.startswith(occtBasePath):
            continue
        if x.underlying_typedef_type.spelling not in d:
            # original code didn't handle duplicate names, that seems bad?
            d[x.underlying_typedef_type.spelling] = x
    return d

def get_oc_includes(path: str):
    index = clang.cindex.Index.create()
    translation_unit = index.parse(
        path,
        ["-x", "c++", "-stdlib=libc++", "-d__emscripten__"]
        + list(map(lambda p: "-I" + p, ocIncludePaths)),
    )
    return "\n".join(sorted(set(map(lambda x: f"#include \"{x.include.name.split('/')[-1]}\"", filter(lambda x: x.include.name.startswith("/occt") and x.include.name.endswith(".hxx"), translation_unit.get_includes())))))

class TuInfo:
    """utility class for tracking information about a translation unit"""

    def __init__(self, custom_code: str):
        self.tu = parse(custom_code)
        print(custom_code)
        """the loaded clang translation unit"""
        self.all_children = all_children_generator(self.tu)
        self.typedefs = typedef_generator(self.tu)
        self.includes = includes_generator(self.tu)
        self.enums = enum_generator(self.tu)
        self.template_typedefs = template_typedef_generator(self.tu)
        self.class_dict = class_dict(self.tu)
        self.typedef_underlying_dict = underlying_dict(self.typedefs, True)
        self.template_typedef_underlying_dict = underlying_dict(
            self.template_typedefs, False
        )
