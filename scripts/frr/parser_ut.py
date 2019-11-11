#!/usr/bin/env python3
# Copyright (c) 2018-2019 AT&T Intellectual Property. All rights reserved.
#
# SPDX-License-Identifier: GPL-2.0-only

from parser import VyattaJSONParser, TEXT_LEAF_LABEL, OrderedDict, DIR_TRAVERSE_UP_LABEL, DICT_ELEM_LABEL
import unittest


class ParserTestCase(unittest.TestCase):
    def test_find_parent_dict(self):
        l0 = {}
        l1 = {}
        l2 = {}
        l31 = [1, 2, 3]
        l32 = {'area': 0}
        l2['l'] = l31
        l2['area'] = l32
        l1['ospf'] = l2
        l0['protocols'] = l1
        v = VyattaJSONParser(l0, {})
        for node, path in v.depth_first_traverse(l0):
            if len(v.parent_stack) > 0:
                if isinstance(v.parent_stack[-1], list):
                    self.assertTrue(node in v.parent_stack[-1])
                else:
                    self.assertTrue(
                        node is v.parent_stack[-1][path.split('/')[-1]])

    def test_null_decode_as_None(self):
        v = VyattaJSONParser({}, {})
        node = '{"protocols": null}'
        actual = v.decode_vyatta_config(node)['protocols']
        expected = None
        self.assertEqual(actual, expected)

    def test_obj_decode_as_OrderedDict(self):
        v = VyattaJSONParser({}, {})
        node = '{"protocols": null}'
        actual = type(v.decode_vyatta_config(node))
        expected = type(OrderedDict())
        self.assertEqual(actual, expected)

    def test_retreive_multi_OrderedDict(self):
        v = VyattaJSONParser({}, {})
        node = OrderedDict(
            [('protocols', OrderedDict([('ospf', OrderedDict([('timers', 'timerVal')]))]))])
        steps = ['protocols', DICT_ELEM_LABEL]
        actual = v.retrieve_value(node, steps)
        print(actual)
        expected = "{'ospf':{'timers':'timerVal'}}"
        self.assertEqual(actual, expected)

    def test_retreive_multi_OrderedDict_from_list(self):
        v = VyattaJSONParser({}, {})
        node = OrderedDict(
            [('protocols', [OrderedDict([('ospf', OrderedDict([('timers', 'timerVal')]))])])])
        steps = ['protocols', DICT_ELEM_LABEL]
        actual = v.retrieve_value(node, steps)
        print(actual)
        expected = "[{'ospf':{'timers':'timerVal'}}]"
        self.assertEqual(actual, expected)

    def test_retrieve_value_traverse_down(self):
        v = VyattaJSONParser({}, {})
        node = {'protocols': {'ospf': {'timers': "timerVal"}}}
        steps = ['protocols', 'ospf', 'timers', TEXT_LEAF_LABEL]
        actual = v.retrieve_value(node, steps)
        expected = "timerVal"
        self.assertEqual(actual, expected)

    def test_retrieve_value_traverse_up_simple(self):
        v = VyattaJSONParser({}, {})
        l3 = {'timers': "timerVal"}
        l2 = {'ospf': l3}
        node = {'protocols': l2, 'key': 'value'}
        v.parent_stack = [node, l2]
        steps = [DIR_TRAVERSE_UP_LABEL,
                 DIR_TRAVERSE_UP_LABEL, 'key', TEXT_LEAF_LABEL]
        actual = v.retrieve_value(l3, steps)
        expected = "value"
        self.assertEqual(actual, expected)

    def test_retrieve_value_traverse_up_mixed(self):
        v = VyattaJSONParser({}, {})
        l4 = {'timers': "timerVal"}
        l3 = [l4]
        l2 = {'ospf': l3}
        l1 = [l2]
        node = {'protocols': l1, 'key': 'value'}
        v.parent_stack = [node, l1, l2, l3]
        steps = [DIR_TRAVERSE_UP_LABEL, DIR_TRAVERSE_UP_LABEL, DIR_TRAVERSE_UP_LABEL,
                 DIR_TRAVERSE_UP_LABEL, 'key', TEXT_LEAF_LABEL]
        actual = v.retrieve_value(l4, steps)
        expected = "value"
        self.assertEqual(actual, expected)

    def test_retrieve_command_as_list(self):
        template = "{/timers/@text} {/@text}"
        path = '/protocols/ospf/freq'
        syntax = {path: template}
        v = VyattaJSONParser({}, syntax)
        actual = list(v.retrieve_commands(path))
        expected = [template]
        self.assertEqual(actual, expected)

    def test_retrieve_command_escape_dots(self):
        template = "{/../timers/@text}"
        path = '/protocols/ospf/freq'
        syntax = {path: template}
        v = VyattaJSONParser({}, syntax)
        actual = list(v.retrieve_commands(path))
        expected = ["{{/{}/timers/@text}}".format(DIR_TRAVERSE_UP_LABEL)]
        self.assertEqual(actual, expected)

    def test_traversal_up_primitive_same_value_children(self):
        l1 = {'keyN': "21", 'ospf': {'timers': "timerVal", "freq": "21"}}
        node = {'keyN': "21", 'protocols': l1, }
        syntax = {'/protocols/ospf/freq': "{/../timers/@text} {/@text}"}
        expected = ['timerVal 21']
        v = VyattaJSONParser(node, syntax)
        actual = v.parse_config()
        self.assertEqual(actual, expected)

    def test_traversal(self):
        l1 = [{'ospf': [{'timers': "timerVal", "freq": "21"}], 'keyl2': 'vall21'},
              {'keyl2': 'vall22'}]
        node = {'protocols': l1, 'key': 'value'}
        syntax = {
            '/protocols': "constant command",
            '/protocols/@element/ospf/@element':
            "timers {/timers/@text} [optional {/../../keyl2/@text},]",
            '/protocols/@element/ospf/@element/timers':
            "{/../../../../../key/@text} [nonexistant optional {/../../../../../abc/@text},]",
            '/protocols/@element/ospf/@element/freq': "{/../timers/@text} {/@text}",
            '/protocols/@element/keyl2': "Level 2 {/@text}"
        }
        expected = ['constant command', 'timers timerVal optional vall21', 'value ',
                    'timerVal 21', 'Level 2 vall21', 'Level 2 vall22']
        v = VyattaJSONParser(node, syntax)
        actual = v.parse_config()
        self.assertEqual(actual, expected)

    def test_enter_exit_commands(self):
        node = {'protocols': [{'ospf': [1, 2, 3]}], 'key': 'value'}
        syntax = {
            '/protocols/@enter': "in",
            '/protocols/@element/ospf/@element': "{/@text}",
            '/protocols/@element/ospf/@element/@enter': "i",
            '/protocols/@element/ospf/@element/@exit': "o",
            '/protocols/@exit': "out",
        }
        expected = ['in', 'i', '1', 'o', 'i', '2', 'o', 'i', '3', 'o', 'out']
        v = VyattaJSONParser(node, syntax)
        actual = v.parse_config()
        self.assertEqual(actual, expected)

    def test_priority_sorting(self):
        node = OrderedDict({'ospf': OrderedDict(
            {'timers': "timerVal", "freq": "21"})})
        syntax = {'/ospf/freq': "{/@text}", '/ospf/timers': "{/@text}"}
        first = []
        # test timers moved at the end
        last = ['timers']
        priorities = {'/ospf': {"first": first, "last": last}}
        expected = ['21', 'timerVal']
        v = VyattaJSONParser(node, syntax)
        v.sort_tree(priorities)
        actual = v.parse_config()
        self.assertEqual(actual, expected)
        # test timers moved at the front
        expected = ['timerVal', '21']
        first.append(last.pop())
        v.sort_tree(priorities)
        actual = v.parse_config()
        self.assertEqual(actual, expected)

    def test_priority_sorting_multiple_nonexisting(self):
        node = OrderedDict(
            {'key1': "1", 'key2': '2', 'key3': '3', 'key4': '4'})
        syntax = {'/key1': "{/@text}", '/key2': "{/@text}", '/key3': "{/@text}",
                  '/key4': "{/@text}"}
        first = ['key1', 'key2', 'keyN']
        last = ['key3', 'key4']
        priorities = {'/': {"first": first, "last": last}}
        v = VyattaJSONParser(node, syntax)
        v.sort_tree(priorities)
        expected = ['1', '2', '3', '4']
        actual = v.parse_config()
        self.assertEqual(actual, expected)
        # test timers moved at the front
        first.clear()
        last.clear()
        first.extend(['key4', 'key1', 'keyZ'])
        last.extend(['key3', 'key2'])
        v.sort_tree(priorities)
        expected = ['4', '1', '3', '2']
        actual = v.parse_config()
        self.assertEqual(actual, expected)

    def test_multiple_commands(self):
        l1 = [{'ospf': [{'timers': "timerVal", "freq": "21"}], 'keyl2': 'vall21'},
              {'keyl2': 'vall22'}]
        node = {'protocols': l1, 'key': 'value'}
        syntax = {
            '/protocols': ["constant command1", "constant command2"],
            '/protocols/@element/ospf/@element':
            ["Level 2 {/../../keyl2/@text}",
             "timers {/timers/@text} [optional {/../../keyl2/@text},]"],
            '/protocols/@element/ospf/@element/timers':
            ["{/../../../../../key/@text} [nonexistant optional {/../../../../../abc/@text},]",
             "{@text} {/../freq/@text}"]
        }
        expected = ["constant command1", "constant command2", 'Level 2 vall21',
                    'timers timerVal optional vall21', 'value ', 'timerVal 21']
        v = VyattaJSONParser(node, syntax)
        actual = v.parse_config()
        self.assertEqual(actual, expected)


suite = unittest.TestLoader().loadTestsFromTestCase(ParserTestCase)
unittest.TextTestRunner(verbosity=2).run(suite)
