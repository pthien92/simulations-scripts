//
//                           SimuLTE
//
// This file is part of a software released under the license included in file
// "license.pdf". This license can be also found at http://www.ltesimulator.com/
// The above file and the present reference are part of the software itself,
// and cannot be removed from it.
//
package d2dtest;

import lte.epc.gtp.GtpUser;
import lte.epc.gtp.GtpUserSimplified;
import inet.linklayer.ppp.PPPInterface;
import inet.node.inet.NodeBase;
import lte.epc.TrafficFlowFilter;
import inet.transportlayer.udp.UDP;

//
// Implements an EPC PDN Gateway (P-GW)
//
module PgwStandardMultipleFilter extends NodeBase
{
    parameters:
        string nodeType; // must be one between ENB and PGW
        int numFilterGates = default(1);
        @display("bgb=920,462;i=device/mainframe");
    gates:
        inout filterGates[] @labels(PPPFrame-conn);

    submodules:
        trafficFlowFilter[numFilterGates]: TrafficFlowFilter {
            ownerType = nodeType;
            @display("p=813,206");
        }
        pppInterface[numFilterGates]: PPPInterface {
            @display("p=727,386");
        }
        udp: UDP {
            @display("p=329,206");
        }
        gtp_user[numFilterGates]: GtpUser {
            @display("p=591,206");
        }

    connections:
        udp.ipOut --> networkLayer.transportIn++;
        udp.ipIn <-- networkLayer.transportOut++;

        for i = 0 .. numFilterGates-1 {
        	pppInterface[i].upperLayerOut --> trafficFlowFilter[i].internetFilterGateIn;
        	pppInterface[i].upperLayerIn <-- gtp_user[i].pppGate;
        	pppInterface[i].phys <--> filterGates[i];
	        udp.appOut++ --> gtp_user[i].udpIn;
        	gtp_user[i].udpOut --> udp.appIn++;
        	trafficFlowFilter[i].gtpUserGateOut --> gtp_user[i].trafficFlowFilterGate;
        }
}

//
// Implements a simplified version of the EPC PDN Gateway (P-GW)
//
