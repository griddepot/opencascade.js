#!/usr/bin/python3

import multiprocessing
import os
import subprocess
import time

from tqdm import tqdm

from common import OCCT_INCLUDE_PATH_ARGS_WITH_3RD_PARTY
from filters.pkgs import filter_packages
from filters.source_files import filter_source_file

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

OCJS_SRC_PATH = "/opencascade.js/build/sources/"
OCJS_PCH_PATH = "/opencascade.js/build/pch/"
OCCT_SRC_PATH = "/occt/src/"


BUILD_MULTITHREADED = os.environ["BUILD_MULTITHREADED"] == "1"


def build_file(file: str):
    relative_file_path = file.replace(OCCT_SRC_PATH, "")
    try:
        os.makedirs(f"{OCJS_SRC_PATH}/{os.path.dirname(relative_file_path)}")
    except OSError:
        pass

    object_path = f"{OCJS_SRC_PATH}/{relative_file_path}.o"

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
        *OCCT_INCLUDE_PATH_ARGS_WITH_3RD_PARTY,
        "-c",
        file,
        "-o",
        object_path,
    ]

    try:
        subprocess.check_call(command)
        return ("ok", relative_file_path)
    except subprocess.CalledProcessError:
        return ("skipped", relative_file_path)


# build_pch.build_pch("/occt/src/AIS/AIS_InteractiveContext.hxx")
# tu = index.parse("/occt/src/AIS/AIS_InteractiveContext.hxx", ["-x", "c++", "-stdlib=libc++", "-Xclang", "-include-pch=/opencascade.js/build/pch/AIS/AIS_InteractiveContext.hxx.pch", *OCCT_INCLUDE_PATH_ARGS], options=cx.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
def build_pch(file: str):
    relative_file_path = file.replace(OCCT_SRC_PATH, "")
    os.makedirs(f"{OCJS_PCH_PATH}/{os.path.dirname(relative_file_path)}", exist_ok=True)

    pch_path = f"{OCJS_PCH_PATH}/{relative_file_path}.pch"

    if os.path.exists(pch_path):
        return ("skipped", relative_file_path)

    command = [
        "emcc",
        "-xc++-header",
        "-flto",
        "-fexceptions",
        "-sDISABLE_EXCEPTION_CATCHING=0",
        "-DIGNORE_NO_ATOMICS=1",
        "-DOCCT_NO_PLUGINS",
        "-frtti",
        "-DHAVE_RAPIDJSON",
        "-Os",
        "-pthread" if BUILD_MULTITHREADED else "",
        *OCCT_INCLUDE_PATH_ARGS_WITH_3RD_PARTY,
        file,
        "-o",
        pch_path,
    ]

    try:
        subprocess.check_call(command)
        return ("ok", relative_file_path)
    except subprocess.CalledProcessError:
        return ("failed", relative_file_path)


allModules: dict[str, list[str]] = {}
for dirpath, dirnames, filenames in os.walk(OCCT_SRC_PATH):
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


def get_build_targets():
    targets = []
    for dirpath, _, filenames in os.walk(OCCT_SRC_PATH):
        packageOrModuleName = os.path.basename(dirpath.replace(OCCT_SRC_PATH, ""))
        if not filter_packages(packageOrModuleName) or not filter_packages(
            getModuleNameByPackageName(packageOrModuleName)
        ):
            continue
        targets.extend(
            [
                f"{dirpath}/{item}"
                for item in filenames
                if filter_source_file(f"{dirpath}/{item}")
            ]
        )
    return targets


if __name__ == "__main__":
    try:
        os.makedirs(OCJS_SRC_PATH)
    except Exception:
        print("Unable to make folder for library base path, exiting.")
        quit(1)

    build_targets = get_build_targets()
    total = len(build_targets)
    print(f"Compiling {total} OCCT source files...")

    ok = failed = skipped = 0
    start = time.time()

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as p:
        for status, path in tqdm(
            p.imap_unordered(build_file, build_targets),
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
