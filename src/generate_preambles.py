import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import clang.cindex as cx
from tqdm import tqdm

from common import OCCT_INCLUDE_FILES, OCCT_INCLUDE_PATH_ARGS, resolve_header_source
from filters.includes import filter_include
from filters.pkgs import filter_packages

buildDirectory = "/opencascade.js/build"


def get_include_name(file_inclusion: cx.FileInclusion):
    return os.path.basename(file_inclusion.include.name)


def generate_preamble(file_path: str) -> tuple[str, str]:
    """Get the preamble from an OCCT source/header file"""
    
    source_path = resolve_header_source(file_path)
    index = cx.Index.create()
    tu = index.parse(
        source_path,
        ["-x", "c++", "-stdlib=libc++", *OCCT_INCLUDE_PATH_ARGS],
        options=cx.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES,
    )

    default_include = os.path.basename(source_path).replace(".cxx", ".hxx")
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
    return (source_path, os.linesep.join(valid_includes) + os.linesep)


def generate_preambles():

    source_files = sorted(
        {
            header
            for header in OCCT_INCLUDE_FILES
            if filter_packages(os.path.basename(os.path.dirname(header)))
        }
    )

    preambles: dict[str, str] = {}

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(generate_preamble, fp): fp for fp in source_files}
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
