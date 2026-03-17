import os

from filters.includes import filter_include

OCCT_SRC_PATH = "/occt/src/"


def as_include_args(paths: list[str]) -> list[str]:
    return [f"-I{path}" for path in paths]


def get_global_includes() -> tuple[
    list[tuple[str, str, str]], list[str]
]:
    include_files: list[tuple[str, str, str]] = []
    include_paths: list[str] = []
    include_map: dict[str, int] = {}

    for dirpath, _, filenames in os.walk(OCCT_SRC_PATH):
        include_paths.append(dirpath)
        for item in filenames:
            file_path = os.path.join(dirpath, item)  # e.g., /occt/src/AIS/AIS.hxx
            pkg = os.path.basename(dirpath)
            if item.endswith(".hxx") and filter_include(item):
                include_files.append((pkg, file_path, item))
                include_map[file_path] = 1

    return (
        sorted(include_files),
        sorted(include_paths),
    )


(
    OCCT_INCLUDE_FILES,
    OCCT_INCLUDE_PATHS,
) = get_global_includes()

OCCT_INCLUDE_PATH_ARGS = as_include_args(OCCT_INCLUDE_PATHS)

_3RD_PARTY_INCLUDES = [
    "/rapidjson/include",
]

OCCT_INCLUDE_PATHS_WITH_3RD_PARTY = OCCT_INCLUDE_PATHS + _3RD_PARTY_INCLUDES
OCCT_INCLUDE_PATH_ARGS_WITH_3RD_PARTY = as_include_args(
    OCCT_INCLUDE_PATHS_WITH_3RD_PARTY
)

EMSDK_INCLUDES = [
    "/emsdk/upstream/emscripten/system/include/",
    "/usr/lib/gcc/x86_64-linux-gnu/8/include-fixed/",
    "/emsdk/upstream/emscripten/system/lib/libcxx/include/",
    "/emsdk/upstream/emscripten/cache/sysroot/include/",
    f"/emsdk/upstream/lib/clang/{next(os.walk('/emsdk/upstream/lib/clang/'))[1][0]}/include/",
    "/emsdk/upstream/emscripten/system/lib/libcxx/include/__support/newlib/",
]

EMCC_INCLUDE_PATH_ARGS = as_include_args(
    EMSDK_INCLUDES + OCCT_INCLUDE_PATHS_WITH_3RD_PARTY
)

ALL_OCCT_INCLUDE_STATEMENTS = (
    os.linesep.join([f'#include "{header_name}"' for (_, _, header_name) in OCCT_INCLUDE_FILES])
    + os.linesep
)
