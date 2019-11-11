# Copyright (c) 2018-2019 AT&T Intellectual Property. All rights reserved.
#
# SPDX-License-Identifier: GPL-2.0-only

from re import sub, findall, split, match
from string import Formatter
import operator
import ast

MISSING_VALUE_TEMPLATE = '???'
OPERATOR_EXPRESSION = r"(==|>=|<=|>|<|!=| in |\s)"


class CommandFiller:
    """Responsible for finding all patterns in the raw commands
    and filling them with their values that are passed as parameters.
    """
    PATTERN_REGEX = r'\[[^]]+\]'

    def __init__(self, command, debug=False):
        self.command = command
        self.debug = debug
        self.formatter = CommandFormatter(self.debug)

    def find_all_path_refs(self):
        """Finds all path references to other tree nodes that exist in the command
        @return: list of paths
        """
        return self.formatter.find_all_path_refs(self.command)

    def fill_command(self, values):
        """Treats all patterns in the raw command string"""
        # print(self.command, values)
        self.command = self.fill_values(values)
        self.execute_functions()
        self.finalize_sets()
        if MISSING_VALUE_TEMPLATE in self.command:
            # couldn't fill all required references
            self.discard_command()
        else:
            self.remove_extra_whitespaces()
        return self.command

    @staticmethod
    def execute_code(code):
        """Evaluate the python code given as string.
        Restrict any use of functions for safety
        """
        return eval(code, {'__builtins__': None})

    @staticmethod
    def _get_operator_fn(op):
        """Return a function based on a string. The returned function must
        operate on two values. If the operator isn't found in the dictionary
        return a shim function that prints a warning.
        When the dictionary is updated with a new operator the  OPERATOR_EXPRESSION
        constant must also be updated.
        """
        oper_dict = {
            '==': operator.eq,
            '>=': operator.ge,
            '<=': operator.le,
            '>': operator.gt,
            '<': operator.lt,
            '!=': operator.ne,
            " in ": CommandFiller.exists_in
        }
        return oper_dict[op] if op in oper_dict else CommandFiller._undefined_operator

    @staticmethod
    def _undefined_operator(a, b):
        """Shim function for when there's no function for an operator.
        TODO: Print the unknown operator as well as what it is acting on.
        """
        print("unknown operator acting on ", a, " and ", b)
        return False

    @staticmethod
    def exists_in(k, json_dict):
        """Wrapper function for a key test of a dictionary.
        Uses the ast.literal_eval as it works only on a reduced set of python
        code.

        It's possible that extremely large dictionaries will crash the python
        interpreter.
        """
        json_dict = json_dict.replace("&", ",")
        return k in ast.literal_eval(json_dict)

    @staticmethod
    def set_else(zipped_list):
        """Replace empty string else condition with a tautology so it's always
        true
        """
        if zipped_list[-1][0] == "":
            zipped_list[-1] = ("1==1", zipped_list[-1][1])
        return zipped_list

    @staticmethod
    def execute_conditional(conditional):
        """Evaluate the result of the conditional statement given as a
        list of
        ['function(if)', 'value1[,value2,...,valueN,]','condition1[condition2,...conditionN,]']
        Parsing each condition into the format [a, oper, b] using a for loop to find the first
        true condtion and then returning the corresponding value.
        """
        result = ''
        params = conditional[2].split(',')
        outcomes = conditional[1].split(',')
        # Keep backwards compatibility of else commands that are already written
        if len(outcomes) == len(params) + 1:
            params.append("")
        expression_pairs = list(zip(params, outcomes))
        expression_pairs = CommandFiller.set_else(expression_pairs)
        for pair in expression_pairs:
            # Filter out any tokens that are the empty string or just spaces
            # should be left with just the operator and what it's to act on
            tokens = [token for token in split(OPERATOR_EXPRESSION, pair[0])
                      if token != "" and match(r'^\s$', token) == None]
            if CommandFiller._get_operator_fn(tokens[1])(tokens[0], tokens[2]):
                result = pair[1]
                break
        return result

    @staticmethod
    def get_acl_target(target):
        """
        Check a dictionary for keys that an ACL could use to filter, also
        checking existance as the JSON can contain things like host but without
        a value.
        """
        if "any" in target:
            return "any"
        if "network" in target and (target["network"] is not None and target["network"] != ""):
            return "{0} {1}".format(target["network"], target["inverse-mask"])
        if "host" in target and (target["host"] is not None and target["host"] != ""):
            return "host {0}".format(target["host"])

    @staticmethod
    def execute_acl(acl_dict):
        """
        Function to generate config for an access control list

        This is a work around for the parser not being powerful enough to test
        a range of numbers, this is easier than extending the if condition code.
        This function will take each element of the /policy/route/access-list
        list and generate multiple lines of config for the access-list
        """
        json_dict = ast.literal_eval(acl_dict.replace("&", ","))
        result = ""
        acl_number = int(json_dict["tagnode"])
        prefix_string = "access-list {0}".format(str(acl_number))
        extended = False
        if (acl_number >= 100 and acl_number <= 199) or (acl_number >= 2000 and acl_number <= 2699):
            extended = True
        for rule in json_dict.get("rule", dict()):
            result += prefix_string+" {0}".format(rule["action"])
            if extended:
                result += " ip"
            result += " "+CommandFiller.get_acl_target(rule["source"])
            if extended:
                result += " "+CommandFiller.get_acl_target(rule["destination"])
            if rule != json_dict["rule"][-1]:
                result += "\n"
        return result

    def execute_functions(self):
        """find functions defined in the command, evaluate them and replace
        the pattern.
        """
        functions = [x[1:-1].split('|') + [x]
                     for x in findall(r'\$[^$]+\$', self.command)]
        result = ''
        for function in functions:
            if function[0] == 'if':
                result = CommandFiller.execute_conditional(function)
            elif function[0] == 'ex':
                result = CommandFiller.execute_code(function[1])
            elif function[0] == 'acl':
                result = CommandFiller.execute_acl(function[1])
            self.command = self.command.replace(function[-1], result)

    def discard_command(self):
        """Erases command to avoid unfilled commands entering the final config"""
        if self.debug:
            print('ERROR: Couldnt fill required parts of',
                  self.command, '. Omitting...')
        self.command = ''

    def fill_values(self, values):
        """Fill all resolved references"""
        return self.formatter.format(self.command, **values)

    def finalize_sets(self):
        """picks the first satisfied member of the set and replaces the set pattern with it.
        If none is satisfied, the command is discarded.
        Set members are comma separated. Optional sets have an empty member
        """
        for pattern in findall(self.PATTERN_REGEX, self.command):
            replacement = None
            for member in pattern[1:-1].split(','):
                if MISSING_VALUE_TEMPLATE not in member:
                    # value was replaced, found a satisfied member
                    replacement = member
                    break
            if replacement is not None:
                self.command = self.command.replace(pattern, replacement)

    def remove_extra_whitespaces(self):
        """remove extra whitespace occuring from substitutions"""
        self.command = sub(r'(\S) +', r'\1 ', self.command)


class CommandFormatter(Formatter):
    """Custom formatter subclass for the resolving of
    references in commands
    """

    def find_all_path_refs(self, msg):
        """use string formatter to retrieve all references inside {}.
        It returns them along with their formatting arguments so cut these out.
        """
        result = [x[1] for x in super().parse(msg) if x[1] is not None]
        return map(self.get_field_name, result)

    def get_field_name(self, identifier):
        """Cuts out formatting arguments from a reference"""
        field_name = identifier
        # currently only ! and : are the formatting operators so remove them if they exist.
        if '!' in field_name:
            field_name = field_name.split('!')[0]
        elif ':' in field_name:
            field_name = field_name.split(':')[0]
        return field_name

    def __init__(self, debug=False):
        self.debug = debug

    def get_value(self, key, args, kwargs):
        try:
            result = super(CommandFormatter, self).get_value(key, args, kwargs)
        except KeyError as _:
            result = MISSING_VALUE_TEMPLATE
            if self.debug:
                print('Warning: Could not find value of', key, 'in', kwargs)
        return result

    def format_field(self, value, format_spec):
        # extend this method for more custom formatting
        if format_spec.startswith('for'):
            template = format_spec.split(':')[-1]
            formatted_field = ''.join(
                [template.format(element=elem) for elem in value])
        else:
            formatted_field = super(
                CommandFormatter, self).format_field(value, format_spec)
        return formatted_field
