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
import lte.epc.PgwStandard;
import lte.epc.SgwStandard;
import lte.world.radio.LteChannelControl;


network lteCoreNetwork
{
    @display("bgb=1291.17,610.84503");
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
            @display("p=50,25;is=s");
        }
        configurator: IPv4NetworkConfigurator {
            @display("p=95,42");
            config = xmldoc("lteCoreConfigFiles/lteIpAddresses.xml");
        }
        pgwStandard: PgwStandard {
            nodeType = "PGW";
            @display("p=874.29004,243.18001");
        }
        eNB3: PgwStandard {
            nodeType = "ENODEB";
            @display("p=288.05252,186.72751");
        }
        eNB1: PgwStandard {
            nodeType = "ENODEB";
            @display("p=408.195,41.9775");
        }
        eNB2: PgwStandard {
            nodeType = "ENODEB";
            @display("p=315.55502,112.90501");
        }
        eNB4: PgwStandard {
            nodeType = "ENODEB";
            @display("p=353.19,248.97");
        }
        eNB5: PgwStandard {
            nodeType = "ENODEB";
            @display("p=380.6925,353.19");
        }
        eNB6: PgwStandard {
            nodeType = "ENODEB";
            @display("p=315.55502,425.565");
        }
        eNB7: PgwStandard {
            nodeType = "ENODEB";
            @display("p=353.19,512.41504");
        }
        eNB8: PgwStandard {
            nodeType = "ENODEB";
            @display("p=408.195,558.73505");
        }
        sgwStandard2: SgwStandard {
            @display("p=684.66754,461.7525");
        }
        sgwStandard1: SgwStandard {
            @display("p=684.66754,112.90501");
        }
        router: Router {
            @display("p=684.66754,243.18001");
        }
        router1: Router {
            @display("p=490.7025,112.90501");
        }
        router2: Router {
            @display("p=479.12253,461.7525");
        }
        router3: Router {
            parameters:
                numExtInterfaces = 1;
                @display("p=1056.675,243.18001");
        }
        InternetHost: StandardHost {
            @display("p=1224.5851,243.18001");
        }
        UE1: StandardHost {
            @display("p=259.1025,39.0825;i=device/cellphone");
        }
        UE2: StandardHost {
            @display("p=208.44,112.90501;i=device/cellphone");
        }
        UE3: StandardHost {
            @display("p=130.27501,186.72751;i=device/cellphone");
        }
        UE4: StandardHost {
            @display("p=208.44,248.97;i=device/cellphone");
        }
        UE5: StandardHost {
            @display("p=130.27501,353.19;i=device/cellphone");
        }
        UE6: StandardHost {
            @display("p=189.62251,425.565;i=device/cellphone");
        }
        UE7: StandardHost {
            @display("p=159.225,512.41504;i=device/cellphone");
        }
        UE8: StandardHost {
            @display("p=208.44,558.73505;i=device/cellphone");
        }

    connections:
        pgwStandard.pppg++ <--> networkConnection <--> router.pppg++;
        pgwStandard.filterGate <--> networkConnection <--> router3.pppg++;

        router.pppg++ <--> networkConnection <--> sgwStandard2.pppg++;
        router2.pppg++ <--> networkConnection <--> sgwStandard2.pppg++;

        router.pppg++ <--> networkConnection <--> sgwStandard1.pppg++;
        router1.pppg++ <--> networkConnection <--> sgwStandard1.pppg++;

        router2.pppg++ <--> networkConnection <--> eNB8.pppg++;
        router2.pppg++ <--> networkConnection <--> eNB7.pppg++;
        router2.pppg++ <--> networkConnection <--> eNB6.pppg++;
        router2.pppg++ <--> networkConnection <--> eNB5.pppg++;
        router1.pppg++ <--> networkConnection <--> eNB4.pppg++;
        router1.pppg++ <--> networkConnection <--> eNB3.pppg++;
        router1.pppg++ <--> networkConnection <--> eNB2.pppg++;
        router1.pppg++ <--> networkConnection <--> eNB1.pppg++;

        InternetHost.ethg++ <--> networkConnection <--> router3.ethg++;

        UE8.pppg++ <--> ueConnection <--> eNB8.filterGate;
        UE7.pppg++ <--> ueConnection <--> eNB7.filterGate;
        UE6.pppg++ <--> ueConnection <--> eNB6.filterGate;
        UE5.pppg++ <--> ueConnection <--> eNB5.filterGate;
        UE4.pppg++ <--> ueConnection <--> eNB4.filterGate;
        UE3.pppg++ <--> ueConnection <--> eNB3.filterGate;
        UE2.pppg++ <--> ueConnection <--> eNB2.filterGate;
        UE1.pppg++ <--> ueConnection <--> eNB1.filterGate;
}
