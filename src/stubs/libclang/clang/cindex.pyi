from __future__ import annotations

from ctypes import Array, Structure, c_char_p, c_int, c_uint, c_void_p
from typing import ClassVar, Iterator

class c_interop_string(c_char_p):
    def __init__(self, p: str | bytes | None = None) -> None: ...
    def __str__(self) -> str: ...
    @property
    def value(self) -> str: ...  # type: ignore[override]
    @classmethod
    def from_param(cls, param: str | bytes | None) -> c_interop_string: ...
    @staticmethod
    def to_python_string(x: c_interop_string, *args: object) -> str: ...

c_object_p = type[Array[c_void_p]]

class TranslationUnitLoadError(Exception): ...

class TranslationUnitSaveError(Exception):
    ERROR_UNKNOWN: ClassVar[int]
    ERROR_TRANSLATION_ERRORS: ClassVar[int]
    ERROR_INVALID_TU: ClassVar[int]
    save_error: int
    def __init__(self, enumeration: int, message: str) -> None: ...

class SourceLocation(Structure):
    _fields_: ClassVar[list[tuple[str, type]]]
    @staticmethod
    def from_position(tu: TranslationUnit, file: File, line: int, column: int) -> SourceLocation: ...
    @staticmethod
    def from_offset(tu: TranslationUnit, file: File, offset: int) -> SourceLocation: ...
    @property
    def file(self) -> File | None: ...
    @property
    def line(self) -> int: ...
    @property
    def column(self) -> int: ...
    @property
    def offset(self) -> int: ...
    @property
    def is_in_system_header(self) -> bool: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...
    def __repr__(self) -> str: ...

class SourceRange(Structure):
    _fields_: ClassVar[list[tuple[str, type]]]
    @staticmethod
    def from_locations(start: SourceLocation, end: SourceLocation) -> SourceRange: ...
    @property
    def start(self) -> SourceLocation: ...
    @property
    def end(self) -> SourceLocation: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...
    def __contains__(self, other: SourceLocation) -> bool: ...
    def __repr__(self) -> str: ...

class Diagnostic:
    Ignored: ClassVar[int]
    Note: ClassVar[int]
    Warning: ClassVar[int]
    Error: ClassVar[int]
    Fatal: ClassVar[int]
    ptr: object
    @property
    def severity(self) -> int: ...
    @property
    def location(self) -> SourceLocation: ...
    @property
    def spelling(self) -> str: ...
    @property
    def ranges(self) -> Iterator[SourceRange]: ...
    @property
    def fixits(self) -> Iterator[FixIt]: ...
    @property
    def children(self) -> Iterator[Diagnostic]: ...
    @property
    def category_number(self) -> int: ...
    @property
    def category_name(self) -> str: ...
    @property
    def option(self) -> str: ...
    @property
    def disable_option(self) -> str: ...
    def format(self, options: int | None = None) -> str: ...
    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...

class FixIt:
    range: SourceRange
    value: str
    def __init__(self, range: SourceRange, value: str) -> None: ...
    def __repr__(self) -> str: ...

class TokenKind:
    value: int
    name: str
    def __init__(self, value: int, name: str) -> None: ...
    def __repr__(self) -> str: ...
    @staticmethod
    def from_value(value: int) -> TokenKind: ...
    @staticmethod
    def register(value: int, name: str) -> TokenKind: ...

class BaseEnumeration:
    _kinds: ClassVar[list[BaseEnumeration | None]]
    _name_map: ClassVar[dict[BaseEnumeration, str] | None]
    value: int
    def __init__(self, value: int) -> None: ...
    def from_param(self) -> int: ...
    @property
    def name(self) -> str: ...
    @classmethod
    def from_id(cls, id: int) -> BaseEnumeration: ...
    def __repr__(self) -> str: ...

class CursorKind(BaseEnumeration):
    _kinds: ClassVar[list[CursorKind | None]]
    _name_map: ClassVar[dict[CursorKind, str] | None]

    @staticmethod
    def get_all_kinds() -> list[CursorKind]: ...
    def is_declaration(self) -> bool: ...
    def is_reference(self) -> bool: ...
    def is_expression(self) -> bool: ...
    def is_statement(self) -> bool: ...
    def is_attribute(self) -> bool: ...
    def is_invalid(self) -> bool: ...
    def is_translation_unit(self) -> bool: ...
    def is_preprocessing(self) -> bool: ...
    def is_unexposed(self) -> bool: ...
    def __repr__(self) -> str: ...

    # Declaration Kinds
    UNEXPOSED_DECL: ClassVar[CursorKind]
    STRUCT_DECL: ClassVar[CursorKind]
    UNION_DECL: ClassVar[CursorKind]
    CLASS_DECL: ClassVar[CursorKind]
    ENUM_DECL: ClassVar[CursorKind]
    FIELD_DECL: ClassVar[CursorKind]
    ENUM_CONSTANT_DECL: ClassVar[CursorKind]
    FUNCTION_DECL: ClassVar[CursorKind]
    VAR_DECL: ClassVar[CursorKind]
    PARM_DECL: ClassVar[CursorKind]
    OBJC_INTERFACE_DECL: ClassVar[CursorKind]
    OBJC_CATEGORY_DECL: ClassVar[CursorKind]
    OBJC_PROTOCOL_DECL: ClassVar[CursorKind]
    OBJC_PROPERTY_DECL: ClassVar[CursorKind]
    OBJC_IVAR_DECL: ClassVar[CursorKind]
    OBJC_INSTANCE_METHOD_DECL: ClassVar[CursorKind]
    OBJC_CLASS_METHOD_DECL: ClassVar[CursorKind]
    OBJC_IMPLEMENTATION_DECL: ClassVar[CursorKind]
    OBJC_CATEGORY_IMPL_DECL: ClassVar[CursorKind]
    TYPEDEF_DECL: ClassVar[CursorKind]
    CXX_METHOD: ClassVar[CursorKind]
    NAMESPACE: ClassVar[CursorKind]
    LINKAGE_SPEC: ClassVar[CursorKind]
    CONSTRUCTOR: ClassVar[CursorKind]
    DESTRUCTOR: ClassVar[CursorKind]
    CONVERSION_FUNCTION: ClassVar[CursorKind]
    TEMPLATE_TYPE_PARAMETER: ClassVar[CursorKind]
    TEMPLATE_NON_TYPE_PARAMETER: ClassVar[CursorKind]
    TEMPLATE_TEMPLATE_PARAMETER: ClassVar[CursorKind]
    FUNCTION_TEMPLATE: ClassVar[CursorKind]
    CLASS_TEMPLATE: ClassVar[CursorKind]
    CLASS_TEMPLATE_PARTIAL_SPECIALIZATION: ClassVar[CursorKind]
    NAMESPACE_ALIAS: ClassVar[CursorKind]
    USING_DIRECTIVE: ClassVar[CursorKind]
    USING_DECLARATION: ClassVar[CursorKind]
    TYPE_ALIAS_DECL: ClassVar[CursorKind]
    OBJC_SYNTHESIZE_DECL: ClassVar[CursorKind]
    OBJC_DYNAMIC_DECL: ClassVar[CursorKind]
    CXX_ACCESS_SPEC_DECL: ClassVar[CursorKind]

    # Reference Kinds
    OBJC_SUPER_CLASS_REF: ClassVar[CursorKind]
    OBJC_PROTOCOL_REF: ClassVar[CursorKind]
    OBJC_CLASS_REF: ClassVar[CursorKind]
    TYPE_REF: ClassVar[CursorKind]
    CXX_BASE_SPECIFIER: ClassVar[CursorKind]
    TEMPLATE_REF: ClassVar[CursorKind]
    NAMESPACE_REF: ClassVar[CursorKind]
    MEMBER_REF: ClassVar[CursorKind]
    LABEL_REF: ClassVar[CursorKind]
    OVERLOADED_DECL_REF: ClassVar[CursorKind]
    VARIABLE_REF: ClassVar[CursorKind]

    # Invalid/Error Kinds
    INVALID_FILE: ClassVar[CursorKind]
    NO_DECL_FOUND: ClassVar[CursorKind]
    NOT_IMPLEMENTED: ClassVar[CursorKind]
    INVALID_CODE: ClassVar[CursorKind]

    # Expression Kinds
    UNEXPOSED_EXPR: ClassVar[CursorKind]
    DECL_REF_EXPR: ClassVar[CursorKind]
    MEMBER_REF_EXPR: ClassVar[CursorKind]
    CALL_EXPR: ClassVar[CursorKind]
    OBJC_MESSAGE_EXPR: ClassVar[CursorKind]
    BLOCK_EXPR: ClassVar[CursorKind]
    INTEGER_LITERAL: ClassVar[CursorKind]
    FLOATING_LITERAL: ClassVar[CursorKind]
    IMAGINARY_LITERAL: ClassVar[CursorKind]
    STRING_LITERAL: ClassVar[CursorKind]
    CHARACTER_LITERAL: ClassVar[CursorKind]
    PAREN_EXPR: ClassVar[CursorKind]
    UNARY_OPERATOR: ClassVar[CursorKind]
    ARRAY_SUBSCRIPT_EXPR: ClassVar[CursorKind]
    BINARY_OPERATOR: ClassVar[CursorKind]
    COMPOUND_ASSIGNMENT_OPERATOR: ClassVar[CursorKind]
    CONDITIONAL_OPERATOR: ClassVar[CursorKind]
    CSTYLE_CAST_EXPR: ClassVar[CursorKind]
    COMPOUND_LITERAL_EXPR: ClassVar[CursorKind]
    INIT_LIST_EXPR: ClassVar[CursorKind]
    ADDR_LABEL_EXPR: ClassVar[CursorKind]
    StmtExpr: ClassVar[CursorKind]
    GENERIC_SELECTION_EXPR: ClassVar[CursorKind]
    GNU_NULL_EXPR: ClassVar[CursorKind]
    CXX_STATIC_CAST_EXPR: ClassVar[CursorKind]
    CXX_DYNAMIC_CAST_EXPR: ClassVar[CursorKind]
    CXX_REINTERPRET_CAST_EXPR: ClassVar[CursorKind]
    CXX_CONST_CAST_EXPR: ClassVar[CursorKind]
    CXX_FUNCTIONAL_CAST_EXPR: ClassVar[CursorKind]
    CXX_TYPEID_EXPR: ClassVar[CursorKind]
    CXX_BOOL_LITERAL_EXPR: ClassVar[CursorKind]
    CXX_NULL_PTR_LITERAL_EXPR: ClassVar[CursorKind]
    CXX_THIS_EXPR: ClassVar[CursorKind]
    CXX_THROW_EXPR: ClassVar[CursorKind]
    CXX_NEW_EXPR: ClassVar[CursorKind]
    CXX_DELETE_EXPR: ClassVar[CursorKind]
    CXX_UNARY_EXPR: ClassVar[CursorKind]
    OBJC_STRING_LITERAL: ClassVar[CursorKind]
    OBJC_ENCODE_EXPR: ClassVar[CursorKind]
    OBJC_SELECTOR_EXPR: ClassVar[CursorKind]
    OBJC_PROTOCOL_EXPR: ClassVar[CursorKind]
    OBJC_BRIDGE_CAST_EXPR: ClassVar[CursorKind]
    PACK_EXPANSION_EXPR: ClassVar[CursorKind]
    SIZE_OF_PACK_EXPR: ClassVar[CursorKind]
    LAMBDA_EXPR: ClassVar[CursorKind]
    OBJ_BOOL_LITERAL_EXPR: ClassVar[CursorKind]
    OBJ_SELF_EXPR: ClassVar[CursorKind]
    OMP_ARRAY_SECTION_EXPR: ClassVar[CursorKind]
    OBJC_AVAILABILITY_CHECK_EXPR: ClassVar[CursorKind]
    FIXED_POINT_LITERAL: ClassVar[CursorKind]
    OMP_ARRAY_SHAPING_EXPR: ClassVar[CursorKind]
    OMP_ITERATOR_EXPR: ClassVar[CursorKind]
    CXX_ADDRSPACE_CAST_EXPR: ClassVar[CursorKind]
    CONCEPT_SPECIALIZATION_EXPR: ClassVar[CursorKind]
    REQUIRES_EXPR: ClassVar[CursorKind]

    # Statement Kinds
    UNEXPOSED_STMT: ClassVar[CursorKind]
    LABEL_STMT: ClassVar[CursorKind]
    COMPOUND_STMT: ClassVar[CursorKind]
    CASE_STMT: ClassVar[CursorKind]
    DEFAULT_STMT: ClassVar[CursorKind]
    IF_STMT: ClassVar[CursorKind]
    SWITCH_STMT: ClassVar[CursorKind]
    WHILE_STMT: ClassVar[CursorKind]
    DO_STMT: ClassVar[CursorKind]
    FOR_STMT: ClassVar[CursorKind]
    GOTO_STMT: ClassVar[CursorKind]
    INDIRECT_GOTO_STMT: ClassVar[CursorKind]
    CONTINUE_STMT: ClassVar[CursorKind]
    BREAK_STMT: ClassVar[CursorKind]
    RETURN_STMT: ClassVar[CursorKind]
    ASM_STMT: ClassVar[CursorKind]
    OBJC_AT_TRY_STMT: ClassVar[CursorKind]
    OBJC_AT_CATCH_STMT: ClassVar[CursorKind]
    OBJC_AT_FINALLY_STMT: ClassVar[CursorKind]
    OBJC_AT_THROW_STMT: ClassVar[CursorKind]
    OBJC_AT_SYNCHRONIZED_STMT: ClassVar[CursorKind]
    OBJC_AUTORELEASE_POOL_STMT: ClassVar[CursorKind]
    OBJC_FOR_COLLECTION_STMT: ClassVar[CursorKind]
    CXX_CATCH_STMT: ClassVar[CursorKind]
    CXX_TRY_STMT: ClassVar[CursorKind]
    CXX_FOR_RANGE_STMT: ClassVar[CursorKind]
    SEH_TRY_STMT: ClassVar[CursorKind]
    SEH_EXCEPT_STMT: ClassVar[CursorKind]
    SEH_FINALLY_STMT: ClassVar[CursorKind]
    MS_ASM_STMT: ClassVar[CursorKind]
    NULL_STMT: ClassVar[CursorKind]
    DECL_STMT: ClassVar[CursorKind]
    OMP_PARALLEL_DIRECTIVE: ClassVar[CursorKind]
    OMP_SIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_FOR_DIRECTIVE: ClassVar[CursorKind]
    OMP_SECTIONS_DIRECTIVE: ClassVar[CursorKind]
    OMP_SECTION_DIRECTIVE: ClassVar[CursorKind]
    OMP_SINGLE_DIRECTIVE: ClassVar[CursorKind]
    OMP_PARALLEL_FOR_DIRECTIVE: ClassVar[CursorKind]
    OMP_PARALLEL_SECTIONS_DIRECTIVE: ClassVar[CursorKind]
    OMP_TASK_DIRECTIVE: ClassVar[CursorKind]
    OMP_MASTER_DIRECTIVE: ClassVar[CursorKind]
    OMP_CRITICAL_DIRECTIVE: ClassVar[CursorKind]
    OMP_TASKYIELD_DIRECTIVE: ClassVar[CursorKind]
    OMP_BARRIER_DIRECTIVE: ClassVar[CursorKind]
    OMP_TASKWAIT_DIRECTIVE: ClassVar[CursorKind]
    OMP_FLUSH_DIRECTIVE: ClassVar[CursorKind]
    SEH_LEAVE_STMT: ClassVar[CursorKind]
    OMP_ORDERED_DIRECTIVE: ClassVar[CursorKind]
    OMP_ATOMIC_DIRECTIVE: ClassVar[CursorKind]
    OMP_FOR_SIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_PARALLELFORSIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_DIRECTIVE: ClassVar[CursorKind]
    OMP_TEAMS_DIRECTIVE: ClassVar[CursorKind]
    OMP_TASKGROUP_DIRECTIVE: ClassVar[CursorKind]
    OMP_CANCELLATION_POINT_DIRECTIVE: ClassVar[CursorKind]
    OMP_CANCEL_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_DATA_DIRECTIVE: ClassVar[CursorKind]
    OMP_TASK_LOOP_DIRECTIVE: ClassVar[CursorKind]
    OMP_TASK_LOOP_SIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_DISTRIBUTE_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_ENTER_DATA_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_EXIT_DATA_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_PARALLEL_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_PARALLELFOR_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_UPDATE_DIRECTIVE: ClassVar[CursorKind]
    OMP_DISTRIBUTE_PARALLELFOR_DIRECTIVE: ClassVar[CursorKind]
    OMP_DISTRIBUTE_PARALLEL_FOR_SIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_DISTRIBUTE_SIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_PARALLEL_FOR_SIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_SIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_TEAMS_DISTRIBUTE_DIRECTIVE: ClassVar[CursorKind]
    OMP_TEAMS_DISTRIBUTE_SIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_TEAMS_DISTRIBUTE_PARALLEL_FOR_SIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_TEAMS_DISTRIBUTE_PARALLEL_FOR_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_TEAMS_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_TEAMS_DISTRIBUTE_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_TEAMS_DISTRIBUTE_PARALLEL_FOR_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_TEAMS_DISTRIBUTE_PARALLEL_FOR_SIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_TEAMS_DISTRIBUTE_SIMD_DIRECTIVE: ClassVar[CursorKind]
    BUILTIN_BIT_CAST_EXPR: ClassVar[CursorKind]
    OMP_MASTER_TASK_LOOP_DIRECTIVE: ClassVar[CursorKind]
    OMP_PARALLEL_MASTER_TASK_LOOP_DIRECTIVE: ClassVar[CursorKind]
    OMP_MASTER_TASK_LOOP_SIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_PARALLEL_MASTER_TASK_LOOP_SIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_PARALLEL_MASTER_DIRECTIVE: ClassVar[CursorKind]
    OMP_DEPOBJ_DIRECTIVE: ClassVar[CursorKind]
    OMP_SCAN_DIRECTIVE: ClassVar[CursorKind]
    OMP_TILE_DIRECTIVE: ClassVar[CursorKind]
    OMP_CANONICAL_LOOP: ClassVar[CursorKind]
    OMP_INTEROP_DIRECTIVE: ClassVar[CursorKind]
    OMP_DISPATCH_DIRECTIVE: ClassVar[CursorKind]
    OMP_MASKED_DIRECTIVE: ClassVar[CursorKind]
    OMP_UNROLL_DIRECTIVE: ClassVar[CursorKind]
    OMP_META_DIRECTIVE: ClassVar[CursorKind]
    OMP_GENERIC_LOOP_DIRECTIVE: ClassVar[CursorKind]
    OMP_TEAMS_GENERIC_LOOP_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_TEAMS_GENERIC_LOOP_DIRECTIVE: ClassVar[CursorKind]
    OMP_PARALLEL_GENERIC_LOOP_DIRECTIVE: ClassVar[CursorKind]
    OMP_TARGET_PARALLEL_GENERIC_LOOP_DIRECTIVE: ClassVar[CursorKind]
    OMP_PARALLEL_MASKED_DIRECTIVE: ClassVar[CursorKind]
    OMP_MASKED_TASK_LOOP_DIRECTIVE: ClassVar[CursorKind]
    OMP_MASKED_TASK_LOOP_SIMD_DIRECTIVE: ClassVar[CursorKind]
    OMP_PARALLEL_MASKED_TASK_LOOP_DIRECTIVE: ClassVar[CursorKind]
    OMP_PARALLEL_MASKED_TASK_LOOP_SIMD_DIRECTIVE: ClassVar[CursorKind]

    # Other Kinds
    TRANSLATION_UNIT: ClassVar[CursorKind]

    # Attributes
    UNEXPOSED_ATTR: ClassVar[CursorKind]
    IB_ACTION_ATTR: ClassVar[CursorKind]
    IB_OUTLET_ATTR: ClassVar[CursorKind]
    IB_OUTLET_COLLECTION_ATTR: ClassVar[CursorKind]
    CXX_FINAL_ATTR: ClassVar[CursorKind]
    CXX_OVERRIDE_ATTR: ClassVar[CursorKind]
    ANNOTATE_ATTR: ClassVar[CursorKind]
    ASM_LABEL_ATTR: ClassVar[CursorKind]
    PACKED_ATTR: ClassVar[CursorKind]
    PURE_ATTR: ClassVar[CursorKind]
    CONST_ATTR: ClassVar[CursorKind]
    NODUPLICATE_ATTR: ClassVar[CursorKind]
    CUDACONSTANT_ATTR: ClassVar[CursorKind]
    CUDADEVICE_ATTR: ClassVar[CursorKind]
    CUDAGLOBAL_ATTR: ClassVar[CursorKind]
    CUDAHOST_ATTR: ClassVar[CursorKind]
    CUDASHARED_ATTR: ClassVar[CursorKind]
    VISIBILITY_ATTR: ClassVar[CursorKind]
    DLLEXPORT_ATTR: ClassVar[CursorKind]
    DLLIMPORT_ATTR: ClassVar[CursorKind]
    CONVERGENT_ATTR: ClassVar[CursorKind]
    WARN_UNUSED_ATTR: ClassVar[CursorKind]
    WARN_UNUSED_RESULT_ATTR: ClassVar[CursorKind]
    ALIGNED_ATTR: ClassVar[CursorKind]

    # Preprocessing
    PREPROCESSING_DIRECTIVE: ClassVar[CursorKind]
    MACRO_DEFINITION: ClassVar[CursorKind]
    MACRO_INSTANTIATION: ClassVar[CursorKind]
    INCLUSION_DIRECTIVE: ClassVar[CursorKind]

    # Extra Declarations
    MODULE_IMPORT_DECL: ClassVar[CursorKind]
    TYPE_ALIAS_TEMPLATE_DECL: ClassVar[CursorKind]
    STATIC_ASSERT: ClassVar[CursorKind]
    FRIEND_DECL: ClassVar[CursorKind]
    CONCEPT_DECL: ClassVar[CursorKind]

    # Overload Candidate
    OVERLOAD_CANDIDATE: ClassVar[CursorKind]

class TemplateArgumentKind(BaseEnumeration):
    _kinds: ClassVar[list[TemplateArgumentKind | None]]
    _name_map: ClassVar[dict[TemplateArgumentKind, str] | None]
    NULL: ClassVar[TemplateArgumentKind]
    TYPE: ClassVar[TemplateArgumentKind]
    DECLARATION: ClassVar[TemplateArgumentKind]
    NULLPTR: ClassVar[TemplateArgumentKind]
    INTEGRAL: ClassVar[TemplateArgumentKind]

class ExceptionSpecificationKind(BaseEnumeration):
    _kinds: ClassVar[list[ExceptionSpecificationKind | None]]
    _name_map: ClassVar[dict[ExceptionSpecificationKind, str] | None]
    NONE: ClassVar[ExceptionSpecificationKind]
    DYNAMIC_NONE: ClassVar[ExceptionSpecificationKind]
    DYNAMIC: ClassVar[ExceptionSpecificationKind]
    MS_ANY: ClassVar[ExceptionSpecificationKind]
    BASIC_NOEXCEPT: ClassVar[ExceptionSpecificationKind]
    COMPUTED_NOEXCEPT: ClassVar[ExceptionSpecificationKind]
    UNEVALUATED: ClassVar[ExceptionSpecificationKind]
    UNINSTANTIATED: ClassVar[ExceptionSpecificationKind]
    UNPARSED: ClassVar[ExceptionSpecificationKind]

class Cursor(Structure):
    _fields_: ClassVar[list[tuple[str, type]]]
    @staticmethod
    def from_location(tu: TranslationUnit, location: SourceLocation) -> Cursor: ...
    @staticmethod
    def from_result(res: object, fn: object = None, args: object = None) -> Cursor | None: ...
    @staticmethod
    def from_cursor_result(res: object, fn: object = None, args: object = None) -> Cursor: ...
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...
    def is_definition(self) -> bool: ...
    def is_const_method(self) -> bool: ...
    def is_converting_constructor(self) -> bool: ...
    def is_copy_constructor(self) -> bool: ...
    def is_default_constructor(self) -> bool: ...
    def is_move_constructor(self) -> bool: ...
    def is_default_method(self) -> bool: ...
    def is_deleted_method(self) -> bool: ...
    def is_copy_assignment_operator_method(self) -> bool: ...
    def is_move_assignment_operator_method(self) -> bool: ...
    def is_explicit_method(self) -> bool: ...
    def is_mutable_field(self) -> bool: ...
    def is_pure_virtual_method(self) -> bool: ...
    def is_static_method(self) -> bool: ...
    def is_virtual_method(self) -> bool: ...
    def is_abstract_record(self) -> bool: ...
    def is_scoped_enum(self) -> bool: ...
    def get_definition(self) -> Cursor | None: ...
    def get_usr(self) -> str: ...
    def get_included_file(self) -> File: ...
    @property
    def kind(self) -> CursorKind: ...
    @property
    def spelling(self) -> str: ...
    @property
    def displayname(self) -> str: ...
    @property
    def mangled_name(self) -> str: ...
    @property
    def location(self) -> SourceLocation: ...
    @property
    def linkage(self) -> LinkageKind: ...
    @property
    def tls_kind(self) -> TLSKind: ...
    @property
    def extent(self) -> SourceRange: ...
    @property
    def storage_class(self) -> StorageClass: ...
    @property
    def availability(self) -> AvailabilityKind: ...
    @property
    def access_specifier(self) -> AccessSpecifier: ...
    @property
    def type(self) -> Type: ...
    @property
    def canonical(self) -> Cursor: ...
    @property
    def result_type(self) -> Type: ...
    @property
    def exception_specification_kind(self) -> ExceptionSpecificationKind: ...
    @property
    def underlying_typedef_type(self) -> Type: ...
    @property
    def enum_type(self) -> Type: ...
    @property
    def enum_value(self) -> int: ...
    @property
    def objc_type_encoding(self) -> str: ...
    @property
    def hash(self) -> int: ...
    @property
    def semantic_parent(self) -> Cursor: ...
    @property
    def lexical_parent(self) -> Cursor: ...
    @property
    def translation_unit(self) -> TranslationUnit: ...
    @property
    def referenced(self) -> Cursor | None: ...
    @property
    def brief_comment(self) -> str | None: ...
    @property
    def raw_comment(self) -> str | None: ...
    def get_arguments(self) -> Iterator[Cursor]: ...
    def get_num_template_arguments(self) -> int: ...
    def get_template_argument_kind(self, num: int) -> TemplateArgumentKind: ...
    def get_template_argument_type(self, num: int) -> Type: ...
    def get_template_argument_value(self, num: int) -> int: ...
    def get_template_argument_unsigned_value(self, num: int) -> int: ...
    def get_children(self) -> Iterator[Cursor]: ...
    def walk_preorder(self) -> Iterator[Cursor]: ...
    def get_tokens(self) -> Iterator[Token]: ...
    def get_field_offsetof(self) -> int: ...
    def is_anonymous(self) -> bool: ...
    def is_bitfield(self) -> bool: ...
    def get_bitfield_width(self) -> int: ...

class StorageClass:
    _kinds: ClassVar[list[StorageClass | None]]
    _name_map: ClassVar[dict[StorageClass, str] | None]
    value: int
    INVALID: ClassVar[StorageClass]
    NONE: ClassVar[StorageClass]
    EXTERN: ClassVar[StorageClass]
    STATIC: ClassVar[StorageClass]
    PRIVATEEXTERN: ClassVar[StorageClass]
    OPENCLWORKGROUPLOCAL: ClassVar[StorageClass]
    AUTO: ClassVar[StorageClass]
    REGISTER: ClassVar[StorageClass]

class AvailabilityKind(BaseEnumeration):
    _kinds: ClassVar[list[AvailabilityKind | None]]
    _name_map: ClassVar[dict[AvailabilityKind, str] | None]
    AVAILABLE: ClassVar[AvailabilityKind]
    DEPRECATED: ClassVar[AvailabilityKind]
    NOT_AVAILABLE: ClassVar[AvailabilityKind]
    NOT_ACCESSIBLE: ClassVar[AvailabilityKind]

class AccessSpecifier(BaseEnumeration):
    _kinds: ClassVar[list[AccessSpecifier | None]]
    _name_map: ClassVar[dict[AccessSpecifier, str] | None]
    INVALID: ClassVar[AccessSpecifier]
    PUBLIC: ClassVar[AccessSpecifier]
    PROTECTED: ClassVar[AccessSpecifier]
    PRIVATE: ClassVar[AccessSpecifier]
    NONE: ClassVar[AccessSpecifier]

class TypeKind(BaseEnumeration):
    _kinds: ClassVar[list[TypeKind | None]]
    _name_map: ClassVar[dict[TypeKind, str] | None]
    @property
    def spelling(self) -> str: ...
    INVALID: ClassVar[TypeKind]
    UNEXPOSED: ClassVar[TypeKind]
    VOID: ClassVar[TypeKind]
    BOOL: ClassVar[TypeKind]
    CHAR_U: ClassVar[TypeKind]
    UCHAR: ClassVar[TypeKind]
    CHAR16: ClassVar[TypeKind]
    CHAR32: ClassVar[TypeKind]
    USHORT: ClassVar[TypeKind]
    UINT: ClassVar[TypeKind]
    ULONG: ClassVar[TypeKind]
    ULONGLONG: ClassVar[TypeKind]
    UINT128: ClassVar[TypeKind]
    CHAR_S: ClassVar[TypeKind]
    SCHAR: ClassVar[TypeKind]
    WCHAR: ClassVar[TypeKind]
    SHORT: ClassVar[TypeKind]
    INT: ClassVar[TypeKind]
    LONG: ClassVar[TypeKind]
    LONGLONG: ClassVar[TypeKind]
    INT128: ClassVar[TypeKind]
    FLOAT: ClassVar[TypeKind]
    DOUBLE: ClassVar[TypeKind]
    LONGDOUBLE: ClassVar[TypeKind]
    NULLPTR: ClassVar[TypeKind]
    OVERLOAD: ClassVar[TypeKind]
    DEPENDENT: ClassVar[TypeKind]
    OBJCID: ClassVar[TypeKind]
    OBJCCLASS: ClassVar[TypeKind]
    OBJCSEL: ClassVar[TypeKind]
    FLOAT128: ClassVar[TypeKind]
    HALF: ClassVar[TypeKind]
    IBM128: ClassVar[TypeKind]
    COMPLEX: ClassVar[TypeKind]
    POINTER: ClassVar[TypeKind]
    BLOCKPOINTER: ClassVar[TypeKind]
    LVALUEREFERENCE: ClassVar[TypeKind]
    RVALUEREFERENCE: ClassVar[TypeKind]
    RECORD: ClassVar[TypeKind]
    ENUM: ClassVar[TypeKind]
    TYPEDEF: ClassVar[TypeKind]
    OBJCINTERFACE: ClassVar[TypeKind]
    OBJCOBJECTPOINTER: ClassVar[TypeKind]
    FUNCTIONNOPROTO: ClassVar[TypeKind]
    FUNCTIONPROTO: ClassVar[TypeKind]
    CONSTANTARRAY: ClassVar[TypeKind]
    VECTOR: ClassVar[TypeKind]
    INCOMPLETEARRAY: ClassVar[TypeKind]
    VARIABLEARRAY: ClassVar[TypeKind]
    DEPENDENTSIZEDARRAY: ClassVar[TypeKind]
    MEMBERPOINTER: ClassVar[TypeKind]
    AUTO: ClassVar[TypeKind]
    ELABORATED: ClassVar[TypeKind]
    PIPE: ClassVar[TypeKind]
    EXTVECTOR: ClassVar[TypeKind]
    ATOMIC: ClassVar[TypeKind]

class RefQualifierKind(BaseEnumeration):
    _kinds: ClassVar[list[RefQualifierKind | None]]
    _name_map: ClassVar[dict[RefQualifierKind, str] | None]
    NONE: ClassVar[RefQualifierKind]
    LVALUE: ClassVar[RefQualifierKind]
    RVALUE: ClassVar[RefQualifierKind]

class LinkageKind(BaseEnumeration):
    _kinds: ClassVar[list[LinkageKind | None]]
    _name_map: ClassVar[dict[LinkageKind, str] | None]
    INVALID: ClassVar[LinkageKind]
    NO_LINKAGE: ClassVar[LinkageKind]
    INTERNAL: ClassVar[LinkageKind]
    UNIQUE_EXTERNAL: ClassVar[LinkageKind]
    EXTERNAL: ClassVar[LinkageKind]

class TLSKind(BaseEnumeration):
    _kinds: ClassVar[list[TLSKind | None]]
    _name_map: ClassVar[dict[TLSKind, str] | None]
    NONE: ClassVar[TLSKind]
    DYNAMIC: ClassVar[TLSKind]
    STATIC: ClassVar[TLSKind]

class Type(Structure):
    _fields_: ClassVar[list[tuple[str, type]]]
    @property
    def kind(self) -> TypeKind: ...
    def argument_types(self) -> Iterator[Type]: ...
    @property
    def element_type(self) -> Type: ...
    @property
    def element_count(self) -> int: ...
    @property
    def translation_unit(self) -> TranslationUnit: ...
    @staticmethod
    def from_result(res: object, fn: object = None, args: object = None) -> Type: ...
    def get_num_template_arguments(self) -> int: ...
    def get_template_argument_type(self, num: int) -> Type: ...
    def get_canonical(self) -> Type: ...
    def is_const_qualified(self) -> bool: ...
    def is_volatile_qualified(self) -> bool: ...
    def is_restrict_qualified(self) -> bool: ...
    def is_function_variadic(self) -> bool: ...
    def get_address_space(self) -> int: ...
    def get_typedef_name(self) -> str: ...
    def is_pod(self) -> bool: ...
    def get_pointee(self) -> Type: ...
    def get_declaration(self) -> Cursor: ...
    def get_result(self) -> Type: ...
    def get_array_element_type(self) -> Type: ...
    def get_array_size(self) -> int: ...
    def get_class_type(self) -> Type: ...
    def get_named_type(self) -> Type: ...
    def get_align(self) -> int: ...
    def get_size(self) -> int: ...
    def get_offset(self, fieldname: str) -> int: ...
    def get_ref_qualifier(self) -> RefQualifierKind: ...
    def get_fields(self) -> Iterator[Cursor]: ...
    def get_exception_specification_kind(self) -> ExceptionSpecificationKind: ...
    @property
    def spelling(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...

class ClangObject:
    obj: object
    def __init__(self, obj: object) -> None: ...
    def from_param(self) -> object: ...

class CompletionChunk:
    class Kind:
        name: str
        def __init__(self, name: str) -> None: ...
        def __repr__(self) -> str: ...
    completionString: object
    key: int
    def __init__(self, completionString: object, key: int) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def spelling(self) -> str: ...
    @property
    def kind(self) -> CompletionChunk.Kind: ...
    @property
    def string(self) -> CompletionString | None: ...
    def isKindOptional(self) -> bool: ...
    def isKindTypedText(self) -> bool: ...
    def isKindPlaceHolder(self) -> bool: ...
    def isKindInformative(self) -> bool: ...
    def isKindResultType(self) -> bool: ...

class CompletionString(ClangObject):
    class Availability:
        name: str
        def __init__(self, name: str) -> None: ...
        def __repr__(self) -> str: ...
    def __len__(self) -> int: ...
    def __getitem__(self, key: int) -> CompletionChunk: ...
    @property
    def priority(self) -> int: ...
    @property
    def availability(self) -> CompletionString.Availability: ...
    @property
    def briefComment(self) -> str: ...
    def __repr__(self) -> str: ...

class CodeCompletionResult(Structure):
    _fields_: ClassVar[list[tuple[str, type]]]
    @property
    def kind(self) -> CursorKind: ...
    @property
    def string(self) -> CompletionString: ...

class CodeCompletionResults(ClangObject):
    @property
    def results(self) -> object: ...
    @property
    def diagnostics(self) -> Iterator[Diagnostic]: ...

class Index(ClangObject):
    @staticmethod
    def create(excludeDecls: bool = False) -> Index: ...
    def read(self, path: str) -> TranslationUnit: ...
    def parse(
        self,
        path: str | None,
        args: list[str] | None = None,
        unsaved_files: list[tuple[str, str]] | None = None,
        options: int = 0,
    ) -> TranslationUnit: ...

class TranslationUnit(ClangObject):
    PARSE_NONE: ClassVar[int]
    PARSE_DETAILED_PROCESSING_RECORD: ClassVar[int]
    PARSE_INCOMPLETE: ClassVar[int]
    PARSE_PRECOMPILED_PREAMBLE: ClassVar[int]
    PARSE_CACHE_COMPLETION_RESULTS: ClassVar[int]
    PARSE_SKIP_FUNCTION_BODIES: ClassVar[int]
    PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION: ClassVar[int]
    @classmethod
    def from_source(
        cls,
        filename: str | None,
        args: list[str] | None = None,
        unsaved_files: list[tuple[str, str]] | None = None,
        options: int = 0,
        index: Index | None = None,
    ) -> TranslationUnit: ...
    @classmethod
    def from_ast_file(cls, filename: str, index: Index | None = None) -> TranslationUnit: ...
    @property
    def cursor(self) -> Cursor: ...
    @property
    def spelling(self) -> str: ...
    def get_includes(self) -> Iterator[FileInclusion]: ...
    def get_file(self, filename: str) -> File: ...
    def get_location(self, filename: str, position: tuple[int, int] | int) -> SourceLocation: ...
    def get_extent(self, filename: str, locations: tuple[SourceLocation, SourceLocation] | tuple[tuple[int, int], tuple[int, int]]) -> SourceRange: ...
    @property
    def diagnostics(self) -> Iterator[Diagnostic]: ...
    def reparse(self, unsaved_files: list[tuple[str, str]] | None = None, options: int = 0) -> None: ...
    def save(self, filename: str) -> None: ...
    def codeComplete(
        self,
        path: str,
        line: int,
        column: int,
        unsaved_files: list[tuple[str, str]] | None = None,
        include_macros: bool = False,
        include_code_patterns: bool = False,
        include_brief_comments: bool = False,
    ) -> CodeCompletionResults | None: ...
    def get_tokens(self, locations: tuple[SourceLocation, SourceLocation] | None = None, extent: SourceRange | None = None) -> Iterator[Token]: ...

class File(ClangObject):
    @staticmethod
    def from_result(res: object, fn: object = None, args: object = None) -> File | None: ...
    @property
    def name(self) -> str: ...
    @property
    def time(self) -> int: ...
    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...

class FileInclusion:
    source: File
    include: File
    location: SourceLocation
    depth: int

class CompilationDatabaseError(Exception):
    ERROR_UNKNOWN: ClassVar[int]
    ERROR_CANNOTLOADDATABASE: ClassVar[int]
    cdb_error: int

class CompileCommand:
    @property
    def directory(self) -> str: ...
    @property
    def filename(self) -> str: ...
    @property
    def arguments(self) -> Iterator[str]: ...

class CompileCommands:
    def __len__(self) -> int: ...
    def __getitem__(self, i: int) -> CompileCommand: ...

class CompilationDatabase(ClangObject):
    @staticmethod
    def fromDirectory(buildDir: str) -> CompilationDatabase: ...
    def getCompileCommands(self, filename: str) -> CompileCommands | None: ...
    def getAllCompileCommands(self) -> CompileCommands: ...

class Token(Structure):
    _fields_: ClassVar[list[tuple[str, type]]]
    @property
    def spelling(self) -> str: ...
    @property
    def kind(self) -> TokenKind: ...
    @property
    def location(self) -> SourceLocation: ...
    @property
    def extent(self) -> SourceRange: ...
    @property
    def cursor(self) -> Cursor: ...

class Config:
    library_path: ClassVar[str]
    library_file: ClassVar[str | None]
    compatibility_check: ClassVar[bool]
    loaded: ClassVar[bool]
    @staticmethod
    def set_library_path(path: str) -> None: ...
    @staticmethod
    def set_library_file(filename: str) -> None: ...
    @staticmethod
    def set_compatibility_check(check_status: bool) -> None: ...
    @property
    def lib(self) -> object: ...
    def get_filename(self) -> str: ...
    def get_cindex_library(self) -> object: ...
    def function_exists(self, name: str) -> bool: ...

conf: Config
