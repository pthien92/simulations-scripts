
# Copyright Thien Pham 2019

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, arp, tcp, udp, ipv4, icmp
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

ARP_REQUEST = 1
ARP_REPLY = 2
ARP_REV_REQUEST = 3
ARP_REV_REPLY = 4

class LteAdapterController13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(LteAdapterController13, self).__init__(*args, **kwargs)
        self.servers = {'10.1.2.1' : '00:00:00:00:00:01',
                        # insert more server if needed
                        }
        self.adapter_veth_ips = {'10.1.2.4' : '00:00:00:00:10:04', 
                        # insert more veth ip:mac if needed
                        '10.1.5.4' : '00:00:00:00:10:04',
                        '10.1.2.5' : '00:00:00:00:10:05'
                        }
        self.in_port_list = [1,3,5]     # clients should connect to this port number, if have, you can choose other port numbers
        self.out_port_map = {'1': '2'}  # which means packets NATTED at port 1, output to port 2, this is important
        self.external_port = 30000;     # initial value
        self.ip_to_port = {};           # keep track of internal IPs represented as external ports, can be used for other purpose

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        for ip in self.adapter_veth_ips:
            match = parser.OFPMatch(
                eth_type=0x0806,
                arp_op=1,
                arp_spa=ip,
                )
            actions = [parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER,
                ofproto.OFPCML_NO_BUFFER
                )]
            self.add_flow(datapath, 20, match, actions)

        for ip in self.servers:
            match = parser.OFPMatch(
                eth_type=0x0806,
                arp_op=1,
                arp_spa=ip,
                )
            actions = [parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER,
                ofproto.OFPCML_NO_BUFFER
                )]
            self.add_flow(datapath, 20, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            self.handle_arp_in(ev)
        if eth.ethertype == ether_types.ETH_TYPE_IP:
            self.handle_connection_in(ev)

    def handle_connection_in(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        self.external_port += 1
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)
        pkt_tcp  = pkt.get_protocol(tcp.tcp)
        pkt_udp  = pkt.get_protocol(udp.udp)
        pkt_icmp = pkt.get_protocol(icmp.icmp)
        if str(in_port) in self.out_port_map.keys():
            out_port = int(self.out_port_map[str(in_port)],10)
        else:
            self.logger.info("Cannot determine outport for inport %d" %(in_port))
            return
        if pkt_ipv4.dst in self.servers.keys() and in_port in self.in_port_list: # filter out packet not comming from client device
            # install NAT rule for TCP connection
            for ip in self.adapter_veth_ips: 
                if pkt_tcp:
                    # Connection to server
                    self.logger.info("[TCP] Install forward translation for %s" %(ip))
                    self.ip_to_port[pkt_ipv4.src] = self.external_port
                    match = parser.OFPMatch(
                        ipv4_src=pkt_ipv4.src,
                        ipv4_dst=pkt_ipv4.dst,
                        eth_type=0x0800,
                        ip_proto=6,
                        tcp_src=pkt_tcp.src_port,
                        tcp_dst=pkt_tcp.dst_port,
                        in_port=in_port
                    )
                    actions = [
                        parser.OFPActionSetField(
                            ipv4_src=ip,
                        ),
                        parser.OFPActionSetField(
                            eth_src=self.adapter_veth_ips[ip]  # get the mac
                        ),
                        parser.OFPActionSetField(
                            tcp_src=self.external_port
                        ),
                        parser.OFPActionSetField(
                            tcp_dst=pkt_tcp.dst_port
                        ),
                        parser.OFPActionOutput(
                            port=out_port
                        )
                    ]
                    self.add_flow(datapath, 500, match, actions)
    
                    # Install a backward (reversed ) translation from server to client
                    self.logger.info("[TCP] Install backward translation for %s" %(ip))
                    match_2 = parser.OFPMatch(
                        ipv4_src=pkt_ipv4.dst,
                        ipv4_dst=ip,
                        eth_type=0x0800,
                        ip_proto=6,
                        tcp_src=pkt_tcp.dst_port,
                        tcp_dst=self.external_port,
                        in_port=out_port
                    )
                    actions_2 = [
                        parser.OFPActionSetField(
                            ipv4_src=pkt_ipv4.dst
                        ),
                        parser.OFPActionSetField(
                            ipv4_dst=pkt_ipv4.src
                        ),
                        parser.OFPActionSetField(
                            tcp_src=pkt_tcp.dst_port
                        ),
                        parser.OFPActionSetField(
                            tcp_dst=pkt_tcp.src_port
                        ),
                        parser.OFPActionOutput(
                            port=in_port
                        )
                    ]
                    self.add_flow(datapath, 500, match_2, actions_2)
                elif pkt_udp:
                    # install NAT rule for UDP forward traffic 
                    self.logger.info("[UDP] Install forward translation for %s" %(pkt_ipv4.dst))
                    self.ip_to_port[pkt_ipv4.src] = self.external_port
                    match = parser.OFPMatch(
                        ipv4_src=pkt_ipv4.src,
                        ipv4_dst=pkt_ipv4.dst,
                        eth_type=0x0800,
                        ip_proto=17,
                        udp_src=pkt_udp.src_port,
                        udp_dst=pkt_udp.dst_port,
                        in_port=in_port
                    )
                    actions = [
                        parser.OFPActionSetField(
                            ipv4_src=ip,
                        ),
                        parser.OFPActionSetField(
                            eth_src=self.adapter_veth_ips[ip]
                        ),
                        parser.OFPActionSetField(
                            udp_src=self.external_port
                        ),
                        parser.OFPActionSetField(
                            udp_dst=pkt_udp.dst_port
                        ),
                        parser.OFPActionOutput(
                            port=out_port
                        )
                    ]
                    self.add_flow(datapath, 500, match, actions)
    
                    # Install a backward (reversed ) translation from server to client
                    self.logger.info("[UDP] Install backward translation for %s" %(pkt_ipv4.dst))
                    match_2 = parser.OFPMatch(
                        ipv4_src=pkt_ipv4.dst,
                        ipv4_dst=ip,
                        eth_type=0x0800,
                        ip_proto=17,
                        udp_src=pkt_udp.dst_port,
                        udp_dst=self.external_port,
                        in_port=out_port
                    )
                    actions_2 = [
                        parser.OFPActionSetField(
                            ipv4_src=pkt_ipv4.dst
                        ),
                        parser.OFPActionSetField(
                            ipv4_dst=pkt_ipv4.src
                        ),
                        parser.OFPActionSetField(
                            udp_src=pkt_udp.dst_port
                        ),
                        parser.OFPActionSetField(
                            udp_dst=pkt_udp.src_port
                        ),
                        parser.OFPActionOutput(
                            port=in_port
                        )
                    ]
                    self.add_flow(datapath, 500, match_2, actions_2)
                elif pkt_icmp:
                    self.logger.info("[ICMP] Install forward redirection for %s" %(pkt_ipv4.dst))
                    match = parser.OFPMatch(
                        eth_src=eth.src,
                        eth_dst=eth.dst,
                        eth_type=0x0800,
                        ip_proto=0x01,
                        in_port=in_port
                    )
                    actions = [
                        parser.OFPActionOutput(
                            port=out_port
                        )
                    ]
                    self.add_flow(datapath, 500, match, actions)
    
                    # Install a backward (reversed ) translation from server to client
                    self.logger.info("[ICMP] Install backward redirection for %s" %(pkt_ipv4.dst))
                    match_2 = parser.OFPMatch(
                        eth_src=eth.dst,
                        eth_dst=eth.src,
                        eth_type=0x0800,
                        ip_proto=0x01,
                        in_port=out_port
                    )
                    actions_2 = [
                        parser.OFPActionOutput(
                            port=in_port
                        )
                    ]
                    self.add_flow(datapath, 500, match_2, actions_2)
                    # still need to forward this initial packet to destination, otherwise ping seq mismatch will appear on wireshark trace, minor
                    ofproto = datapath.ofproto
                    pkt.serialize()
                    actions = [parser.OFPActionOutput(out_port)]
                    out = parser.OFPPacketOut(datapath=datapath,
                                buffer_id=ofproto.OFP_NO_BUFFER,
                                in_port=ofproto.OFPP_CONTROLLER,
                                actions=actions,
                                data=pkt.data)
                    datapath.send_msg(out)

    def handle_arp_in(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        arp_pkt = self.arp_parse(msg.data)
        if arp_pkt.opcode != arp.ARP_REQUEST:
            # we don't handle arp reply
            return
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src

        self.logger.info("arp for [%s][%s] from [%s][%s]", dst, arp_pkt.dst_ip, src, arp_pkt.src_ip)

        if arp_pkt.src_ip in self.adapter_veth_ips.keys() and arp_pkt.dst_ip in self.servers.keys():
            # we need to touch the arp
            self.logger.info("arp sent by UEs, looking for server[%s]" %(arp_pkt.dst_ip))
            # Create reply packet
            arp_reply_pkt = packet.Packet()
            # Add ethernet frame
            arp_reply_pkt.add_protocol(ethernet.ethernet(ethertype=eth.ethertype, dst=src, src=self.servers[arp_pkt.dst_ip]))
            # Add arp payload
            arp_reply_pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                               src_mac=self.servers[arp_pkt.dst_ip],
                                               src_ip=arp_pkt.dst_ip,
                                               dst_mac=self.adapter_veth_ips[arp_pkt.src_ip],
                                               dst_ip=arp_pkt.src_ip
            ))
            arp_reply_pkt.serialize()
            actions = [parser.OFPActionOutput(in_port)]
            out = parser.OFPPacketOut(datapath=datapath,
                            buffer_id=ofproto.OFP_NO_BUFFER,
                            in_port=ofproto.OFPP_CONTROLLER,
                            actions=actions,
                            data=arp_reply_pkt.data)
            datapath.send_msg(out)
        elif arp_pkt.src_ip in self.servers.keys() and (arp_pkt.dst_ip in self.adapter_veth_ips.keys()): 
            self.logger.info("arp sent by Server, looking for mac address of UE[%s]", arp_pkt.dst_ip)
            # Create reply packet
            arp_reply_pkt = packet.Packet()
            # Add ethernet frame
            arp_reply_pkt.add_protocol(ethernet.ethernet(ethertype=eth.ethertype, dst=src, src=self.adapter_veth_ips[arp_pkt.dst_ip]))
            # Add arp payload
            arp_reply_pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                               src_mac=self.adapter_veth_ips[arp_pkt.dst_ip],
                                               src_ip=arp_pkt.dst_ip,
                                               dst_mac=arp_pkt.src_mac,
                                               dst_ip=arp_pkt.src_ip
            ))
            arp_reply_pkt.serialize()
            actions = [parser.OFPActionOutput(in_port)]
            out = parser.OFPPacketOut(datapath=datapath,
                            buffer_id=ofproto.OFP_NO_BUFFER,
                            in_port=ofproto.OFPP_CONTROLLER,
                            actions=actions,
                            data=arp_reply_pkt.data)
            datapath.send_msg(out)
        else:
            self.logger.info("Unhandled ARPs %s" %(arp_pkt)) 


    def arp_parse(self, data):
        """
        Parse ARP packet, return ARP class from packet library.
        """
        # Iteratize pkt
        pkt = packet.Packet(data)
        i = iter(pkt)
        eth_pkt = next(i)
        # Ensure it's an ethernet frame.
        assert isinstance(eth_pkt, ethernet.ethernet)

        arp_pkt = next(i)
        if not isinstance(arp_pkt, arp.arp):
            raise ARPPacket.ARPUnknownFormat()

        if arp_pkt.opcode not in (ARP_REQUEST, ARP_REPLY):
            raise ARPPacket.ARPUnknownFormat(
                msg='unsupported opcode %d' % arp_pkt.opcode)

        if arp_pkt.proto != ether_types.ETH_TYPE_IP:
            raise ARPPacket.ARPUnknownFormat(
                msg='unsupported arp ethtype 0x%04x' % arp_pkt.proto)

        return arp_pkt
