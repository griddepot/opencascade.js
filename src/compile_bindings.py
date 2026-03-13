import multiprocessing
import os
import subprocess
import time
from functools import partial

from tqdm import tqdm

from common import (
    OCCT_INCLUDE_PATH_ARGS_WITH_3RD_PARTY,
)

libraryBasePath = "/opencascade.js/build/bindings"

BUILD_MULTITHREADED = os.environ["BUILD_MULTITHREADED"] == "1"


def compile_binding(item):
    if os.path.exists(item + ".o"):
        return ("skipped", item)

    command = [
        "emcc",
        "-flto",
        "-fexceptions",
        "-sDISABLE_EXCEPTION_CATCHING=0",
        "-Wno-deprecated-declarations",
        "-DIGNORE_NO_ATOMICS=1",
        "-DOCCT_NO_PLUGINS",
        "-frtti",
        "-DHAVE_RAPIDJSON",
        "-Os",
        "-pthread" if BUILD_MULTITHREADED else "",
        *OCCT_INCLUDE_PATH_ARGS_WITH_3RD_PARTY,
        "-c",
        item,
        "-o",
        f"{item}.o",
    ]
    try:
        subprocess.check_call(command)
        return ("ok", item)
    except subprocess.CalledProcessError:
        return ("failed", item)


def compileCustomCodeBindings(args):
    filesToBuild = []
    for dirpath, dirnames, filenames in os.walk(libraryBasePath + "/myMain.h"):
        filesToBuild.extend(
            map(
                lambda x: dirpath + "/" + x,
                filter(lambda x: x.endswith(".cpp"), filenames),
            )
        )

    ok = failed = skipped = 0
    start = time.time()

    with multiprocessing.Pool(processes=int(multiprocessing.cpu_count() / 1)) as p:
        for status, path in tqdm(
            p.imap_unordered(
                partial(
                    compile_binding,
                    {
                        "threading": args.threading,
                    },
                ),
                sorted(filesToBuild),
            ),
            total=total,
            desc="Compiling bindings",
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
        f"\nBinding compilation done: {ok} compiled, {failed} failed, {skipped} skipped (total: {total}) in {elapsed / 60:.1f}min"
    )


if __name__ == "__main__":
    build_targets = []
    for dirpath, _, filenames in os.walk(libraryBasePath):
        build_targets.extend(
            [f"{dirpath}/{file}" for file in filenames if file.endswith(".cpp")]
        )

    build_targets.sort()
    total = len(build_targets)
    print(f"Compiling {total} binding files...")

    ok = failed = skipped = 0
    start = time.time()

    with multiprocessing.Pool(processes=int(multiprocessing.cpu_count())) as p:
        for status, path in tqdm(
            p.imap_unordered(
                compile_binding,
                build_targets,
            ),
            total=total,
            desc="Compiling bindings",
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
        f"\nBinding compilation done: {ok} compiled, {failed} failed, {skipped} skipped (total: {total}) in {elapsed / 60:.1f}min"
    )
