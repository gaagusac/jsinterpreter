"""
JSInterpreter

A simple JavaScript interpreter - gaagusac - FIUSAC.
"""

from flask import Flask, render_template, url_for, request, jsonify
import ply.lex as lex
import ply.yacc as yacc
from enum import Enum
import traceback

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/eval", methods=["POST"])
def evaluate():
    olcscript_parser = None
    try:
        # Get the request with a dictionary of values
        request_dict = request.get_json()
        source_code = request_dict["payload"]
        # Create the parser
        olcscript_parser = OLCScriptParser(source_code)
        ast = olcscript_parser.parse()
        if len(olcscript_parser.errors) > 0:
            return jsonify(
                {
                    "result": olcscript_parser.errors_as_string,
                    "errs": (
                        olcscript_parser.errors_as_string
                        if len(olcscript_parser.errors) > 0
                        else ""
                    ),
                }
            )
        # A global context
        global_context = GlobalContext("<global>")
        # The interpreter
        olcscript_interpreter = Interpreter(
            olcscript_parser.lexer.lexdata, global_context, "file.olc"
        )
        result = olcscript_interpreter.visit(ast, global_context)
        the_result = olcscript_interpreter.log_as_string
        return jsonify(
            {
                "result": the_result,
                "errs": (
                    olcscript_interpreter.errors_as_string
                    if len(olcscript_interpreter.errors) > 0
                    else ""
                ),
                "symbols": (
                    olcscript_interpreter.symbols_as_string
                    if len(olcscript_interpreter.symbols) > 0
                    else ""
                ),
            }
        )
    except BaseException as e:
        print(e.with_traceback())


# #########################################################################################
#                ___  _     ____ ____       _       _
#               / _ \| |   / ___/ ___|  ___(_)_ __ | |_
#              | | | | |  | |   \___ \ / __| | '_ \| __|
#              | |_| | |__| |___ ___) | (__| | |_) | |_
#               \___/|_____\____|____/ \___|_| .__/ \__|
#                                            |_|
# #########################################################################################


# ------------------------------------------------------------------------------------
#                                 ERRORS
# ------------------------------------------------------------------------------------


def mark_error_location(text, line, column):
    padding = f"{line}:  "
    result = f"{padding}{text}\n"
    result += " " * (len(padding) + column + 1) + "^" + "\n"
    return result


class ErrorType(Enum):
    LEXICAL = 1
    SYNTAX = 2
    SEMANCTIC = 3


class Error:
    def __init__(self, error_type, text_line, line, column, error_name, details, file):
        self.text_line = text_line
        self.error_type = error_type
        self.error_name = error_name
        self.line = line
        self.column = column
        self.details = details
        self.file = file

    def as_string(self):
        result = ""

        if self.error_type == ErrorType.LEXICAL:
            result = f">>> LEXICAL ERROR:\n"
        elif self.error_type == ErrorType.SYNTAX:
            result = f">>> SYNTAX ERROR:\n"

        result += f"File: {self.file}, line: {self.line}, column: {self.column + 1}\n"
        result += f"{self.error_name}: {self.details}\n"
        result += mark_error_location(self.text_line, self.line, self.column)

        return result


class IllegalCharError(Error):
    def __init__(self, text_line, line, column, error_name, details, file):
        super().__init__(
            ErrorType.LEXICAL, text_line, line, column, error_name, details, file
        )


class InvalidSyntaxError(Error):
    def __init__(self, text_line, line, column, error_name, details, file):
        super().__init__(
            ErrorType.SYNTAX, text_line, line, column, error_name, details, file
        )


class RTError(Error):
    def __init__(self, text_line, line, column, error_name, details, context, file):
        super().__init__(
            ErrorType.SEMANCTIC, text_line, line, column, error_name, details, file
        )
        self.context = context

    def generate_traceback(self):
        result = ""
        line = self.line
        column = self.column
        file = self.file
        ctx = self.context

        while ctx:
            result = (
                f"   File {file}, line {str(line)}, column: {str(self.column)}, in {ctx.display_name}\n"
                + result
            )
            line = ctx.parent_entry_point
            ctx = ctx.parent

        return "Traceback (most recent call last):\n" + result

    def as_string(self):
        result = f">>> SEMANTIC(RUNTIME) ERROR:\n"
        result += self.generate_traceback()
        result += f"{self.error_name}: {self.details}\n\n"
        result += mark_error_location(self.text_line, self.line, self.column)
        return result


# ------------------------------------------------------------------------------------
#                                 TYPES
# ------------------------------------------------------------------------------------


class TypeSpec:
    def __init__(self, form):
        self.form = form
        self.identifier = None
        self.attributes = {}
        self.base_type = None

    def get_form(self):
        return self.form

    def set_form(self, form):
        self.form = form

    def set_identifier(self, identifier):
        self.identifier = identifier

    def get_identifier(self):
        return self.identifier

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def get_attribute(self, key):
        return self.attributes.get(key, None)

    def get_base_type(self):
        if (
            self.form == TypeForm.ARRAY
            or self.form == TypeForm.MATRIX
            or self.form == TypeForm.INTERFACE
        ):
            return self.base_type
        return self

    def set_base_type(self, base_type):
        self.base_type = base_type


class TypeForm(Enum):
    NUMBER = 1
    FLOAT = 2
    BOOLEAN = 3
    STRING = 4
    CHAR = 5
    ARRAY = 6
    MATRIX = 7
    INTERFACE = 8
    NULL = 9
    UNDEFINED = 10


class TypeKey(Enum):
    ARRAY_ELEMENT_TYPE = 1


class Predefined:
    # predefined types
    number_type = None
    float_type = None
    boolean_type = None
    char_type = None
    string_type = None
    null_type = None
    undefined_type = None

    # predefined identifiers
    number_id = None
    float_id = None
    boolean_id = None
    char_id = None
    string_id = None
    null_id = None
    undefined_id = None

    @staticmethod
    def initialize_types(context):
        # number type
        Predefined.number_id = context.enter_type("number")
        Predefined.number_type = TypeFactory.create_type(TypeForm.NUMBER)
        Predefined.number_type.set_identifier(Predefined.number_id)
        Predefined.number_id.set_definition(Definition.TYPE)
        Predefined.number_id.set_type_spec(Predefined.number_type)

        # float type
        Predefined.float_id = context.enter_type("float")
        Predefined.float_type = TypeFactory.create_type(TypeForm.FLOAT)
        Predefined.float_type.set_identifier(Predefined.float_id)
        Predefined.float_id.set_definition(Definition.TYPE)
        Predefined.float_id.set_type_spec(Predefined.float_type)

        # boolean type
        Predefined.boolean_id = context.enter_type("boolean")
        Predefined.boolean_type = TypeFactory.create_type(TypeForm.BOOLEAN)
        Predefined.boolean_type.set_identifier(Predefined.boolean_id)
        Predefined.boolean_id.set_definition(Definition.TYPE)
        Predefined.boolean_id.set_type_spec(Predefined.boolean_type)

        # char type
        Predefined.char_id = context.enter_type("char")
        Predefined.char_type = TypeFactory.create_type(TypeForm.CHAR)
        Predefined.char_type.set_identifier(Predefined.char_id)
        Predefined.char_id.set_definition(Definition.TYPE)
        Predefined.char_id.set_type_spec(Predefined.char_type)

        # string type
        Predefined.string_id = context.enter_type("string")
        Predefined.string_type = TypeFactory.create_type(TypeForm.STRING)
        Predefined.string_type.set_identifier(Predefined.string_id)
        Predefined.string_id.set_definition(Definition.TYPE)
        Predefined.string_id.set_type_spec(Predefined.string_type)

        # null type
        Predefined.null_id = context.enter_type("null")
        Predefined.null_type = TypeFactory.create_type(TypeForm.NULL)
        Predefined.null_type.set_identifier(Predefined.null_id)
        Predefined.null_id.set_definition(Definition.TYPE)
        Predefined.null_id.set_type_spec(Predefined.null_type)

        # undefined type
        Predefined.undefined_id = context.enter_type("undefined")
        Predefined.undefined_type = TypeFactory.create_type(TypeForm.UNDEFINED)
        Predefined.undefined_type.set_identifier(Predefined.undefined_id)
        Predefined.undefined_id.set_definition(Definition.TYPE)
        Predefined.undefined_id.set_type_spec(Predefined.undefined_type)

    @staticmethod
    def initialize(context):
        Predefined.initialize_types(context)


class Definition(Enum):
    CONSTANT = 1
    TYPE = 2
    VARIABLE = 3
    FIELD = 4
    VALUE_PARAMETER = 5
    REF_PARAMETER = 6
    FUNCTION = 7


class TypeFactory:

    @staticmethod
    def create_type(form):
        return TypeSpec(form)


# ------------------------------------------------------------------------------------
#                                 SYMBOL TABLE
# ------------------------------------------------------------------------------------


class SymTab:

    def __init__(self):
        self._entries = {}

    def enter(self, name):
        entry = SymtabEntry(name, self)
        self._entries[name] = entry

        return entry

    def lookup(self, name):
        return self._entries.get(name, None)

    def entries(self):
        return [str(key) for key in self._entries.keys()]


class SymtabEntry:

    def __init__(self, name, symtab):
        self.name = name
        self.symtab = symtab
        self.definition = None
        self.type_spec = None
        self._entries = {}

    def set_attribute(self, key, value):
        self._entries[key] = value

    def get_attribute(self, key):
        return self._entries.get(key, None)

    def set_definition(self, definition):
        self.definition = definition

    def get_definition(self):
        return self.definition

    def set_type_spec(self, type_spec):
        self.type_spec = type_spec

    def get_type_spec(self):
        return self.type_spec


class SymtabKey(Enum):
    RUNTIME_VALUE = 1


# ------------------------------------------------------------------------------------
#                                 CONTEXT
# ------------------------------------------------------------------------------------


class GlobalContext:
    def __init__(self, display_name, parent=None, parent_entry_point=None):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_point = parent_entry_point
        self.variables = SymTab()
        self.functions = {}
        self.interfaces = {}
        self.types = SymTab()
        Predefined.initialize_types(self)

    def enter_interface(self, name, fields):
        self.interfaces[name] = fields

    def lookup_interface(self, name):
        return self.interfaces.get(name, None)

    def enter_type(self, name):
        return self.types.enter(name)

    def lookup_type(self, name):
        return self.types.lookup(name)

    def enter(self, name):
        return self.variables.enter(name)

    def enter_function(self, name, value):
        self.functions[name] = value

    def lookup_function(self, name):
        return self.functions.get(name, None)

    def lookup(self, name):
        entry = self.variables.lookup(name)
        return entry

    def lookup_local(self, name):
        return self.lookup(name)

    def is_break_allowed(self):
        return False

    def is_continue_allowed(self):
        return False

    def is_return_allowed(self):
        return False


class IfContext:
    def __init__(self, display_name, parent=None, parent_entry_point=None):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_point = parent_entry_point
        self.variables = SymTab()

    def is_break_allowed(self):
        allow = False
        if not allow and self.parent:
            allow = self.parent.is_break_allowed()
        return allow

    def is_continue_allowed(self):
        allow = False
        if not allow and self.parent:
            allow = self.parent.is_continue_allowed()
        return allow

    def is_return_allowed(self):
        allow = False
        if not allow and self.parent:
            allow = self.parent.is_return_allowed()
        return allow

    def lookup_local(self, name):
        return self.variables.lookup(name)

    def lookup(self, name):
        entry = self.variables.lookup(name)
        if not entry and self.parent:
            entry = self.parent.lookup(name)
        return entry

    def enter(self, name):
        return self.variables.enter(name)


class WhileContext:
    def __init__(self, display_name, parent=None, parent_entry_pos=None):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_point = parent_entry_pos
        self.variables = SymTab()

    def is_break_allowed(self):
        return True

    def is_continue_allowed(self):
        return True

    def is_return_allowed(self):
        allow = False
        if not allow and self.parent:
            allow = self.parent.is_return_allowed()
        return allow

    def lookup(self, name):
        entry = self.variables.lookup(name)
        if not entry and self.parent:
            entry = self.parent.lookup(name)
        return entry

    def lookup_local(self, name):
        return self.variables.lookup(name)

    def enter(self, name):
        return self.variables.enter(name)


class ForContext:
    def __init__(self, display_name, parent=None, parent_entry_pos=None):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_point = parent_entry_pos
        self.variables = SymTab()

    def is_break_allowed(self):
        return True

    def is_continue_allowed(self):
        return True

    def is_return_allowed(self):
        allow = False
        if not allow and self.parent:
            allow = self.parent.is_return_allowed()
        return allow

    def lookup(self, name):
        entry = self.variables.lookup(name)
        if not entry and self.parent:
            entry = self.parent.lookup(name)
        return entry

    def lookup_local(self, name):
        return self.variables.lookup(name)

    def enter(self, name):
        return self.variables.enter(name)


class FunctionContext:
    def __init__(self, display_name, parent=None, parent_entry_pos=None):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_point = parent_entry_pos
        self.variables = SymTab()

    def is_break_allowed(self):
        allow = False
        if not allow and self.parent:
            allow = self.parent.is_break_allowed()

    def is_continue_allowed(self):
        allow = False
        if not allow and self.parent:
            allow = self.parent.is_continue_allowed()
        return allow

    def is_return_allowed(self):
        return True

    def lookup(self, name):
        entry = self.variables.lookup(name)
        if not entry and self.parent:
            entry = self.parent.lookup(name)
        return entry

    def lookup_local(self, name):
        return self.variables.lookup(name)

    def enter(self, name):
        return self.variables.enter(name)


class CaseContext:

    def __init__(self, display_name, parent=None, parent_entry_pos=None):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_point = parent_entry_pos
        self.variables = SymTab()

    def is_break_allowed(self):
        return True

    def is_continue_allowed(self):
        allow = False
        if not allow and self.parent:
            allow = self.parent.is_return_allowed()
        return allow

    def is_return_allowed(self):
        allow = False
        if not allow and self.parent:
            allow = self.parent.is_return_allowed()
        return allow

    def lookup(self, name):
        entry = self.variables.lookup(name)
        if not entry and self.parent:
            entry = self.parent.lookup(name)
        return entry

    def lookup_local(self, name):
        return self.variables.lookup(name)

    def enter(self, name):
        return self.variables.enter(name)


class InterfaceContext:
    def __init__(self, display_name, parent=None, parent_entry_pos=None):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_point = parent_entry_pos
        self.variables = SymTab()

    def lookup(self, name):
        return self.variables.lookup(name)

    def lookup_local(self, name):
        return self.variables.lookup(name)

    def enter(self, name):
        return self.variables.enter(name)


# ------------------------------------------------------------------------------------
#                                 AST
# ------------------------------------------------------------------------------------


class NumberLiteralNode:
    def __init__(self, token):
        self.token = token
        self.value = token.value

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class FloatLiteralNode:
    def __init__(self, token):
        self.token = token
        self.value = token.value

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class StringLiteralNode:
    def __init__(self, token):
        self.token = token
        self.value = token.value

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class BooleanLiteralNode:
    def __init__(self, token):
        self.token = token
        self.value = True if token.value == "true" else False

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class NullLiteralNode:
    def __init__(self, token):
        self.token = token

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class CharLiteralNode:
    def __init__(self, token):
        self.token = token
        self.value = token.value

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class ArithmeticOperationNode:
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

        self.line = operator.lineno
        self.column = operator.lexpos

    def __repr__(self):
        # buffer = f'({self.operator.value}'
        # buffer += f' {self.left.__repr__()}'
        # buffer += f' {self.right.__repr__()}'
        # buffer += ')'
        # return buffer
        pass


class RelationalOperationNode:
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

        self.line = operator.lineno
        self.column = operator.lexpos

    def __repr__(self):
        # buffer = f'({self.operator.value}'
        # buffer += f' {self.left.__repr__()}'
        # buffer += f' {self.right.__repr__()}'
        # buffer += ')'
        # return buffer
        pass


class LogicalOperationNode:
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

        self.line = operator.lineno
        self.column = operator.lexpos

    def __repr__(self):
        # buffer = f'({self.operator.value}'
        # buffer += f' {self.left.__repr__()}'
        # buffer += f' {self.right.__repr__()}'
        # buffer += ')'
        # return buffer
        pass


class EqualityOperationNode:
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

        self.line = operator.lineno
        self.column = operator.lexpos

    def __repr__(self):
        # buffer = f'({self.operator.value}'
        # buffer += f' {self.left.__repr__()}'
        # buffer += f' {self.right.__repr__()}'
        # buffer += ')'
        # return buffer
        pass


class UnaryOperationNode:
    def __init__(self, operator, expr_node):
        self.operator = operator
        self.expr_node = expr_node

        self.line = operator.lineno
        self.column = operator.lexpos

    def __repr__(self):
        # buffer = f'({self.operator.value} '
        # buffer += self.expr_node.__repr__()
        # buffer += ')'
        # return buffer
        pass


class TypeOfNode:
    def __init__(self, token, expr_node):
        self.token = token
        self.expr_node = expr_node

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class VarDeclarationNode:
    def __init__(
        self, token, identifier_node, init_expr_node, is_constant, type_spec_node=None
    ):
        self.token = token
        self.identifier_node = identifier_node
        self.init_expr_node = init_expr_node
        self.is_constant = is_constant
        self.type_spec_node = type_spec_node

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class IdentifierNode:
    def __init__(self, token):
        self.token = token
        self.name = token.value

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class ConsoleLogNode:
    def __init__(self, token, arguments):
        self.token = token
        self.arguments = arguments

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class ObjectKeysNode:
    def __init__(self, token, argument):
        self.token = token
        self.argument = argument

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class ObjectValuesNode:
    def __init__(self, token, argument):
        self.token = token
        self.argument = argument

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class MemberSetExpression:
    def __init__(self, token, lvalue, target, rvalue):
        self.token = token
        self.lvalue = lvalue
        self.target = target
        self.rvalue = rvalue

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class ArraySetExpression:
    def __init__(self, token, lvalue, target, rvalue):
        self.token = token
        self.lvalue = lvalue
        self.target = target
        self.rvalue = rvalue

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class ArrayAccessNode:
    def __init__(self, left, token, right):
        self.left = left
        self.token = token
        self.right = right

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class CallExprNode:
    def __init__(self, caller, token, arguments):
        self.caller = caller
        self.token = token
        self.arguments = arguments

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class MemberAccessNode:
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

        self.line = operator.lineno
        self.column = operator.lexpos

    def __repr__(self):
        pass


class BlockNode:
    def __init__(self, token, statements):
        self.token = token
        self.statements = statements

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class ProgramNode:
    def __init__(self, statements):
        self.statements = statements

        self.line = 1
        self.column = 1

    def __repr__(self):
        pass


class BreakNode:
    def __init__(self, token):
        self.token = token

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class ContinueNode:
    def __init__(self, token):
        self.token = token

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class ReturnNode:
    def __init__(self, token, expr_node=None):
        self.token = token
        self.expr_node = expr_node

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class IfElseNode:
    def __init__(self, token, expr_node, consequence, alternative=None):
        self.token = token
        self.expr_node = expr_node
        self.consequence = consequence
        self.alternative = alternative

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class WhileNode:
    def __init__(self, token, expr_node, block):
        self.token = token
        self.expr_node = expr_node
        self.block = block

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class AssignNode:
    def __init__(self, token, target, rvalue):
        self.token = token
        self.target = target
        self.rvalue = rvalue

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class BuiltinPush:
    def __init__(self, token, arr, argument):
        self.token = token
        self.arr = arr
        self.argument = argument

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class BuiltinIndexOf:
    def __init__(self, token, arr, argument):
        self.token = token
        self.arr = arr
        self.argument = argument

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class BuiltinPop:
    def __init__(self, token, arr):
        self.token = token
        self.arr = arr

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class BuiltinLength:
    def __init__(self, token, arr):
        self.token = token
        self.arr = arr

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class BuiltinParseInt:
    def __init__(self, token, argument):
        self.token = token
        self.argument = argument

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class BuiltinParseFloat:
    def __init__(self, token, argument):
        self.token = token
        self.argument = argument

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class BuiltinToString:
    def __init__(self, token, argument):
        self.token = token
        self.argument = argument

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class BuiltinToLowerCase:
    def __init__(self, token, argument):
        self.token = token
        self.argument = argument

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class BuiltinToUpperCase:
    def __init__(self, token, argument):
        self.token = token
        self.argument = argument

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class BuiltinJoin:
    def __init__(self, token, arr):
        self.token = token
        self.arr = arr

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class ArrayNode:
    def __init__(self, token, elements):
        self.token = token
        self.elements = elements

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class FunctionNode:
    def __init__(self, token, name, parameters, body, ret_type_spec=None):
        self.token = token
        self.name = name
        self.parameters = parameters
        self.body = body
        self.ret_type_spec = ret_type_spec

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class ParameterNode:
    def __init__(self, token, parameter_name, parameter_type_spec):
        self.token = token
        self.parameter_name = parameter_name
        self.parameter_type_spec = parameter_type_spec

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class InterfaceNode:
    def __init__(self, token, name, fields):
        self.token = token
        self.name = name
        self.fields = fields

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class InterfaceExprNode:
    def __init__(self, token, expr_fields):
        self.token = token
        self.expr_fields = expr_fields

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class SwitchCaseNode:
    def __init__(
        self,
        token,
        switch_expr_node,
        cases_node,
        number_of_default_nodes,
        default_case_node=None,
    ):
        self.token = token
        self.switch_expr_node = switch_expr_node
        self.cases_node = cases_node
        self.number_of_default_nodes = number_of_default_nodes
        self.default_case_node = default_case_node

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class CaseNode:
    def __init__(self, token, case_expr_node, statements):
        self.token = token
        self.case_expr_node = case_expr_node
        self.statements = statements

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class DefaultCaseNode:
    def __init__(self, token, statements):
        self.token = token
        self.statements = statements

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class ForNode:
    def __init__(self, token, init_node, test_node, update_node, statements):
        self.token = token
        self.init_node = init_node
        self.test_node = test_node
        self.update_node = update_node
        self.statements = statements

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class ForOfNode:
    def __init__(self, token, left, right, block):
        self.token = token
        self.left = left
        self.right = right
        self.block = block

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class TypeNode:
    def __init__(self, token, type_, dims=0):
        self.token = token
        self.type_ = type_
        self.dims = dims

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class FieldNode:
    def __init__(self, token, field_name, field_type):
        self.token = token
        self.field_name = field_name
        self.field_type = field_type

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class FieldExprNode:
    def __init__(self, token, field_name, expr_node):
        self.token = token
        self.field_name = field_name
        self.expr_node = expr_node

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


class TernaryOperationNode:
    def __init__(self, token, expr_node, true_expr, false_expr):
        self.token = token
        self.expr_node = expr_node
        self.true_expr = true_expr
        self.false_expr = false_expr

        self.line = token.lineno
        self.column = token.lexpos

    def __repr__(self):
        pass


# ------------------------------------------------------------------------------------
#                                 PARSER
# ------------------------------------------------------------------------------------


class OLCScriptParser:
    """Class for a lexer/parser that has the rules defined as methods."""

    def __init__(self, source_code, file=None):
        """Create an instances of Parser."""
        self.lexer = lex.lex(module=self)
        self.parser = yacc.yacc(module=self)
        self.errors = []
        self.log = []
        self.source_code = source_code
        self.source_code_listing = self.make_source_code_listing()
        self.file = file or "<stdin>"
        self.errors_as_string = ""

    def parse(self):
        """Parse a string."""
        # Parse the input string
        parse_result = self.parser.parse(self.source_code)
        # Build a string with the error list
        self.errors_as_string = "\n".join([err for err in self.errors])
        print(self.errors_as_string)
        # Return the parse result, a list of ast nodes.
        return parse_result

    def make_source_code_listing(self):
        listing = {}
        lines = self.source_code.split("\n")
        counter = 1
        for line in lines:
            listing[counter] = line
            counter += 1
        return listing

    def execute(self):
        context = GlobalContext("<global>")
        ast = self.parse()
        interpreter = Interpreter(self.lexer.lexdata, context, self.file)
        result = interpreter.visit(ast, context)

    def run(self):
        """runs a repl"""
        context = GlobalContext("<global>")
        while True:
            try:
                s = input("> ")
            except EOFError:
                break
            if not s:
                continue
            ast = self.parse(s)
            interpreter = Interpreter(self.lexer.lexdata)
            result = interpreter.visit(ast, context)

    reserved = {
        "true": "TRUE",
        "false": "FALSE",
        "null": "NULL",
        "var": "VAR",
        "const": "CONST",
        "console": "CONSOLE",
        "log": "LOG",
        "if": "IF",
        "else": "ELSE",
        "break": "BREAK",
        "continue": "CONTINUE",
        "return": "RETURN",
        "while": "WHILE",
        "for": "FOR",
        "of": "OF",
        "function": "FUNCTION",
        "switch": "SWITCH",
        "case": "CASE",
        "default": "DEFAULT",
        "interface": "INTERFACE",
        "typeof": "TYPEOF",
        "parseInt": "PARSEINT",
        "parseFloat": "PARSEFLOAT",
    }

    tokens = (
        "NUMBER",
        "FLOAT",
        "STRING",
        "CHAR",
        "IDENTIFIER",
        "EQ",
        "LT",
        "LTE",
        "GT",
        "GTE",
        "EQ_EQ",
        "BANG",
        "BANG_EQ",
        "COMPLUS",
        "COMMINUS",
        "COMTIMES",
        "COMDIVIDE",
        "COMMOD",
        "PPINC",
        "PPDEC",
        "AND",
        "OR",
        "QMARK",
        "PLUS",
        "MINUS",
        "MOD",
        "TIMES",
        "DIVIDE",
        "DOT",
        "SEMICOLON",
        "COMMA",
        "COLON",
        "LPAREN",
        "RPAREN",
        "RBRACER",
        "LBRACER",
        "LBRACKET",
        "RBRACKET",
    ) + tuple(reserved.values())

    # Tokens
    t_PPINC = r"\+\+"
    t_PLUS = r"\+"
    t_PPDEC = r"--"
    t_MINUS = r"-"
    t_MOD = r"%"
    t_TIMES = r"\*"
    t_DIVIDE = r"/"
    t_LPAREN = r"\("
    t_RPAREN = r"\)"
    t_LTE = r"<="
    t_LT = r"<"
    t_GTE = r">="
    t_GT = r">"
    t_COMPLUS = r"\+\="
    t_COMMINUS = r"-="
    t_COMTIMES = r"\*\="
    t_COMDIVIDE = r"/="
    t_COMMOD = r"%="
    t_EQ_EQ = r"=="
    t_EQ = r"="
    t_BANG_EQ = r"!="
    t_BANG = r"!"
    t_AND = r"&&"
    t_OR = r"\|\|"
    t_DOT = r"\."
    t_SEMICOLON = r";"
    t_LBRACER = r"\{"
    t_RBRACER = r"\}"
    t_LBRACKET = r"\["
    t_RBRACKET = r"\]"
    t_COMMA = r","
    t_COLON = r":"
    t_QMARK = r"\?"

    def t_FLOAT(self, t):
        r"\d+\.\d+"
        try:
            t.value = float(t.value)
        except ValueError:
            print("Float value too large %s" % t.value)
            t.value = 0.0
        return t

    def t_NUMBER(self, t):
        r"\d+"
        try:
            t.value = int(t.value)
        except ValueError:
            print("Integer value too large %s" % t.value)
            t.value = 0
        return t

    def t_STRING(self, t):
        r"\"(?:\\.|[^\"\\])*\" "
        # t.value = t.value[1:-1].encode().decode("unicode_escape")
        t.value = str(t.value[1:-1])
        return t

    def t_IDENTIFIER(self, t):
        r"[a-zA-Z_][a-zA-Z0-9_]*"
        t.type = self.reserved.get(t.value, "IDENTIFIER")
        return t

    def t_CHAR(self, t):
        r"'(?:\\.|[^\'\\])*'"
        t.value = str(t.value[1:-1])
        return t

    t_ignore = " \t"

    # this ignores one line c-style comment
    t_ignore_COMMENT_LINE = r"\/\/.*"

    # ignore multi-line comments
    def t_ignore_COMENT_BLOCK(self, t):
        r"\/\*[^*]*\*+(?:[^/*][^*]*\*+)*\/"
        t.lexer.lineno += t.value.count("\n")

    def find_column(self, token):
        line_start = self.lexer.lexdata.rfind("\n", 0, token.lexpos) + 1
        return (token.lexpos - line_start) + 1

    def t_newline(self, t):
        r"\n+"
        self.lexer.lineno += t.value.count("\n")

    def t_error(self, t):
        the_error = IllegalCharError(
            self.source_code_listing.get(self.lexer.lineno),
            self.lexer.lineno,
            self.find_column(t),
            f"illegal character",
            f"invalid character '{t.value[0]}' found.",
            self.file,
        )
        print(the_error.as_string())
        self.errors.append(the_error.as_string())
        t.lexer.skip(1)

    # Parsing rules

    precedence = (
        ("right", "QMARK", "COLON"),
        ("left", "OR"),
        ("left", "AND"),
        ("nonassoc", "EQ_EQ", "BANG_EQ"),
        ("nonassoc", "LT", "LTE", "GT", "GTE"),
        ("left", "PLUS", "MINUS"),
        ("left", "TIMES", "DIVIDE", "MOD"),
        ("right", "UMINUS", "TYPEOF"),
        ("left", "DOT"),
    )

    # set ths token position relative to the beginning(index 0) of a line.
    def set_token_column(self, t):
        t.lexpos = self.find_column(t)

    # ############################### PROGRAM ##########################################
    # this production should be the root node of the ast
    # is a list of statement nodes.
    def p_program(self, p):
        "program : declarations"
        p[0] = ProgramNode(p[1])

    def p_declaration_list(self, p):
        """
        declarations : declarations declaration
                     | declaration
        """
        if len(p) > 2:
            p[1].append(p[2])
            p[0] = p[1]
        else:
            p[0] = [p[1]]

    # ################################## DECLARATIONS ##########################################
    # A declaration is a statement
    def p_declaration_statement(self, p):
        "declaration : statement"
        p[0] = p[1]

    # ################################# INTERFACE ################################################
    # interface declaration statement
    def p_interface_declaration_statement(self, p):
        "declaration : INTERFACE IDENTIFIER LBRACER field_list RBRACER"
        self.set_token_column(p.slice[1])
        p[0] = InterfaceNode(p.slice[1], p[2], p[4])

    def p_field_list(self, p):
        """
        field_list : field_list field
                   | field
        """
        if len(p) > 2:
            p[1].append(p[2])
            p[0] = p[1]
        else:
            p[0] = [p[1]]

    def p_field(self, p):
        "field : IDENTIFIER COLON type_ SEMICOLON"
        self.set_token_column(p.slice[2])
        p[0] = FieldNode(p.slice[2], p[1], p[3])

    # Types
    def p_lang_types(self, p):
        """
        type_ : IDENTIFIER dims
              | IDENTIFIER
        """
        self.set_token_column(p.slice[1])
        if len(p) > 2:
            p[0] = TypeNode(p.slice[1], p[1], p[2])
        else:
            p[0] = TypeNode(p.slice[1], p[1])

    # type dimensions
    def p_lang_types_dims(self, p):
        """
        dims : dims dim
             | dim
        """
        if len(p) > 2:
            p[1] = p[1] + p[2]
            p[0] = p[1]
        else:
            p[0] = p[1]

    def p_lang_types_dim(self, p):
        "dim : LBRACKET RBRACKET"
        p[0] = 1

    # ################################### FUNCTION ##############################################
    # Function declaration statement
    def p_function_declaration_statement_with_args(self, p):
        "declaration : FUNCTION IDENTIFIER LPAREN function_parameter_list RPAREN block"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = FunctionNode(p.slice[1], IdentifierNode(p.slice[2]), p[4], p[6])

    def p_function_declaration_statement_no_args(self, p):
        "declaration : FUNCTION IDENTIFIER LPAREN RPAREN block"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = FunctionNode(p.slice[1], IdentifierNode(p.slice[2]), [], p[5])

    def p_function_declaration_statement_no_args_but_ret_type(self, p):
        "declaration : FUNCTION IDENTIFIER LPAREN RPAREN COLON type_ block"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = FunctionNode(p.slice[1], IdentifierNode(p.slice[2]), [], p[7], p[6])

    def p_function_declaration_statement_with_args_and_ret_type(self, p):
        "declaration : FUNCTION IDENTIFIER LPAREN function_parameter_list RPAREN COLON type_ block"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = FunctionNode(p.slice[1], IdentifierNode(p.slice[2]), p[4], p[8], p[7])

    def p_function_parameter_list(self, p):
        """function_parameter_list : function_parameter_list COMMA parameter
        | parameter
        """
        if len(p) > 2:
            p[1].append(p[3])
            p[0] = p[1]
        else:
            p[0] = [p[1]]

    def p_function_parameter(self, p):
        "parameter : IDENTIFIER COLON type_"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = ParameterNode(p.slice[2], IdentifierNode(p.slice[1]), p[3])

    # ----------------------------- IF/ELSEIF/ELSE --------------------------------------------
    def p_statement_if(self, p):
        "statement : ifstmt"
        p[0] = p[1]

    def p_statement_if_single(self, p):
        "ifstmt : IF LPAREN expression RPAREN block"
        self.set_token_column(p.slice[1])
        p[0] = IfElseNode(p.slice[1], p[3], p[5])

    def p_statement_if_else(self, p):
        "ifstmt : IF LPAREN expression RPAREN block ELSE block"
        self.set_token_column(p.slice[1])
        p[0] = IfElseNode(p.slice[1], p[3], p[5], p[7])

    def p_statement_if_elseif(self, p):
        "ifstmt : IF LPAREN expression RPAREN block elseiflist"
        self.set_token_column(p.slice[1])
        p[0] = IfElseNode(p.slice[1], p[3], p[5], p[6])

    def p_statement_elseif_single(self, p):
        "elseiflist : ELSE IF LPAREN expression RPAREN block"
        self.set_token_column(p.slice[1])
        p[0] = IfElseNode(p.slice[1], p[4], p[6])

    def p_statement_elseif_else(self, p):
        "elseiflist : ELSE IF LPAREN expression RPAREN block ELSE block"
        self.set_token_column(p.slice[1])
        p[0] = IfElseNode(p.slice[1], p[4], p[6], p[8])

    def p_statement_elseif_list(self, p):
        "elseiflist : ELSE IF LPAREN expression RPAREN block elseiflist"
        self.set_token_column(p.slice[1])
        p[0] = IfElseNode(p.slice[1], p[4], p[6], p[7])

    # ------------------------------------ SWITCH/CASE ---------------------------------------------------
    def p_statement_switch(self, p):
        "statement : switch"
        p[0] = p[1]

    def p_statement_switch_case(self, p):
        "switch : SWITCH LPAREN expression RPAREN LBRACER cases RBRACER"
        default_nodes = []
        number_of_default_cases = 0
        for case in p[6]:
            if isinstance(case, DefaultCaseNode):
                default_nodes.append(case)
                number_of_default_cases += 1
        for default_case in default_nodes:
            p[6].remove(default_case)
        self.set_token_column(p.slice[1])
        p[0] = SwitchCaseNode(
            p.slice[1], p[3], p[6], number_of_default_cases, default_nodes[-1]
        )

    def p_statement_case(self, p):
        """
        cases : cases case
              | case
        """
        if len(p) > 2:
            p[1].append(p[2])
            p[0] = p[1]
        else:
            p[0] = [p[1]]

    def p_statement_cases(self, p):
        "case : CASE expression COLON statements"
        self.set_token_column(p.slice[1])
        p[0] = CaseNode(p.slice[1], p[2], p[4])

    def p_statements_cases_empty(self, p):
        "case : CASE expression COLON"
        self.set_token_column(p.slice[1])
        p[0] = CaseNode(p.slice[1], p[2], [])

    def p_statement_default_case(self, p):
        "case : DEFAULT COLON statements"
        self.set_token_column(p.slice[1])
        p[0] = DefaultCaseNode(p.slice[1], p[3])

    # ----------------------------------------- WHILE -------------------------------------------------------
    def p_statement_whlle(self, p):
        "statement : WHILE LPAREN expression RPAREN block"
        self.set_token_column(p.slice[1])
        p[0] = WhileNode(p.slice[1], p[3], p[5])

    # ------------------------------------------ FOR --------------------------------------------------------
    def p_statement_for_loop(self, p):
        "statement : for"
        p[0] = p[1]

    def p_statement_for(self, p):
        "for : FOR LPAREN for_init_list SEMICOLON expression SEMICOLON for_update_list RPAREN block"
        self.set_token_column(p.slice[1])
        p[0] = ForNode(p.slice[1], p[3], p[5], p[7], p[9])

    def p_statement_for_init_list(self, p):
        """
        for_init_list : for_init_list COMMA for_init
                      | for_init
        """
        if len(p) > 2:
            p[1].append(p[3])
            p[0] = p[1]
        else:
            p[0] = [p[1]]

    def p_statement_for_init(self, p):
        "for_init : VAR IDENTIFIER COLON type_ EQ expression"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = VarDeclarationNode(
            p.slice[1], IdentifierNode(p.slice[2]), p[6], False, p[4]
        )

    def p_statement_for_init_1(self, p):
        "for_init : VAR IDENTIFIER EQ expression"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = VarDeclarationNode(p.slice[1], IdentifierNode(p.slice[2]), p[4], False)

    def p_statement_for_update_list(self, p):
        """
        for_update_list : for_update_list COMMA for_update
                        | for_update
        """
        if len(p) > 2:
            p[1].append(p[3])
            p[0] = p[1]
        else:
            p[0] = [p[1]]

    def p_statement_for_update_normal(self, p):
        "for_update : expression EQ expression"
        self.set_token_column(p.slice[2])
        p[0] = AssignNode(p.slice[2], p[1], p[3])

    def p_statement_for_update_compound(self, p):
        """
        for_update : expression COMPLUS   expression
                   | expression COMMINUS  expression
                   | expression COMTIMES  expression
                   | expression COMDIVIDE expression
                   | expression COMMOD    expression
        """
        self.set_token_column(p.slice[2])
        if p.slice[2].value == "+=":
            p.slice[2].type = "PLUS"
            p.slice[2].value = "+"
            bin_operation = ArithmeticOperationNode(p[1], p.slice[2], p[3])
        elif p.slice[2].value == "-=":
            p.slice[2].type = "MINUS"
            p.slice[2].value = "-"
            bin_operation = ArithmeticOperationNode(p[1], p.slice[2], p[3])
        elif p.slice[2].value == "*=":
            p.slice[2].type = "TIMES"
            p.slice[2].value = "*"
            bin_operation = ArithmeticOperationNode(p[1], p.slice[2], p[3])
        elif p.slice[2].value == "/=":
            p.slice[2].type = "DIVIDE"
            p.slice[2].value = "/"
            bin_operation = ArithmeticOperationNode(p[1], p.slice[2], p[3])
        else:
            p.slice[2].type = "MOD"
            p.slice[2].value = "%"
            bin_operation = ArithmeticOperationNode(p[1], p.slice[2], p[3])
        p[0] = AssignNode(p.slice[2], p[1], bin_operation)

    def p_statement_for_update_ppinc_prefix(self, p):
        "for_update : PPINC expression"
        self.set_token_column(p.slice[1])
        one_obj = type(
            "",
            (object,),
            {
                "type": "NUMBER",
                "value": int(1),
                "lineno": p.slice[1].lineno,
                "lexpos": p.slice[1].lexpos,
            },
        )()
        one_token = NumberLiteralNode(one_obj)
        p.slice[1].type = "PLUS"
        p.slice[1].value = "+"
        bin_operation = ArithmeticOperationNode(p[2], p.slice[1], one_token)
        p[0] = AssignNode(p.slice[1], p[2], bin_operation)
        pass

    def p_statement_for_update_ppinc_postfix(self, p):
        "for_update : expression PPINC"
        self.set_token_column(p.slice[2])
        one_obj = type(
            "",
            (object,),
            {
                "type": "NUMBER",
                "value": int(1),
                "lineno": p.slice[2].lineno,
                "lexpos": p.slice[2].lexpos,
            },
        )()
        one_token = NumberLiteralNode(one_obj)
        p.slice[2].type = "PLUS"
        p.slice[2].value = "+"
        bin_operation = ArithmeticOperationNode(p[1], p.slice[2], one_token)
        p[0] = AssignNode(p.slice[2], p[1], bin_operation)

    def p_statement_for_update_ppdec_prefix(self, p):
        "for_update : PPDEC expression"
        self.set_token_column(p.slice[1])
        one_obj = type(
            "",
            (object,),
            {
                "type": "NUMBER",
                "value": int(1),
                "lineno": p.slice[1].lineno,
                "lexpos": p.slice[1].lexpos,
            },
        )()
        one_token = NumberLiteralNode(one_obj)
        p.slice[1].type = "MINUS"
        p.slice[1].value = "-"
        bin_operation = ArithmeticOperationNode(p[2], p.slice[1], one_token)
        p[0] = AssignNode(p.slice[1], p[2], bin_operation)

    def p_statement_for_update_ppdec_posfix(self, p):
        "for_update : expression PPDEC"
        self.set_token_column(p.slice[2])
        one_obj = type(
            "",
            (object,),
            {
                "type": "NUMBER",
                "value": int(1),
                "lineno": p.slice[2].lineno,
                "lexpos": p.slice[2].lexpos,
            },
        )()
        one_token = NumberLiteralNode(one_obj)
        p.slice[2].type = "MINUS"
        p.slice[2].value = "-"
        bin_operation = ArithmeticOperationNode(p[1], p.slice[2], one_token)
        p[0] = AssignNode(p.slice[2], p[1], bin_operation)

    # ------------------------------------------ FOR OF --------------------------------------------------------
    def p_statement_forof_loop(self, p):
        "statement : FOR LPAREN VAR IDENTIFIER OF expression RPAREN block"
        self.set_token_column(p.slice[1])
        p[0] = ForOfNode(p.slice[1], p[4], p[6], p[8])

    # ----------------------------------------- ASSIGN ------------------------------------------------
    def p_statement_assign(self, p):
        "statement : assign"
        p[0] = p[1]

    def p_statement_assign_simple(self, p):
        "assign : expression EQ expression SEMICOLON"
        self.set_token_column(p.slice[2])
        if isinstance(p[1], IdentifierNode):
            p[0] = AssignNode(p.slice[2], p[1], p[3])

        elif isinstance(p[1], ArrayAccessNode):
            target = p[1].right
            p[1].right = None
            p[0] = ArraySetExpression(p.slice[2], p[1], target, p[3])

        elif isinstance(p[1], MemberAccessNode):
            target = p[1].right
            p[1].right = None
            p[0] = MemberSetExpression(p.slice[2], p[1], target, p[3])

    def p_statement_assign_compound(self, p):
        """
        assign : expression COMPLUS   expression SEMICOLON
               | expression COMMINUS  expression SEMICOLON
               | expression COMTIMES  expression SEMICOLON
               | expression COMDIVIDE expression SEMICOLON
               | expression COMMOD    expression SEMICOLON
        """
        self.set_token_column(p.slice[2])
        if p.slice[2].value == "+=":
            p.slice[2].type = "PLUS"
            p.slice[2].value = "+"
            bin_operation = ArithmeticOperationNode(p[1], p.slice[2], p[3])
        elif p.slice[2].value == "-=":
            p.slice[2].type = "MINUS"
            p.slice[2].value = "-"
            bin_operation = ArithmeticOperationNode(p[1], p.slice[2], p[3])
        elif p.slice[2].value == "*=":
            p.slice[2].type = "TIMES"
            p.slice[2].value = "*"
            bin_operation = ArithmeticOperationNode(p[1], p.slice[2], p[3])
        elif p.slice[2].value == "/=":
            p.slice[2].type = "DIVIDE"
            p.slice[2].value = "/"
            bin_operation = ArithmeticOperationNode(p[1], p.slice[2], p[3])
        else:
            p.slice[2].type = "MOD"
            p.slice[2].value = "%"
            bin_operation = ArithmeticOperationNode(p[1], p.slice[2], p[3])
        p[0] = AssignNode(p.slice[2], p[1], bin_operation)

    # --------------------------------------- JUMPS ----------------------------------------
    def p_statement_break(self, p):
        "statement : BREAK SEMICOLON"
        self.set_token_column(p.slice[1])
        p[0] = BreakNode(p.slice[1])

    def p_statement_continue(self, p):
        "statement : CONTINUE SEMICOLON"
        self.set_token_column(p.slice[1])
        p[0] = ContinueNode(p.slice[1])

    def p_statement_return_empty(self, p):
        "statement : RETURN SEMICOLON"
        self.set_token_column(p.slice[1])
        p[0] = ReturnNode(p.slice[1])

    def p_statement_return_expr(self, p):
        "statement : RETURN expression SEMICOLON"
        self.set_token_column(p.slice[1])
        p[0] = ReturnNode(p.slice[1], p[2])

    # ----------------------------------------- BLOCK -------------------------------------------------------
    # A block of statements is a list of statement
    # e,i., if { stmt1; stmt2; ... }
    def p_block(self, p):
        "block : LBRACER statements RBRACER"
        self.set_token_column(p.slice[1])
        p[0] = BlockNode(p.slice[1], p[2])

    # We can empty blocks, e.i., if {} els {}
    def p_block_empty(self, p):
        "block : LBRACER RBRACER"
        self.set_token_column(p.slice[1])
        p[0] = BlockNode(p.slice[1], [])

    # ----------------------------------- VARIABLE/CONST DECLARATION -----------------------------------------
    def p_statement_var_declaration_form_one(self, p):
        "statement : VAR IDENTIFIER EQ expression SEMICOLON"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = VarDeclarationNode(p.slice[1], IdentifierNode(p.slice[2]), p[4], False)

    def p_statement_var_declaration_form_two(self, p):
        "statement : CONST IDENTIFIER EQ expression SEMICOLON"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = VarDeclarationNode(p.slice[1], IdentifierNode(p.slice[2]), p[4], True)

    def p_statement_var_declaration_form_three(self, p):
        "statement : VAR IDENTIFIER COLON type_ EQ expression SEMICOLON"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = VarDeclarationNode(
            p.slice[1], IdentifierNode(p.slice[2]), p[6], False, p[4]
        )

    def p_statement_var_declaration_form_four(self, p):
        "statement : CONST IDENTIFIER COLON type_ EQ expression SEMICOLON"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = VarDeclarationNode(
            p.slice[1], IdentifierNode(p.slice[2]), p[6], True, p[4]
        )

    def p_statement_var_declaration_form_five(self, p):
        "statement : VAR IDENTIFIER SEMICOLON"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = VarDeclarationNode(p.slice[1], IdentifierNode(p.slice[2]), None, False)

    def p_statement_var_declaration_form_six(self, p):
        "statement : CONST IDENTIFIER SEMICOLON"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = VarDeclarationNode(p.slice[1], IdentifierNode(p.slice[2]), None, True)

    def p_statement_var_declaration_form_seven(self, p):
        "statement : CONST IDENTIFIER COLON type_ SEMICOLON"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = VarDeclarationNode(
            p.slice[1], IdentifierNode(p.slice[2]), None, True, p[4]
        )

    def p_statement_var_declaration_form_eigth(self, p):
        "statement : VAR IDENTIFIER COLON type_ SEMICOLON"
        self.set_token_column(p.slice[1])
        self.set_token_column(p.slice[2])
        p[0] = VarDeclarationNode(
            p.slice[1], IdentifierNode(p.slice[2]), None, False, p[4]
        )

    # ---------------------------------- CONSOLE.LOG -----------------------------------------------------------
    def p_statement_console_log(self, p):
        "statement : CONSOLE DOT LOG LPAREN argument_expression_list RPAREN SEMICOLON"
        self.set_token_column(p.slice[1])
        p[0] = ConsoleLogNode(p.slice[1], p[5])

    def p_statement_list(self, p):
        """
        statements : statements statement
                   | statement
        """
        if len(p) > 2:
            p[1].append(p[2])
            p[0] = p[1]
        else:
            p[0] = [p[1]]

    # ------------------------------- EXPRESSION -----------------------------------------------------------------
    def p_statement_expr(self, p):
        "statement : expression SEMICOLON"
        p[0] = p[1]

    # builtin function
    def p_expression_parseInt(self, p):
        "expression : PARSEINT LPAREN expression RPAREN"
        self.set_token_column(p.slice[1])
        p[0] = BuiltinParseInt(p.slice[1], p[3])

    def p_expression_parseFloat(self, p):
        "expression : PARSEFLOAT LPAREN expression RPAREN"
        self.set_token_column(p.slice[1])
        p[0] = BuiltinParseFloat(p.slice[1], p[3])

    # binary expression with +, -, *, / or % operators
    def p_expression_arithmetic(self, p):
        """
        expression : expression PLUS expression
                   | expression MINUS expression
                   | expression TIMES expression
                   | expression DIVIDE expression
                   | expression MOD expression
        """
        self.set_token_column(p.slice[2])
        p[0] = ArithmeticOperationNode(p[1], p.slice[2], p[3])

    # binary expression with <, <=, >, >= operators
    def p_expression_relational(self, p):
        """
        expression : expression LT expression
                           | expression GT expression
                           | expression LTE expression
                           | expression GTE expression
        """
        self.set_token_column(p.slice[2])
        p[0] = RelationalOperationNode(p[1], p.slice[2], p[3])

    # binary expression with && or || operators
    def p_expression_logical(self, p):
        """
        expression : expression OR expression
                   | expression AND expression
        """
        self.set_token_column(p.slice[2])
        p[0] = LogicalOperationNode(p[1], p.slice[2], p[3])

    # binary expression with == or != operators
    def p_expression_equality(self, p):
        """
        expression : expression EQ_EQ expression
                   | expression BANG_EQ expression
        """
        self.set_token_column(p.slice[2])
        p[0] = EqualityOperationNode(p[1], p.slice[2], p[3])

    # ternary expression
    def p_expression_ternary(self, p):
        "expression : expression QMARK expression COLON expression"
        self.set_token_column(p.slice[2])
        p[0] = TernaryOperationNode(p.slice[2], p[1], p[3], p[5])

    # unary expression with - or ! operators
    def p_expression_negate(self, p):
        """
        expression : BANG expression %prec UMINUS
                   | MINUS expression %prec UMINUS
        """
        self.set_token_column(p.slice[1])
        p[0] = UnaryOperationNode(p.slice[1], p[2])

    # typeof expression
    def p_expression_typeof(self, p):
        "expression : TYPEOF expression %prec UMINUS"
        self.set_token_column(p.slice[1])
        p[0] = TypeOfNode(p.slice[1], p[2])

    # an expression can be in the form of a postfix expression
    def p_expression_primary(self, p):
        "expression : postfix_expression"
        p[0] = p[1]

    # post fix expression. e.i.,: f(), id.id, a[b], a[b][c], foo, ...
    def p_postfix_expression_primary_expression(self, p):
        "postfix_expression : primary_expression"
        p[0] = p[1]

    # foo[1], foo[baz][spam], ...
    def p_postfix_expression_array_access(self, p):
        "postfix_expression : postfix_expression LBRACKET expression RBRACKET"
        self.set_token_column(p.slice[2])
        p[0] = ArrayAccessNode(p[1], p.slice[2], p[3])

    # call expression with no arguments: fun(), add(), ...
    def p_postfix_expression_call_expression_no_args(self, p):
        "postfix_expression : postfix_expression LPAREN RPAREN"
        if isinstance(p[1], IdentifierNode):
            self.set_token_column(p.slice[2])
            p[0] = CallExprNode(p[1], p.slice[2], [])
            return
        if p[1].right.token.value == "toString":
            p[0] = BuiltinToString(p[1].right.token, p[1].left)
            return
        if p[1].right.token.value == "toLowerCase":
            p[0] = BuiltinToLowerCase(p[1].right.token, p[1].left)
            return
        if p[1].right.token.value == "toUpperCase":
            p[0] = BuiltinToUpperCase(p[1].right.token, p[1].left)
            return
        if p[1].right.token.value == "pop":
            p[0] = BuiltinPop(p[1].right.token, p[1].left)
            return
        if p[1].right.token.value == "join":
            p[0] = BuiltinJoin(p[1].right.token, p[1].left)
            return

        self.set_token_column(p.slice[2])
        p[0] = CallExprNode(p[1], p.slice[2])

    # call expression with arguments: fun(1,2), add(1, 2), ...
    def p_postfix_expression_call_expression_with_args(self, p):
        "expression : postfix_expression LPAREN argument_expression_list RPAREN"
        if isinstance(p[1], IdentifierNode):
            self.set_token_column(p.slice[2])
            p[0] = CallExprNode(p[1], p.slice[2], p[3])
            return
        if isinstance(p[1], MemberAccessNode):
            if (
                isinstance(p[1].left, IdentifierNode)
                and isinstance(p[1].right, IdentifierNode)
                and p[1].right.token.value == "push"
            ):
                self.set_token_column(p.slice[2])
                p[0] = BuiltinPush(p.slice[2], p[1].left, p[3])
                return
            if (
                isinstance(p[1].left, IdentifierNode)
                and isinstance(p[1].right, IdentifierNode)
                and p[1].right.token.value == "indexOf"
            ):
                self.set_token_column(p.slice[2])
                p[0] = BuiltinIndexOf(p.slice[2], p[1].left, p[3])
                return
        if (
            isinstance(p[1].left, IdentifierNode)
            and isinstance(p[1].right, IdentifierNode)
            and p[1].left.token.value == "Object"
            and p[1].right.token.value == "keys"
        ):
            self.set_token_column(p.slice[2])
            p[0] = ObjectKeysNode(p.slice[2], p[3])
            return
        if (
            isinstance(p[1].left, IdentifierNode)
            and isinstance(p[1].right, IdentifierNode)
            and p[1].left.token.value == "Object"
            and p[1].right.token.value == "values"
        ):
            self.set_token_column(p.slice[2])
            p[0] = ObjectValuesNode(p.slice[2], p[3])
            return

        self.set_token_column(p.slice[2])
        p[0] = CallExprNode(p[1], p.slice[2], p[3])

    # Comma separated list of arguments
    def p_argument_expression_list(self, p):
        """
        argument_expression_list : argument_expression_list COMMA expression
                                 | expression
        """
        if len(p) > 2:
            p[1].append(p[3])
            p[0] = p[1]
        else:
            p[0] = [p[1]]

    # person.name, person.name.last_name, ...
    def p_postfix_expression_member_access_expr(self, p):
        "postfix_expression : postfix_expression DOT IDENTIFIER"
        if isinstance(p[1], IdentifierNode) and p[3] == "length":
            self.set_token_column(p.slice[2])
            p[0] = BuiltinLength(p.slice[2], p[1])
            return

        self.set_token_column(p.slice[2])
        p[0] = MemberAccessNode(p[1], p.slice[2], IdentifierNode(p.slice[3]))

    # foo, bar, baz, ...
    def p_expression_primary_identifier(self, p):
        "primary_expression : IDENTIFIER"
        self.set_token_column(p.slice[1])
        p[0] = IdentifierNode(p.slice[1])

    # 123, 42, 1000, ...
    def p_expression_primary_number(self, p):
        "primary_expression : NUMBER"
        self.set_token_column(p.slice[1])
        p[0] = NumberLiteralNode(p.slice[1])

    # 3.1415, 0.00018, 42.4646, 2.76...
    def p_expression_primary_float(self, p):
        "primary_expression : FLOAT"
        self.set_token_column(p.slice[1])
        p[0] = FloatLiteralNode(p.slice[1])

    # "hello world", "", ...
    def p_expression_primary_string(self, p):
        "primary_expression : STRING"
        self.set_token_column(p.slice[1])
        p[0] = StringLiteralNode(p.slice[1])

    # 'a', '\n', ' ', ...
    def p_expression_primary_char(self, p):
        "primary_expression : CHAR"
        self.set_token_column(p.slice[1])
        p[0] = CharLiteralNode(p.slice[1])

    # true
    def p_primary_expresion_boolean_true(self, p):
        "primary_expression : TRUE"
        self.set_token_column(p.slice[1])
        p[0] = BooleanLiteralNode(p.slice[1])

    # false
    def p_primary_expression_boolean_false(self, p):
        "primary_expression : FALSE"
        self.set_token_column(p.slice[1])
        p[0] = BooleanLiteralNode(p.slice[1])

    # null
    def p_primary_expression_null(self, p):
        "primary_expression : NULL"
        self.set_token_column(p.slice[1])
        p[0] = NullLiteralNode(p.slice[1])

    # Array expression [1,2,3]
    def p_primary_expression_array(self, p):
        "primary_expression : LBRACKET argument_expression_list RBRACKET"
        self.set_token_column(p.slice[1])
        p[0] = ArrayNode(p.slice[1], p[2])

    # Array expression empty []
    def p_primary_expression_array_empty(self, p):
        "primary_expression : LBRACKET RBRACKET"
        self.set_token_column(p.slice[1])
        p[0] = ArrayNode(p.slice[1], [])

    # Interface expression
    def p_primary_expression_interface(self, p):
        "primary_expression : LBRACER interface_expression_list RBRACER"
        self.set_token_column(p.slice[1])
        p[0] = InterfaceExprNode(p.slice[1], p[2])

    def p_primary_expression_interface_expresssion_list(self, p):
        """
        interface_expression_list : interface_expression_list COMMA interface_expression
                                  | interface_expression
        """
        if len(p) > 2:
            p[1].append(p[3])
            p[0] = p[1]
        else:
            p[0] = [p[1]]

    def p_primary_expression_interface_expression(self, p):
        "interface_expression : IDENTIFIER COLON expression"
        self.set_token_column(p.slice[2])
        p[0] = FieldExprNode(p.slice[2], p[1], p[3])

    # ( expresison )
    def p_primary_expression_grouped(self, p):
        "primary_expression : LPAREN expression RPAREN"
        p[0] = p[2]

    def p_error(self, p):
        if p:
            self.set_token_column(p)
            the_error = InvalidSyntaxError(
                self.source_code_listing.get(p.lineno),
                p.lineno,
                p.lexpos,
                f"Syntax error",
                f"at {p.value!r}",
                self.file,
            )
            self.errors.append(the_error.as_string())
            print(the_error.as_string())
        else:
            the_error = InvalidSyntaxError(
                self.source_code_listing.get(len(self.source_code_listing)),
                len(self.source_code_listing),
                0,
                f"OLC666",
                f"Syntax error at EOF",
                self.file,
            )
            self.errors.append(the_error.as_string())
            print(the_error.as_string())


# ------------------------------------------------------------------------------------
#                                 VALUES
# ------------------------------------------------------------------------------------


class Number:
    def __init__(self, value):
        self.value = value
        self.type_spec = (
            Predefined.number_type if isinstance(value, int) else Predefined.float_type
        )
        self.set_pos()
        self.set_context()

    def get_type_spec(self):
        return self.type_spec

    def set_context(self, context=None):
        self.context = context
        return self

    def set_pos(self, line=None, column=None):
        self.line = line
        self.column = column
        return self

    def copy(self):
        the_copy = Number(self.value)
        the_copy.set_context(self.context)
        the_copy.set_pos(self.line, self.column)
        return the_copy

    def __add__(self, other):
        return Number(self.value + other.value).set_context(self.context)

    def __sub__(self, other):
        return Number(self.value - other.value).set_context(self.context)

    def __mul__(self, other):
        return Number(self.value * other.value).set_context(self.context)

    def __truediv__(self, other):
        result = self.value / other.value
        # uncomment if you want integer division.
        # if self.type_spec == Predefined.number_type and other.type_spec == Predefined.number_type:
        # 	return Number(round(result)).set_context(self.context)
        if result.is_integer() and (
            self.type_spec != Predefined.float_type
            or other.type_spec != Predefined.float_type
        ):
            return Number(int(result)).set_context(self.context)
        return Number(result).set_context(self.context)

    def __mod__(self, other):
        return Number(self.value % other.value).set_context(self.context)

    def __lt__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value < other.value
            else Boolean(False).set_context(self.context)
        )

    def __gt__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value > other.value
            else Boolean(False).set_context(self.context)
        )

    def __ge__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value >= other.value
            else Boolean(False).set_context(self.context)
        )

    def __le__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value <= other.value
            else Boolean(False).set_context(self.context)
        )

    def __eq__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value == other.value
            else Boolean(False).set_context(self.context)
        )

    def __ne__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value != other.value
            else Boolean(False).set_context(self.context)
        )

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return str(self.value)


class String:
    def __init__(self, value):
        self.value = value
        self.type_spec = Predefined.string_type
        self.set_pos()
        self.set_context()

    def set_context(self, context=None):
        self.context = context
        return self

    def set_pos(self, line=None, column=None):
        self.line = line
        self.column = column
        return self

    def get_type_spec(self):
        return self.type_spec

    def copy(self):
        the_copy = String(self.value)
        the_copy.set_context(self.context)
        the_copy.set_pos(self.line, self.column)
        return the_copy

    def __add__(self, other):
        return String(self.value + other.value).set_context(self.context)

    def __lt__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value < other.value
            else Boolean(False).set_context(self.context)
        )

    def __gt__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value > other.value
            else Boolean(False).set_context(self.context)
        )

    def __le__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value <= other.value
            else Boolean(False).set_context(self.context)
        )

    def __ge__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value >= other.value
            else Boolean(False).set_context(self.context)
        )

    def __eq__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value == other.value
            else Boolean(False).set_context(self.context)
        )

    def __ne__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value != other.value
            else Boolean(False).set_context(self.context)
        )

    def to_array(self):
        arr = Array().set_context(self.context).set_pos(self.line, self.column)
        arr.dims = 1
        arr.get_type_spec().set_base_type(Predefined.string_type)
        chars = list(self.value)
        for ch in chars:
            arr.push(
                String(ch).set_context(self.context).set_pos(self.line, self.column)
            )
        return arr

    def __str__(self):
        return f"{self.value}"

    def __repr__(self):
        return f"'{self.value}'"


class Boolean:
    def __init__(self, value):
        self.value = value
        self.type_spec = Predefined.boolean_type
        self.set_pos()
        self.set_context()

    def set_context(self, context=None):
        self.context = context
        return self

    def get_type_spec(self):
        return self.type_spec

    def set_pos(self, line=None, column=None):
        self.line = line
        self.column = column
        return self

    def copy(self):
        the_copy = Boolean(self.value)
        the_copy.set_context(self.context)
        the_copy.set_pos(self.line, self.column)
        return the_copy

    def __eq__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value == other.value
            else Boolean(False).set_context(self.context)
        )

    def __ne__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value != other.value
            else Boolean(False).set_context(self.context)
        )

    def negated(self):
        return (
            Boolean(True).set_context(self.context)
            if not self.value
            else Boolean(False).set_context(self.context)
        )

    def anded_by(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value and other.value
            else Boolean(False).set_context(self.context)
        )

    def orded_by(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value or other.value
            else Boolean(False).set_context(self.context)
        )

    def __str__(self):
        return f"true" if self.value else f"false"

    def __repr__(self):
        return "true" if self.value else "false"


class Char:
    def __init__(self, value):
        self.value = value
        self.type_spec = Predefined.char_type
        self.set_pos()
        self.set_context()

    def set_pos(self, line=None, column=None):
        self.line = line
        self.column = column
        return self

    def set_context(self, context=None):
        self.context = context
        return self

    def get_type_spec(self):
        return self.type_spec

    def copy(self):
        the_copy = Char(self.value)
        the_copy.set_context(self.context)
        the_copy.set_pos(self.line, self.column)
        return the_copy

    def __str__(self):
        return f"{self.value}"

    def __repr__(self):
        return f"'{self.value}'"

    def __eq__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value == other.value
            else Boolean(False).set_context(self.context)
        )

    def __ne__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value != other.value
            else Boolean(False).set_context(self.context)
        )

    def __lt__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value < other.value
            else Boolean(False).set_context(self.context)
        )

    def __gt__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value > other.value
            else Boolean(False).set_context(self.context)
        )

    def __le__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value <= other.value
            else Boolean(False).set_context(self.context)
        )

    def __ge__(self, other):
        return (
            Boolean(True).set_context(self.context)
            if self.value >= other.value
            else Boolean(False).set_context(self.context)
        )


class Undefined:
    def __init__(self):
        self.value = None
        self.type_spec = Predefined.undefined_type
        self.set_pos()
        self.set_context()

    def set_pos(self, line=None, column=None):
        self.line = line
        self.column = column
        return self

    def set_context(self, context=None):
        self.context = context
        return self

    def get_type_spec(self):
        return self.type_spec

    def copy(self):
        the_copy = Undefined()
        the_copy.set_context(self.context)
        the_copy.set_pos(self.line, self.column)
        return the_copy

    def __repr__(self):
        return f"undefined"

    def __str__(self):
        return f"undefined"


class Null:
    def __init__(self):
        self.value = None
        self.type_spec = Predefined.null_type
        self.set_pos()
        self.set_context()

    def set_pos(self, line=None, column=None):
        self.line = line
        self.column = column
        return self

    def set_context(self, context=None):
        self.context = context
        return self

    def get_type_spec(self):
        return self.type_spec

    def copy(self):
        the_copy = Null()
        the_copy.set_context(self.context)
        the_copy.set_pos(self.line, self.column)
        return the_copy

    def __repr__(self):
        return f"null"

    def __str__(self):
        return f"null"


class Array:
    def __init__(self):
        self.elements = []
        self.type_spec = TypeFactory.create_type(TypeForm.ARRAY)
        self.dims = 0
        self.set_pos()
        self.set_context()

    def set_pos(self, line=None, column=None):
        self.line = line
        self.column = column
        return self

    def set_context(self, context=None):
        self.context = context
        return self

    def get_type_spec(self):
        return self.type_spec

    def set_type_spec(self, type_spec):
        self.type_spec = type_spec

    def get_item(self, index):
        return self.elements[index]

    def add_item(self, value):
        self.elements.append(value)

    def is_empty(self):
        return len(self.elements) == 0

    def length(self):
        return len(self.elements)

    def builtin_length(self):
        return Number(len(self.elements))

    def push(self, value):
        self.elements.append(value)

    def pop(self):
        if len(self.elements) > 0:
            val = self.elements.pop()
            return val
        return Null().set_context(self.context).set_pos(self.line, self.column)

    def indexOf(self, value):
        for index, val in enumerate(self.elements):
            if value.value == val.value:
                return (
                    Number(index)
                    .set_context(self.context)
                    .set_pos(self.line, self.column)
                )
        return Number(-1).set_context(self.context).set_pos(self.line, self.column)

    def join(self):
        return (
            String(",".join([str(item) for item in self.elements]))
            .set_context(self.context)
            .set_pos(self.line, self.column)
        )

    def __repr__(self):
        buffer = "["
        buffer += ", ".join([item.__repr__() for item in self.elements])
        buffer += "]"
        return buffer


class Interface:
    def __init__(self):
        self.fields = InterfaceContext("")
        self.type_spec = TypeFactory.create_type(TypeForm.INTERFACE)
        self.set_pos()
        self.set_context()

    def set_pos(self, line=None, column=None):
        self.line = line
        self.column = column
        return self

    def set_context(self, context=None):
        self.context = context
        return self

    def get_type_spec(self):
        return self.type_spec

    def keys(self):
        # Create the array
        keys_array = Array().set_context(self.context).set_pos(self.line, self.column)
        keys_array.dims = 1
        keys_array.get_type_spec().set_base_type(Predefined.string_type)

        # Fill the array with string values
        for item in self.fields.variables.entries():
            keys_array.push(
                String(item).set_context(self.context).set_pos(self.line, self.column)
            )

        return keys_array

    def values(self):
        vals = Array().set_context(self.context).set_pos(self.line, self.column)
        vals.dims = 1
        vals.get_type_spec().set_base_type(Predefined.string_type)

        for field in self.fields.variables.entries():
            value = self.fields.variables.lookup(field).get_attribute(
                SymtabKey.RUNTIME_VALUE
            )
            if value.get_type_spec().get_form() == TypeForm.INTERFACE:
                interface_type_name = (
                    value.get_type_spec().get_base_type().get_identifier().name
                )
                vals.push(
                    String(f"[{interface_type_name}: interface]")
                    .set_context(self.context)
                    .set_pos(self.line, self.column)
                )
            else:
                vals.push(
                    String(value)
                    .set_context(self.context)
                    .set_pos(self.line, self.column)
                )

        return vals

    def __repr__(self):
        fields = []
        for field in self.fields.variables.entries():
            line = ""
            line += field + ": "
            line += (
                "'"
                + self.fields.variables.lookup(field)
                .get_attribute(SymtabKey.RUNTIME_VALUE)
                .__str__()
                + "'"
            )
            fields.append(line)
        buffer = "{ " + ", ".join([item for item in fields]) + " }"
        return buffer

    def __str__(self):
        buffer = "{ "
        for field in self.fields.variables.entries():
            buffer += field + ": "
            buffer += (
                "'"
                + self.fields.variables.lookup(field)
                .get_attribute(SymtabKey.RUNTIME_VALUE)
                .__str__()
                + "', "
            )
        buffer += " }"
        return buffer


# ------------------------------------------------------------------------------------
#                                 RUNTIME RESULT
# ------------------------------------------------------------------------------------


class RTResult:
    def __init__(self):
        self.reset()

    def reset(self):
        self.value = None
        self.error = None
        self.func_return_value = None
        self.loop_should_continue = False
        self.loop_should_break = False

    def register(self, res):
        self.error = res.error
        self.func_return_value = res.func_return_value
        self.loop_should_continue = res.loop_should_continue
        self.loop_should_break = res.loop_should_break
        return res.value

    def success(self, value):
        self.reset()
        self.value = value
        return self

    def success_return(self, value):
        self.reset()
        self.func_return_value = value
        return self

    def success_continue(self):
        self.reset()
        self.loop_should_continue = True
        return self

    def success_break(self):
        self.reset()
        self.loop_should_break = True
        return self

    def failure(self, error):
        self.reset()
        self.error = error
        return self

    def should_return(self):
        return (
            self.error
            or self.func_return_value
            or self.loop_should_break
            or self.loop_should_continue
        )


# ------------------------------------------------------------------------------------
#                                 SYMBOL
# ------------------------------------------------------------------------------------


class Symbol:
    def __init__(self, name, symbol_type, type_, context, line, column):
        self.name = name
        self.symbol_type = symbol_type
        self.type_ = type_
        self.context = context
        self.line = line
        self.column = column

    def as_string(self):
        buffer = ("-" * 50) + "\n"
        buffer += "ID:                " + self.name + "\n"
        buffer += "Symbol Type:       " + self.symbol_type + "\n"
        buffer += "Data type:         " + self.type_ + "\n"
        buffer += "Context:           " + self.context + "\n"
        buffer += "Line:              " + str(self.line) + "\n"
        buffer += "Column:            " + str(self.column) + "\n"
        buffer += ("-" * 50) + "\n"
        return buffer


# ------------------------------------------------------------------------------------
#                                 INTERPRETER
# ------------------------------------------------------------------------------------


class Interpreter:

    def __init__(self, source_code, global_context, file=None):

        self.global_context = global_context
        self.source_code = source_code
        self.source_code_listing = self.make_source_code_listing()
        self.array_dimensions = []
        self.file = file or "<stdin>"
        self.init_result_types_map()
        self.init_assign_result_types_map()
        self.log = []
        self.errors = []
        self.errors_as_string = ""
        self.log_as_string = ""
        self.symbols = {}
        self.symbols_as_string = ""

    def init_assign_result_types_map(self):
        self.ASSIGN_RESULT_TYPE = {
            (TypeForm.NUMBER, TypeForm.NUMBER): True,
            (TypeForm.FLOAT, TypeForm.FLOAT): True,
            (TypeForm.STRING, TypeForm.STRING): True,
            (TypeForm.BOOLEAN, TypeForm.BOOLEAN): True,
            (TypeForm.CHAR, TypeForm.CHAR): True,
            (TypeForm.ARRAY, TypeForm.ARRAY): True,
            (TypeForm.MATRIX, TypeForm.MATRIX): True,
            (TypeForm.FLOAT, TypeForm.NUMBER): True,
            (TypeForm.NUMBER, TypeForm.FLOAT): True,
            (TypeForm.ARRAY, TypeForm.NULL): True,
            (TypeForm.MATRIX, TypeForm.NULL): True,
            (TypeForm.INTERFACE, TypeForm.INTERFACE): True,
        }

    def init_result_types_map(self):
        self.ARITH_RESULT_TYPE = {
            (Predefined.number_type, Predefined.number_type): Predefined.number_type,
            (Predefined.float_type, Predefined.float_type): Predefined.float_type,
            (Predefined.number_type, Predefined.float_type): Predefined.float_type,
            (Predefined.string_type, Predefined.string_type): Predefined.string_type,
            (Predefined.float_type, Predefined.number_type): Predefined.float_type,
        }
        self.PROMOTE_FROM_TO = {
            (Predefined.number_type, Predefined.float_type): Predefined.float_type,
            (Predefined.float_type, Predefined.number_type): Predefined.float_type,
        }
        self.RELATIONAL_RESULT_TYPE = {
            (Predefined.number_type, Predefined.number_type): Predefined.boolean_type,
            (Predefined.number_type, Predefined.float_type): Predefined.boolean_type,
            (Predefined.float_type, Predefined.float_type): Predefined.boolean_type,
            (Predefined.float_type, Predefined.number_type): Predefined.boolean_type,
            (Predefined.string_type, Predefined.string_type): Predefined.boolean_type,
            (Predefined.char_type, Predefined.char_type): Predefined.boolean_type,
        }
        self.LOGICAL_RESULT_TYPE = {
            (Predefined.boolean_type, Predefined.boolean_type): Predefined.boolean_type,
        }
        self.EQUALITY_RESULT_TYPE = {
            (Predefined.number_type, Predefined.number_type): Predefined.boolean_type,
            (Predefined.number_type, Predefined.float_type): Predefined.boolean_type,
            (Predefined.float_type, Predefined.float_type): Predefined.boolean_type,
            (Predefined.float_type, Predefined.number_type): Predefined.boolean_type,
            (Predefined.boolean_type, Predefined.boolean_type): Predefined.boolean_type,
            (Predefined.string_type, Predefined.string_type): Predefined.boolean_type,
            (Predefined.char_type, Predefined.char_type): Predefined.boolean_type,
        }

    def visit(self, node, context):
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.no_visit_method)
        return method(node, context)

    def no_visit_method(self, node, context):
        raise Exception(f"No visit_{type(node).__name__} method defined")

    def assign_result_type(self, type_form_1, type_form_2):
        return self.ASSIGN_RESULT_TYPE.get((type_form_1, type_form_2), False)

    def arithmetic_result_type(self, type1, type2):
        return self.ARITH_RESULT_TYPE.get((type1, type2), None)

    def relational_result_type(self, type1, type2):
        return self.RELATIONAL_RESULT_TYPE.get((type1, type2), None)

    def logical_result_type(self, type1, type2):
        return self.LOGICAL_RESULT_TYPE.get((type1, type2), None)

    def equality_result_type(self, type1, type2):
        return self.EQUALITY_RESULT_TYPE.get((type1, type2), None)

    def promote_from_to(self, type1, operators, type2):
        if operators.union({"PLUS", "MINUS", "TIMES", "DIVIDE", "MOD"}) == operators:
            return self.PROMOTE_FROM_TO.get((type1, type2), None)
        if operators.union({"LT", "LTE", "GT", "GTE"}) == operators:
            return self.PROMOTE_FROM_TO.get((type1, type2), None)

    def create_runtime_value(self, type_spec, value):
        if type_spec == Predefined.number_type:
            return Number(int(value))
        elif type_spec == Predefined.float_type:
            return Number(float(value))
        elif type_spec == Predefined.boolean_type:
            return Boolean(value)
        elif type_spec == Predefined.string_type:
            return String(value)
        elif type_spec == Predefined.char_type:
            return Char(value)

    def make_type_error(self, val1, operator, val2):
        result = ""
        t1 = self.get_name_of_type(val1)
        t2 = self.get_name_of_type(val2)
        result = (
            f"unsupported operand type(s) for '{operator.value}': '{t1}' and '{t2}'"
        )
        return result

    def make_source_code_listing(self):
        listing = {}
        lines = self.source_code.split("\n")
        counter = 1
        for line in lines:
            listing[counter] = line
            counter += 1
        return listing

    def get_name_of_type(self, value):
        if isinstance(value, tuple):
            value_type_form = value[0].get_form()
        else:
            value_type_form = value.get_type_spec().get_form()

        if value_type_form == TypeForm.NUMBER:
            return f"number"
        elif value_type_form == TypeForm.FLOAT:
            return f"float"
        elif value_type_form == TypeForm.CHAR:
            return f"char"
        elif value_type_form == TypeForm.BOOLEAN:
            return f"boolean"
        elif value_type_form == TypeForm.STRING:
            return f"string"
        elif value_type_form == TypeForm.NULL:
            return f"null"
        elif value_type_form == TypeForm.UNDEFINED:
            return f"undefined"
        elif value_type_form == TypeForm.ARRAY or value_type_form == TypeForm.MATRIX:
            if isinstance(value, tuple):
                base_type_name = (
                    value[0].get_base_type().get_type_spec().get_identifier().name
                )
                dims = "[]" * value[1]
                return f"{base_type_name + dims}"
            else:
                base_type_name = (
                    value.get_type_spec().get_base_type().get_identifier().name
                )
                dims = "[]" * value.dims
                return f"{base_type_name + dims}"
        elif value_type_form == TypeForm.INTERFACE:
            if isinstance(value, tuple):
                base_type_name = value[0].get_identifier().name
                return f"{base_type_name}"
            else:
                base_type_name = (
                    value.get_type_spec().get_base_type().get_identifier().name
                )
                return f"{base_type_name}"
        else:  # Should never get here
            return f"!@#$%"

    #######################################################################################

    def visit_ArithmeticOperationNode(self, node, context):
        res = RTResult()

        # visit the left and right child nodes
        left = res.register(self.visit(node.left, context))
        if res.should_return():
            return res
        right = res.register(self.visit(node.right, context))
        if res.should_return():
            return res

        # Are both types compatible ?
        lhs_type = left.get_type_spec()
        rhs_type = right.get_type_spec()
        result_type = self.arithmetic_result_type(lhs_type, rhs_type)
        is_string = result_type == Predefined.string_type
        if result_type is None:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    f"TypeError",
                    self.make_type_error(left, node.operator, right),
                    context,
                    self.file,
                )
            )

        # Do we need to promote any value? A None result means no promotion needed.
        lhs_prom_type = self.promote_from_to(
            lhs_type, {"PLUS", "MINUS", "TIMES", "DIVIDE", "MOD"}, result_type
        )
        rhs_prom_type = self.promote_from_to(
            rhs_type, {"PLUS", "MINUS", "TIMES", "DIVIDE", "MOD"}, result_type
        )
        if lhs_prom_type is not None:
            left = self.create_runtime_value(result_type, left.value)
        if rhs_prom_type is not None:
            right = self.create_runtime_value(result_type, right.value)

        if node.operator.type == "PLUS":
            result = left + right
        elif node.operator.type == "MINUS":
            if is_string:
                return res.failure(
                    RTError(
                        self.source_code_listing.get(node.line),
                        node.line,
                        node.column,
                        f"TypeError",
                        self.make_type_error(left, node.operator, right),
                        context,
                        self.file,
                    )
                )
            result = left - right
        elif node.operator.type == "TIMES":
            if is_string:
                return res.failure(
                    RTError(
                        self.source_code_listing.get(node.line),
                        node.line,
                        node.column,
                        f"TypeError",
                        self.make_type_error(left, node.operator, right),
                        context,
                        self.file,
                    )
                )
            result = left * right
        elif node.operator.type == "DIVIDE":
            if is_string:
                return res.failure(
                    RTError(
                        self.source_code_listing.get(node.line),
                        node.line,
                        node.column,
                        f"TypeError",
                        self.make_type_error(left, node.operator, right),
                        context,
                        self.file,
                    )
                )
            if right.value == 0:
                return res.failure(
                    RTError(
                        self.source_code_listing.get(node.line),
                        node.line,
                        node.column,
                        f"OLC1010",
                        f"Division by 0",
                        context,
                        self.file,
                    )
                )
            result = left / right
        else:  # the only operator left is the mod operator '%'
            # little hack for the % operator (we only allow mod between numbers)
            if (
                left.get_type_spec().get_form() == TypeForm.NUMBER
                and right.get_type_spec().get_form() == TypeForm.NUMBER
            ):
                if right.value == 0:
                    return res.failure(
                        RTError(
                            self.source_code_listing.get(node.right.line),
                            node.line,
                            node.column,
                            f"OLC1010",
                            f"Division by 0",
                            context,
                            self.file,
                        )
                    )
                result = left % right
            else:
                return res.failure(
                    RTError(
                        self.source_code_listing.get(node.right.line),
                        node.line,
                        node.column,
                        f"OLC2220",
                        self.make_type_error(left, node.operator, right),
                        context,
                        self.file,
                    )
                )

        return res.success(result.set_pos(node.line, node.column))

    #######################################################################################

    def visit_RelationalOperationNode(self, node, context):
        res = RTResult()

        # visit the left and right child nodes
        lhs = res.register(self.visit(node.left, context))
        if res.should_return():
            return res
        rhs = res.register(self.visit(node.right, context))
        if res.should_return():
            return res

        # Are both types compatibles?
        lhs_type = lhs.get_type_spec()
        rhs_type = rhs.get_type_spec()
        result_type = self.relational_result_type(lhs_type, rhs_type)

        # A None result means incompatible types
        if result_type is None:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.right.line),
                    node.line,
                    node.column,
                    f"TypeMismatchError",
                    self.make_type_error(lhs, node.operator, rhs),
                    context,
                    self.file,
                )
            )
        # Do we need to promote any values?
        # A None value means no promotion.
        lhs_prom_type = self.promote_from_to(
            lhs_type, {"LT", "LTE", "GT", "GTE"}, rhs_type
        )
        rhs_prom_type = self.promote_from_to(
            rhs_type, {"LT", "LTE", "GT", "GTE"}, lhs_type
        )
        if lhs_prom_type:
            lhs = self.create_runtime_value(lhs_prom_type, lhs.value)
        if rhs_prom_type:
            rhs = self.create_runtime_value(rhs_prom_type, rhs.value)

        if node.operator.type == "LT":
            result = lhs < rhs
        elif node.operator.type == "LTE":
            result = lhs <= rhs
        elif node.operator.type == "GT":
            result = lhs > rhs
        else:
            result = lhs >= rhs

        return res.success(result.set_pos(node.line, node.column))

    #######################################################################################

    def visit_EqualityOperationNode(self, node, context):
        res = RTResult()

        # visit the left and right child nodes
        lhs = res.register(self.visit(node.left, context))
        if res.should_return():
            return res
        rhs = res.register(self.visit(node.right, context))
        if res.should_return():
            return res

        # Are both types compatibles?
        lhs_type = lhs.get_type_spec()
        rhs_type = rhs.get_type_spec()
        result_type = self.equality_result_type(lhs_type, rhs_type)

        # A None result means incompatible types
        if result_type is None:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.right.line),
                    node.line,
                    node.column,
                    f"TypeError",
                    self.make_type_error(lhs, node.operator, rhs),
                    context,
                    self.file,
                )
            )

        # Do we need to promote any values?
        # A None value means no promotion.
        lhs_prom_type = self.promote_from_to(lhs_type, {"EQ_EQ", "BANG_EQ"}, rhs_type)
        rhs_prom_type = self.promote_from_to(rhs_type, {"EQ_EQ", "BANG_EQ"}, lhs_type)
        if lhs_prom_type:
            lhs = self.create_runtime_value(lhs_prom_type, lhs.value)
        if rhs_prom_type:
            rhs = self.create_runtime_value(rhs_prom_type, rhs.value)

        if node.operator.type == "EQ_EQ":
            result = lhs == rhs
        else:
            result = lhs != rhs

        return res.success(result.set_pos(node.line, node.column))

    #######################################################################################

    def visit_LogicalOperationNode(self, node, context):
        res = RTResult()

        # visit child nodes
        left = res.register(self.visit(node.left, context))
        if res.should_return():
            return res
        right = res.register(self.visit(node.right, context))
        if res.should_return():
            return res

        # are both types compatible
        left_type = left.get_type_spec()
        right_type = right.get_type_spec()
        result_type = self.logical_result_type(left_type, right_type)
        # A None result means incompatible types
        if result_type is None:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.right.line),
                    node.line,
                    node.column,
                    f"TypeError",
                    self.make_type_error(left, node.operator, right),
                    context,
                    self.file,
                )
            )

        if node.operator.type == "OR":
            result = left.orded_by(right)
        else:
            result = left.anded_by(right)

        return res.success(result.set_pos(node.line, node.column))

    def visit_NumberLiteralNode(self, node, context):
        return RTResult().success(
            Number(int(node.token.value))
            .set_context(context)
            .set_pos(node.line, node.column)
        )

    def visit_FloatLiteralNode(self, node, context):
        return RTResult().success(
            Number(float(node.token.value))
            .set_context(context)
            .set_pos(node.line, node.column)
        )

    def visit_StringLiteralNode(self, node, context):
        return RTResult().success(
            String(node.token.value)
            .set_context(context)
            .set_pos(node.line, node.column)
        )

    def visit_BooleanLiteralNode(self, node, context):
        return RTResult().success(
            Boolean(node.value).set_context(context).set_pos(node.line, node.column)
        )

    def visit_NullLiteralNode(self, node, context):
        return RTResult().success(
            Null().set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_CharLiteralNode(self, node, context):
        res = RTResult()
        especial_chars = ("\\a", "\\b", "\\t", "\\n", "\\v", "\\f", "\\r")
        if len(node.value) == 1 or node.value in especial_chars:
            return res.success(
                Char(node.token.value)
                .set_context(context)
                .set_pos(node.line, node.column)
            )
        return res.failure(
            RTError(
                self.source_code_listing.get(node.line),
                node.line,
                node.column,
                f"OLC1233",
                f"invalid character literal '{node.value}'",
                context,
                self.file,
            )
        )

    #######################################################################################

    def visit_UnaryOperationNode(self, node, context):
        res = RTResult()

        if node.operator.type == "MINUS":
            right = res.register(self.visit(node.expr_node, context))
            if res.should_return():
                return res
            right_type = right.get_type_spec()
            if (
                right_type.get_form() == TypeForm.NUMBER
                or right_type.get_form() == TypeForm.FLOAT
            ):
                result = self.create_runtime_value(right_type, right.value * -1)
                return res.success(result.set_pos(node.line, node.column))
            else:
                return res.failure(
                    RTError(
                        self.source_code_listing.get(node.expr_node.line),
                        node.line,
                        node.column,
                        f"OLC2011",
                        f"unsupported operand type for '-': {self.get_name_of_type(right)}",
                        context,
                        self.file,
                    )
                )
        else:
            right = res.register(self.visit(node.expr_node, context))
            if res.should_return():
                return res
            right_type = right.get_type_spec()
            if right_type.get_form() == TypeForm.BOOLEAN:
                result = right.negated()
                return res.success(result.set_pos(node.line, node.column))
            else:
                return res.failure(
                    RTError(
                        self.source_code_listing.get(node.expr_node.line),
                        node.line,
                        node.column,
                        f"OLC2020",
                        f"unsupported operand type for '!': {self.get_name_of_type(right)}",
                        context,
                        self.file,
                    )
                )

    #######################################################################################

    def are_values_assignment_compatible(self, target, source, context, node):
        # target - a runtime value
        # source - a runtime value
        # context - the context, for error report
        # node - the '=' token node
        res = RTResult()

        target_type_form = target.get_type_spec().get_form()
        source_type_form = source.get_type_spec().get_form()

        if target_type_form == TypeForm.ARRAY and source_type_form == TypeForm.ARRAY:
            target_type_name = (
                target.get_type_spec().get_base_type().get_identifier().name
            )
            source_type_name = (
                source.get_type_spec().get_base_type().get_identifier().name
            )
            if target_type_name != source_type_name:
                return res.failure(
                    RTError(
                        self.source_code_listing.get(node.line),
                        node.line,
                        node.column,
                        f"OLC1155",
                        f"type '{source_type_name}[]' cannot be assign to type '{target_type_name}[]'",
                        context,
                        self.file,
                    )
                )
        if target_type_form == TypeForm.MATRIX and source_type_form == TypeForm.MATRIX:
            target_type_name = (
                target.get_type_spec().get_base_type().get_identifier().name
            )
            source_type_name = (
                source.get_type_spec().get_base_type().get_identifier().name
            )
            target_dimensions = target.dims
            source_dimensions = source.dims
            if (
                not target_type_name == source_type_name
                and not target_dimensions == source_dimensions
            ):
                tdims = "[]" * target_dimensions
                sdims = "[]" * source_dimensions
                return res.failure(
                    RTError(
                        self.source_code_listing.get(node.line),
                        node.line,
                        node.column,
                        f"OLC1155",
                        f"type '{source_type_name + sdims}' cannot be assign to type '{target_type_name + tdims}'",
                        context,
                        self.file,
                    )
                )
        if (
            target_type_form == TypeForm.INTERFACE
            and source_type_form == TypeForm.INTERFACE
        ):
            target_type_name = (
                target.get_type_spec().get_base_type().get_identifier().name
            )
            source_type_name = (
                source.get_type_spec().get_base_type().get_identifier().name
            )
            if target_type_name != source_type_name:
                return res.failure(
                    RTError(
                        self.source_code_listing.get(node.line),
                        node.line,
                        node.column,
                        f"OLC1155",
                        f"type '{source_type_name}' cannot be assign to type '{target_type_name}'",
                        context,
                        self.file,
                    )
                )

        are_types_assignables = self.assign_result_type(
            target_type_form, source_type_form
        )

        if are_types_assignables is False:
            target_type_name = ""
            target_dimensions = 0
            source_type_name = ""
            source_dimensions = 0
            if (
                target_type_form == TypeForm.ARRAY
                or target_type_form == TypeForm.MATRIX
            ):
                target_type_name = (
                    target.get_type_spec().get_base_type().get_identifier().name
                )
                target_dimensions = target.dims
            if (
                source_type_form == TypeForm.ARRAY
                or source_type_form == TypeForm.MATRIX
            ):
                source_type_name = (
                    source.get_type_spec().get_base_type().get_identifier().name
                )
                source_dimensions = source.dims
            if target_type_form == TypeForm.INTERFACE:
                target_type_name = (
                    target.get_type_spec().get_base_type().get_identifier().name
                )
            if source_type_form == TypeForm.INTERFACE:
                source_type_name = (
                    source.get_type_spec().get_base_type().get_identifier().name
                )
            if (
                target_type_form == TypeForm.NUMBER
                or target_type_form == TypeForm.FLOAT
                or target_type_form == TypeForm.BOOLEAN
                or target_type_form == TypeForm.CHAR
                or target_type_form == TypeForm.STRING
                or target_type_form == TypeForm.NULL
                or target_type_form == TypeForm.UNDEFINED
            ):
                target_type_name = target_type_form.name.lower()
            if (
                source_type_form == TypeForm.NUMBER
                or source_type_form == TypeForm.FLOAT
                or source_type_form == TypeForm.BOOLEAN
                or source_type_form == TypeForm.CHAR
                or source_type_form == TypeForm.STRING
                or source_type_form == TypeForm.NULL
                or source_type_form == TypeForm.UNDEFINED
            ):
                source_type_name = source_type_form.name.lower()
            tdims = "[]" * target_dimensions
            sdims = "[]" * source_dimensions
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    f"OLC1155",
                    f"type '{source_type_name + sdims}' cannot be assign to type '{target_type_name + tdims}'",
                    context,
                    self.file,
                )
            )

        return res.success(
            Boolean(are_types_assignables)
            .set_context(context)
            .set_pos(node.line, node.column)
        )

    def are_types_assignment_compatible(self, target, source, context, type_spec_node):
        # target - a tuple (TypeSpec, int)
        # source - a runtime value
        # context - the context, for error report
        # type_spec_node - the ast node for the typespec (string, int)
        res = RTResult()

        target_type_form = target[0].get_form()
        source_type_form = source.get_type_spec().get_form()

        if target_type_form == TypeForm.ARRAY and source_type_form == TypeForm.ARRAY:
            target_type_name = (
                target[0].get_base_type().get_type_spec().get_identifier().name
            )
            source_type_name = (
                source.get_type_spec().get_base_type().get_identifier().name
            )
            if target_type_name != source_type_name:
                return res.failure(
                    RTError(
                        self.source_code_listing.get(type_spec_node.line),
                        type_spec_node.line,
                        type_spec_node.column,
                        f"OLC1155",
                        f"type '{source_type_name}[]' cannot be assign to type '{target_type_name}[]'",
                        context,
                        self.file,
                    )
                )
        if target_type_form == TypeForm.MATRIX and source_type_form == TypeForm.MATRIX:
            target_type_name = (
                target[0].get_base_type().get_type_spec().get_identifier().name
            )
            source_type_name = (
                source.get_type_spec().get_base_type().get_identifier().name
            )
            target_dimensions = target[1]
            source_dimensions = source.dims
            if (
                not target_type_name == source_type_name
                and not target_dimensions == source_dimensions
            ):
                tdims = "[]" * target_dimensions
                sdims = "[]" * source_dimensions
                return res.failure(
                    RTError(
                        self.source_code_listing.get(type_spec_node.line),
                        type_spec_node.line,
                        type_spec_node.column,
                        f"OLC1155",
                        f"type '{source_type_name + sdims}' cannot be assign to type '{target_type_name + tdims}'",
                        context,
                        self.file,
                    )
                )
        if (
            target_type_form == TypeForm.INTERFACE
            and source_type_form == TypeForm.INTERFACE
        ):
            target_type_name = target[0].get_identifier().name
            source_type_name = (
                source.get_type_spec().get_base_type().get_identifier().name
            )
            if target_type_name != source_type_name:
                return res.failure(
                    RTError(
                        self.source_code_listing.get(type_spec_node.line),
                        type_spec_node.line,
                        type_spec_node.column,
                        f"OLC1155",
                        f"type '{source_type_name}' cannot be assign to type '{target_type_name}'",
                        context,
                        self.file,
                    )
                )

        are_types_assignables = self.assign_result_type(
            target_type_form, source_type_form
        )

        if are_types_assignables is False:
            target_type_name = ""
            target_dimensions = 0
            source_type_name = ""
            source_dimensions = 0
            if (
                target_type_form == TypeForm.ARRAY
                or target_type_form == TypeForm.MATRIX
            ):
                target_type_name = (
                    target[0].get_base_type().get_type_spec().get_identifier().name
                )
                target_dimensions = target[1]
            if (
                source_type_form == TypeForm.ARRAY
                or source_type_form == TypeForm.MATRIX
            ):
                source_type_name = (
                    source.get_type_spec().get_base_type().get_identifier().name
                )
                source_dimensions = source.dims
            if target_type_form == TypeForm.INTERFACE:
                target_type_name = target[0].get_identifier().name
            if source_type_form == TypeForm.INTERFACE:
                source_type_name = (
                    source.get_type_spec().get_base_type().get_identifier().name
                )
            if (
                target_type_form == TypeForm.NUMBER
                or target_type_form == TypeForm.FLOAT
                or target_type_form == TypeForm.BOOLEAN
                or target_type_form == TypeForm.CHAR
                or target_type_form == TypeForm.STRING
                or target_type_form == TypeForm.NULL
                or target_type_form == TypeForm.UNDEFINED
            ):
                target_type_name = target_type_form.name.lower()
            if (
                source_type_form == TypeForm.NUMBER
                or source_type_form == TypeForm.FLOAT
                or source_type_form == TypeForm.BOOLEAN
                or source_type_form == TypeForm.CHAR
                or source_type_form == TypeForm.STRING
                or source_type_form == TypeForm.NULL
                or source_type_form == TypeForm.UNDEFINED
            ):
                source_type_name = source_type_form.name.lower()
            tdims = "[]" * target_dimensions
            sdims = "[]" * source_dimensions
            return res.failure(
                RTError(
                    self.source_code_listing.get(type_spec_node.line),
                    type_spec_node.line,
                    type_spec_node.column,
                    f"OLC1155",
                    f"type '{source_type_name + sdims}' cannot be assign to type '{target_type_name + tdims}'",
                    context,
                    self.file,
                )
            )

        return res.success(
            Boolean(are_types_assignables)
            .set_context(context)
            .set_pos(type_spec_node.line, type_spec_node.column)
        )

    #######################################################################################

    def visit_VarDeclarationNode(self, node, context):
        # class VarDeclarationNode:
        # 	def __init__(self, token, identifier_node, init_expr_node, is_constant, type_spec_node=None):
        # 		self.token = token # The 'VAR' token
        # 		self.identifier_node = identifier_node # An IdentifierNode
        # 		self.init_expr_node = init_expr_node # An expression node to initialize the variable or constant
        # 		self.is_constant = is_constant # True if constant, else False
        # 		self.type_spec_node = type_spec_node # A type spec node
        #
        # 		self.line = token.lineno
        # 		self.column = token.lexpos

        res = RTResult()

        # Check some restrictions on variable declaration

        # Constant declaration must have an initialization expression
        if node.is_constant and not node.init_expr_node:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    f"OLC1155",
                    f"constant expressions must be initialized",
                    context,
                    self.file,
                )
            )

        # If not type given and no init expression given
        if not node.type_spec_node or not node.init_expr_node:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    f"OLC1155",
                    f"must provide a type and an init expression for the declaration",
                    context,
                    self.file,
                )
            )

        # the name of the variable to be declared
        var_name = node.identifier_node.token.value

        # check if we were given a type
        type_ = None
        if node.type_spec_node:
            # get the type
            type_ = res.register(self.visit(node.type_spec_node, context))
            if res.should_return():
                return res

        # Check if variable is already defined
        entry = context.lookup_local(var_name)

        # If already defined we return an error
        if entry is not None:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    f"OLC2020",
                    f"name '{var_name}' is already defined.",
                    context,
                    self.file,
                )
            )

        # Evaluate the init expression
        value = res.register(self.visit(node.init_expr_node, context))
        if res.should_return():
            return res

        expr_type_form = value.get_type_spec().get_form()
        # This is for interface variable declarations
        if type_:
            # check if the type is an interface
            if (
                type_[0].get_form() == TypeForm.INTERFACE
                and expr_type_form == TypeForm.INTERFACE
            ):
                # get the interface entry info
                interface_entry = self.global_context.lookup_interface(
                    type_[0].get_identifier().name
                )
                if not interface_entry:
                    return res.failure(
                        RTError(
                            self.source_code_listing.get(node.line),
                            node.line,
                            node.column,
                            f"NameError",
                            f"name '{type_[0].get_identifier().name}' is not defined.",
                            context,
                            self.file,
                        )
                    )
                # compare field names in the interface map against the expression fields
                interface_entry_fields = set(interface_entry.keys())
                value_fields = set(value.fields.variables.entries())
                if interface_entry_fields != value_fields:
                    if len(value_fields) < len(interface_entry_fields):
                        msg = (
                            f'Propertie(s): \'{", ".join(interface_entry_fields - value_fields)}\''
                            f" missing in '{type_[0].get_identifier().name}'"
                        )
                    else:
                        msg = (
                            f'\'{", ".join(value_fields - interface_entry_fields)}\''
                            f" does not exist in '{type_[0].get_identifier().name}'"
                        )
                    return res.failure(
                        RTError(
                            self.source_code_listing.get(node.line),
                            node.line,
                            node.column,
                            f"OLC2322",
                            msg,
                            context,
                            self.file,
                        )
                    )
                # Type checking of fields
                fields = interface_entry.keys()
                for field in fields:
                    field_type_spec = interface_entry[field]
                    field_value = value.fields.variables.lookup(field).get_attribute(
                        SymtabKey.RUNTIME_VALUE
                    )
                    type_check_result = res.register(
                        self.are_types_assignment_compatible(
                            field_type_spec, field_value, context, node
                        )
                    )
                    if res.should_return():
                        return res
                # lookup the interface type in the global context
                the_type = self.global_context.lookup_type(
                    type_[0].get_identifier().name
                ).get_type_spec()
                value.get_type_spec().set_base_type(the_type)

        # are type compatibles for assignment
        assign_result = res.register(
            self.are_types_assignment_compatible(
                type_, value, context, node.type_spec_node
            )
        )
        if res.should_return():
            return res

        # enter the new variable into the symbol table
        entry = context.enter(var_name)

        # Set the value attribute of the entry
        entry.set_attribute(SymtabKey.RUNTIME_VALUE, value)

        # set if it's a constant definition
        if node.is_constant:
            entry.set_definition(Definition.CONSTANT)
        else:
            entry.set_definition(Definition.VARIABLE)

        # Set the entry type spec
        entry.set_type_spec(type_)

        self.symbols[(var_name, node.token.lineno, node.token.lexpos)] = Symbol(
            var_name,
            "constant" if node.is_constant else "variable",
            self.get_name_of_type(value),
            context.display_name,
            node.token.lineno,
            node.token.lexpos,
        )

        return res.success(
            Undefined().set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_IdentifierNode(self, node, context):
        res = RTResult()
        var_name = node.token.value
        value = context.lookup(var_name)

        if value is None:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    f"NameError",
                    f"name '{var_name}' is not defined.",
                    context,
                    self.file,
                )
            )

        return res.success(value.get_attribute(SymtabKey.RUNTIME_VALUE))

    #######################################################################################

    def print_context_variables(self, context):
        print(f"Context Name: {context.display_name}")
        print("------------------------------------------")
        for key in context.variables.entries():
            print(key)
        print("------------------------------------------")

    #######################################################################################

    def visit_ProgramNode(self, node, context):
        res = RTResult()
        last_evaluated = None

        for statement in node.statements:
            last_evaluated = res.register(self.visit(statement, context))
            if res.error:
                self.errors.append(res.error.as_string())
                self.log.append(res.error.as_string())
                print(res.error.as_string())

        # Create the report for errors and logs
        self.errors_as_string = "\n".join([err for err in self.errors])

        # Create the log for console
        self.log_as_string = "\n".join([line for line in self.log])

        # Create the symbol table report
        self.symbols_as_string = "\n".join(
            [value.as_string() for value in self.symbols.values()]
        )

        return 0

    #######################################################################################

    def visit_ConsoleLogNode(self, node, context):
        res = RTResult()
        results = []
        for expr in node.arguments:
            result = res.register(self.visit(expr, context))
            if res.should_return():
                return res
            results.append(result.__str__())

        line = " ".join(results)
        self.log.append(line)
        print(line)

        return res.success(
            Undefined().set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_BreakNode(self, node, context):
        res = RTResult()
        if not context.is_break_allowed():
            runtime_error = RTError(
                self.source_code_listing.get(node.line),
                node.line,
                node.column,
                "SyntaxError",
                f"'break' outside of switch/case or loop",
                context,
                self.file,
            )
            return res.failure(runtime_error)
        return res.success_break()

    #######################################################################################

    def visit_ContinueNode(self, node, context):
        res = RTResult()
        if not context.is_continue_allowed():
            runtime_error = RTError(
                self.source_code_listing.get(node.line),
                node.line,
                node.column,
                "SyntaxError",
                f"'continue' outside of loop",
                context,
                self.file,
            )
            return res.failure(runtime_error)

        return res.success_continue()

    #######################################################################################

    def visit_ReturnNode(self, node, context):
        res = RTResult()
        if not context.is_return_allowed():
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    f"OLC4122",
                    f"'return' outside of function.",
                    context,
                    self.file,
                )
            )
        if node.expr_node:
            value = res.register(self.visit(node.expr_node, context))
            if res.should_return():
                return res
        else:
            value = Undefined().set_context(context).set_pos(node.line, node.column)

        return res.success_return(value)

    #######################################################################################

    def visit_IfElseNode(self, node, context):
        # token
        # expr_node
        # consequence
        # alternative

        res = RTResult()

        # eval the expression
        expr_value = res.register(self.visit(node.expr_node, context))
        if res.should_return():
            return res

        # type check
        if not isinstance(expr_value, Boolean):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC3411",
                    f"'{self.get_name_of_type(expr_value)}' is not a valid type for 'if' test expression, required 'boolean'.",
                    context,
                    self.file,
                )
            )

        # If true...
        if expr_value.value is True:
            stmts = node.consequence.statements
            if_context = IfContext("if", context, node.line)
            for stmt in stmts:
                value = res.register(self.visit(stmt, if_context))
                if res.should_return():
                    return res
        else:  # else branch (if any)
            if node.alternative:
                if isinstance(node.alternative, IfElseNode):
                    stmt = res.register(self.visit(node.alternative, context))
                    if res.should_return():
                        return res
                elif isinstance(node.alternative, BlockNode):
                    stmts = node.alternative.statements
                    else_context = IfContext("if", context, node.line)
                    for stmt in stmts:
                        value = res.register(self.visit(stmt, else_context))
                        if res.should_return():
                            return res

        # If is a statement should not return anything, but we return undefined for the sake of it.
        return res.success(
            Undefined().set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_AssignNode(self, node, context):
        res = RTResult()

        # lookup the variable name in the context and any parent context
        entry = context.lookup(node.target.token.value)

        # not found
        if not entry:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "TypeError",
                    f"'{node.target.token.value}' is not defined.",
                    context,
                    self.file,
                )
            )

        # Error if it's a constant definition
        if entry.get_definition() == Definition.CONSTANT:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC2588",
                    f"cannot assign to '{node.target.token.value}' because is a constant",
                    context,
                    self.file,
                )
            )

        # Evaluate the expression for the assignment
        value = res.register(self.visit(node.rvalue, context))

        # Get the type spec for the entry
        entry_type_spec = entry.get_type_spec()
        # Chck if types are compatible for assignment.
        are_assignment_compatible = res.register(
            self.are_types_assignment_compatible(entry_type_spec, value, context, node)
        )
        if res.should_return():
            return res

        # All OK.
        entry.set_attribute(SymtabKey.RUNTIME_VALUE, value)

        # Assignment is a statement, should not return anything but we return undefined for the sake of it.
        return res.success(
            Undefined().set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_WhileNode(self, node, context):
        res = RTResult()
        # The body of the while node
        stmts = node.block.statements
        # For logic control of the loop
        should_continue = False
        should_break = False
        while True:
            condition = res.register(self.visit(node.expr_node, context))
            if res.should_return():
                return res
            # Type checking the condition must be of type boolean
            if not isinstance(condition, Boolean):
                return res.failure(
                    RTError(
                        self.source_code_listing.get(node.line),
                        node.line,
                        node.column,
                        "OLC2588",
                        f"while test condition must be of type 'boolean', got {self.get_name_of_type(condition)}",
                        context,
                        self.file,
                    )
                )
            if condition.value is not True or should_break:
                break
            while_context = WhileContext("while", context, node.line)
            for stmt in stmts:
                value = res.register(self.visit(stmt, while_context))
                if (
                    res.should_return()
                    and res.loop_should_continue is False
                    and res.loop_should_break is False
                ):
                    return res

                if res.loop_should_continue:
                    break

                if res.loop_should_break:
                    should_break = True
                    break

        return res.success(
            Undefined().set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_BuiltinParseInt(self, node, context):
        res = RTResult()
        value = res.register(self.visit(node.argument, context))
        if res.should_return():
            return res
        # Type checking?
        # all values at runtime have a string representation, so it should be
        # not to do type checking.
        try:
            value_as_python_int = int(value.value)
            value = Number(value_as_python_int)
        except ValueError:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC7714",
                    f"could not parse number",
                    context,
                    self.file,
                )
            )
        return res.success(value.set_context(context).set_pos(node.line, node.column))

    #######################################################################################

    def visit_BuiltinParseFloat(self, node, context):
        res = RTResult()
        value = res.register(self.visit(node.argument, context))
        if res.should_return():
            return res
        # Type checking?
        # all values at runtime have a string representation, so it should be
        # not to do type checking.
        try:
            value_as_python_float = float(value.value)
            value = Number(value_as_python_float)
        except ValueError:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC7715",
                    f"Could not parse float.",
                    context,
                    self.file,
                )
            )
        return res.success(value.set_context(context).set_pos(node.line, node.column))

    #######################################################################################

    def visit_BuiltinToString(self, node, context):
        res = RTResult()

        value = res.register(self.visit(node.argument, context))
        if res.should_return():
            return res

        # TODO: Typechecking
        value_as_string = String(value.__repr__())

        return res.success(
            value_as_string.set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_BuiltinToLowerCase(self, node, context):
        res = RTResult()

        value = res.register(self.visit(node.argument, context))
        if res.should_return():
            return res

        if not isinstance(value, String):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC7715",
                    f"invalid type for toLowerCase()",
                    context,
                    self.file,
                )
            )

        value_as_string = String(value.__str__().lower())

        return res.success(
            value_as_string.set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_BuiltinToUpperCase(self, node, context):
        res = RTResult()

        value = res.register(self.visit(node.argument, context))
        if res.should_return():
            return res

        # type check
        if not isinstance(value, String):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC7715",
                    f"invalid type for toUpperCase()",
                    context,
                    self.file,
                )
            )
        value_as_string = String(value.__str__().upper())

        return res.success(
            value_as_string.set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_ArrayNode(self, node, context):
        res = RTResult()
        # add a dimension to the array
        self.array_dimensions.append(1)

        # Create the array object
        arr = Array()
        arr.dims = len(self.array_dimensions)

        # eval the array expression's
        for element in node.elements:
            value = res.register(self.visit(element, context))
            if res.should_return():
                self.array_dimensions = []
                return res
            arr.add_item(value)

        # remove a dimension from the array
        self.array_dimensions.pop()

        # Do all the type checking
        if arr.dims == 1:
            # Find the base type of the array(should be a primitive type or interface type)
            # Returns a tuple with the types in the array, if the length of the tuple is
            # greater than one, then we got an error.
            array_base_type = self.get_types_in_array(arr, {})
            is_array_of_interfaces = True
            for item in arr.elements:
                if not item.get_type_spec().get_form() == TypeForm.INTERFACE:
                    is_array_of_interfaces = False
            if len(array_base_type) != 1 and not is_array_of_interfaces:
                # set the array dimension stack to zero
                self.array_dimensions = []
                return res.failure(
                    RTError(
                        self.source_code_listing.get(node.line),
                        node.line,
                        node.column,
                        "TypeError",
                        f"Invalid array expression.",
                        context,
                        self.file,
                    )
                )
            # the base type of the array
            if is_array_of_interfaces:
                base_type = arr.elements[0].get_type_spec().get_base_type()
            else:
                base_type = next(iter(array_base_type.values()))

            # Get the maximum dimension of the array
            max_dim = self.get_max_dim_in_array(arr)
            arr.dims = max_dim

            # if the array has more than one dimension it becomes a matrix
            if arr.dims > 1:
                arr.set_type_spec(TypeFactory.create_type(TypeForm.MATRIX))
            arr.get_type_spec().set_base_type(base_type)

            # set the array and sub-arrays dimension and base type form
            self.set_array_dims_and_form(arr, arr.dims, base_type)

            # check the matrix dimension equality
            if arr.dims > 1:
                for item in arr.elements:
                    if isinstance(item, Array):
                        if item.dims != arr.dims - 1:
                            self.array_dimensions = []
                            return res.failure(
                                RTError(
                                    self.source_code_listing.get(node.line),
                                    node.line,
                                    node.column,
                                    "TypeError",
                                    f"Invalid array expression.",
                                    context,
                                    self.file,
                                )
                            )
                    else:
                        self.array_dimensions = []
                        return res.failure(
                            RTError(
                                self.source_code_listing.get(node.line),
                                node.line,
                                node.column,
                                "TypeError",
                                f"Invalid array expression.",
                                context,
                                self.file,
                            )
                        )

        # returns the array
        return res.success(arr.set_context(context).set_pos(node.line, node.column))

    def get_types_in_array(self, arr, types_=None):
        if isinstance(arr, Array):
            for item in arr.elements:
                if not isinstance(item, Array):
                    types_[item.get_type_spec()] = item.get_type_spec()
                self.get_types_in_array(item, types_)
        else:
            types_[arr.get_type_spec()] = arr.get_type_spec()
        return types_

    def set_array_dims_and_form(self, arr, dims, type_):
        for item in arr.elements:
            if isinstance(item, Array):
                item.dims = dims - 1
                item.get_type_spec().set_base_type(type_)
                self.set_array_dims_and_form(item, item.dims, type_)
            if isinstance(arr, Array):
                if arr.dims > 1:
                    arr.set_type_spec(TypeFactory.create_type(TypeForm.MATRIX))
                    arr.get_type_spec().set_base_type(type_)

    def get_max_dim_in_array(self, arr):
        for item in arr.elements:
            if isinstance(item, Array):
                return self.get_max_dim_in_array(item)
        return arr.dims

    #######################################################################################

    def visit_ArrayAccessNode(self, node, context):
        res = RTResult()

        left = res.register(self.visit(node.left, context))
        if res.should_return():
            return res

        # is the left hand side a valid array expression ?
        if (
            not left.get_type_spec().form == TypeForm.ARRAY
            and not left.get_type_spec().form == TypeForm.MATRIX
        ):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "TypeError",
                    f"'{self.get_name_of_type(left)}' type is not subscriptable",
                    context,
                    self.file,
                )
            )

        # If node.right is None then node.left is a set array expression
        if node.right is None:
            return res.success(
                left.set_context(context).set_pos(node.line, node.column)
            )

        # visit the right side of the node
        right = res.register(self.visit(node.right, context))
        if res.should_return():
            return res

        # right must be of type number
        if not isinstance(right, Number):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "TypeError",
                    f"'{right}' is not a valid index",
                    context,
                    self.file,
                )
            )

        max_index = left.length()
        if right.value < 0 or right.value > max_index - 1:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "IndexError",
                    f"Array index out of bounds.",
                    context,
                    self.file,
                )
            )

        # get the value of the python list variable
        value = left.get_item(right.value)

        return res.success(value.set_context(context).set_pos(node.line, node.column))

    #######################################################################################

    def visit_BuiltinIndexOf(self, node, context):
        res = RTResult()

        left = res.register(self.visit(node.arr, context))
        if res.should_return():
            return res
        if len(node.argument) != 1:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC8812",
                    f"to many or to few arguments, got: {len(node.argument)}, expect: 1",
                    context,
                    self.file,
                )
            )

        if not isinstance(left, Array):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC8811",
                    f"not an array",
                    context,
                    self.file,
                )
            )

        right = res.register(self.visit(node.argument[0], context))
        if res.should_return():
            return res

        return_value = left.indexOf(right)

        return res.success(
            return_value.set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_BuiltinPush(self, node, context):
        res = RTResult()

        left = res.register(self.visit(node.arr, context))
        if res.should_return():
            return res

        if len(node.argument) != 1:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC8812",
                    f"to many or to few arguments, got: {len(node.argument)}, expect: 1",
                    context,
                    self.file,
                )
            )

        if not isinstance(left, Array):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC8811",
                    f"not an array",
                    context,
                    self.file,
                )
            )

        right = res.register(self.visit(node.argument[0], context))
        if res.should_return():
            return res

        left.push(right)
        return_value = Number(len(left.elements))

        return res.success(
            return_value.set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_BuiltinPop(self, node, context):
        res = RTResult()

        left = res.register(self.visit(node.arr, context))
        if res.should_return():
            return res

        if not isinstance(left, Array):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC8811",
                    f"not an array",
                    context,
                    self.file,
                )
            )

        return_value = left.pop()

        return res.success(
            return_value.set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_BuiltinLength(self, node, context):
        res = RTResult()

        left = res.register(self.visit(node.arr, context))
        if res.should_return():
            return res

        if not isinstance(left, Array):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC8811",
                    f"not an array",
                    context,
                    self.file,
                )
            )

        return_value = left.builtin_length()

        return res.success(
            return_value.set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_BuiltinJoin(self, node, context):
        res = RTResult()

        left = res.register(self.visit(node.arr, context))
        if res.should_return():
            return res

        if not isinstance(left, Array):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC8811",
                    f"not an array",
                    context,
                    self.file,
                )
            )

        return_value = left.join()

        return res.success(
            return_value.set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_FunctionNode(self, node, context):
        # node structure
        # token - The token 'function'
        # name - An Identifier node
        # parameters - An array of ParameterNodes
        # body - A block node with an array of statements nodes
        # ret_type_spec - A type spec for the return type of the function
        res = RTResult()

        # check if the function is already defined
        fn_name = self.global_context.lookup_function(node.name.token.value)

        if fn_name:
            res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC1222",
                    f"function {node.name.token.value} is already defined",
                    context,
                    self.file,
                )
            )

        # Check the function return type
        if node.ret_type_spec:
            res_type = res.register(self.visit(node.ret_type_spec, context))
            if res.should_return():
                return res
        else:
            res_type = None

        fn_ret_type_name = self.get_name_of_type(res_type) if res_type else "undefined"
        fn_symbol = Symbol(
            node.name.token.value,
            "function",
            fn_ret_type_name,
            context.display_name,
            node.line,
            node.column,
        )

        # check for parameter already defined
        fn_param_names = []
        for param in node.parameters:
            if param.parameter_name.token.value in fn_param_names:
                return res.failure(
                    RTError(
                        self.source_code_listing.get(param.parameter_name.line),
                        param.parameter_name.line,
                        param.parameter_name.column,
                        "OLC1224",
                        f"parameter {param.parameter_name.token.value} is already defined",
                        context,
                        self.file,
                    )
                )
            fn_param_names.append(param.parameter_name.token.value)

        fn_param_symbols = {}
        for param in node.parameters:
            param_type = res.register(self.visit(param.parameter_type_spec, context))
            if res.should_return():
                return res
            param_type_name = self.get_name_of_type(param_type)
            fn_param_symbols[
                (param.parameter_name.token.value, param.line, param.column)
            ] = (
                param.parameter_name.token.value,
                "parameter",
                param_type_name,
                node.name.token.value,
                param.line,
                param.column,
            )

        # Enter the symbol for reports
        self.symbols[(node.name.token.value, node.line, node.column)] = fn_symbol
        # Enter the parameters
        for key, value in fn_param_symbols.items():
            self.symbols[key] = Symbol(
                value[0],
                value[1],
                value[2],
                value[3],
                value[4],
                value[5],
            )

        # enter the function into the functions map
        self.global_context.enter_function(node.name.token.value, node)

        return res.success(
            Undefined().set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_CallExprNode(self, node, context):
        # CallExprNode:
        # caller - the name of the caller
        # token - the token (
        # arguments - a list of arguments (expressions)

        # ParameterNode:
        # token - the token ':'
        # parameter_name - the name of the parameter (IdentifierNode)
        # parameter_type_spec - the type spec of the parameter
        # self.ret_type_spec - A type spec node with the function return type(if any)

        res = RTResult()

        # check that the caller is a valid identifier function name
        if not isinstance(node.caller, IdentifierNode):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC1223",
                    f"Invalid call expression.",
                    context,
                    self.file,
                )
            )

        # get the function information
        fn = self.global_context.lookup_function(node.caller.token.value)
        # if the function is not defined
        if not fn:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC1224",
                    f"Function '{node.caller.token.value}' is not defined.",
                    context,
                    self.file,
                )
            )

        # check arg number vs param number
        if len(node.arguments) < len(fn.parameters) or len(node.arguments) > len(
            fn.parameters
        ):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC1225",
                    f"Too few or too many arguments in function call, {len(node.arguments)} given, {len(fn.parameters)} expected",
                    context,
                    self.file,
                )
            )

        # visit each argument to get its value
        args = []
        params = fn.parameters

        for index, arg in enumerate(node.arguments):
            value = res.register(self.visit(arg, context))
            if res.should_return():
                return res
            args.append(value.set_context(context).set_pos(node.line, node.column))

            # Type checking argument type vs parameter type
            param_type = res.register(
                self.visit(params[index].parameter_type_spec, context)
            )
            if res.should_return():
                return res
            are_compatible = res.register(
                self.are_types_assignment_compatible(
                    param_type, args[-1], context, params[index].parameter_type_spec
                )
            )
            if res.should_return():
                return res

        # A context to execute the function
        function_context = FunctionContext(fn.name.token.value, context, node.line)

        # bind every argument value to every parameter
        # Enter the argument name in the context
        for param in fn.parameters:
            function_context.enter(param.parameter_name.token.value)
        for index, val in enumerate(fn.parameters):
            entry = function_context.lookup_local(val.parameter_name.token.value)
            entry.set_attribute(SymtabKey.RUNTIME_VALUE, args[index])

        function_return_type = (
            res.register(self.visit(fn.ret_type_spec, context))
            if fn.ret_type_spec
            else None
        )
        # Start evaluating each statement in the function body
        for stmt in fn.body.statements:
            v = res.register(self.visit(stmt, function_context))
            if res.should_return():
                if res.func_return_value:
                    return_value = res.func_return_value
                    if function_return_type:
                        check_type = res.register(
                            self.are_types_assignment_compatible(
                                function_return_type, return_value, context, node
                            )
                        )
                        if res.should_return():
                            return res
                    else:
                        if (
                            return_value.get_type_spec().get_form()
                            != TypeForm.UNDEFINED
                        ):
                            return res.failure(
                                RTError(
                                    self.source_code_listing.get(node.line),
                                    node.line,
                                    node.column,
                                    "OLC1225",
                                    f"function '{node.caller.token.value}' SHOULD NOT return a value",
                                    context,
                                    self.file,
                                )
                            )

                    # Propagate the return value
                    return res.success(
                        return_value.set_context(context).set_pos(
                            node.line, node.column
                        )
                    )
                # return res.success(res.func_return_value.set_context(context).set_pos(node.line, node.column))
                return res

        if function_return_type:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC1225",
                    f"function '{node.caller.token.value}' must return a value",
                    context,
                    self.file,
                )
            )

        return res.success(
            Undefined().set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_SwitchCaseNode(self, node, context):
        # token - the 'switch' token
        # switch_expr_node - expression to switch
        # cases_node - list of case nodes
        # number_of_default_nodes - number of default node ( for error checking )
        # default_case_node - the default case node

        res = RTResult()

        # switch errors
        if (
            len(node.cases_node) == 0
            and node.number_of_default_nodes != 1
            or node.number_of_default_nodes != 1
        ):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "SwitchError",
                    f"Switch with no cases or too many default cases",
                    context,
                    self.file,
                )
            )

        # eval the expression to switch on
        switch_expr_value = res.register(self.visit(node.switch_expr_node, context))
        if res.should_return():
            return res

        seen_break = False
        found_a_match = False
        for case in node.cases_node:
            if not found_a_match:
                case_expr_value = res.register(self.visit(case.case_expr_node, context))
                if res.should_return():
                    return res
            else:
                case_expr_value = switch_expr_value
            case_context = CaseContext("case", context, node.line)
            if switch_expr_value.value == case_expr_value.value:
                found_a_match = True
                for stmt in case.statements:
                    value = res.register(self.visit(stmt, case_context))
                    if res.should_return():
                        if res.loop_should_break:
                            seen_break = True
                            break
                        return res
            if seen_break:
                break
        # execute the default node if not found a match
        if not found_a_match:
            case_context = CaseContext("case", context, node.line)
            for stmt in node.default_case_node.statements:
                value = res.register(self.visit(stmt, case_context))
                if res.should_return():
                    return res

        return res.success(
            Undefined().set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_ForNode(self, node, context):
        # token - the token 'for'
        # init_node - a list of variable declaration nodes
        # test_node - an expression that controls the loop
        # update_node - a list of assignments nodes
        # statements - the body of the loop
        res = RTResult()

        for_context = ForContext("for", context, node.line)

        # eval the init node
        for declaration in node.init_node:
            value = res.register(self.visit(declaration, for_context))
            if res.should_return():
                return res

        # eval the loop condition and then the body
        stmts = node.statements.statements
        should_continue = False
        should_break = False

        while True:
            condition = res.register(self.visit(node.test_node, for_context))
            if res.should_return():
                return res
            if condition.value is not True or should_break:
                break
            inner_for_context = ForContext("for", for_context, node.line)
            for stmt in stmts:
                value = res.register(self.visit(stmt, inner_for_context))
                if (
                    res.should_return()
                    and res.loop_should_continue is False
                    and res.loop_should_break is False
                ):
                    return res

                if res.loop_should_continue:
                    break

                if res.loop_should_break:
                    should_break = True
                    break

            # update the loop control variable
            if not should_break:
                for update in node.update_node:
                    value = res.register(self.visit(update, for_context))
                    if res.should_return():
                        return res

        return res.success(
            Undefined().set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_TernaryOperationNode(self, node, context):
        # token - the '?' token
        # expr_node - the expression to branch either true or false
        # true_expr - the true branch
        # false_expr - the false branch
        res = RTResult()

        # Eval the expression node
        expr_value = res.register(self.visit(node.expr_node, context))
        if res.should_return():
            return res
        # The condition expression must be of type boolean
        if not isinstance(expr_value, Boolean):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.expr_node.line),
                    node.expr_node.line,
                    node.expr_node.column,
                    "TypeError",
                    f"not a boolean expression for ternary operator",
                    context,
                    self.file,
                )
            )
        # The flow is pretty much like a if/else statement
        if expr_value.value is True:
            value = res.register(self.visit(node.true_expr, context))
            if res.should_return():
                return res
        else:
            value = res.register(self.visit(node.false_expr, context))
            if res.should_return():
                return res

        # return the result
        return res.success(value.set_context(context).set_pos(node.line, node.column))

    #######################################################################################

    def visit_TypeNode(self, node, context):
        res = RTResult()
        # token - the token type identifier ( a string )
        # type_ - the type identifier ( a string )
        # dims - the number of dimensions (if any) of the type

        # look the type identifier in the global context
        type_entry = self.global_context.lookup_type(node.type_)

        # if not found
        if not type_entry:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC2304",
                    f"Cannot find name '{node.type_}'",
                    context,
                    self.file,
                )
            )

        # check if the type is declared as array or matrix
        if node.dims >= 2:
            new_matrix_type = TypeFactory.create_type(TypeForm.MATRIX)
            new_matrix_type.set_base_type(type_entry)
            return res.success((new_matrix_type, node.dims))
        if node.dims == 1:
            new_array_type = TypeFactory.create_type(TypeForm.ARRAY)
            new_array_type.set_base_type(type_entry)
            return res.success((new_array_type, node.dims))

        # the type is no array or matrix
        if type_entry.get_type_spec().get_form() == TypeForm.INTERFACE:
            return res.success((type_entry.get_type_spec(), node.dims))

        return res.success((type_entry.get_type_spec(), node.dims))

    #######################################################################################

    def visit_InterfaceNode(self, node, context):
        # token - the 'interface' token
        # name - the interface identifier (string)
        # fields - the interface fields ( a list of FieldNode )

        # class FieldNode:
        # 	__init__(self, token, field_name, field_type):
        # 		self.token = token
        # 		self.field_name = field_name
        # 		self.field_type = field_type

        # class TypeNode:
        # 	def __init__(self, token, type_, dims=0):
        # 		self.token = token
        # 		self.type_ = type_
        # 		self.dims = dims

        res = RTResult()

        # look up the interface type name in the types symbol table
        interface_entry_name = self.global_context.lookup_type(node.name)
        if interface_entry_name:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC2145",
                    f"field is already declared in interface",
                    context,
                    self.file,
                )
            )

        fields = {}
        interface_symbols = {}
        for field in node.fields:
            # check if the field is already declared
            if field.field_name in fields.keys():
                return res.failure(
                    RTError(
                        self.source_code_listing.get(field.line),
                        node.line,
                        node.column,
                        "TypeError",
                        f"'{field.field_name}' is already declared in interface",
                        context,
                        self.file,
                    )
                )
            # eval the type node
            type_ = res.register(self.visit(field.field_type, context))
            if res.should_return():
                return res
            # enter the field in the fields map
            fields[field.field_name] = type_
            # Add the field as a symbol for reporting
            interface_symbols[
                (field.field_name, field.token.lineno, field.token.lexpos)
            ] = (
                field.field_name,
                "field",
                self.get_name_of_type(type_),
                node.name,
                field.token.lineno,
                field.token.lexpos,
            )

        # Create an entry for the interface name
        self.global_context.enter_interface(node.name, fields)

        # Create the type
        interface_id = self.global_context.enter_type(node.name)
        interface_type = TypeFactory.create_type(TypeForm.INTERFACE)
        interface_type.set_identifier(interface_id)
        interface_id.set_definition(Definition.TYPE)
        interface_id.set_type_spec(interface_type)

        # Enter the symbol for reports
        i_sym = Symbol(
            node.name,
            "interface",
            node.name,
            context.display_name,
            node.token.lineno,
            node.token.lexpos,
        )
        self.symbols[(node.name, node.token.lineno, node.token.lexpos)] = i_sym
        # Enter the fields
        for key, value in interface_symbols.items():
            self.symbols[key] = Symbol(
                value[0], value[1], value[2], value[3], value[4], value[5]
            )

        # Since this is a statement it should not return anything
        return res.success(
            Undefined().set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_InterfaceExprNode(self, node, context):
        # token - the '{' token
        # expr_fields - a list of field_expr nodes
        res = RTResult()

        interface_value = Interface()

        for field in node.expr_fields:
            entry = interface_value.fields.lookup(field.field_name)
            if entry:
                return res.failure(
                    RTError(
                        self.source_code_listing.get(field.line),
                        node.line,
                        node.column,
                        "TypeError",
                        f"'{field.field_name}' is already declared in interface",
                        context,
                        self.file,
                    )
                )
            expr_value = res.register(self.visit(field.expr_node, context))
            if res.should_return():
                return res
            entry = interface_value.fields.enter(field.field_name)
            entry.set_attribute(SymtabKey.RUNTIME_VALUE, expr_value)

        return res.success(
            interface_value.set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_MemberAccessNode(self, node, context):
        res = RTResult()

        # left should be an Interface value with a map of valid field names and value
        left_expr = res.register(self.visit(node.left, context))
        if res.should_return():
            return res

        if not isinstance(left_expr, Interface):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.right.line),
                    node.line,
                    node.column,
                    "OLC6614",
                    f"only interfaces have fields",
                    context,
                    self.file,
                )
            )

        # If node.right is None then node.left is a set member expression
        if node.right is None:
            return res.success(
                left_expr.set_context(context).set_pos(node.line, node.column)
            )

        if not isinstance(node.right, IdentifierNode):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.right.line),
                    node.line,
                    node.column,
                    "TypeError",
                    f"invalid field name.",
                    context,
                    self.file,
                )
            )

        right_expr = left_expr.fields.lookup(node.right.token.value)
        if not right_expr:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.right.line),
                    node.line,
                    node.column,
                    "TypeError",
                    f"'{node.right.token.value}' is not a field of '{self.get_name_of_type(left_expr)}'.",
                    context,
                    self.file,
                )
            )

        value = right_expr.get_attribute(SymtabKey.RUNTIME_VALUE)

        return res.success(value.set_context(context).set_pos(node.line, node.column))

    #######################################################################################

    def visit_ArraySetExpression(self, node, context):
        # token - the token '['
        # lvalue - An ArrayAccessNode
        # target - An expression that should be evaluated to a number
        # rvalue - The expression to set the array
        res = RTResult()

        lvalue = res.register(self.visit(node.lvalue, context))
        if res.should_return():
            return res

        # lvalue must be of type array or matrix
        if not isinstance(lvalue, Array):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC5111",
                    f"'{self.get_name_of_type(lvalue)}' is not subscriptable",
                    context,
                    self.file,
                )
            )

        target = res.register(self.visit(node.target, context))
        if res.should_return():
            return res
        # target must be of type number
        if not isinstance(target, Number):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC5111",
                    f"invalid index",
                    context,
                    self.file,
                )
            )

        # check index out of bound
        if target.value < 0 or target.value > len(lvalue.elements) - 1:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC5111",
                    f"index out of bounds.",
                    context,
                    self.file,
                )
            )

        rvalue = res.register(self.visit(node.rvalue, context))
        if res.should_return():
            return res

        # Type check, value to override and rvalue must be type compatible
        value_to_override = lvalue.elements[target.value]
        type_check_result = res.register(
            self.are_values_assignment_compatible(
                value_to_override, rvalue, context, node
            )
        )
        if res.should_return():
            return res

        # All OK
        lvalue.elements[target.value] = rvalue

        return res.success(
            Undefined().set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_MemberSetExpression(self, node, context):
        # token - the token '.'
        # lvalue - An interface value
        # target - A string
        # rvalue - the value to set the field
        res = RTResult()

        left = res.register(self.visit(node.lvalue, context))
        if res.should_return():
            return res

        # check if left is an interface
        if not isinstance(left, Interface):
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.rvalue.line),
                    node.line,
                    node.column,
                    "OLC6614",
                    f"only interfaces have fields.",
                    context,
                    self.file,
                )
            )

        entry = left.fields.variables.lookup(node.target.token.value)
        if not entry:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.rvalue.line),
                    node.line,
                    node.column,
                    "OLC6618",
                    f"'{node.target.token.value}' is not a field of '{self.get_name_of_type(left)}'",
                    context,
                    self.file,
                )
            )

        value = res.register(self.visit(node.rvalue, context))
        # type check
        result_type = res.register(
            self.are_values_assignment_compatible(
                entry.get_attribute(SymtabKey.RUNTIME_VALUE), value, context, node
            )
        )
        if res.should_return():
            return res

        # All OK
        entry.set_attribute(SymtabKey.RUNTIME_VALUE, value)

        return res.success(
            Undefined().set_context(context).set_pos(node.line, node.column)
        )

    #######################################################################################

    def visit_ObjectKeysNode(self, node, context):
        res = RTResult()
        # Should only have one argument
        if len(node.argument) > 1:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "TypeError",
                    f"Invalid number of parameters for Object.keys()",
                    context,
                    self.file,
                )
            )

        # Eval the first argument
        result = res.register(self.visit(node.argument[0], context))

        # Type checking
        if result.get_type_spec().get_form() is not TypeForm.INTERFACE:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC2345",
                    f"'{self.get_name_of_type(result)}' is not an interface",
                    context,
                    self.file,
                )
            )

        keys = result.keys()

        return res.success(keys)

    #######################################################################################

    def visit_ObjectValuesNode(self, node, context):
        res = RTResult()

        if len(node.argument) > 1:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "TypeError",
                    f"Invalid number of parameters for Object.keys()",
                    context,
                    self.file,
                )
            )

        # Eval the first argument
        result = res.register(self.visit(node.argument[0], context))

        # Typ checking
        if result.get_type_spec().get_form() is not TypeForm.INTERFACE:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "OLC2345",
                    f"'{self.get_name_of_type(result)}' is not an interface",
                    context,
                    self.file,
                )
            )

        values = result.values()

        return res.success(values)

    #######################################################################################

    def visit_TypeOfNode(self, node, context):
        # class TypeOfNode:
        # 	def __init__(self, token, expr_node):
        # 		self.token = token
        # 		self.expr_node = expr_node
        #
        # 		self.line = token.lineno
        # 		self.column = token.lexpos
        res = RTResult()

        value = res.register(self.visit(node.expr_node, context))
        if res.should_return():
            return res

        form = value.get_type_spec().get_form()
        string_form = ""

        if form == TypeForm.NUMBER:
            string_form = "number"
        elif form == TypeForm.FLOAT:
            string_form = "float"
        elif form == TypeForm.BOOLEAN:
            string_form = "boolean"
        elif form == TypeForm.STRING:
            string_form = "string"
        elif form == TypeForm.CHAR:
            string_form = "char"
        elif form == TypeForm.NULL:
            string_form = "null"
        elif form == TypeForm.UNDEFINED:
            string_form = "undefined"
        elif form == TypeForm.ARRAY or form == TypeForm.MATRIX:
            string_form = (
                value.get_type_spec().get_base_type().get_identifier().name
                + "[]" * value.dims
            )
        elif form == TypeForm.INTERFACE:
            string_form = value.get_type_spec().get_base_type().get_identifier().name
        else:  # Should never get here
            string_form = "@#$!"

        return_value = (
            String(string_form).set_context(context).set_pos(node.line, node.column)
        )

        return res.success(return_value)

    #######################################################################################

    def visit_ForOfNode(self, node, context):
        # def __init__(self, token, left, right, statements):
        # 	self.token = token
        # 	self.left = left
        # 	self.right = right
        # 	self.block = block
        #
        # 	self.line = token.lineno
        # 	self.column = token.lexpos
        res = RTResult()

        # The for context
        for_context = ForContext("for", context, node.line)

        # Enter the control variable to the for context
        for_context.enter(node.left)

        # Figure out the type of the first element of the array to iterate
        right = res.register(self.visit(node.right, context))
        if res.should_return():
            return res

        if (
            right.get_type_spec().get_form() == TypeForm.ARRAY
            or right.get_type_spec().get_form() == TypeForm.MATRIX
        ):
            arr = right
        elif right.get_type_spec().get_form() == TypeForm.STRING:
            arr = right.to_array()
        else:
            return res.failure(
                RTError(
                    self.source_code_listing.get(node.line),
                    node.line,
                    node.column,
                    "TypeError",
                    f"'{self.get_name_of_type(right)}' is not subscriptable",
                    context,
                    self.file,
                )
            )

        # no point going any further since the array is empty
        if arr.is_empty():
            return res.success(
                Undefined().set_context(context).set_pos(node.line, node.column)
            )

        # The type of the element array
        # The for context
        for_context = ForContext("for", context, node.line)
        # Enter the control variable to the for context
        entry = for_context.enter(node.left)
        entry.set_definition(Definition.CONSTANT)

        # the body of the for loop
        stmts = node.block.statements
        should_continue = False
        should_break = False
        for element in arr.elements:
            entry.set_attribute(SymtabKey.RUNTIME_VALUE, element)
            inner_for_context = ForContext("for", for_context, node.line)
            for stmt in stmts:
                value = res.register(self.visit(stmt, inner_for_context))
                if (
                    res.should_return()
                    and res.loop_should_continue is False
                    and res.loop_should_break is False
                ):
                    return res

                if res.loop_should_continue:
                    should_continue = True
                    break

                if res.loop_should_break:
                    should_break = True
                    break
            if should_continue:
                should_continue = False
                continue
            if should_break:
                break

        return res.success(
            Undefined().set_context(context).set_pos(node.line, node.column)
        )


# ------------------------------------------------------------------- #
#                             MAIN                                    #
# ------------------------------------------------------------------- #

if __name__ == "__main__":
    app.run()
