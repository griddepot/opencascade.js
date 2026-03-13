import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import clang.cindex as cx
from tqdm import tqdm

from common import OCCT_INCLUDE_FILES, OCCT_INCLUDE_PATH_ARGS
from filters.includes import filter_include
from filters.pkgs import filter_packages

buildDirectory = "/opencascade.js/build"

SOURCE_EXTENSIONS = [".cxx", ".cpp", ".c"]


def get_include_name(file_inclusion: cx.FileInclusion):
    return os.path.basename(file_inclusion.include.name)


def get_one_preamble(path: str):
    """Get the preamble from an OCCT source/header file"""
    index = cx.Index.create()
    tu = index.parse(
        path,
        ["-x", "c++", "-stdlib=libc++", *OCCT_INCLUDE_PATH_ARGS],
        options=cx.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES,
    )

    default_include = os.path.basename(path).replace(".cxx", ".hxx")
    valid_includes = list(
        dict.fromkeys(
            [
                f'#include "{get_include_name(n)}"'
                for n in tu.get_includes()
                if n.depth == 1
                and n.include.name.startswith("/occt")
                and filter_include(get_include_name(n))
            ]
            + [f'#include "{default_include}"']
        )
    )

    index = None
    tu = None
    return os.linesep.join(valid_includes) + os.linesep


def get_compiled_source_path(header_path: str) -> str | None:
    """Check if a compiled source file exists for the given header path."""
    base, _ = os.path.splitext(header_path)
    for ext in SOURCE_EXTENSIONS:
        candidate = base + ext
        if os.path.exists(candidate):
            return candidate
    return None


def generate_preamble(file_path: str) -> tuple[str, str]:
    source_path = get_compiled_source_path(file_path)
    includes = (
        get_one_preamble(source_path)
        if source_path is not None
        else get_one_preamble(file_path)
    )
    return file_path, includes


def generate_preambles():

    source_files = set()
    for file in OCCT_INCLUDE_FILES:
        if filter_packages(os.path.basename(os.path.dirname(file))):
            source_files.add(file)

    sorted_files = sorted(source_files)
    preambles = {}

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(generate_preamble, fp): fp for fp in sorted_files}
        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Generating preambles"
        ):
            file_path, preamble = future.result()
            preambles[file_path] = preamble

    output_path = os.path.join(buildDirectory, "preambles.json")
    os.makedirs(buildDirectory, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(preambles, f)

    print(f"Generated {len(preambles)} preambles")


if __name__ == "__main__":
    generate_preambles()
