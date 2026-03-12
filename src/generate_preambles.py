#!/usr/bin/python3

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from common import occtBasePath
from filters.pkgs import filter_packages
from tu_info import TuInfo, get_includes

buildDirectory = "/opencascade.js/build"
sourcesDirectory = "/opencascade.js/build/sources"

SOURCE_EXTENSIONS = [".cxx", ".cpp", ".c"]


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
        get_includes(source_path)
        if source_path is not None
        else get_includes(file_path)
    )
    return file_path, includes


def generate_preambles():
    tuInfo = TuInfo("")

    source_files = set()
    for child in tuInfo.all_children:
        if (
            child.extent.start.file is not None
            and child.extent.start.file.name.startswith(occtBasePath)
            and child.location.file is not None
            and filter_packages(
                os.path.basename(os.path.dirname(child.location.file.name))
            )
        ):
            source_files.add(child.extent.start.file.name)

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
