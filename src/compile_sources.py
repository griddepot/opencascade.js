#!/usr/bin/python3

import multiprocessing
import os
import subprocess
import time
from argparse import ArgumentParser

from tqdm import tqdm

from filters.pkgs import filter_packages
from filters.source_files import filter_source_file

lib_base_path = "/opencascade.js/build/sources"

# Potentially problematic packages, when used with dynamic linking
# These files contain function pointer definitions and header files and are therefore likely to cause problems.
# https://github.com/emscripten-core/emscripten/issues/13241
# "AdvApp2Var"
# "BRepGProp"
# "BRepMesh"
# "BSplSLib"
# "CPnts"
# "DDF"
# "Draw"
# "Graphic3d"
# "IFSelect"
# "Interface"
# "MoniTool"
# "NCollection"
# "OpenGl"
# "OSD"
# "ShapeProcess"
# "Standard"
# "StdObjMgt"
# "TDF

source_base_path = "/occt/src/"

include_paths = []
include_paths.extend(
    [
        "/rapidjson/include",
    ]
)
for dirpath, dirnames, filenames in os.walk(os.path.join(source_base_path)):
    include_paths.append(dirpath)

INCLUDE_ARGS = [f"-I{p}" for p in include_paths]

BUILD_MULTITHREADED = os.environ["BUILD_MULTITHREADED"] == "1"


def build_file(file: str):
    relative_file_path = file.replace(source_base_path, "")
    try:
        os.makedirs(f"{lib_base_path}/{os.path.dirname(relative_file_path)}")
    except OSError:
        pass

    object_path = f"{lib_base_path}/{relative_file_path}.o"

    if os.path.exists(object_path):
        return ("skipped", relative_file_path)

    command = [
        "emcc",
        "-flto",
        "-fexceptions",
        "-sDISABLE_EXCEPTION_CATCHING=0",
        "-DIGNORE_NO_ATOMICS=1",
        "-DOCCT_NO_PLUGINS",
        "-frtti",
        "-DHAVE_RAPIDJSON",
        "-Os",
        "-pthread" if BUILD_MULTITHREADED else "",
        *INCLUDE_ARGS,
        "-c",
        file,
    ]

    try:
        subprocess.check_call(
            [
                *command,
                "-o",
                object_path,
            ]
        )
        return ("ok", relative_file_path)
    except subprocess.CalledProcessError:
        return ("skipped", relative_file_path)


allModules = {}
for dirpath, dirnames, filenames in os.walk(source_base_path):
    if not any(x for x in filenames if x == "PACKAGES"):
        continue
    allModules[os.path.basename(dirpath)] = []
    with open(dirpath + "/PACKAGES", "r") as a_file:
        for package in a_file:
            packageName = package.strip()
            allModules[os.path.basename(dirpath)].append(packageName)


def getModuleNameByPackageName(inputPackageName):
    for moduleName in allModules:
        for package in allModules[moduleName]:
            packageName = package.strip()
            if packageName == inputPackageName:
                return moduleName
    return ""


filesToBuild = []
for dirpath, dirnames, filenames in os.walk(source_base_path):
    packageOrModuleName = os.path.basename(dirpath.replace(source_base_path, ""))
    for item in filenames:
        if not filter_packages(packageOrModuleName) or not filter_packages(
            getModuleNameByPackageName(packageOrModuleName)
        ):
            continue
        if filter_source_file(dirpath + "/" + item):
            filesToBuild.append(dirpath + "/" + item)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        dest="threading",
        choices=["single-threaded", "multi-threaded"],
        help="Build in single vs. multi-threaded mode",
    )
    parser.add_argument(
        dest="release",
        choices=["true", "false"],
        help='Whether to build for release. A value of "false" will build without optimizations (-O0).',
    )
    args = parser.parse_args()

    try:
        os.makedirs(lib_base_path)
    except Exception:
        print("Unable to make folder for library base path, exiting.")
        quit(1)

    def build_fn(x):
        return build_file(
            x,
        )

    total = len(filesToBuild)
    print(f"Compiling {total} OCCT source files...")

    ok = failed = skipped = 0
    start = time.time()

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as p:
        for status, path in tqdm(
            p.imap_unordered(build_fn, filesToBuild),
            total=total,
            desc="Compiling sources",
            unit="file",
        ):
            if status == "ok":
                ok += 1
            elif status == "failed":
                failed += 1
            else:
                skipped += 1

    elapsed = time.time() - start
    print(
        f"\nSource compilation done: {ok} compiled, {failed} failed, {skipped} skipped (total: {total}) in {elapsed / 60:.1f}min"
    )
