from typing import Callable
import logging
import re
from abc import abstractmethod

import clang.cindex as cx

from clang_utils import TuInfo, is_public_ctor, is_public_base_specifier
from filters.method_or_property import filter_method_or_property
from wasm_gen.common import (
    SkipException,
    getMethodOverloadPostfix,
    isAbstractClass,
)

logger = logging.getLogger()


def merge(sep: str, *strings: str) -> str:
    return sep.join(strings)


def pick(condition: bool, strTrue: str, strFalse: str) -> str:
    return strTrue if condition else strFalse


def pickWrap(
    condition: bool, wrapStart: tuple[str, str], center: str, wrapEnd: tuple[str, str]
) -> str:
    return (
        (wrapStart[0] if condition else wrapStart[1])
        + center
        + (wrapEnd[0] if condition else wrapEnd[1])
    )


def indent(level: int) -> str:
    return " " * level * 2


builtInTypes = [  # according to https://en.cppreference.com/w/cpp/language/types
    # Integer types
    "int",
    "short",
    "short int",
    "signed short",
    "signed short int",
    "unsigned short",
    "unsigned short int",
    "int",
    "signed",
    "signed int",
    "unsigned",
    "unsigned int",
    "long",
    "long int",
    "signed long",
    "signed long int",
    "unsigned long",
    "unsigned long int",
    "long long",
    "long long int",
    "signed long long",
    "signed long long int",
    "unsigned long long",
    "unsigned long long int",
    # Boolean type
    "bool",
    # Character types
    "char",
    "signed char",
    "unsigned char",
    "wchar_t",
    "char16_t",
    "char32_t",
    "char8_t",
    # Floating point types
    "float",
    "double",
    "long double",
]

cStringTypes = [
    "const char *",
    "const char *const",
    "char *",
    "char *const",
]


def isCString(type: cx.Type) -> bool:
    return type.get_canonical().spelling in cStringTypes


def getClassTypeName(
    class_node: cx.Cursor, template_decl: cx.Cursor | None = None
) -> str:
    return template_decl.spelling if template_decl is not None else class_node.spelling


class Bindings:
    def __init__(self, tu_info: TuInfo):
        self.tu_info = tu_info

    @abstractmethod
    def processSimpleConstructor(self, class_node: cx.Cursor):
        pass

    @abstractmethod
    def processMethodOrProperty(
        self,
        class_node: cx.Cursor,
        method: cx.Cursor,
        template_decl: cx.Cursor | None = None,
        template_args: dict[str, cx.Type] | None = None,
    ) -> str:
        pass

    @abstractmethod
    def processFinalizeClass(self) -> str:
        pass

    @abstractmethod
    def processOverloadedConstructors(
        self,
        class_node: cx.Cursor,
        children: list[cx.Cursor] | None = None,
        template_decl: cx.Cursor | None = None,
        template_args: dict[str, cx.Type] | None = None,
    ) -> str:
        pass

    def getTypedefedTemplateTypeAsString(
        self,
        type_spelling: str,
        template_decl: cx.Cursor | None = None,
        template_args: dict[str, cx.Type] | None = None,
    ) -> str:
        if template_decl is None:
            tud = self.tu_info.typedef_underlying_dict
            if type_spelling in tud:
                typedefType = tud[type_spelling].spelling
            else:
                typedefType = None
        else:
            templateType = self.replacetemplate_args(type_spelling, template_args)
            rawTemplateType = templateType.replace("&", "").replace("const", "").strip()
            ttud = self.tu_info.template_typedef_underlying_dict
            oc_rawTemplateType = "opencascade::" + rawTemplateType
            if rawTemplateType in ttud:
                rawTypedefType = ttud[rawTemplateType].spelling
            elif oc_rawTemplateType in ttud:
                rawTypedefType = ttud[oc_rawTemplateType].spelling
            else:
                rawTypedefType = rawTemplateType
            typedefType = templateType.replace(rawTemplateType, rawTypedefType)
        result = type_spelling if typedefType is None else typedefType
        return result

    def replacetemplate_args(
        self, spelling: str, template_args: dict[str, cx.Type] | None = None
    ) -> str:
        newString = spelling
        if template_args is None:
            return newString
        for key in template_args:
            p = re.compile("(\\W+|^)" + key + "(\\W|$)")
            newString = p.sub("\\1" + template_args[key].spelling + "\\2", newString)
        return newString

    def process_class(
        self,
        class_node: cx.Cursor,
        template_decl: cx.Cursor | None = None,
        template_args: dict[str, cx.Type] | None = None,
    ) -> str:
        output = ""
        isAbstract = isAbstractClass(class_node, self.tu_info.class_dict)
        if not isAbstract:
            output += self.processSimpleConstructor(class_node)
        for method in class_node.get_children():
            if not filter_method_or_property(class_node, method):
                continue
            try:
                output += self.processMethodOrProperty(
                    class_node, method, template_decl, template_args
                )
            except SkipException as e:
                pass
                # print(str(e))
        output += self.processFinalizeClass()
        if not isAbstract:
            try:
                output += self.processOverloadedConstructors(
                    class_node, None, template_decl, template_args
                )
            except SkipException as e:
                pass
                # print(str(e))
        return output


class EmbindBindings(Bindings):
    def __init__(self, tu_info: TuInfo):
        super().__init__(tu_info)

    def process_class(
        self,
        class_node: cx.Cursor,
        template_decl: cx.Cursor | None = None,
        template_args: dict[str, cx.Type] | None = None,
    ) -> str:
        output = ""
        className = getClassTypeName(class_node, template_decl)
        if className == "":
            className = class_node.type.spelling

        baseSpec = [n for n in class_node.get_children() if is_public_base_specifier(n)]

        baseClassBinding = (
            f", base<{baseSpec[0].type.spelling}>" if len(baseSpec) > 0 else ""
        )

        output += f"EMSCRIPTEN_BINDINGS({class_node.spelling if template_decl is None else template_decl.spelling}) {{\n"
        output += f"  class_<{className}{baseClassBinding}>(" + className + '")\n'

        output += super().process_class(class_node, template_decl, template_args)

        output += "}\n\n"

        # Epilog
        nonPublicDestructor = any(
            x.kind == cx.CursorKind.DESTRUCTOR
            and not x.access_specifier == cx.AccessSpecifier.PUBLIC
            for x in class_node.get_children()
        )
        placementDelete = (
            next(
                (
                    x
                    for x in class_node.get_children()
                    if x.spelling == "operator delete"
                    and len(list(x.get_arguments())) == 2
                ),
                None,
            )
            is not None
        )
        if nonPublicDestructor or placementDelete:
            output += f"namespace emscripten {{ namespace internal {{ template<> void raw_destructor<{class_node.spelling}>({class_node.spelling}* ptr) {{ /* do nothing */ }} }} }}\n"
        return output

    def processFinalizeClass(self) -> str:
        return "  ;\n"

    def processSimpleConstructor(self, class_node: cx.Cursor) -> str:
        output = ""
        children = list(class_node.get_children())
        constructors = [x for x in children if x.kind == cx.CursorKind.CONSTRUCTOR]

        if len(constructors) == 0:
            output += "    .constructor<>()\n"
            return output
        publicConstructors = [
            x
            for x in children
            if x.kind == cx.CursorKind.CONSTRUCTOR
            and x.access_specifier == cx.AccessSpecifier.PUBLIC
        ]

        if len(publicConstructors) == 0 or len(publicConstructors) > 1:
            return output
        standard_ctor = publicConstructors[0]
        if not standard_ctor:
            return output

        argTypesBindings = ", ".join(
            [x.type.spelling for x in standard_ctor.get_arguments()]
        )

        output += f"    .constructor<{argTypesBindings}>()\n"
        return output

    def getSingleArgumentBinding(
        self,
        argNames=True,
        is_ctor=False,
        template_decl: cx.Cursor | None = None,
        template_args: dict[str, cx.Type] | None = None,
    ) -> Callable[[cx.Cursor], tuple[str, bool]]:
        def f(arg: cx.Cursor) -> tuple[str, bool]:
            argChildren = list(arg.get_children())
            argBinding = ""
            hasDefaultValue = any(x.spelling == "=" for x in list(arg.get_tokens()))
            isArray = (
                not hasDefaultValue
                and len(argChildren) > 1
                and argChildren[1].kind == cx.CursorKind.INTEGER_LITERAL
            )
            changed = False
            if isArray:
                const = (
                    "const " if list(arg.get_tokens())[0].spelling == "const" else ""
                )
                arrayCount = list(argChildren[1].get_tokens())[0].spelling
                argBinding = f"{const}{argChildren[0].type.spelling} (&{arg.spelling if argNames else ''})[{arrayCount}]"
                changed = True
            else:
                typename = self.getTypedefedTemplateTypeAsString(
                    arg.type.spelling, template_decl, template_args
                )
                if arg.type.kind == cx.TypeKind.LVALUEREFERENCE:
                    tokenList = list(arg.get_tokens())
                    isConstRef = len(tokenList) > 0 and tokenList[0].spelling == "const"
                    if not isConstRef:
                        if typename[-2] == "*" or "".join(
                            typename.rsplit("&", 1)
                        ).strip() in [
                            "Standard_Boolean",
                            "Standard_Real",
                            "Standard_Integer",
                        ]:  # types that can be copied
                            typename = "".join(typename.rsplit("&", 1))
                            changed = True
                        else:
                            if is_ctor:
                                typename = typename
                                changed = True
                            else:
                                typename = "const " + typename
                                changed = True
                argBinding = typename + ((" " + arg.spelling) if argNames else "")
            return (argBinding, changed)

        return f

    def processMethodOrProperty(
        self,
        class_node: cx.Cursor,
        method: cx.Cursor,
        template_decl: cx.Cursor | None = None,
        template_args: dict[str, cx.Type] | None = None,
    ) -> str:
        output = ""
        className = getClassTypeName(class_node, template_decl)
        if className == "":
            className = class_node.type.spelling
        if (
            method.access_specifier == cx.AccessSpecifier.PUBLIC
            and method.kind == cx.CursorKind.CXX_METHOD
            and not method.spelling.startswith("operator")
        ):
            [overloadPostfix, numOverloads] = getMethodOverloadPostfix(
                class_node, method
            )

            def needsWrapper(arg_type: cx.Type) -> bool:
                return (
                    arg_type.kind == cx.TypeKind.LVALUEREFERENCE
                    and (
                        arg_type.get_pointee().get_canonical().spelling in builtInTypes
                        or arg_type.get_pointee().kind == cx.TypeKind.ENUM
                        or arg_type.get_pointee().kind == cx.TypeKind.POINTER
                        or (
                            class_node.kind == cx.CursorKind.CLASS_TEMPLATE
                            and template_args is not None
                            and arg_type.get_pointee().spelling in template_args
                            and template_args[arg_type.get_pointee().spelling]
                            .get_canonical()
                            .spelling
                            in builtInTypes
                        )
                    )
                    or (
                        arg_type.get_canonical().kind == cx.TypeKind.POINTER
                        and isCString(arg_type)
                    )
                )

            args = list(method.get_arguments())
            argsNeedingWrapper = [
                needsWrapper(arg.type) for arg in args if needsWrapper(arg.type)
            ]
            returnNeedsWrapper = needsWrapper(method.result_type)
            if any(argsNeedingWrapper) or returnNeedsWrapper:

                def replacetemplate_args(arg_idx: int):
                    if (
                        template_args is not None
                        and args[arg_idx]
                        .type.get_pointee()
                        .spelling.replace("const ", "")
                        in template_args
                    ):
                        return args[arg_idx].type.spelling.replace(
                            args[arg_idx]
                            .type.get_pointee()
                            .spelling.replace("const ", ""),
                            template_args[
                                args[arg_idx]
                                .type.get_pointee()
                                .spelling.replace("const ", "")
                            ].spelling,
                        )
                    else:
                        return args[arg_idx].type.spelling

                def getArgName(arg_idx: int) -> str:
                    return pick(
                        not args[arg_idx].spelling == "",
                        args[arg_idx].spelling,
                        f"argNo{str(arg_idx)}",
                    )

                def getArgTypeName(type: cx.Type) -> str:
                    if (
                        template_args is not None
                        and type.get_pointee().spelling.replace("const ", "")
                        in template_args
                    ):
                        return type.get_pointee().spelling.replace(
                            type.get_pointee().spelling.replace("const ", ""),
                            template_args[
                                type.get_pointee().spelling.replace("const ", "")
                            ].spelling,
                        )
                    else:
                        return type.get_pointee().spelling

                classTypeName = getClassTypeName(class_node, template_decl)
                wrappedParamTypes = merge(
                    ", ",
                    *map(
                        lambda x: pick(
                            x[1], "emscripten::val", replacetemplate_args(x[0])
                        ),
                        enumerate(argsNeedingWrapper),
                    ),
                )
                wrappedParamTypesAndNames = merge(
                    ", ",
                    *[
                        pick(
                            condition,
                            f"emscripten::val {getArgName(arg_idx)}",
                            f"{replacetemplate_args(arg_idx)} {getArgName(arg_idx)}",
                        )
                        for arg_idx, condition in enumerate(argsNeedingWrapper)
                    ],
                )

                def generateGetReferenceValue(x: tuple[int, bool]) -> str:
                    if x[1] and not isCString(args[x[0]].type):
                        return merge(
                            "",
                            indent(4),
                            "auto ref_",
                            pick(
                                not args[x[0]].spelling == "",
                                args[x[0]].spelling,
                                f"argNo{str(x[0])}",
                            ),
                            f" = getReferenceValue<{getArgTypeName(args[x[0]].type)}>({getArgName(x[0])});\n",
                        )
                    else:
                        return ""

                def generateUpdateReferenceValue(x: tuple[int, bool]) -> str:
                    if x[1] and not isCString(args[x[0]].type):
                        return f"{indent(4)}updateReferenceValue<{getArgTypeName(args[x[0]].type)}>({getArgName(x[0])}, ref_{getArgName(x[0])});\n"
                    else:
                        return ""

                def generateInvocationArgs(x: tuple[int, bool]) -> str:
                    if x[1]:
                        if not isCString(args[x[0]].type):
                            return f"ref_{getArgName(x[0])}"
                        else:
                            if (
                                not args[x[0]]
                                .type.get_canonical()
                                .get_pointee()
                                .is_const_qualified()
                                or args[x[0]].type.is_const_qualified()
                            ):
                                return f"{getArgName(x[0])}.isNull() ? nullptr : strdup({getArgName(x[0])}.as<std::string>().c_str())"
                            else:
                                return f"{getArgName(x[0])}.isNull() ? nullptr : {getArgName(x[0])}.as<std::string>().c_str()"
                    else:
                        return getArgName(x[0])

                resultTypeSpelling = pick(
                    returnNeedsWrapper,
                    "emscripten::val",
                    self.getTypedefedTemplateTypeAsString(
                        method.result_type.spelling, template_decl, template_args
                    ),
                )
                functionBindingHead = merge(
                    "",
                    "\n",
                    indent(3),
                    pickWrap(
                        not method.is_static_method(),
                        (
                            f"std::function<{resultTypeSpelling}(",
                            f"(({resultTypeSpelling} (*)(",
                        ),
                        merge(
                            "",
                            pick(
                                not method.is_static_method(), f"{classTypeName}&", ""
                            ),
                            pick(
                                not method.is_static_method() and len(args) > 0,
                                ", ",
                                "",
                            ),
                            wrappedParamTypes,
                        ),
                        (")>(", "))"),
                    ),
                    merge(
                        "",
                        "[](",
                        pick(
                            not method.is_static_method(), f"{classTypeName}& that", ""
                        ),
                        pick(not method.is_static_method() and len(args) > 0, ", ", ""),
                        wrappedParamTypesAndNames,
                        ")",
                    ),
                    f" -> {resultTypeSpelling} {{\n",
                    merge(
                        "",
                        *[
                            generateGetReferenceValue(x)
                            for x in enumerate(argsNeedingWrapper)
                        ],
                    ),
                )
                functionBindingBody = merge(
                    "",
                    indent(4),
                    pick(
                        not method.result_type.spelling == "void",
                        merge(
                            "",
                            pick(
                                not isCString(method.result_type)
                                and (
                                    method.result_type.is_const_qualified()
                                    or method.result_type.get_pointee().is_const_qualified()
                                ),
                                "const ",
                                "",
                            ),
                            "auto",
                            pick(
                                not isCString(method.result_type)
                                and method.result_type.kind
                                == cx.TypeKind.LVALUEREFERENCE,
                                "& ",
                                " ",
                            ),
                            "ret = ",
                        ),
                        "",
                    ),
                    merge(
                        "",
                        pick(
                            not method.is_static_method(),
                            "that.",
                            f"{class_node.spelling}::",
                        ),
                        f"{method.spelling}({
                            merge(
                                ', ',
                                *[
                                    generateInvocationArgs(x)
                                    for x in enumerate(argsNeedingWrapper)
                                ],
                            )
                        })",
                    ),
                    ";\n",
                    merge(
                        "",
                        *[
                            generateUpdateReferenceValue(x)
                            for x in enumerate(argsNeedingWrapper)
                        ],
                    ),
                    pick(
                        method.result_type.spelling == "void",
                        "",
                        pick(
                            returnNeedsWrapper,
                            pick(
                                method.result_type.kind == cx.TypeKind.POINTER,
                                merge(
                                    "",
                                    indent(4),
                                    "return ret == nullptr ? emscripten::val::null() : emscripten::val(static_cast<",
                                    pick(
                                        isCString(method.result_type),
                                        "std::string",
                                        self.getTypedefedTemplateTypeAsString(
                                            method.result_type.spelling,
                                            template_decl,
                                            template_args,
                                        ),
                                    ),
                                    ">(ret));\n",
                                ),
                                f"{indent(4)}return emscripten::val(ret);\n",
                            ),
                            f"{indent(4)}return ret;\n",
                        ),
                    ),
                )
                functionBinding = merge(
                    "",
                    functionBindingHead,
                    functionBindingBody,
                    f"{indent(3)}}}\n",
                    f"{indent(2)})",
                )
            else:
                if numOverloads == 1:
                    functionBinding = " &" + className + "::" + method.spelling
                else:
                    functionBinding = merge(
                        "",
                        " select_overload<",
                        self.getTypedefedTemplateTypeAsString(
                            method.result_type.spelling, template_decl, template_args
                        ),
                        f"({
                            merge(
                                ', ',
                                *map(
                                    lambda x: self.getSingleArgumentBinding(
                                        True, True, template_decl, template_args
                                    )(x)[0],
                                    list(method.get_arguments()),
                                ),
                            )
                        })",
                        pick(method.is_const_method(), "const", ""),
                        pick(
                            not method.is_static_method(),
                            f", {getClassTypeName(class_node, template_decl)}",
                            "",
                        ),
                        f">(&{className}::{method.spelling})",
                    )

            if method.is_static_method():
                functionCommand = "class_function"
            else:
                functionCommand = "function"

            output += f'{indent(2)}.{functionCommand}("{method.spelling}{overloadPostfix}",{functionBinding}, allow_raw_pointers())\n'
        if (
            method.access_specifier == cx.AccessSpecifier.PUBLIC
            and method.kind == cx.CursorKind.FIELD_DECL
        ):
            if method.type.kind == cx.TypeKind.CONSTANTARRAY:
                pass
                # print(
                #     "Cannot handle array properties, skipping "
                #     + className
                #     + "::"
                #     + method.spelling
                # )
            elif not method.type.get_pointee().kind == cx.TypeKind.INVALID:
                pass
                # print(
                #     "Cannot handle pointer properties, skipping "
                #     + className
                #     + "::"
                #     + method.spelling
                # )
            else:
                output += f'{indent(2)}.property("{method.spelling}", &{className}::{method.spelling})\n'
        return output

    def processOverloadedConstructors(
        self,
        class_node: cx.Cursor,
        children=None,
        template_decl: cx.Cursor | None = None,
        template_args: dict[str, cx.Type] | None = None,
    ):
        output = ""
        if children is None:
            children = list(class_node.get_children())
        constructors = list(filter(is_public_ctor, children))

        if len(constructors) == 1:
            return output
        constructorBindings = ""
        allOverloads = list(filter(is_public_ctor, children))
        if len(allOverloads) == 1:
            raise Exception("Something weird happened")
        for constructor in [
            x for x in constructors if filter_method_or_property(class_node, x)
        ]:
            overloadPostfix = (
                ""
                if (not len(allOverloads) > 1)
                else "_" + str(allOverloads.index(constructor) + 1)
            )

            args = ", ".join(
                list(
                    map(
                        lambda x: (
                            ("std::string " + x.spelling)
                            if isCString(x.type)
                            else self.getSingleArgumentBinding(
                                True, True, template_decl, template_args
                            )(x)[0]
                        ),
                        constructor.get_arguments(),
                    )
                )
            )
            argNames = ", ".join(
                list(
                    ((x.spelling + ".c_str()") if isCString(x.type) else x.spelling)
                    for x in constructor.get_arguments()
                )
            )
            argTypes = ", ".join(
                list(
                    map(
                        lambda x: (
                            "std::string"
                            if isCString(x.type)
                            else self.getSingleArgumentBinding(
                                False, True, template_decl, template_args
                            )(x)[0]
                        ),
                        constructor.get_arguments(),
                    )
                )
            )

            name = getClassTypeName(class_node, template_decl)
            constructorBindings += (
                f"    struct {name}{overloadPostfix} : public {name} {{\n"
            )
            constructorBindings += (
                f"      {name}{overloadPostfix}({args}) : {name}({argNames}) {{}}\n"
            )
            constructorBindings += "    };\n"
            constructorBindings += (
                f"    class_<{name}{overloadPostfix}, base<{name}>({argNames}) {{}}\n"
            )
            constructorBindings += "    };\n"
            constructorBindings += (
                f"    class_<{name}{overloadPostfix}, base<{name}>({argNames}) {{}}\n"
            )
            constructorBindings += "      .constructor<" + argTypes + ">()\n"
            constructorBindings += "    ;\n"

        output += constructorBindings
        return output

    def process_enum(self, theEnum) -> str:
        output = f"EMSCRIPTEN_BINDINGS({theEnum.spelling}) {{\n"

        bindingsOutput = f'  enum_<{theEnum.spelling}>("{theEnum.spelling}")\n'
        enumChildren = list(theEnum.get_children())
        prefix = (theEnum.spelling + "::") if theEnum.is_scoped_enum() else ""
        for enumChild in enumChildren:
            bindingsOutput += (
                f'    .value("{enumChild.spelling}", {prefix}{enumChild.spelling})\n'
            )
        bindingsOutput += "  ;\n"
        output += bindingsOutput

        output += "}\n\n"
        return output


class TypescriptBindings(Bindings):
    def __init__(self, tuInfo):
        super().__init__(tuInfo)
        self.imports = {}

        self.exports = []

    def process_class(
        self,
        class_node: cx.Cursor,
        template_decl: cx.Cursor | None = None,
        template_args: dict[str, cx.Type] | None = None,
    ) -> str:
        output = ""
        baseSpec = [n for n in class_node.get_children() if is_public_base_specifier(n)]
        baseClassDefinition = ""
        if len(baseSpec) > 0:
            if any(x in baseSpec[0].type.spelling for x in [":", "<"]):
                pass
                # print(
                #     f'Unsupported character for base class "{baseSpec[0].type.spelling}" ({class_node.spelling})'
                # )
            else:
                baseClassDefinition = " extends " + baseSpec[0].type.spelling
                # self.addImportIfWeHaveTo(baseSpec[0].type.spelling)

        name = getClassTypeName(class_node, template_decl)
        output += "export declare class " + name + baseClassDefinition + " {\n"
        self.exports.append(name)

        output += super().process_class(class_node, template_decl, template_args)
        return output

    def processFinalizeClass(self) -> str:
        return "  delete(): void;\n}\n\n"

    def processSimpleConstructor(self, class_node: cx.Cursor) -> str:
        output = ""
        children = list(class_node.get_children())
        constructors = list(x for x in children if x.kind == cx.CursorKind.CONSTRUCTOR)

        if len(constructors) == 0:
            output += "  constructor();\n"
            return output
        publicConstructors = list(filter(is_public_ctor, children))
        if len(publicConstructors) == 0 or len(publicConstructors) > 1:
            return output
        standardConstructor = publicConstructors[0]
        if not standardConstructor:
            return output

        argsTypescriptDef = ", ".join(
            self.getTypescriptDefFromArg(x)
            for x in list(standardConstructor.get_arguments())
        )

        output += f"  constructor({argsTypescriptDef})\n"
        return output

    def to_ts_type(self, typename: str) -> str:
        if typename in [
            "int",
            "int16_t",
            "unsigned",
            "uint32_t",
            "unsigned int",
            "unsigned longlong",
            "long int",
            "unsigned short",
            "short",
            "short int",
            "float",
            "unsigned float",
            "double",
            "unsigned double",
        ]:
            return "number"

        if typename in ["char", "unsigned char", "std::string"]:
            return "string"

        if typename in ["bool"]:
            return "boolean"
        return typename

    def getTypescriptDefFromResultType(
        self,
        res: cx.Type,
        template_decl: cx.Cursor | None = None,
        template_args: dict[str, cx.Type] | None = None,
    ) -> str:
        if not res.spelling == "void":
            typedefType = self.getTypedefedTemplateTypeAsString(
                res.spelling.replace("&", "")
                .replace("const", "")
                .replace("*", "")
                .strip(),
                template_decl,
                template_args,
            )
            resTypeName = (
                typedefType.replace("&", "")
                .replace("const", "")
                .replace("*", "")
                .strip()
            )
            resTypeName = self.to_ts_type(resTypeName)
        else:
            resTypedefType = (
                res.spelling.replace("&", "")
                .replace("const", "")
                .replace("*", "")
                .strip()
            )
            resTypeName = resTypedefType
        if (
            resTypeName == ""
            or "(" in resTypeName
            or ":" in resTypeName
            or "<" in resTypeName
        ):
            # print(
            #     "could not generate proper types for type name '"
            #     + resTypeName
            #     + "', using 'any' instead."
            # )
            resTypeName = "any"
        return resTypeName

    def getTypescriptDefFromArg(
        self,
        arg: cx.Cursor,
        suffix="",
        template_decl: cx.Cursor | None = None,
        template_args: dict[str, cx.Type] | None = None,
    ) -> str:
        arg_typename = self.getTypedefedTemplateTypeAsString(
            arg.type.spelling.replace("&", "")
            .replace("const", "")
            .replace("*", "")
            .strip(),
            template_decl,
            template_args,
        )
        arg_typename = (
            arg_typename.replace("&", "").replace("const", "").replace("*", "").strip()
        )
        arg_typename = self.to_ts_type(arg_typename)
        if arg_typename == "" or "(" in arg_typename or ":" in arg_typename:
            # print(
            #     f"could not generate proper types for type name '{arg_typename}', using 'any' instead.'"
            # )
            arg_typename = "any"

        argname = arg.spelling if not arg.spelling == "" else ("a" + str(suffix))
        if argname in ["var", "with", "super"]:
            argname += "_"
        return argname + ": " + arg_typename

    def processMethodOrProperty(
        self,
        class_node: cx.Cursor,
        method: cx.Cursor,
        template_decl: cx.Cursor | None = None,
        template_args: dict[str, cx.Type] | None = None,
    ) -> str:
        output = ""
        if (
            method.access_specifier == cx.AccessSpecifier.PUBLIC
            and method.kind == cx.CursorKind.CXX_METHOD
            and not method.spelling.startswith("operator")
        ):
            [overloadPostfix, numOverloads] = getMethodOverloadPostfix(
                class_node, method
            )

            args = ", ".join(
                self.getTypescriptDefFromArg(arg, suffix, template_decl, template_args)
                for suffix, arg in enumerate(method.get_arguments())
            )

            returnType = self.getTypescriptDefFromResultType(
                method.result_type, template_decl, template_args
            )

            output += f"  {'static ' if method.is_static_method() else ''}{method.spelling}{overloadPostfix}({args}): {returnType};\n"
        return output

    def processOverloadedConstructors(
        self,
        class_node: cx.Cursor,
        children: list[cx.Cursor] | None = None,
        template_decl: cx.Cursor | None = None,
        template_args: dict[str, cx.Type] | None = None,
    ) -> str:
        output = ""
        if children is None:
            children = list(class_node.get_children())
        constructors = list(filter(is_public_ctor, children))
        if len(constructors) == 1:
            return output

        constructorTypescriptDef = ""
        allOverloadedConstructors = []

        for constructor in filter(
            lambda x: filter_method_or_property(class_node, x), constructors
        ):
            [overloadPostfix, numOverloads] = getMethodOverloadPostfix(
                class_node, constructor, children
            )

            argsTypescriptDef = ", ".join(
                self.getTypescriptDefFromArg(x, "", template_decl, template_args)
                for x in constructor.get_arguments()
            )
            name = getClassTypeName(class_node, template_decl)
            constructorTypescriptDef += (
                f"  export declare class {name}{overloadPostfix} extends {name} {{\n"
            )
            constructorTypescriptDef += f"    constructor({argsTypescriptDef});\n"
            constructorTypescriptDef += "  }\n\n"
            allOverloadedConstructors.append(name + overloadPostfix)
        output += constructorTypescriptDef
        self.exports.extend(allOverloadedConstructors)
        return output

    def process_enum(self, enum_node: cx.Cursor) -> str:
        output = ""
        bindingsOutput = f"export declare type {enum_node.spelling} = {{\n"
        for enumChild in list(enum_node.get_children()):
            bindingsOutput += f"  {enumChild.spelling}: {{}};\n"
        bindingsOutput += "}\n\n"
        output += bindingsOutput
        self.exports.append(enum_node.spelling)
        return output
