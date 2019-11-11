#!/usr/bin/env python3
# Copyright (c) 2018-2019 AT&T Intellectual Property. All rights reserved.
#
# SPDX-License-Identifier: GPL-2.0-only

import unittest
from command import CommandFiller, MISSING_VALUE_TEMPLATE


class CommandFillerTestCase(unittest.TestCase):

    # def setUp(self):
    #     self.actioner = Actioner()

    def test_find_patterns_simple(self):
        command = CommandFiller('abc {/name/@text} ef {/../surname/@text}')
        expected = ['/name/@text', '/../surname/@text']
        actual = list(command.find_all_path_refs())
        self.assertCountEqual(expected, actual)

    def test_find_patterns_optional(self):
        command = CommandFiller(
            'a [name is: {/name/@text},] ef [and surname {/../surname/@text}]')
        expected = ['/name/@text', '/../surname/@text']
        actual = list(command.find_all_path_refs())
        self.assertCountEqual(expected, actual)

    def test_find_patterns_optional_subs(self):
        command = CommandFiller(
            'abc [name is: {/name/@text}, and surname {/../surname/@text},]')
        expected = ['/name/@text', '/../surname/@text']
        actual = list(command.find_all_path_refs())
        self.assertCountEqual(expected, actual)

    def test_fill_simple(self):
        command = CommandFiller('abc {/name/@text} ef')
        inputValues = dict([('/name/@text', 'Mix')])
        actual = command.fill_values(inputValues)
        expected = 'abc Mix ef'
        self.assertEqual(expected, actual)

    def test_fill_optionals_refs(self):
        command = CommandFiller('abc [{/name/@text}] [whose surname is {/namesurname/@text},]' +
                                ' ef [{name-surname/@text}, initials {/names/@text}]')
        inputValues = dict([('/name/@text', 'Mix'), ('/namesurname/@text', 'mair'),
                            ('name-surname/@text', 'MM'), ('/names/@text', 'theo')])
        actual = command.fill_values(inputValues)
        expected = 'abc [Mix] [whose surname is mair,] ef [MM, initials theo]'
        self.assertEqual(expected, actual)

    def test_fill_missing_marked(self):
        command = CommandFiller(
            'abc {/name/@text} ef [name {/names/@text}] and {/age/@text}')
        inputValues = dict([('/name/@text', 'Mix')])
        actual = command.fill_values(inputValues)
        expected = 'abc Mix ef [name {}] and {}'.format(
            MISSING_VALUE_TEMPLATE, MISSING_VALUE_TEMPLATE)
        self.assertEqual(expected, actual)

    def test_fill_multiple_missing_not_replaced(self):
        command = CommandFiller(
            'abc {/name/@text} {/namesurname/@text} ef {name-surname/@text} {/names/@text}')
        inputValues = dict(
            [('/namesurname/@text', 'mair'), ('/names/@text', 'theo')])
        actual = command.fill_values(inputValues)
        expected = 'abc {} mair ef {} theo'.format(
            MISSING_VALUE_TEMPLATE, MISSING_VALUE_TEMPLATE)
        self.assertEqual(expected, actual)

    def test_filled_optionals_fixed(self):
        command = CommandFiller('ef [name {/names/@text}] and [{/age/@text}]')
        inputValues = dict([('/names/@text', 'theo'), ('/age/@text', '20')])
        command.fill_command(inputValues)
        actual = command.command
        expected = 'ef name theo and 20'
        self.assertEqual(expected, actual)

    def test_filled_optionals_substitutes_keep_one(self):
        command = CommandFiller('ef [name {/names/@text}, age {/age/@text}]')
        inputValues = [('/names/@text', 'theo'), ('/age/@text', '20')]
        command.fill_command(dict(inputValues))
        actual = command.command
        expected = 'ef name theo'
        self.assertEqual(expected, actual)

        command = CommandFiller('ef [name {/names/@text}, age {/age/@text}]')
        inputValues.pop(0)
        command.fill_command(dict(inputValues))
        actual = command.command
        expected = 'ef age 20'
        self.assertEqual(expected, actual)

    def test_unfilled_optionals_removed(self):
        command = CommandFiller('ef [name {/names/@text},] and [{/age/@text}]')
        inputValues = dict([('/age/@text', '20')])
        command.fill_command(inputValues)
        actual = command.command
        expected = 'ef and 20'
        self.assertEqual(expected, actual)

    def test_unfilled_optionals_subs_removed(self):
        command = CommandFiller('ef [name {/names/@text}, age {/age/@text},]')
        inputValues = dict([])
        command.fill_command(inputValues)
        actual = command.command
        expected = 'ef '
        self.assertEqual(expected, actual)

    def test_unfilled_required_set_discard_command(self):
        command = CommandFiller('ef [name {/names/@text}, age {/age/@text}]')
        inputValues = dict([])
        command.fill_command(inputValues)
        actual = command.command
        expected = ''
        self.assertEqual(expected, actual)

    def test_unfilled_required_single_discard_command(self):
        command = CommandFiller('ef age {/age/@text}')
        inputValues = dict([])
        command.fill_command(inputValues)
        actual = command.command
        expected = ''
        self.assertEqual(expected, actual)

    def test_filled_required_set(self):
        command = CommandFiller('ef [name {/names/@text}, age {/age/@text}]')
        inputValues = dict([('/age/@text', '21')])
        command.fill_command(inputValues)
        actual = command.command
        expected = 'ef age 21'
        self.assertEqual(expected, actual)

    def test_conditional_with_references(self):
        command = CommandFiller(
            'ef $if|age {/age/@text},name {/name/@text}|md5==md{/ver/@text},$')
        inputValues = dict(
            [('/age/@text', 21), ('/name/@text', 'mm'), ('/ver/@text', 5)])
        actual = command.fill_command(inputValues)
        expected = 'ef age 21'
        self.assertEqual(expected, actual)

    def test_conditional_if_elseif_else(self):
        conditional = ['if', 'age 21,age 22,age 23', '1 == 1,1 == 2,']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'age 21'
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 21,age 22,age 23', '2 == 1,2 == 2,']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'age 22'
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 21,age 22,age 23', '2 == 1,1 == 2,']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'age 23'
        self.assertEqual(expected, actual)

    def test_conditional_equality(self):
        conditional = ['if', 'age 21,name mm', 'md5==md5,']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'age 21'
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 21,name mm', 'md5==md6,']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'name mm'
        self.assertEqual(expected, actual)

    def test_conditional_equality_backwards_compat(self):
        conditional = ['if', 'age 21,name mm', 'md5==md5']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'age 21'
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 21,name mm', 'md5==md6']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'name mm'
        self.assertEqual(expected, actual)

    def test_conditional_greater_or_equal(self):
        conditional = ['if', 'age 21', '2 >= 1']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'age 21'
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 22', '2 >= 2']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'age 22'
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 23', '2 >= 3']
        actual = CommandFiller.execute_conditional(conditional)
        expected = ''
        self.assertEqual(expected, actual)

    def test_conditional_less_or_equal(self):
        conditional = ['if', 'age 21', '1<= 2']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'age 21'
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 22', '2 <= 2']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'age 22'
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 23', '3 <=2']
        actual = CommandFiller.execute_conditional(conditional)
        expected = ''
        self.assertEqual(expected, actual)

    def test_conditional_greater_than(self):
        conditional = ['if', 'age 21', '2 > 1']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'age 21'
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 22', '2 > 2']
        actual = CommandFiller.execute_conditional(conditional)
        expected = ''
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 23', '2 > 3']
        actual = CommandFiller.execute_conditional(conditional)
        expected = ''
        self.assertEqual(expected, actual)

    def test_conditional_less_than(self):
        conditional = ['if', 'age 21', '1< 2']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'age 21'
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 22', '2 < 2']
        actual = CommandFiller.execute_conditional(conditional)
        expected = ''
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 23', '3 <2']
        actual = CommandFiller.execute_conditional(conditional)
        expected = ''
        self.assertEqual(expected, actual)

    def test_conditional_inequality(self):
        conditional = ['if', 'age 21,name mm', 'md5!=md5,']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'name mm'
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 21,name mm', 'md5!=md6,']
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'age 21'
        self.assertEqual(expected, actual)

    def test_conditional_key_in_dictionary(self):
        conditional = ['if', 'age 21,name mm',
                       "test in {'notest':2&'test':1},"]
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'age 21'
        self.assertEqual(expected, actual)

        conditional = ['if', 'age 21,name mm', "result in {'test':1},"]
        actual = CommandFiller.execute_conditional(conditional)
        expected = 'name mm'
        self.assertEqual(expected, actual)

    def test_None_value_parsed(self):
        command = CommandFiller('ef {/name/@text}')
        inputValues = dict([('/name/@text', None)])
        actual = command.fill_command(inputValues)
        expected = "ef None"
        self.assertEqual(expected, actual)

    def test_formatting_string(self):
        command = CommandFiller('ef {/name/@text!r:s>5}')
        inputValues = dict([('/name/@text', 'mm')])
        actual = command.fill_command(inputValues)
        expected = "ef s'mm'"
        self.assertEqual(expected, actual)

    def test_formatting_numbers(self):
        command = CommandFiller('ef {/name/@text:x}')
        inputValues = dict([('/name/@text', 10)])
        actual = command.fill_command(inputValues)
        expected = "ef a"
        self.assertEqual(expected, actual)

        command = CommandFiller('ef {/name/@text:+05}')
        actual = command.fill_command(inputValues)
        expected = "ef +0010"
        self.assertEqual(expected, actual)

    def test_formatting_loop(self):
        command = CommandFiller('ef {/name/@text:for:{{element}} }')
        inputValues = dict([('/name/@text', ['a', 'b', 'c'])])
        actual = command.fill_command(inputValues)
        expected = "ef a b c "
        self.assertEqual(expected, actual)


suite = unittest.TestLoader().loadTestsFromTestCase(CommandFillerTestCase)
unittest.TextTestRunner(verbosity=2).run(suite)
