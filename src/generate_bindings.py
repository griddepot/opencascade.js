import multiprocessing
import errno
import json
import os
import time
from typing import Any, Callable

import clang.cindex as cx
from tqdm import tqdm

from bindings import EmbindBindings, TypescriptBindings
from common import OCCT_SRC_PATH, OCCT_INCLUDE_FILES
from filters.classes import filter_class
from filters.includes import filter_include
from filters.pkgs import filter_packages
from clang_utils import TuInfo, is_source_definition
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


def mkdirp(name: str) -> None:
    try:
        os.makedirs(name)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def should_process_class(node: cx.Cursor, is_custom_build: bool) -> bool:
    def should_process(n: cx.Cursor) -> bool:
        if not is_source_definition(n):
            return False

        if not filter_class(n):
            return False

        if (
            n.kind == cx.CursorKind.CLASS_DECL or n.kind == cx.CursorKind.STRUCT_DECL
        ) and not n.type.get_num_template_arguments() == -1:
            return False

        if n.kind == cx.CursorKind.CLASS_DECL or n.kind == cx.CursorKind.STRUCT_DECL:
            baseSpec = [
                x
                for x in n.get_children()
                if x.kind == cx.CursorKind.CXX_BASE_SPECIFIER
                and x.access_specifier == cx.AccessSpecifier.PUBLIC
            ]
            if len(baseSpec) > 1:
                # print(f"cannot handle multiple base classes ({n.spelling})")
                return False
            return True

        return False

    filename = node.extent.start.file.name if node.extent.start.file is not None else ""
    if is_custom_build:
        return filename == "myMain.h" and should_process(node)
    return (
        filename.startswith(OCCT_SRC_PATH)
        and filter_packages(os.path.basename(os.path.dirname(filename)))
        and should_process(node)
    )


def should_process_template(node: cx.Cursor, is_custom_build: bool) -> bool:
    filename = node.extent.start.file.name if node.extent.start.file is not None else ""
    if is_custom_build:
        return (
            filename == "myMain.h"
            and node.kind == cx.CursorKind.TYPEDEF_DECL
            and (
                node.underlying_typedef_type.kind == cx.TypeKind.ELABORATED
                or node.underlying_typedef_type.kind == cx.TypeKind.UNEXPOSED
            )
        )
    return (
        (
            filename.startswith(OCCT_SRC_PATH)
            and filter_packages(os.path.basename(os.path.dirname(filename)))
        )
        and node.kind == cx.CursorKind.TYPEDEF_DECL
        and (
            node.underlying_typedef_type.kind == cx.TypeKind.ELABORATED
            or node.underlying_typedef_type.kind == cx.TypeKind.UNEXPOSED
        )
    )


def should_process_enum(node: cx.Cursor, is_custom_build: bool) -> bool:
    filename = node.extent.start.file.name if node.extent.start.file is not None else ""
    if is_custom_build:
        return filename == "myMain.h"
    return (
        filename.startswith(OCCT_SRC_PATH)
        and filter_packages(os.path.basename(os.path.dirname(filename)))
    ) and node.kind == cx.CursorKind.ENUM_DECL


def process_template(node: cx.Cursor) -> tuple[cx.Cursor, dict[str, cx.Type]]:
    template_refs: list[cx.Cursor] = [
        child
        for child in node.get_children()
        if child.kind == cx.CursorKind.TEMPLATE_REF
    ]
    if len(template_refs) != 1 or not template_refs[0].get_definition():
        raise SkipException(
            f'The number of template refs for the template typedef "{node.spelling}" is not 1!'
        )

    template_class: cx.Cursor | None = template_refs[0].get_definition()
    if template_class is None:
        raise SkipException(f"Template class is None ({node.spelling})")
    template_arg_names: list[cx.Cursor] = [
        n
        for n in template_class.get_children()
        if n.kind == cx.CursorKind.TEMPLATE_TYPE_PARAMETER
    ]

    template_args: dict[str, cx.Type] = {}
    for i, arg_name in enumerate(template_arg_names):
        arg_type = node.type.get_template_argument_type(i)
        if arg_type.spelling == "":
            raise SkipException(
                f"Template argument type is empty for at least one argument. Is this class using default values for template arguments? This is currently not supported ({node.spelling})"
            )
        template_args[arg_name.spelling] = arg_type

    return (template_class, template_args)


def embind_generate_class(tu_info: TuInfo, preamble: str, node: cx.Cursor) -> str:
    embindings = EmbindBindings(tu_info)
    output = embindings.process_class(node)
    return preamble + output


def embind_generate_template(tu_info: TuInfo, preamble: str, node: cx.Cursor) -> str:
    template_class, template_args = process_template(node)
    embindings = EmbindBindings(tu_info)
    output = embindings.process_class(template_class, node, template_args)
    return preamble + output


def embind_generate_enum(tu_info: TuInfo, preamble: str, node: cx.Cursor) -> str:
    embindings = EmbindBindings(tu_info)
    output = embindings.process_enum(node)
    return preamble + output


def ts_generate_class(tu_info: TuInfo, preamble: str, node: cx.Cursor) -> str:
    typescript = TypescriptBindings(tu_info)
    output = typescript.process_class(node)
    return json.dumps(
        {
            ".d.ts": preamble + output,
            "kind": "class",
            "exports": typescript.exports,
        }
    )


def ts_generate_template(tu_info: TuInfo, preamble: str, node: cx.Cursor) -> str:
    template_class, template_args = process_template(node)
    typescript = TypescriptBindings(tu_info)
    output = typescript.process_class(template_class, node, template_args)
    return json.dumps(
        {
            ".d.ts": preamble + output,
            "kind": "class",
            "exports": typescript.exports,
        }
    )


def ts_generate_enum(tu_info: TuInfo, preamble: str, node: cx.Cursor) -> str:
    typescript = TypescriptBindings(tu_info)
    output = typescript.process_enum(node)
    return json.dumps(
        {
            ".d.ts": preamble + output,
            "kind": "enum",
            "exports": typescript.exports,
        }
    )


def process_node(
    tu_info: TuInfo,
    node: cx.Cursor,
    filter_fn: Callable[[Any, bool], bool],
    cpp_process_fn: Callable[[TuInfo, str, Any], str],
    dts_process_fn: Callable[[TuInfo, str, Any], str],
    custom_code: str,
    processed_cache: dict[str, str],
    is_custom_build: bool,
) -> int:
    if (
        not filter_fn(node, is_custom_build)
        or node.spelling == ""
        or node.spelling.startswith("(unnamed")
    ):
        return 0

    preamble_key: str | None = (
        node.extent.start.file.name if node.extent.start.file is not None else None
    )
    if preamble_key is None or (preamble_key in processed_cache and processed_cache[preamble_key] == "done"):
        return 0
    else:
        processed_cache[preamble_key] = "processing"

    relative_file: str = preamble_key.replace(OCCT_SRC_PATH, "")

    base_filename = f"{buildDirectory}/bindings/{relative_file}/{node.spelling if node.spelling != '' else node.type.spelling}"
    dts_filename = f"{base_filename}.d.ts"
    cpp_filename = f"{base_filename}.cpp"

    if os.path.exists(cpp_filename):
        return 0

    # print(f"Processing {relative_file} ({node.spelling})...")
    mkdirp(f"{buildDirectory}/bindings/{os.path.dirname(relative_file)}")
    mkdirp(f"{buildDirectory}/bindings/{relative_file}")

    cached_preamble = preambles_cache.get(preamble_key)

    preamble = (
        cached_preamble + referenceTypeTemplateDefs + custom_code
        if cached_preamble is not None
        else custom_code
        + referenceTypeTemplateDefs  # if the preamble isn't in the cache, uhhhh, skill issue? (this should never happen and should be fixed)
    )
    try:
        cpp_output = cpp_process_fn(tu_info, preamble, node)
        dts_output = dts_process_fn(tu_info, preamble, node)
        with open(cpp_filename, "w") as f:
            f.write(cpp_output)
        with open(dts_filename, "w") as f:
            f.write(dts_output)
        processed_cache[preamble_key] = "done"
        return 1
    except SkipException as e:
        print(str(e))
        return 0


def process_children(
    tu_info: TuInfo,
    child_nodes: list[cx.Cursor],
    filter_fn: Callable[[Any, bool], bool],
    cpp_process_fn: Callable[[TuInfo, str, Any], str],
    dts_process_fn: Callable[[TuInfo, str, Any], str],
    custom_code: str,
    processed_cache: dict[str, str],
) -> int:
    is_custom_build = custom_code.strip() != ""

    process_count = 0
    for node in child_nodes:
        process_count += process_node(
            tu_info,
            node,
            filter_fn,
            cpp_process_fn,
            dts_process_fn,
            custom_code,
            processed_cache,
            is_custom_build,
        )

    return process_count


def process_header(
    include_path: str, processed_cache: dict[str, str], custom_code: str
) -> tuple[str, int]:
    # print(f"Processing {include_path}...")
    if include_path in processed_cache or not filter_include(
        os.path.basename(include_path)
    ):
        return ("skipped", 0)
    else:
        processed_cache[include_path] = "pending"

    tu_info = TuInfo(include_path)

    all_children_count = process_children(
        tu_info,
        tu_info.all_children,
        should_process_class,
        embind_generate_class,
        ts_generate_class,
        custom_code,
        processed_cache,
    )
    typedefs_count = process_children(
        tu_info,
        tu_info.template_typedefs,
        should_process_template,
        embind_generate_template,
        ts_generate_template,
        custom_code,
        processed_cache,
    )
    enums_count = process_children(
        tu_info,
        tu_info.enums,
        should_process_enum,
        embind_generate_enum,
        ts_generate_enum,
        custom_code,
        processed_cache,
    )
    return ("ok", all_children_count + typedefs_count + enums_count)


def process_sources(custom_code: str = ""):
    manager = multiprocessing.Manager()
    processed_cache = manager.dict()
    ok = 0
    start = time.time()
    targets = OCCT_INCLUDE_FILES
    # targets = ["/occt/src/AIS/AIS_Circle.hxx"]

    args = [
        (header_path, processed_cache, custom_code) for (_, header_path, _) in targets
    ]

    with tqdm(total=len(targets), desc="Generating bindings", unit="file") as pbar:
        with multiprocessing.Pool() as p:
            for status, count in p.starmap(process_header, args):
                pbar.update(count)
                if status == "ok":
                    ok += count
                if status == "skipped":
                    print("uhhh")

    elapsed = time.time() - start
    print(
        f"\nBinding generation done: {ok} generated, (total: {len(targets)}) in {elapsed / 60:.1f}min"
    )


referenceTypeTemplateDefs = """
#include <emscripten/bind.h>
using namespace emscripten;
#include <functional>

template<typename T>
T getReferenceValue(const emscripten::val& v) {
  if(!(v.typeOf().as<std::string>() == "object")) {
    return v.as<T>(allow_raw_pointers());
  } else if(v.typeOf().as<std::string>() == "object" && v.hasOwnProperty("current")) {
    return v["current"].as<T>(allow_raw_pointers());
  }
  throw("unsupported type");
}

template<typename T>
void updateReferenceValue(emscripten::val& v, T& val) {
  if(v.typeOf().as<std::string>() == "object" && v.hasOwnProperty("current")) {
    v.set("current", val);
  }
}

"""


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
