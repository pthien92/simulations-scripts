/* -*-  Mode: C++; c-file-style: "gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2011 Centre Tecnologic de Telecomunicacions de Catalunya (CTTC)
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 * Author: Jaume Nin <jaume.nin@cttc.cat>
 * Modified: Thien Pham <thien.pham@adelaide.edu.au>
 */

#include "ns3/lte-helper.h"
#include "ns3/epc-helper.h"
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/ipv4-global-routing-helper.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/lte-module.h"
#include "ns3/applications-module.h"
#include "ns3/point-to-point-helper.h"
#include "ns3/config-store.h"
#include <ns3/tap-bridge-module.h>
#include <ns3/csma-module.h>
#include <ns3/nstime.h>
#include "ns3/fd-net-device-module.h"
//#include "ns3/gtk-config-store.h"

using namespace ns3;

/**
 * Sample simulation script for LTE+EPC. It instantiates several eNodeB,
 * attaches one UE per eNodeB starts a flow for each UE to  and from a remote host.
 * It also  starts yet another flow between each UE pair.
 */

NS_LOG_COMPONENT_DEFINE ("EpcSDNExample");

int
main (int argc, char *argv[])
{
  std::string mode    = "UseLocal";
  std::string tapName = "pgwtap";
  uint16_t nEnbNodes = 2;
  uint16_t nUePerEnb = 2;
  double simTime = 100;
  double distance = 60.0;
  double interPacketInterval = 1;
  bool useCa = false;
  bool trace = true;

  // Command line arguments
  CommandLine cmd;
  cmd.AddValue("nEnbNodes", "Number of eNodeBs", nEnbNodes);
  cmd.AddValue("nUePerEnb", "Number of UE pairs", nUePerEnb);
  cmd.AddValue("simTime", "Total duration of the simulation [s])", simTime);
  cmd.AddValue("tapDevice", "The binding external Tap or Veth Device [pgwtap]", tapName);
  cmd.AddValue("distance", "Distance between eNBs [m]", distance);
  cmd.AddValue("interPacketInterval", "Inter packet interval [us])", interPacketInterval); cmd.AddValue("useCa", "Whether to use carrier aggregation.", useCa); cmd.Parse(argc, argv);

  if (useCa)
   {
     Config::SetDefault ("ns3::LteHelper::UseCa", BooleanValue (useCa));
     Config::SetDefault ("ns3::LteHelper::NumberOfComponentCarriers", UintegerValue (2));
     Config::SetDefault ("ns3::LteHelper::EnbComponentCarrierManager", StringValue ("ns3::RrComponentCarrierManager"));
   }

  // Increase TCP MSS for larger packets
  Config::SetDefault ("ns3::TcpSocket::SegmentSize", UintegerValue (1400));
  Config::SetDefault ("ns3::LteEnbRrc::SrsPeriodicity", UintegerValue (160));
  // Config::SetDefault ("ns3::LteRlcUm::MaxTxBufferSize", UintegerValue (1024 * 1024));

  // Enable checksum computations (required by OFSwitch13 module)
  GlobalValue::Bind ("ChecksumEnabled", BooleanValue (true));


  

  Ptr<LteHelper> lteHelper = CreateObject<LteHelper> ();
  Ptr<PointToPointEpcHelper>  epcHelper = CreateObject<PointToPointEpcHelper> ();
  lteHelper->SetEpcHelper (epcHelper);

  ConfigStore inputConfig;
  inputConfig.ConfigureDefaults();

  // parse again so you can override default values from the command line
  cmd.Parse(argc, argv);

  Ptr<Node> pgw = epcHelper->GetPgwNode ();

   // Create a single RemoteHost
  NodeContainer remoteHostContainer, tapContainer;
  remoteHostContainer.Create (1);
  tapContainer.Create(1);
  Ptr<Node> remoteHost = remoteHostContainer.Get (0);
  Ptr<Node> intermediateHost = tapContainer.Get (0);
  InternetStackHelper internet;
  internet.Install (remoteHostContainer);
  internet.Install (tapContainer);


  // Create the Internet
  PointToPointHelper p2ph;
  p2ph.SetDeviceAttribute ("DataRate", DataRateValue (DataRate ("100Gb/s")));
  p2ph.SetDeviceAttribute ("Mtu", UintegerValue (1500));
  p2ph.SetChannelAttribute ("Delay", TimeValue (Seconds (0.010)));
  NetDeviceContainer internetDevices = p2ph.Install (remoteHost, pgw);
  
  Mac48AddressValue localMac1;
  Mac48AddressValue localMac2;
  Mac48AddressValue localMac3;
  Mac48AddressValue localMac4;
  std::string mac1("00:00:00:00:10:01");
  std::string mac2("00:00:00:00:10:02");
  std::string mac4("00:00:00:00:10:03");
  std::string mac3("00:00:00:00:10:04");

  localMac1 =  Mac48AddressValue (mac1.c_str ());
  localMac2 =  Mac48AddressValue (mac2.c_str ());
  localMac3 =  Mac48AddressValue (mac3.c_str ());
  localMac4 =  Mac48AddressValue (mac4.c_str ());

  internetDevices.Get(0)->SetAttribute("Address", localMac1);
  internetDevices.Get(1)->SetAttribute("Address", localMac2);

  Ipv4AddressHelper ipv4h;
  ipv4h.SetBase ("10.1.0.0", "255.255.0.0", "0.0.5.1");
  Ipv4InterfaceContainer internetIpIfaces = ipv4h.Assign (internetDevices);
  // interface 0 is localhost, 1 is the p2p device
  // Ipv4Address remoteHostAddr = internetIpIfaces.GetAddress (1);

  ipv4h.SetBase ("10.1.0.0", "255.255.0.0", "0.0.5.3");
  CsmaHelper csmaHelper;
  csmaHelper.SetChannelAttribute ("DataRate", DataRateValue (DataRate ("100Mbps")));
  NetDeviceContainer tapContainerDevices = csmaHelper.Install(NodeContainer(tapContainer.Get(0), remoteHostContainer.Get(0))) ;
  tapContainerDevices.Get(0)->SetAttribute("Address", localMac2);
  tapContainerDevices.Get(1)->SetAttribute("Address", localMac3);

  Ipv4InterfaceContainer internetTapIfaces = ipv4h.Assign (tapContainerDevices);
  
  Ipv4Address remoteHostAddr("10.1.2.1");


  TapBridgeHelper tapBridge;
  tapBridge.SetAttribute ("Mode", StringValue(mode));
  tapBridge.SetAttribute ("DeviceName", StringValue(tapName));
  tapBridge.Install (tapContainer.Get(0), tapContainerDevices.Get(0));
  // tapBridge.Install (remoteHostContainer.Get(0), internetDevices.Get(0));

  // EmuFdNetDeviceHelper emu;
  // emu.SetDeviceName(tapName);
  // NetDeviceContainer devices = emu.Install (remoteHostContainer.Get(0));
  // Ptr<NetDevice> device = devices.Get (0);
  // device->SetAttribute ("Address", localMac);
  // Ptr<Ipv4> ipv4 = (remoteHostContainer.Get(0))->GetObject<Ipv4> ();
  // uint32_t interface = ipv4->AddInterface (device);
  // Ipv4InterfaceAddress address = Ipv4InterfaceAddress (localIp, localMask);
  // ipv4->AddAddress (interface, address);
  // ipv4->SetMetric (interface, 1);
  // ipv4->SetUp (interface);

  Ipv4StaticRoutingHelper ipv4RoutingHelper;
  Ptr<Ipv4> remoteHostIpv4 = remoteHost->GetObject<Ipv4>();
  // remoteHostIpv4->SetAttribute("IpForward", BooleanValue(true));
  Ptr<Ipv4StaticRouting> remoteHostStaticRouting = ipv4RoutingHelper.GetStaticRouting (remoteHost->GetObject<Ipv4> ());
  remoteHostStaticRouting->AddNetworkRouteTo (Ipv4Address ("7.0.0.0"), Ipv4Mask ("255.0.0.0"), 1);
  remoteHostStaticRouting->AddNetworkRouteTo (Ipv4Address ("10.1.0.0"), Ipv4Mask ("255.255.0.0"), 2);
  Ptr<Ipv4StaticRouting> intermediateHostStaticRouting = ipv4RoutingHelper.GetStaticRouting (intermediateHost->GetObject<Ipv4> ());
  intermediateHostStaticRouting->AddNetworkRouteTo (Ipv4Address ("7.0.0.0"), Ipv4Mask ("255.0.0.0"), 1);
  intermediateHostStaticRouting->AddNetworkRouteTo (Ipv4Address ("10.1.0.0"), Ipv4Mask ("255.255.0.0"), 2);
  // Ptr<OutputStreamWrapper> routingStream = Create<OutputStreamWrapper> ("epc-core.routes", std::ios::out);
  // remoteHostStaticRouting->PrintRoutingTable(routingStream);
  // intermediateHostStaticRouting->PrintRoutingTable(routingStream);

  NodeContainer ueNodes;
  NodeContainer enbNodes;
  enbNodes.Create(nEnbNodes);
  ueNodes.Create(nUePerEnb* nEnbNodes);

  // Install Mobility Model
  Ptr<ListPositionAllocator> positionAlloc = CreateObject<ListPositionAllocator> ();
  for (uint16_t i = 0; i < nEnbNodes; i++)
    {
      positionAlloc->Add (Vector(distance * i, 0, 0));
    }
  MobilityHelper mobility;
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  mobility.SetPositionAllocator(positionAlloc);
  mobility.Install(enbNodes);
  mobility.Install(ueNodes);

  // Install LTE Devices to the nodes
  NetDeviceContainer enbLteDevs = lteHelper->InstallEnbDevice (enbNodes);
  NetDeviceContainer ueLteDevs  = lteHelper->InstallUeDevice (ueNodes);

  // Install the IP stack on the UEs
  internet.Install (ueNodes);
  Ipv4InterfaceContainer ueIpIface;
  ueIpIface = epcHelper->AssignUeIpv4Address (NetDeviceContainer (ueLteDevs));
  // Assign IP address to UEs, and install applications
  std::cout << epcHelper->GetUeDefaultGatewayAddress() << std::endl;
  for (uint32_t u = 0; u < ueNodes.GetN (); ++u)
    {
      Ptr<Node> ueNode = ueNodes.Get (u);
      // Set the default gateway for the UE
      Ptr<Ipv4StaticRouting> ueStaticRouting = ipv4RoutingHelper.GetStaticRouting (ueNode->GetObject<Ipv4> ());
      ueStaticRouting->SetDefaultRoute (epcHelper->GetUeDefaultGatewayAddress (), 1);
    }

  lteHelper->Attach (ueLteDevs);
  // Attach one UE per eNodeB
  // for (uint16_t i = 0; i < ueNodes.GetN(); i++)
      // {
        // lteHelper->Attach (ueLteDevs.Get(i), enbLteDevs.Get(i));
        // side effect: the default EPS bearer will be activated
  // for (uint16_t j = 0; j < enbNodes.GetN(); j++) {
  //   uint16_t nUeStart = j*nUePerEnb;
  //   uint16_t nUeStop  = nUePerEnb + nUeStart;
  //   for (uint16_t i = nUeStart; i < nUeStop; i++) {
  //     lteHelper->Attach (ueLteDevs.Get(i), enbLteDevs.Get(j));
  //   }
  // }


  // Install and start applications on UEs and remote host
  // uint16_t dlPort = 1234;
  uint16_t ulPort = 2000;
  // uint16_t otherPort = 3000;
  // uint16_t serverPort = 9;
  ApplicationContainer clientApps;
  // ApplicationContainer serverApps;
  // for (uint32_t u = 0; u < ueNodes.GetN(); ++u) {
  //   Ptr<Node> ue = ueNodes.Get(u);
  //   BulkSendHelper senderHelper ("ns3::TcpSocketFactory", InetSocketAddress (remoteHostAddr, serverPort));
  //   senderHelper.SetAttribute("MaxBytes", UintegerValue(0));
  //   clientApps.Add(senderHelper.Install (ue));
  // }
  //  // Get random start times
  // Ptr<UniformRandomVariable> rngStart = CreateObject<UniformRandomVariable> ();
  // rngStart->SetAttribute ("Min", DoubleValue (0));
  // rngStart->SetAttribute ("Max", DoubleValue (1));
  // ApplicationContainer::Iterator appIt;
  // for (appIt = clientApps.Begin (); appIt != clientApps.End (); ++appIt)
  //   {
  //     (*appIt)->SetStartTime (Seconds (rngStart->GetValue ()));
  //   }

  for (uint32_t u = 0; u < ueNodes.GetN (); ++u)
    {

      UdpClientHelper ulClient (remoteHostAddr, ulPort);
      ulClient.SetAttribute ("Interval", TimeValue (MilliSeconds(interPacketInterval)));
      ulClient.SetAttribute ("MaxPackets", UintegerValue(4294967295));

      clientApps.Add (ulClient.Install (ueNodes.Get(u)));
    }
  
  ApplicationContainer::Iterator appIt;
  uint16_t startTime= 0;
  Ptr<UniformRandomVariable> rngStart = CreateObject<UniformRandomVariable> ();
  rngStart->SetAttribute ("Min", DoubleValue (0));
  rngStart->SetAttribute ("Max", DoubleValue (1));
  for (appIt = clientApps.Begin (); appIt != clientApps.End (); ++appIt)
    {

      (*appIt)->SetStartTime (MilliSeconds(rngStart->GetValue()+ startTime));
      startTime++;
      // (*appIt)->SetStartTime (Seconds (100));
    }
  if (trace) {
    lteHelper->EnableTraces ();
    // Uncomment to enable PCAP tracing
    p2ph.EnablePcapAll("lena-epc-sdn");
    // csmaHelper.EnablePcapAll("cmsa-tap", true);
    csmaHelper.EnablePcap("remoteHost", remoteHostContainer, true);
  }

  Simulator::Stop(Seconds(simTime));
  Simulator::Run();

  /*GtkConfigStore config;
  config.ConfigureAttributes();*/

  Simulator::Destroy();
  return 0;

}

