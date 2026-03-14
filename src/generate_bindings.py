#!/usr/bin/python3

import errno
from functools import partial
import json
import multiprocessing
import os
import time
from typing import Callable, Any
from filters.classes import filter_class


from UltraDict import UltraDict
import clang.cindex as cx
from tqdm import tqdm

from bindings import EmbindBindings, TypescriptBindings
from common import OCCT_INCLUDE_FILES
from filters.pkgs import filter_packages
from tu_info import TuInfo
from wasm_gen.common import SkipException

libraryBasePath = "/opencascade.js/build/bindings"
buildDirectory = "/opencascade.js/build"


def load_preambles() -> dict[str, str]:
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


def should_process_class(child, is_custom_build):
    def should_process(child: cx.Cursor, occtBasePath: str):
        if child.get_definition() is None or not child == child.get_definition():
            return False

        if not filter_class(child, is_custom_build):
            return False

        if (
            child.kind == cx.CursorKind.CLASS_DECL
            or child.kind == cx.CursorKind.STRUCT_DECL
        ) and not child.type.get_num_template_arguments() == -1:
            return False

        if (
            child.kind == cx.CursorKind.CLASS_DECL
            or child.kind == cx.CursorKind.STRUCT_DECL
        ):
            baseSpec = [
                x
                for x in child.get_children()
                if x.kind == cx.CursorKind.CXX_BASE_SPECIFIER
                and x.access_specifier == cx.AccessSpecifier.PUBLIC
            ]
            if len(baseSpec) > 1:
                print("cannot handle multiple base classes (" + child.spelling + ")")
                return False
            return True

        return False

    if is_custom_build:
        return child.location.file.name == "myMain.h" and should_process(
            child, occtBasePath
        )
    return (
        child.extent.start.file.name.startswith(occtBasePath)
        and filter_packages(os.path.basename(os.path.dirname(child.location.file.name)))
        and should_process(child, occtBasePath)
    )


def should_process_template(child, is_custom_build):
    if is_custom_build:
        return (
            child.location.file.name == "myMain.h"
            and child.kind == cx.CursorKind.TYPEDEF_DECL
            and (
                child.underlying_typedef_type.kind == cx.TypeKind.ELABORATED
                or child.underlying_typedef_type.kind == cx.TypeKind.UNEXPOSED
            )
        )
    return (
        (
            child.extent.start.file.name.startswith(occtBasePath)
            and filter_packages(
                os.path.basename(os.path.dirname(child.location.file.name))
            )
        )
        and child.kind == cx.CursorKind.TYPEDEF_DECL
        and (
            child.underlying_typedef_type.kind == cx.TypeKind.ELABORATED
            or child.underlying_typedef_type.kind == cx.TypeKind.UNEXPOSED
        )
    )


def should_process_enum(child, is_custom_build):
    if is_custom_build:
        return child.location.file.name == "myMain.h"
    return (
        child.extent.start.file.name.startswith(occtBasePath)
        and filter_packages(os.path.basename(os.path.dirname(child.location.file.name)))
    ) and child.kind == cx.CursorKind.ENUM_DECL  # ty:ignore[unresolved-attribute]


def process_children(
    tu_info: TuInfo,
    items: list[cx.Cursor],
    filter_fn: Callable[[Any, bool], bool],
    cpp_process_fn: Callable[[TuInfo, str, Any], str],
    dts_process_fn: Callable[[TuInfo, str, Any], str],
    custom_code: str,
):
    is_custom_build = custom_code.strip() != ""

    process_count = 0
    for child in items:
        if (
            not filter_fn(child, is_custom_build)
            or child.spelling == ""
            or child.spelling.startswith("(unnamed")
        ):
            continue

        child_path = child.extent.start.file.name
        child_source_variant = child_path.replace(".hxx", ".cxx")
        preamble_key = (
            child_source_variant if os.path.isfile(child_source_variant) else child_path
        )
        # preamble_key = os.path.basename(preamble_target)

        relative_file: str = child_path.replace(occtBasePath, "")

        base_filename = f"{buildDirectory}/bindings/{relative_file}/{child.spelling if child.spelling != '' else child.type.spelling}"
        dts_filename = f"{base_filename}.d.ts"
        cpp_filename = f"{base_filename}.cpp"

        if os.path.exists(cpp_filename):
            continue

        mkdirp(f"{buildDirectory}/bindings/{os.path.dirname(relative_file)}")
        mkdirp(f"{buildDirectory}/bindings/{relative_file}")

        cached_preamble = preambles_cache.get(preamble_key)
        # if the preamble isn't in the cache, uhhhh, skill issue? (this should never happen and should be fixed)
        preamble = (
            cached_preamble + referenceTypeTemplateDefs + custom_code
            if cached_preamble is not None
            else custom_code
        )
        try:
            cpp_output = cpp_process_fn(tu_info, preamble, child)
            dts_output = dts_process_fn(tu_info, preamble, child)
            with open(cpp_filename, "w") as f:
                f.write(cpp_output)
            with open(dts_filename, "w") as f:
                f.write(dts_output)
            process_count += 1
        except SkipException as e:
            print(str(e))

    return process_count


def process_include(custom_code: str, completed_includes: UltraDict, include: str):
    if include in completed_includes:
        return ("skipped", 0)

    source_variant = include.replace(".hxx", ".cxx")
    target = source_variant if os.path.isfile(source_variant) else include
    tu_info = TuInfo(target)

    all_children_count = process_children(
        tu_info,
        tu_info.all_children,
        should_process_class,
        embindGenerationFuncClasses,
        typescriptGenerationFuncClasses,
        custom_code,
    )
    typedefs_count = process_children(
        tu_info,
        tu_info.template_typedefs,
        should_process_template,
        embindGenerationFuncTemplates,
        typescriptGenerationFuncTemplates,
        custom_code,
    )
    enums_count = process_children(
        tu_info,
        tu_info.enums,
        should_process_enum,
        embindGenerationFuncEnums,
        typescriptGenerationFuncEnums,
        custom_code,
    )
    completed_includes[include] = True
    return ("ok", all_children_count + typedefs_count + enums_count)


def process_sources(custom_code: str = ""):
    completed_includes = UltraDict()
    ok = 0
    start = time.time()
    targets = ["/occt/src/AIS/AIS_InteractiveContext.cxx"]
    print(targets)
    total = len(targets)

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as p:
        for status, count in tqdm(
            p.imap_unordered(
                partial(process_include, custom_code, completed_includes),
                sorted(targets),
            ),
            total=total,
            desc="Generating bindings",
            unit="file",
        ):
            if status == "ok":
                ok += count
            if status == "skipped":
                print("uhhh")

    elapsed = time.time() - start
    print(
        f"\nBinding generation done: {ok} generated, (total: {len(targets)}) in {elapsed / 60:.1f}min"
    )


def process_template(child: cx.Cursor):
    template_refs: list[cx.Cursor] = [
        node for node in child.get_children() if node.kind == cx.CursorKind.TEMPLATE_REF
    ]
    if len(template_refs) != 1:
        raise SkipException(
            'The number of template refs for the template typedef "'
            + child.spelling
            + '" is not 1!'
        )

    template_class: cx.Cursor = template_refs[0].get_definition()
    if template_class is None:
        raise SkipException("Template class is None (" + child.spelling + ")")
    template_arg_names: list[cx.Cursor] = [
        node
        for node in template_class.get_children()
        if node.kind == cx.CursorKind.TEMPLATE_TYPE_PARAMETER
    ]

    template_args = {}
    for i, arg_name in enumerate(template_arg_names):
        arg_type = child.type.get_template_argument_type(i)
        if arg_type.spelling == "":
            raise SkipException(
                f"Template argument type is empty for at least one argument. Is this class using default values for template arguments? This is currently not supported ({child.spelling})"
            )
        template_args[arg_name.spelling] = arg_type

    return [template_class, template_args]


def embindGenerationFuncClasses(tuInfo: TuInfo, preamble, child) -> str:
    embindings = EmbindBindings(tuInfo)
    output = embindings.processClass(child)

    return preamble + output


def embindGenerationFuncTemplates(tuInfo: TuInfo, preamble, child) -> str:
    [templateClass, templateArgs] = process_template(child)
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
    [templateClass, templateArgs] = process_template(child)
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
