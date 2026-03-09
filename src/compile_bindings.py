import multiprocessing
import os
import subprocess
import time
from argparse import ArgumentParser
from functools import partial

from tqdm import tqdm

from common import additionalIncludePaths, ocIncludePaths

libraryBasePath = "/opencascade.js/build/bindings"


def buildOneFile(args, item):
    if os.path.exists(item + ".o"):
        return ("skipped", item)

    command = [
        "emcc",
        "-flto",
        "-fexceptions",
        "-sDISABLE_EXCEPTION_CATCHING=0",
        "-DIGNORE_NO_ATOMICS=1",
        "-DOCCT_NO_PLUGINS",
        "-frtti",
        "-DHAVE_RAPIDJSON",
        "-Os" if args["release"] == "true" else "-O0",
        # "-g3",
        # "-gsource-map",
        # "--source-map-base=http://localhost:8080",
        "-pthread" if args["threading"] == "multi-threaded" else "",
        *list(map(lambda x: "-I" + x, ocIncludePaths + additionalIncludePaths)),
        "-c",
        item,
    ]
    try:
        subprocess.check_call(
            [
                *command,
                "-o",
                item + ".o",
            ]
        )
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

    with multiprocessing.Pool(processes=int(multiprocessing.cpu_count() / 1)) as p:
        p.map(partial(buildOneFile, args), sorted(filesToBuild))


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

    filesToBuild = []
    for dirpath, dirnames, filenames in os.walk(libraryBasePath):
        filesToBuild.extend(
            map(
                lambda x: dirpath + "/" + x,
                filter(lambda x: x.endswith(".cpp"), filenames),
            )
        )
        
    total = len(filesToBuild)
    print(f"Compiling {total} binding files...")

    ok = failed = skipped = 0
    start = time.time()

    with multiprocessing.Pool(processes=int(multiprocessing.cpu_count() / 1)) as p:
        for status, path in tqdm(
            p.imap_unordered(
                partial(
                    buildOneFile,
                    {
                        "threading": args.threading,
                        "release": args.release,
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
    print(f"\nBinding compilation done: {ok} compiled, {failed} failed, {skipped} skipped (total: {total}) in {elapsed/60:.1f}min")
