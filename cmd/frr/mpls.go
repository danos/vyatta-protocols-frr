// Copyright (c) 2018-2019, AT&T Intellectual Property.
// All rights reserved.
//
// SPDX-License-Identifier: GPL-2.0-only

package main

import (
	"errors"
	"fmt"
	"os"
)

func Mpls(frontend_map map[string]interface{}) error {
	if frontend_map == nil || frontend_map["protocols"] == nil {
		return nil
	}

	proto_map := frontend_map["protocols"].(map[string]interface{})
	if proto_map == nil || proto_map["mpls-ldp"] == nil {
		return nil
	}

	ldp_map := proto_map["mpls-ldp"].(map[string]interface{})
	if ldp_map == nil || ldp_map["address-family"] == nil {
		return nil
	}

	af_map := ldp_map["address-family"].(map[string]interface{})
	if af_map == nil || af_map["ipv4"] == nil {
		return nil
	}

	v4_map := af_map["ipv4"].(map[string]interface{})
	if v4_map == nil || v4_map["discovery"] == nil {
		return nil
	}

	disc_map := v4_map["discovery"].(map[string]interface{})
	if disc_map == nil || disc_map["interfaces"] == nil {
		return nil
	}

	intf_map := disc_map["interfaces"].(map[string]interface{})
	if intf_map == nil || intf_map["interface"] == nil {
		return nil
	}

	intf_arr := intf_map["interface"].([]interface{})
	if intf_arr == nil {
		return nil
	}

	//Set up kernel label table
	f, err := os.OpenFile("/proc/sys/net/mpls/platform_labels",
		os.O_WRONLY, 0)
	if err != nil {
		msg := "Failed to open platform labels: " + err.Error()
		fmt.Println(msg)
		return errors.New(msg)
	}
	_, err = f.Write([]byte("1048575\n"))
	f.Close()
	if err != nil {
		msg := "Failed to write platform labels: " + err.Error()
		fmt.Println(msg)
		return errors.New(msg)
	}

	for _, intf_entry := range intf_arr {
		intf_entry_map := intf_entry.(map[string]interface{})
		if intf_entry_map["interface"] == nil {
			continue
		}

		intf_name := intf_entry_map["interface"].(string)

		//Enable MPLS forwarding on the interface
		f, err = os.OpenFile("/proc/sys/net/mpls/conf/"+intf_name+
			"/input", os.O_WRONLY, 0)
		if err != nil {
			msg := "Failed to open MPLS conf for " +
				intf_name + ": " + err.Error()
			fmt.Println(msg)
			return errors.New(msg)
		}
		_, err = f.Write([]byte("1\n"))
		f.Close()
		if err != nil {
			msg := "Failed to write MPLS conf for " +
				intf_name + ": " + err.Error()
			fmt.Println(msg)
			return errors.New(msg)
		}
	}

	return nil
}
