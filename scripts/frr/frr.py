#!/usr/bin/env python3
# Copyright (c) 2017-2019 AT&T Intellectual Property. All rights reserved.
#
# SPDX-License-Identifier: GPL-2.0-only

import json
import os

input_file = "/etc/vyatta-routing/frr.json"
output_file = "/etc/vyatta-routing/frr.conf"


def iterate_routes(route_arr, write_file, prefix):
    for route in route_arr:
        if 'next-hop' in route:
            for nexthop in route['next-hop']:
                write_file.write(
                    prefix + ' route ' + route['tagnode'] + " " + nexthop['tagnode'] + " " + str(nexthop['distance']) + "\n")
        elif 'blackhole' in route:
            nexthop = route['blackhole']
            write_file.write(
                prefix + ' route ' + route['tagnode'] + " blackhole " + str(nexthop['distance']) + "\n")
        elif 'unreachable' in route:
            nexthop = route['unreachable']
            write_file.write(
                prefix + ' route ' + route['tagnode'] + " " + "reject " + str(nexthop['distance']) + "\n")
        elif 'next-hop-interface' in route:
            for nexthop in route['next-hop-interface']:
                write_file.write(
                    prefix + ' route ' + route['tagnode'] + " " + nexthop['tagnode'] + " " + str(nexthop['distance']) + "\n")


if __name__ == "__main__":
    with open(input_file, "r") as read_file:
        with open(output_file, "w") as write_file:
            data = json.load(read_file)
            # avoid empty file
            write_file.write("!\n")
            if 'protocols' in data:
                protocols = data['protocols']
                if 'static' in protocols:
                    static = protocols['static']
                    if 'route' in static:
                        route_arr = static['route']
                        iterate_routes(route_arr, write_file, "ip")
                    if 'interface-route' in static:
                        int_route_arr = static['interface-route']
                        iterate_routes(int_route_arr, write_file, "ip")
                    if 'route6' in static:
                        route_arr = static['route6']
                        iterate_routes(route_arr, write_file, "ipv6")
                    if 'interface-route6' in static:
                        int_route_arr = static['interface-route6']
                        iterate_routes(int_route_arr, write_file, "ipv6")
    os.system("/opt/vyatta/bin/frr-reload.py --reload /etc/vyatta-routing/frr.conf")
