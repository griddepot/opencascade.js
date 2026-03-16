import os

import clang.cindex as cx
from typing import Callable
from common import (
    EMCC_INCLUDE_PATH_ARGS,
    OCCT_SRC_PATH,
)
from filters.enums import filter_enum
from filters.typedefs import filter_typedef
from wasm_gen.common import ignore_duplicate_typedef


def default_parse(
    path: str,
    additional_cpp_code: list[tuple[str, str]] = [],
    additional_flags: list[str] = [],
    includes: list[str] = EMCC_INCLUDE_PATH_ARGS,
):
    index = cx.Index.create()
    translation_unit = index.parse(
        path,
        ["-x", "c++", "-stdlib=libc++"] + additional_flags + includes,
        [[name, code] for name, code in additional_cpp_code],
        options=cx.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES,
    )

    if len(translation_unit.diagnostics) > 0:
        print("diagnostic messages:")
        for d in translation_unit.diagnostics:
            print("  " + d.format())

    return translation_unit


def is_template_typedef_node(node):
    return (
        node.kind == cx.CursorKind.TYPEDEF_DECL
        and not (node.get_definition() is None or not node == node.get_definition())
        and filter_typedef(node)
        and node.type.get_num_template_arguments() != -1
        and not ignore_duplicate_typedef(node)
    )


def is_typedef_node(node):
    return node.kind == cx.CursorKind.TYPEDEF_DECL


def is_enum_node(node):
    return node.kind == cx.CursorKind.ENUM_DECL and filter_enum(node)


def is_class_node(node):
    return (
        node.kind == cx.CursorKind.CLASS_DECL or node.kind == cx.CursorKind.STRUCT_DECL
    ) and not (node.get_definition() is None or not node == node.get_definition())


def node_is_include(n: cx.Cursor):
    return n.kind == cx.CursorKind.INCLUSION_DIRECTIVE


def is_underlying(node: cx.Cursor, check_occt_base_path=True):
    return check_occt_base_path and not node.location.file.name.startswith(
        OCCT_SRC_PATH
    )


class TuInfo:
    """Utility class for tracking information about a translation unit"""

    def __init__(
        self,
        path: str,
        additional_cpp_code: list[tuple[str, str]] = [],
        additional_flags: list[str] = [],
        includes: list[str] = EMCC_INCLUDE_PATH_ARGS,
        parse_fn: Callable[
            [str, list[tuple[str, str]], list[str], list[str]], cx.TranslationUnit
        ] = default_parse,
    ):
        self.path: str = path
        """The path to the source file"""
        
        self.symbol_name = os.path.basename(self.path)
        """The name of the actual source path extracted from the path"""
        
        self.tu: cx.TranslationUnit = parse_fn(
            path, additional_cpp_code, additional_flags, includes
        )
        """The loaded clang translation unit"""

        self.all_children: list[cx.Cursor] = []
        """All children of the translation unit, in no particular order"""
        self.typedefs: list[cx.Cursor] = []
        """All typedef declarations in the translation unit"""
        self.includes: list[cx.Cursor] = []
        """All include directives in the translation unit"""
        self.enums: list[cx.Cursor] = []
        """All enum declarations in the translation unit"""
        self.template_typedefs: list[cx.Cursor] = []
        """All template typedef declarations in the translation unit"""
        self.class_dict: dict[str, cx.Cursor] = {}
        """All class declarations in the translation unit"""
        self.typedef_underlying_dict: dict[str, cx.Cursor] = {}
        """All underlying typedef declarations in the translation unit"""
        self.template_typedef_underlying_dict: dict[str, cx.Cursor] = {}
        """All underlying template typedef declarations in the translation unit"""

        for n in self.tu.cursor.get_children():
            self.all_children.append(n)
            if is_template_typedef_node(n):
                self.template_typedefs.append(n)
            if is_underlying(n):
                self.template_typedef_underlying_dict[
                    n.underlying_typedef_type.spelling
                ] = n
            if is_typedef_node(n):
                self.typedefs.append(n)
            if node_is_include(n):
                self.includes.append(n)
            if is_enum_node(n):
                self.enums.append(n)
            if is_class_node(n):
                self.class_dict[n.spelling] = n
            if is_template_typedef_node(n):
                if is_underlying(n, False):
                    self.typedef_underlying_dict[n.underlying_typedef_type.spelling] = n
