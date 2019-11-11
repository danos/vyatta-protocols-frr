// Copyright (c) 2018-2019, AT&T Intellectual Property.
// All rights reserved.
//
// SPDX-License-Identifier: GPL-2.0-only

package main

import (
	"encoding/json"
	"eng.vyatta.net/protocols"
	"eng.vyatta.net/protocols/static"
	"errors"
	log "github.com/Sirupsen/logrus"
	"os/exec"
)

const (
	cfgFileName   = "frr.json"
	componentName = "net.vyatta.vci.frr"
	v1Component   = componentName + ".v1"
)

func Set(pmc *protocols.ProtocolsModelComponent, cfg []byte) error {
	var frontend_interface, old_frontend_interface interface{}

	old_cfg := pmc.Get()
	old_conv_cfg, err := protocols.ConvertConfigToInternalJson(old_cfg)
	if err != nil {
		log.Errorln("Failed to convert old config from RFC 7951 JSON: " + err.Error())
		return err
	}
	json.Unmarshal(old_conv_cfg, &old_frontend_interface)
	old_frontend_map := old_frontend_interface.(map[string]interface{})

	json.Unmarshal(cfg, &frontend_interface)
	frontend_map := frontend_interface.(map[string]interface{})

	//Strip out disabled nexthops and other translations
	static.Translate(frontend_map, old_frontend_map)

	//Enable MPLS in kernel if required
	Mpls(frontend_map)

	//Write new config file
	jsonString, _ := json.MarshalIndent(frontend_map, "", "    ")
	err = pmc.WriteJsonFile(jsonString, pmc.GetDaemonConfigFilePath())
	if err != nil {
		log.Errorln(err)
		return err
	}

	err = exec.Command("/opt/vyatta/sbin/parser.py").Run()
	if err != nil {
		msg := "Failed to run FRR translation: " + err.Error()
		log.Errorln(msg)
		return errors.New(msg)
	}

	log.Infoln("FRR translation successful")
	return nil
}

func main() {
	pmc := protocols.NewProtocolsModelComponent(v1Component, cfgFileName)
	pmc.SetSetFunction(Set)
	pmc.Run(componentName)
}
