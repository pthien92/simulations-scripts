//
//                           SimuLTE
//
// This file is part of a software released under the license included in file
// "license.pdf". This license can be also found at http://www.ltesimulator.com/
// The above file and the present reference are part of the software itself,
// and cannot be removed from it.
//

package d2dtest;

import inet.networklayer.configurator.ipv4.IPv4NetworkConfigurator;
import inet.node.inet.Router;
import inet.node.inet.StandardHost;
import inet.common.misc.ThruputMeteringChannel;
import d2dtest.PgwStandardMultipleFilter;
import d2dtest.SgwStandardMultipleGtpUsers;
import lte.epc.PgwStandard;
import lte.epc.SgwStandard;
import lte.world.radio.LteChannelControl;


network lteCoreNetwork4UesPerEnB
{
    @display("bgb=1421.4451,738.22504");
    types:
        channel networkConnection extends ThruputMeteringChannel
        {
            delay = 0.1us;
            datarate = 100Mbps;
            thruputDisplayFormat = "u";
        }

        channel ueConnection extends ThruputMeteringChannel
        {
            delay = 100ms;
            datarate = 20Mbps;
            thruputDisplayFormat = "u";
        }

    submodules:
        channelControl: LteChannelControl {
            @display("p=82.5075,24.6075;is=s");
        }
        configurator: IPv4NetworkConfigurator {
            @display("p=225.81001,24.6075");
            config = xmldoc("lteCoreConfigFiles/lteIpAddresses.xml");
        }
        pgwStandard: PgwStandard {
            nodeType = "PGW";
            @display("p=926.4,369.11252");
        }
        eNB1: PgwStandardMultipleFilter {
            nodeType = "ENODEB";
            numFilterGates = 4;
            @display("p=305.42252,243.18001");
            gates:
                filterGates[4];
        }
        eNB2: PgwStandardMultipleFilter {
            numFilterGates = 4;
            nodeType = "ENODEB";
            @display("p=305.42252,495.045");
        }
        sgwStandard2: SgwStandard {
            @display("p=736.7775,495.045");
        }
        sgwStandard1: SgwStandard {
//            numGtpUsers = 5;
            @display("p=736.7775,238.83751");
        }
        router: Router {
            @display("p=736.7775,369.11252");
        }
        router1: Router {
            @display("p=561.63,238.83751");
        }
        router2: Router {
            @display("p=561.63,495.045");
        }
        router3: Router {
            parameters:
                numExtInterfaces = 1;
                @display("p=1108.785,369.11252");
        }
        InternetHost: StandardHost {
            @display("p=1276.6951,369.11252");
        }
        UE1: StandardHost {
            @display("p=140.4075,123.037506;i=device/cellphone");
        }
        UE2: StandardHost {
            @display("p=92.64,162.12001;i=device/cellphone");
        }
        UE3: StandardHost {
            @display("p=94.0875,243.18001;i=device/cellphone");
        }
        UE4: StandardHost {
            @display("p=130.27501,318.45;i=device/cellphone");
        }
        UE5: StandardHost {
            @display("p=140.4075,419.77502;i=device/cellphone");
        }
        UE6: StandardHost {
            @display("p=130.27501,509.52002;i=device/cellphone");
        }
        UE7: StandardHost {
            @display("p=159.225,565.97253;i=device/cellphone");
        }
        UE8: StandardHost {
            @display("p=224.3625,594.92255;i=device/cellphone");
        }
    connections:
        pgwStandard.pppg++ <--> networkConnection <--> router.pppg++;
	    pgwStandard.filterGate <--> networkConnection <--> router3.pppg++;

        router.pppg++ <--> networkConnection <--> sgwStandard2.pppg++;
        router2.pppg++ <--> networkConnection <--> sgwStandard2.pppg++;

        router.pppg++ <--> networkConnection <--> sgwStandard1.pppg++;
        router1.pppg++ <--> networkConnection <--> sgwStandard1.pppg++;

        router2.pppg++ <--> networkConnection <--> eNB2.pppg++;
        router1.pppg++ <--> networkConnection <--> eNB1.pppg++;

        InternetHost.ethg++ <--> networkConnection <--> router3.ethg++;

        UE5.pppg++ <--> ueConnection <--> eNB2.filterGates++;
        UE6.pppg++ <--> ueConnection <--> eNB2.filterGates++;
        UE7.pppg++ <--> ueConnection <--> eNB2.filterGates++;
        UE8.pppg++ <--> ueConnection <--> eNB2.filterGates++;
        UE1.pppg++ <--> ueConnection <--> eNB1.filterGates++;
        UE2.pppg++ <--> ueConnection <--> eNB1.filterGates++;
        UE3.pppg++ <--> ueConnection <--> eNB1.filterGates++;
        UE4.pppg++ <--> ueConnection <--> eNB1.filterGates++;
}
