#!/usr/bin/perl
#
# Copyright (c) 2018-2019 AT&T Intellectual Property
# Copyright (c) 2013-2017 Brocade Communications Systems, Inc.
# Copyright (c) 2007-2010 Vyatta, Inc.
#
# SPDX-License-Identifier: GPL-2.0-only

use strict;
use warnings;

($ARGV[0] eq 'show' ) or die "must be a show command\n";

my $p = join(' ', @ARGV);

# Translate between the DANOS CLI and the FRR CLI.
$p =~ s/ospf routing-instance .* process/ospf/g;
$p =~ s/ospf process/ospf/g;
$p =~ s/ospfv3/ospf6/g; 
$p =~ s/routing-instance/vrf/g;
$p =~ s/vrf (\S+)/vrf vrf${1}/g;
$p =~ s/vpnv4 unicast/vpnv4/g;
$p =~ s/(ip|ipv6) route( vrf \S+|)? database/${1} route${2}/g;
$p =~ s/ any/ */g;

exec '/usr/bin/vtysh', '-c', $p;
die "Could not exec vtysh";
