/* -*-  Mode: C++; c-file-style: "gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2016 University of Campinas (Unicamp)
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as * published by the Free Software Foundation; *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 * Author:  Luciano Chaves <luciano@lrc.ic.unicamp.br>
 *
 * - This is the internal network of an organization.
 * - 2 servers and N client nodes are located far from each other.
 * - Between border and aggregation switches there are two narrowband links of
 *   10 Mbps each. Other local connections have links of 100 Mbps.
 * - The default learning application manages the client switch.
 * - An specialized OpenFlow QoS controller is used to manage the border and
 *   aggregation switches, balancing traffic among internal servers and
 *   aggregating narrowband links to increase throughput.
 *
 *                          QoS controller       Learning controller
 *                                |                       |
 *   10.1.1.x              +--------------+               |
 *  +----------+           |              |               |           +----------+
 *  | Server 0 | ==== +--------+      +--------+      +--------+ ==== | Client 0 |
 *  +----------+      | Border | ~~~~ | Aggreg |      | Client |      +----------+ 10.1.2.x
 *  +----------+      | Switch | ~~~~ | Switch | ==== | Switch |      +----------+
 *  | Server 1 | ==== +--------+      +--------+      +--------+ ==== | Client N |
 *  +----------+                 2x10            100        ||        +----------+
 *                               Mbps            Mbps       || 
 *                                                          ||
 *                                                    ##############                              ###########         +----------+
 *                                                      TAP DEVICE                                  TAP DEV   ------  | LTE CORE |
 *                                                       0.0.0.0                                   0.0.0.0            |   PGW    |
 *                                                    ##############                              ###########         +----------+
 *                                                           |----------------| Bridge |---------------|
 *                                                                             Linux Host
 *                                                                
 * */


#include <ns3/core-module.h>
#include <ns3/network-module.h>
#include <ns3/csma-module.h>
#include <ns3/internet-module.h>
#include <ns3/applications-module.h>
#include <ns3/ofswitch13-module.h>
#include <ns3/netanim-module.h>
#include <ns3/mobility-module.h>
#include "qos-controller.h"
#include "learning-controller.h"
#include <ns3/tap-bridge-module.h>
#include <ns3/internet-apps-module.h>

using namespace ns3;

int
main (int argc, char *argv[])
{
  std::string mode    = "UseLocal";
  std::string tapName = "thetap";
  uint16_t clients = 2;
  uint16_t simTime = 20;
  bool verbose = false;
  bool trace = true;


  // Configure command line parameters
  CommandLine cmd;
  cmd.AddValue ("clients", "Number of client nodes", clients);
  cmd.AddValue ("simTime", "Simulation time (seconds)", simTime);
  cmd.AddValue ("tapDevice", "The binding external Tap or Veth Device [pgwtap]", tapName);
  cmd.AddValue ("verbose", "Enable verbose output", verbose);
  cmd.AddValue ("trace", "Enable datapath stats and pcap traces", trace);
  cmd.Parse (argc, argv);

  if (verbose)
    {
      OFSwitch13Helper::EnableDatapathLogs ();
      LogComponentEnable ("OFSwitch13Device", LOG_LEVEL_ALL);
      LogComponentEnable ("OFSwitch13Port", LOG_LEVEL_ALL);
      LogComponentEnable ("OFSwitch13Queue", LOG_LEVEL_ALL);
      LogComponentEnable ("OFSwitch13SocketHandler", LOG_LEVEL_ALL);
      LogComponentEnable ("OFSwitch13Controller", LOG_LEVEL_ALL);
      LogComponentEnable ("LearningController", LOG_LEVEL_ALL);
      LogComponentEnable ("OFSwitch13Helper", LOG_LEVEL_ALL);
      LogComponentEnable ("OFSwitch13InternalHelper", LOG_LEVEL_ALL);
      LogComponentEnable ("QosController", LOG_LEVEL_ALL);
    }


  // Configure dedicated connections between controller and switches
  Config::SetDefault ("ns3::OFSwitch13Helper::ChannelType", EnumValue (OFSwitch13Helper::DEDICATEDCSMA));

  // Increase TCP MSS for larger packets
  Config::SetDefault ("ns3::TcpSocket::SegmentSize", UintegerValue (1400));

  // Enable checksum computations (required by OFSwitch13 module)
  GlobalValue::Bind ("ChecksumEnabled", BooleanValue (true));

  // Discard the first MAC address ("00:00:00:00:00:01") which will be used by
  // the border switch in association with the first IP address ("10.1.1.1")
  // for the Internet service.
  Mac48Address::Allocate ();

  // Create nodes for servers, switches, controllers and clients
  NodeContainer serverNodes, switchNodes, controllerNodes, clientNodes, backboneNode;
  serverNodes.Create (2);
  switchNodes.Create (3);
  controllerNodes.Create (2);
  clientNodes.Create (clients);
  backboneNode.Create(1);

  // Setting node positions for NetAnim support
  Ptr<ListPositionAllocator> listPosAllocator;
  listPosAllocator = CreateObject<ListPositionAllocator> ();
  listPosAllocator->Add (Vector (  0,  0, 0));  // Server 0
  listPosAllocator->Add (Vector (  0, 75, 0));  // Server 1
  listPosAllocator->Add (Vector ( 50, 50, 0));  // Border switch
  listPosAllocator->Add (Vector (100, 50, 0));  // Aggregation switch
  listPosAllocator->Add (Vector (150, 50, 0));  // Client switch
  listPosAllocator->Add (Vector ( 75, 25, 0));  // QoS controller
  listPosAllocator->Add (Vector (150, 25, 0));  // Learning controller
  for (size_t i = 0; i < clients; i++)
    {
      listPosAllocator->Add (Vector (200, 25 * i, 0)); // Clients
    }

  MobilityHelper mobilityHelper;
  mobilityHelper.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  mobilityHelper.SetPositionAllocator (listPosAllocator);
  mobilityHelper.Install (NodeContainer (serverNodes, switchNodes, controllerNodes, clientNodes));

  // Create device containers
  NetDeviceContainer serverDevices, clientDevices, backboneDevice;
  NetDeviceContainer switch0Ports, switch1Ports, switch2Ports;
  NetDeviceContainer link;
  Ipv4InterfaceContainer backboneInterface;

  // Create two 10Mbps connections between border and aggregation switches
  CsmaHelper csmaHelper;
  csmaHelper.SetChannelAttribute ("DataRate", DataRateValue (DataRate ("10Mbps")));

  link = csmaHelper.Install (NodeContainer (switchNodes.Get (0), switchNodes.Get (1)));
  switch0Ports.Add (link.Get (0));
  switch1Ports.Add (link.Get (1));

  link = csmaHelper.Install (NodeContainer (switchNodes.Get (0), switchNodes.Get (1)));
  switch0Ports.Add (link.Get (0));
  switch1Ports.Add (link.Get (1));

  // Configure the CsmaHelper for 100Mbps connections
  csmaHelper.SetChannelAttribute ("DataRate", DataRateValue (DataRate ("100Mbps")));

  // Connect aggregation switch to client switch
  link = csmaHelper.Install (NodeContainer (switchNodes.Get (1), switchNodes.Get (2)));
  switch1Ports.Add (link.Get (0));
  switch2Ports.Add (link.Get (1));

  // Connect servers to border switch
  link = csmaHelper.Install (NodeContainer (serverNodes.Get (0), switchNodes.Get (0)));
  serverDevices.Add (link.Get (0));
  switch0Ports.Add (link.Get (1));

  link = csmaHelper.Install (NodeContainer (serverNodes.Get (1), switchNodes.Get (0)));
  serverDevices.Add (link.Get (0));
  switch0Ports.Add (link.Get (1));

  // Connect client nodes to client switch
  for (size_t i = 0; i < clients; i++)
    {
      link = csmaHelper.Install (NodeContainer (clientNodes.Get (i), switchNodes.Get (2)));
      clientDevices.Add (link.Get (0));
      switch2Ports.Add (link.Get (1));
    }
  
  // Connect backbone nodes to client switch
  link = csmaHelper.Install (NodeContainer(backboneNode.Get(0), switchNodes.Get(2)));
  backboneDevice.Add(link.Get (0));
  switch2Ports.Add(link.Get (1));

  // Configure OpenFlow QoS controller for border and aggregation switches
  // (#0 and #1) into controller node 0.
  Ptr<OFSwitch13InternalHelper> ofQosHelper =
    CreateObject<OFSwitch13InternalHelper> ();
  Ptr<QosController> qosCtrl = CreateObject<QosController> ();
  ofQosHelper->InstallController (controllerNodes.Get (0), qosCtrl);

  // Configure OpenFlow learning controller for client switch (#2) into controller node 1
  Ptr<OFSwitch13InternalHelper> ofLearningHelper = CreateObject<OFSwitch13InternalHelper> ();
  Ptr<LearningController> learnCtrl = CreateObject<LearningController> ();
  ofLearningHelper->InstallController (controllerNodes.Get (1), learnCtrl);

  // Install OpenFlow switches 0 and 1 with border controller
  OFSwitch13DeviceContainer ofSwitchDevices;
  ofSwitchDevices.Add (ofQosHelper->InstallSwitch (switchNodes.Get (0), switch0Ports));
  ofSwitchDevices.Add (ofQosHelper->InstallSwitch (switchNodes.Get (1), switch1Ports));
  ofQosHelper->CreateOpenFlowChannels ();

  // Install OpenFlow switches 2 with learning controller
  ofSwitchDevices.Add (ofLearningHelper->InstallSwitch (switchNodes.Get (2), switch2Ports));
  ofLearningHelper->CreateOpenFlowChannels ();

  // Install the TCP/IP stack into hosts nodes
  InternetStackHelper internet;
  internet.Install (serverNodes);
  internet.Install (clientNodes);
  internet.Install (backboneNode);

  // Set IPv4 server and client addresses (discarding the first server address)
  Ipv4AddressHelper ipv4switches;
  Ipv4InterfaceContainer internetIpIfaces;
  ipv4switches.SetBase ("10.1.0.0", "255.255.0.0", "0.0.2.2");
  internetIpIfaces = ipv4switches.Assign (serverDevices);
  ipv4switches.SetBase ("10.1.0.0", "255.255.0.0", "0.0.3.1");
  internetIpIfaces = ipv4switches.Assign (clientDevices);
  ipv4switches.SetBase ("10.1.0.0", "255.255.0.0", "0.0.4.1");
  internetIpIfaces = ipv4switches.Assign (backboneDevice);

  TapBridgeHelper tapBridge;
  tapBridge.SetAttribute ("Mode", StringValue(mode));
  tapBridge.SetAttribute ("DeviceName", StringValue(tapName));
  tapBridge.Install (backboneNode.Get(0), backboneDevice.Get(0));


  // Ipv4StaticRoutingHelper ipv4RoutingHelper;
  // Ptr<Ipv4StaticRouting> interceptStaticRouting = ipv4RoutingHelper.GetStaticRouting ((backboneNode.Get(0))->GetObject<Ipv4> ());
  // interceptStaticRouting->AddNetworkRouteTo (Ipv4Address ("7.0.0.0"), Ipv4Mask ("255.0.0.0"), 2);
  // interceptStaticRouting->AddNetworkRouteTo (Ipv4Address ("10.1.0.0"), Ipv4Mask ("255.255.0.0"), 1);
  // Ptr<OutputStreamWrapper> routingStream = Create<OutputStreamWrapper> ("sdn.routes", std::ios::out);
  // interceptStaticRouting->PrintRoutingTable(routingStream);
  // Configure applications for traffic generation. Client hosts send traffic
  // to server. The server IP address 10.1.1.1 is attended by the border
  // switch, which redirects the traffic to internal servers, equalizing the
  // number of connections to each server.
  Ipv4Address serverAddr ("10.1.2.1");
  // Ipv4Address ueAddr("7.0.0.3");

  // Installing a sink application at server nodes
  PacketSinkHelper sinkHelper ("ns3::TcpSocketFactory", InetSocketAddress (Ipv4Address::GetAny (), 9));
  PacketSinkHelper sinkHelperExternalUes ("ns3::TcpSocketFactory", InetSocketAddress (Ipv4Address::GetAny (), 5001));
  PacketSinkHelper sinkHelperExternalUes_2 ("ns3::TcpSocketFactory", InetSocketAddress (Ipv4Address::GetAny (), 5002));
  ApplicationContainer sinkApps = sinkHelper.Install (serverNodes);
  ApplicationContainer sinkApps2 = sinkHelperExternalUes.Install (serverNodes);
  ApplicationContainer sinkApps3 = sinkHelperExternalUes_2.Install (serverNodes);
  ApplicationContainer sinkLteApps ;
  sinkApps.Start (Seconds (0));
  sinkApps2.Start (Seconds (0));

  uint16_t lteUlPort = 2000;
  // for (uint16_t i = 0; i  < 10; i++ ) {
  //   lteUlPort++;
    PacketSinkHelper sinkLteHelper ("ns3::UdpSocketFactory", InetSocketAddress (Ipv4Address::GetAny (), lteUlPort));
    sinkLteApps = sinkLteHelper.Install (serverNodes);
  // }
  sinkLteApps.Start (Seconds (0));

  // PacketSinkHelper sinkUdpHelper ("ns3::UdpSocketFactory", InetSocketAddress (Ipv4Address::GetAny (), 2000));
  // UdpServerHelper udpServer(2000);
  // ApplicationContainer udpServerApps = udpServer.Install(serverNodes);
  // udpServerApps.Start( Seconds(0) );
  

  // Installing a sender application at client nodes
  BulkSendHelper senderHelper("ns3::TcpSocketFactory", InetSocketAddress(serverAddr, 9)); // for wan clients
  // OnOffHelper senderHelper ("ns3::TcpSocketFactory", InetSocketAddress(serverAddr,9));
  // senderHelper.SetAttribute ("Interval", TimeValue (MilliSeconds(500)));
  // senderHelper.SetAttribute ("MaxPackets", UintegerValue(1000000));
  ApplicationContainer senderApps = senderHelper.Install (clientNodes);
  // V4PingHelper pingHelper = V4PingHelper(serverAddr);
  // ApplicationContainer pingerApps = pingHelper.Install(clientNodes);
  // BulkSendHelper senderUeHelper("ns3::UdpSocketFactory", InetSocketAddress (ueAddr, 2000));
  // UdpClientHelper senderUeHelper(ueAddr, 2000);
  // senderUeHelper.SetAttribute ("Interval", TimeValue (MilliSeconds(interPacketInterval)));
  // senderUeHelper.SetAttribute ("MaxPackets", UintegerValue(1000000));
  // ApplicationContainer ueSender = senderUeHelper.Install(clientNodes);
  // ueSender.Start(Seconds(0));

  //     clientApps.Add (ulClient.Install (ueNodes.Get(u)));


  // Get random start times
  Ptr<UniformRandomVariable> rngStart = CreateObject<UniformRandomVariable> ();
  rngStart->SetAttribute ("Min", DoubleValue (0));
  rngStart->SetAttribute ("Max", DoubleValue (1));
  ApplicationContainer::Iterator appIt;
  for (appIt = senderApps.Begin (); appIt != senderApps.End (); ++appIt)
    {
      (*appIt)->SetStartTime (Seconds (rngStart->GetValue ()));
      // (*appIt)->SetStartTime (Seconds (100));
    }
  // for (appIt = pingerApps.Begin (); appIt != pingerApps.End (); ++appIt)
    // {
      // (*appIt)->SetStartTime (Seconds (rngStart->GetValue ()));
    // }

  // Enable pcap traces and datapath stats
  if (trace)
    {
      ofLearningHelper->EnableOpenFlowPcap ("openflow");
      ofLearningHelper->EnableDatapathStats ("switch-stats");
      ofQosHelper->EnableOpenFlowPcap ("openflow");
      ofQosHelper->EnableDatapathStats ("switch-stats");
      csmaHelper.EnablePcap ("switch-border", NodeContainer(switchNodes.Get(0)), true);
      csmaHelper.EnablePcap ("switch-aggreation", NodeContainer(switchNodes.Get(1)), true);
      csmaHelper.EnablePcap ("switch-client", NodeContainer(switchNodes.Get(2)), true);
      csmaHelper.EnablePcap ("intercept", backboneNode, true);
      csmaHelper.EnablePcap ("server", serverDevices);
      csmaHelper.EnablePcap ("client", clientDevices);
    }


  // Run the simulation
  Simulator::Stop (Seconds (simTime));
  Simulator::Run ();
  Simulator::Destroy ();

  // Dump total of received bytes by sink applications
  Ptr<PacketSink> sink1 = DynamicCast<PacketSink> (sinkApps.Get (0));
  Ptr<PacketSink> sink2 = DynamicCast<PacketSink> (sinkApps.Get (1));
  // TCP lte connections 
  Ptr<PacketSink> sink3 = DynamicCast<PacketSink> (sinkApps2.Get(0));
  Ptr<PacketSink> sink4 = DynamicCast<PacketSink> (sinkApps2.Get(1));

  Ptr<PacketSink> sink5 = DynamicCast<PacketSink> (sinkApps3.Get(0));
  Ptr<PacketSink> sink6 = DynamicCast<PacketSink> (sinkApps3.Get(1));

  double udpSink=  0;
  for (appIt = sinkLteApps.Begin (); appIt != sinkLteApps.End (); ++appIt)
    {
      Ptr<PacketSink> sinkUdp = DynamicCast<PacketSink> ((*appIt));
      udpSink += (8.0 * sinkUdp->GetTotalRx()) / 1000000 / simTime;
    }
  double tcpSink1 = (8. * sink1->GetTotalRx()) / 1000000 / simTime;
  double tcpSink2 = (8. * sink2->GetTotalRx()) / 1000000 / simTime;
  double tcpSink3 = (8. * sink3->GetTotalRx()) / 1000000 / simTime;
  double tcpSink4 = (8. * sink4->GetTotalRx()) / 1000000 / simTime;
  double tcpSink5 = (8. * sink5->GetTotalRx()) / 1000000 / simTime;
  double tcpSink6 = (8. * sink6->GetTotalRx()) / 1000000 / simTime;

  std::cout << "Simulation Time = " << simTime << std::endl;
  std::cout << "(TCP) WAN Bytes received by server 1: " << sink1->GetTotalRx () << " ("
            << tcpSink1 << " Mbps)"
            << std::endl;
  std::cout << "(TCP) WAN Bytes received by server 2: " << sink2->GetTotalRx () << " ("
            << tcpSink2 << " Mbps)"
            << std::endl;
  std::cout << "(TCP) WAN Bytes received by both server : " << "("
            << tcpSink1 + tcpSink2 << " Mbps)"
            << std::endl;
  std::cout << "(TCP) LTE Bytes received by server 1: " << sink3->GetTotalRx () << " ("
            << tcpSink3 + tcpSink5 << " Mbps)"
            << std::endl;
  std::cout << "(TCP) LTE Bytes received by server 2: " << sink4->GetTotalRx () << " ("
            << tcpSink4 + tcpSink6 << " Mbps)"
            << std::endl;
  std::cout << "(TCP) LTE Bytes received by both server : " << "("
            << tcpSink3 + tcpSink4 + tcpSink5 + tcpSink6<< " Mbps)"
            << std::endl;
  std::cout << "(UDP) Bytes received by both server : " << "("
            << udpSink << " Mbps)"
            << std::endl;
  std::cout << "(TCP+UDP) Total throughput: " << tcpSink1 + tcpSink2 + tcpSink3 + tcpSink4 + tcpSink5 + tcpSink6+ udpSink << " Mbps"
            << std::endl;
}
