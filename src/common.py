from filters.includes import filter_include
import os

occtBasePath = "/occt/src/"


def getGlobalIncludes() -> tuple[list[str], list[str]]:
    includeFiles = list()
    additionalIncludePaths = list()
    for dirpath, dirnames, filenames in os.walk(occtBasePath):
        additionalIncludePaths.append(str(dirpath))
        for item in filenames:
            if filter_include(item):
                includeFiles.append(str(os.path.join(dirpath, item)))
    return [includeFiles, additionalIncludePaths]


[ocIncludeFiles, ocIncludePaths] = getGlobalIncludes()

additionalIncludePaths = [
    "/rapidjson/include",
]

includePathArgs = (
    list(dict.fromkeys(map(lambda x: "-I" + x, ocIncludePaths)))
    + list(
        map(
            lambda x: "-I" + x,
            [
                "/emsdk/upstream/emscripten/system/include/",
                "/usr/lib/gcc/x86_64-linux-gnu/8/include-fixed/",
                "/emsdk/upstream/emscripten/system/lib/libcxx/include/",
                "/emsdk/upstream/lib/clang/"
                + next(os.walk("/emsdk/upstream/lib/clang/"))[1][0]
                + "/include/",
                "/emsdk/upstream/emscripten/system/lib/libcxx/include/__support/newlib/",
            ],
        )
    )
    + list(map(lambda x: "-I" + x, ocIncludePaths + additionalIncludePaths))
)

ocIncludeStatements = os.linesep.join(
    map(
        lambda x: '#include "' + os.path.basename(x) + '"', list(sorted(ocIncludeFiles))
    )
)
