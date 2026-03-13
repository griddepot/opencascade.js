#!/usr/bin/python3

import errno
import json
import os
from typing import Callable

import clang.cindex

from bindings import EmbindBindings, TypescriptBindings, shouldProcessClass
from common import OCCT_INCLUDE_FILES
from filters.pkgs import filter_packages
from tu_info import TuInfo
from wasm_gen.common import SkipException

libraryBasePath = "/opencascade.js/build/bindings"
buildDirectory = "/opencascade.js/build"


def load_preambles():
    preambles_path = os.path.join(buildDirectory, "preambles.json")
    if os.path.exists(preambles_path):
        with open(preambles_path) as f:
            return json.load(f)
    return {}


preambles_cache = load_preambles()
occtBasePath = "/occt/src/"


def mkdirp(name: str) -> None:
    try:
        os.makedirs(name)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def filterClasses(child, is_custom_build):
    if is_custom_build:
        return child.location.file.name == "myMain.h" and shouldProcessClass(
            child, occtBasePath
        )
    return (
        child.extent.start.file.name.startswith(occtBasePath)
        and filter_packages(os.path.basename(os.path.dirname(child.location.file.name)))
        and shouldProcessClass(child, occtBasePath)
    )


def filterTemplates(child, is_custom_build):
    if is_custom_build:
        return (
            child.location.file.name == "myMain.h"
            and child.kind == clang.cindex.CursorKind.TYPEDEF_DECL
            and (
                child.underlying_typedef_type.kind == clang.cindex.TypeKind.ELABORATED
                or child.underlying_typedef_type.kind == clang.cindex.TypeKind.UNEXPOSED
            )
        )
    return (
        (
            child.extent.start.file.name.startswith(occtBasePath)
            and filter_packages(
                os.path.basename(os.path.dirname(child.location.file.name))
            )
        )
        and child.kind == clang.cindex.CursorKind.TYPEDEF_DECL
        and (
            child.underlying_typedef_type.kind == clang.cindex.TypeKind.ELABORATED
            or child.underlying_typedef_type.kind == clang.cindex.TypeKind.UNEXPOSED
        )
    )


def filterEnums(child, is_custom_build):
    if is_custom_build:
        return child.location.file.name == "myMain.h"
    return (
        child.extent.start.file.name.startswith(occtBasePath)
        and filter_packages(os.path.basename(os.path.dirname(child.location.file.name)))
    ) and child.kind == clang.cindex.CursorKind.ENUM_DECL


def process_source(
    tu_info: TuInfo,
    items: list[clang.cindex.Cursor],
    extension: str,
    preamble: str,
    filter_fn: Callable[[any], bool],
    process_fn: Callable[[any, any], str],
    is_custom_build: bool,
):
    for child in items:
        if (
            not filter_fn(child, is_custom_build)
            or child.spelling == ""
            or child.spelling.startswith("(unnamed")
        ):
            continue

        relative_file: str = child.extent.start.file.name.replace(occtBasePath, "")
        mkdirp(f"{buildDirectory}/bindings/{os.path.dirname(relative_file)}")
        mkdirp(f"{buildDirectory}/bindings/{relative_file}")
        filename = f"{buildDirectory}/bindings/{relative_file}/{child.spelling if child.spelling != '' else child.type.spelling}{extension}"

        if os.path.exists(filename):
            print(f"File {child.spelling}.cpp already exists, skipping")
            continue
        print(f"Processing {child.spelling} ({relative_file})")

        try:
            output = process_fn(tu_info, preamble, child)
            with open(filename, "w") as f:
                f.write(output)
        except SkipException as e:
            print(str(e))


def process_sources(custom_code: str = ""):
    is_custom_build = custom_code != ""
    for header in OCCT_INCLUDE_FILES:
        tu_info = TuInfo(header)
        cached_preamble = preambles_cache.get(header)
        # if the preamble isn't in the cache, uhhhh, skill issue? (this should never happen and should be fixed)
        preamble = (
            cached_preamble + referenceTypeTemplateDefs + custom_code
            if cached_preamble is not None
            else custom_code
        )
        process_source(
            tu_info,
            tu_info.all_children,
            ".cpp",
            preamble,
            filterClasses,
            embindGenerationFuncClasses,
            is_custom_build,
        )
        process_source(
            tu_info,
            tu_info.all_children,
            ".d.ts.json",
            preamble,
            filterClasses,
            typescriptGenerationFuncClasses,
            is_custom_build,
        )
        process_source(
            tu_info,
            tu_info.template_typedefs,
            ".cpp",
            preamble,
            filterTemplates,
            embindGenerationFuncTemplates,
            is_custom_build,
        )
        process_source(
            tu_info,
            tu_info.template_typedefs,
            ".d.ts.json",
            preamble,
            filterTemplates,
            typescriptGenerationFuncTemplates,
            is_custom_build,
        )
        process_source(
            tu_info,
            tu_info.enums,
            ".cpp",
            preamble,
            filterEnums,
            embindGenerationFuncEnums,
            is_custom_build,
        )
        process_source(
            tu_info,
            tu_info.enums,
            ".d.ts.json",
            preamble,
            filterEnums,
            typescriptGenerationFuncEnums,
            is_custom_build,
        )


def split(a: list, n):
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n))


def processTemplate(child):
    templateRefs = list(
        filter(
            lambda x: x.kind == clang.cindex.CursorKind.TEMPLATE_REF,
            child.get_children(),
        )
    )
    if len(templateRefs) != 1:
        raise SkipException(
            'The number of template refs for the template typedef "'
            + child.spelling
            + '" is not 1!'
        )

    templateClass = templateRefs[0].get_definition()
    if templateClass is None:
        raise SkipException("Template class is None (" + child.spelling + ")")
    templateArgNames = list(
        filter(
            lambda x: x.kind == clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER,
            templateClass.get_children(),
        )
    )
    templateArgs = {}
    for i, templateArgName in enumerate(templateArgNames):
        templateArgType = child.type.get_template_argument_type(i)
        if templateArgType.spelling == "":
            raise SkipException(
                "Template argument type is empty for at least one argument. Is this class using default values for template arguments? This is currently not supported ("
                + child.spelling
                + ")"
            )
        templateArgs[templateArgName.spelling] = templateArgType

    return [templateClass, templateArgs]


def embindGenerationFuncClasses(tuInfo: TuInfo, preamble, child) -> str:
    embindings = EmbindBindings(tuInfo)
    output = embindings.processClass(child)

    return preamble + output


def embindGenerationFuncTemplates(tuInfo: TuInfo, preamble, child) -> str:
    [templateClass, templateArgs] = processTemplate(child)
    embindings = EmbindBindings(tuInfo)
    output = embindings.processClass(templateClass, child, templateArgs)

    return preamble + output


def embindGenerationFuncEnums(tuInfo: TuInfo, preamble, child) -> str:
    embindings = EmbindBindings(tuInfo)
    output = embindings.processEnum(child)

    return preamble + output


def typescriptGenerationFuncClasses(tuInfo: TuInfo, preamble, child) -> str:
    typescript = TypescriptBindings(tuInfo)
    output = typescript.processClass(child)

    return json.dumps(
        {
            ".d.ts": preamble + output,
            "kind": "class",
            "exports": typescript.exports,
        }
    )


def typescriptGenerationFuncTemplates(tuInfo: TuInfo, preamble, child) -> str:
    [templateClass, templateArgs] = processTemplate(child)
    typescript = TypescriptBindings(tuInfo)
    output = typescript.processClass(templateClass, child, templateArgs)

    return json.dumps(
        {
            ".d.ts": preamble + output,
            "kind": "class",
            "exports": typescript.exports,
        }
    )


def typescriptGenerationFuncEnums(tuInfo: TuInfo, preamble, child) -> str:
    typescript = TypescriptBindings(tuInfo)
    output = typescript.processEnum(child)

    return json.dumps(
        {
            ".d.ts": preamble + output,
            "kind": "enum",
            "exports": typescript.exports,
        }
    )


referenceTypeTemplateDefs = (
    "\n"
    + "#include <emscripten/bind.h>\n"
    + "using namespace emscripten;\n"
    + "#include <functional>\n"
    + "\n"
    + "template<typename T>\n"
    + "T getReferenceValue(const emscripten::val& v) {\n"
    + '  if(!(v.typeOf().as<std::string>() == "object")) {\n'
    + "    return v.as<T>(allow_raw_pointers());\n"
    + '  } else if(v.typeOf().as<std::string>() == "object" && v.hasOwnProperty("current")) {\n'
    + '    return v["current"].as<T>(allow_raw_pointers());\n'
    + "  }\n"
    + '  throw("unsupported type");\n'
    + "}\n"
    + "\n"
    + "template<typename T>\n"
    + "void updateReferenceValue(emscripten::val& v, T& val) {\n"
    + '  if(v.typeOf().as<std::string>() == "object" && v.hasOwnProperty("current")) {\n'
    + '    v.set("current", val);\n'
    + "  }\n"
    + "}\n"
    + "\n"
)


def custom_code_bindgen(custom_code):
    try:
        os.makedirs(libraryBasePath)
    except Exception:
        pass

    process_sources(custom_code)


if __name__ == "__main__":
    try:
        os.makedirs(libraryBasePath)
    except Exception:
        pass

    process_sources()
