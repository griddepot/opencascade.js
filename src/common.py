import os

from filters.includes import filter_include

OCCT_BASE_PATH = "/occt/src/"


def as_include_args(paths: list[str]) -> list[str]:
    return [f"-I{path}" for path in paths]


def get_global_includes() -> tuple[list[str], list[str]]:
    includeFiles = list()
    additionalIncludePaths = list()
    for dirpath, _, filenames in os.walk(OCCT_BASE_PATH):
        additionalIncludePaths.append(str(dirpath))
        for item in filenames:
            if filter_include(item):
                includeFiles.append(str(os.path.join(dirpath, item)))
    return [includeFiles, additionalIncludePaths]


[OCCT_INCLUDE_FILES, OCCT_INCLUDE_PATHS] = get_global_includes()

OCCT_INCLUDE_PATH_ARGS = as_include_args(OCCT_INCLUDE_PATHS)

_3RD_PARTY_INCLUDES = [
    "/rapidjson/include",
]

OCCT_INCLUDE_PATHS_WITH_3RD_PARTY = OCCT_INCLUDE_PATHS + _3RD_PARTY_INCLUDES

EMSDK_INCLUDES = [
    "/emsdk/upstream/emscripten/system/include/",
    "/usr/lib/gcc/x86_64-linux-gnu/8/include-fixed/",
    "/emsdk/upstream/emscripten/system/lib/libcxx/include/",
    f"/emsdk/upstream/lib/clang/{next(os.walk('/emsdk/upstream/lib/clang/'))[1][0]}/include/",
    "/emsdk/upstream/emscripten/system/lib/libcxx/include/__support/newlib/",
]

EMCC_INCLUDE_PATH_ARGS = (
    as_include_args(EMSDK_INCLUDES) + as_include_args(OCCT_INCLUDE_PATHS_WITH_3RD_PARTY)
)

ALL_OCCT_INCLUDE_STATEMENTS = (
    os.linesep.join([f'#include "{os.path.basename(x)}"' for x in OCCT_INCLUDE_FILES])
    + os.linesep
)
