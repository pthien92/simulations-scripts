from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, arp, ipv4, icmp, tcp, udp
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu import utils


ARP_REQUEST = 1
ARP_REPLY = 2
ARP_REV_REQUEST = 3
ARP_REV_REPLY = 4

class QoSController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self, *args, **kwargs):
        super(QoSController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.server_address = {'ip': '10.1.2.1', 'mac': '00:00:00:00:00:01'}
        self.internal_servers = {
            '1': {'ip': '10.1.2.2', 'mac': '00:00:00:00:00:08'},
            '2': {'ip': '10.1.2.3', 'mac': '00:00:00:00:00:0a'},
        }
        self.connection_counter = 0

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.mac_to_port.setdefault(datapath.id, {})
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
        

        if datapath.id == 1:
            self.logger.info("Border switch is at %s", ev.msg.datapath.address)
            self.configure_border_switch(datapath)
        elif datapath.id == 2:
            self.logger.info("Aggregation switch is at %s", ev.msg.datapath.address)
            self.configure_aggregation_switch(datapath) 
        else:
            self.logger.info("Not handled this datapath id %d", datapath.id)

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
        
    def add_flow_2(self, datapath, table_id, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [
            # parser.OFPInstructionGotoTable(table_id),
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)
            ]
            
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id, table_id=table_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,table_id=table_id,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)
        
    def add_group_flow(self, datapath, buckets, group_id):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        
        req_delete = parser.OFPGroupMod(datapath, ofproto.OFPGC_DELETE, 
                    ofproto.OFPGT_SELECT, group_id, buckets=[])
        datapath.send_msg(req_delete)
        req_add = parser.OFPGroupMod(datapath, ofproto.OFPGC_ADD, 
                    ofproto.OFPGT_SELECT, group_id, buckets)
        # datapath.send_msg(req_delete)
        datapath.send_msg(req_add)

    def configure_border_switch(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        '''
           DpctlExecute (swtch, "flow-mod cmd=add,table=0,prio=20 "
                "eth_type=0x0806,arp_op=1 apply:output=ctrl"); 
        '''
        match   = parser.OFPMatch(
            eth_type=0x0806,
            arp_op=1
        )
        actions = [parser.OFPActionOutput(port=ofproto.OFPP_CONTROLLER)]
        self.add_flow_2(datapath, 0, 20, match, actions)
        
        '''
        -- Configure Group #3 for aggregating links 1 and 2
        DpctlExecute (swtch, "group-mod cmd=add,type=sel,group=3 "
                    "weight=1,port=any,group=any set_field=ip_src:10.1.2.1"
                    ",set_field=eth_src:00:00:00:00:00:01,output=3 "
                    "weight=1,port=any,group=any set_field=ip_src:10.1.2.1"
                    ",set_field=eth_src:00:00:00:00:00:01,output=4");
        '''
        actions_1 = [
            parser.OFPActionSetField(
                ipv4_src="10.1.2.1",
            ),
            parser.OFPActionSetField(
                eth_src="00:00:00:00:00:01"
            ),
            parser.OFPActionOutput(port=3),
        ]
        actions_2 = [
            parser.OFPActionSetField(
                ipv4_src="10.1.2.1",
            ),
            parser.OFPActionSetField(
                eth_src="00:00:00:00:00:01"
            ),
            parser.OFPActionOutput(port=4)
        ]
        buckets_1 = [parser.OFPBucket(
                weight=1,
                watch_port=ofproto.OFPP_ANY,
                watch_group=ofproto.OFPG_ANY,
                actions=actions_1),
            ]
        buckets_2 = [
            parser.OFPBucket(
                weight=1,
                watch_port=ofproto.OFPP_ANY,
                watch_group=ofproto.OFPG_ANY,
                actions=actions_2)
            ]
        self.add_group_flow(datapath, buckets_1, 3)
        self.add_group_flow(datapath, buckets_2, 4)
        
        '''
            // Groups #1 and #2 send traffic to internal servers (ports 3 and 4)
        DpctlExecute (swtch, "group-mod cmd=add,type=ind,group=1 "
                "weight=0,port=any,group=any set_field=ip_dst:10.1.2.2,"
                "set_field=eth_dst:00:00:00:00:00:08,output=1");
        DpctlExecute (swtch, "group-mod cmd=add,type=ind,group=2 "
                "weight=0,port=any,group=any set_field=ip_dst:10.1.2.3,"
                "set_field=eth_dst:00:00:00:00:00:0a,output=2");
        '''
        actions = [
            parser.OFPActionSetField(
                ipv4_dst="10.1.2.2",
            ),
            parser.OFPActionSetField(
                eth_dst="00:00:00:00:00:08"
            ),
            parser.OFPActionOutput(
                port=1
            )
        ]
        buckets = [parser.OFPBucket(
            weight=1,
            watch_port=ofproto.OFPP_ANY,
            watch_group=ofproto.OFPG_ANY,
            actions=actions)]
        self.add_group_flow(datapath, buckets, 1)
        
        actions = [
            parser.OFPActionSetField(
                ipv4_dst="10.1.2.3",
            ),
            parser.OFPActionSetField(
                eth_dst="00:00:00:00:00:0a"
            ),
            parser.OFPActionOutput(
                port=2
            )
        ]
        buckets = [parser.OFPBucket(
            weight=1,
            watch_port=ofproto.OFPP_ANY,
            watch_group=ofproto.OFPG_ANY,
            actions=actions)]
        self.add_group_flow(datapath, buckets, 2)

        '''
        // Incoming TCP connections (ports 3 and 4) are sent to the controller
        DpctlExecute (swtch, "flow-mod cmd=add,table=0,prio=500 "
                "in_port=3,eth_type=0x0800,ip_proto=6,ip_dst=10.1.2.1,"
                "eth_dst=00:00:00:00:00:01 apply:output=ctrl");
        DpctlExecute (swtch, "flow-mod cmd=add,table=0,prio=500 "
                "in_port=4,eth_type=0x0800,ip_proto=6,ip_dst=10.1.2.1,"
                "eth_dst=00:00:00:00:00:01 apply:output=ctrl");
        '''
        match = parser.OFPMatch(
            in_port=3,
            eth_type=0x0800,
            ip_proto=6,
            ipv4_dst="10.1.2.1",
            eth_dst="00:00:00:00:00:01"
        ) 
        actions = [parser.OFPActionOutput(
            port=ofproto.OFPP_CONTROLLER
        )]
        self.add_flow_2(datapath, 0, 500, match, actions);
        
        match = parser.OFPMatch(
            in_port=4,
            eth_type=0x0800,
            ip_proto=6,
            ipv4_dst="10.1.2.1",
            eth_dst="00:00:00:00:00:01"
        ) 
        actions = [parser.OFPActionOutput(
            port=ofproto.OFPP_CONTROLLER
        )]
        self.add_flow_2(datapath, 0, 500, match, actions);
        
        '''
        // TCP packets from servers are sent to the external network through group 3
    DpctlExecute (swtch, "flow-mod cmd=add,table=0,prio=700 "
                "in_port=1,eth_type=0x0800,ip_proto=6 apply:group=3");
    DpctlExecute (swtch, "flow-mod cmd=add,table=0,prio=700 "
                "in_port=2,eth_type=0x0800,ip_proto=6 apply:group=3");
        '''
        
        # match = parser.OFPMatch(
        #     in_port=1,
        #     eth_type=0x0800,
        #     ip_proto=6,
        # ) 
        # match_2 = parser.OFPMatch(
        #     in_port=2,
        #     eth_type=0x0800,
        #     ip_proto=6,
        # ) 
        # actions = [parser.OFPActionGroup(
        #     group_id=3
        # )]
        # self.add_flow_2(datapath, 0, 700, match, actions);
        # self.add_flow_2(datapath, 0, 700, match_2, actions);
        
        
    def configure_aggregation_switch(self,datapath):
        ofproto = datapath.ofproto
        parser  = datapath.ofproto_parser
        actions_1 = [
            parser.OFPActionOutput(
                port=1
            )
        ]
        actions_2 = [
            parser.OFPActionOutput(
                port=2
            )
        ]
        buckets_1 = [parser.OFPBucket(
                weight=1,
                watch_port=ofproto.OFPP_ANY,
                watch_group=ofproto.OFPG_ANY,
                actions=actions_1),
            ]
        buckets_2 = [
            parser.OFPBucket(
                weight=1,
                watch_port=ofproto.OFPP_ANY,
                watch_group=ofproto.OFPG_ANY,
                actions=actions_2),
        ]
        self.add_group_flow(datapath, buckets_1, 1)
        self.add_group_flow(datapath, buckets_2, 2)
        
        '''
        // Packets from input ports 1 and 2 are redirected to port 3
    DpctlExecute (swtch, "flow-mod cmd=add,table=0,prio=500 "
                "in_port=1 write:output=3");
    DpctlExecute (swtch, "flow-mod cmd=add,table=0,prio=500 "
                "in_port=2 write:output=3");

        // Packets from input port 3 are redirected to group 1
    DpctlExecute (swtch, "flow-mod cmd=add,table=0,prio=500 "
                "in_port=3 write:group=1");
        '''
        match = parser.OFPMatch(
            in_port=1,
        ) 
        match_2 = parser.OFPMatch(
            in_port=2,
        ) 
        actions = [parser.OFPActionOutput(
            port=3
        )]
        self.add_flow_2(datapath, 0, 500, match, actions);
        self.add_flow_2(datapath, 0, 500, match_2, actions);

        # handle TCP connection for aggregation switch 
        match = parser.OFPMatch(
            in_port=3,
            eth_type=0x0800,
            ip_proto=6,
            ipv4_dst="10.1.2.1",
            eth_dst="00:00:00:00:00:01"
        ) 
        actions = [parser.OFPActionOutput(
            port=ofproto.OFPP_CONTROLLER
        )]
        self.add_flow_2(datapath, 0, 500, match, actions);
        
        # match = parser.OFPMatch(
        #     in_port=3,
        # ) 
        # actions = [parser.OFPActionGroup(
        #     group_id=1
        # )]
        # self.add_flow_2(datapath, 0, 500, match, actions);
        

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

        if eth.ethertype == ether_types.ETH_TYPE_LLDP or eth.ethertype == ether_types.ETH_TYPE_IPV6:
            # ignore lldp packet
            return
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            return self.handle_arp_in(ev)
        if eth.ethertype == ether_types.ETH_TYPE_IP:
            self.handle_connection_in(ev)

        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port


    def handle_connection_in(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        self.connection_counter = self.connection_counter + 1
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4) 
        pkt_tcp  = pkt.get_protocol(tcp.tcp)
        pkt_icmp = pkt.get_protocol(icmp.icmp)
        pkt_udp  = pkt.get_protocol(udp.udp)
        # ipv4_icmp = pkt_ipv4 if pkt_ipv4 else pkt_icmp
        # send arp request out
        dpid = datapath.id
        if dpid == 2:
            if not pkt_icmp:
                self.logger.info('thien here')
                match = parser.OFPMatch(
                    eth_src=src,
                    eth_dst=dst,
                )
                serverNumber = 1 + (self.connection_counter % 2)
                self.logger.info('[Aggregation] Client %s is directed to internal server %d on datapath %d' %(pkt_ipv4.src, serverNumber, dpid))
                actions = [
                    parser.OFPActionGroup(
                        group_id=serverNumber
                    )
                ]
                self.add_flow_2(datapath, 0, 1000, match, actions)
            elif pkt_icmp:
                # bypassing icmp
                icmp_reply_pkt = packet.Packet()
                icmp_reply_pkt.add_protocol(ethernet.ethernet(ethertype=eth.ethertype, dst=dst, src=src))
                icmp_reply_pkt.add_protocol(ipv4.ipv4(dst=pkt_ipv4.dst, 
                                            src=pkt_ipv4.src, 
                                            proto=pkt_ipv4.proto))
                icmp_reply_pkt.add_protocol(icmp.icmp(type_=icmp.ICMP_ECHO_REQUEST,
                                                        csum=0,
                                                        data=pkt_icmp.data))
                icmp_reply_pkt.serialize()
                actions = [parser.OFPActionOutput(1)]
                out = parser.OFPPacketOut(datapath=datapath,
                                buffer_id=ofproto.OFP_NO_BUFFER,
                                in_port=ofproto.OFPP_CONTROLLER,
                                actions=actions,
                                data=icmp_reply_pkt.data
                                )
                datapath.send_msg(out)
            return

        if dpid == 1:
            if dpid in self.mac_to_port.keys() and src not in self.mac_to_port[dpid]:
                self.send_arp_from_server(parser, datapath, ofproto, in_port, '00:00:00:00:00:00', pkt_ipv4.src)
                # learn the mac
                self.mac_to_port[dpid][src] = in_port
            if not pkt_icmp:
                if pkt_tcp:
                    # set up connection for reaching the host
                    match = parser.OFPMatch(
                        ipv4_src=pkt_ipv4.src,
                        ipv4_dst=pkt_ipv4.dst,
                        eth_type=0x0800,
                        ip_proto=6,
                        tcp_src=pkt_tcp.src_port,
                        tcp_dst=pkt_tcp.dst_port
                    )
                    serverNumber = 1 + (self.connection_counter % 2)
                    self.logger.info('[Border] Client %s is directed to internal server %d on datapath %d' %(pkt_ipv4.src, serverNumber, dpid))
                    actions = [
                        parser.OFPActionGroup(
                            group_id=serverNumber
                        )
                    ]
                    self.add_flow_2(datapath, 0, 1000, match, actions)
        
                    # install reverse flow for server traffic following exactly the incoming route
                    match = parser.OFPMatch(
                        in_port=serverNumber,
                        eth_type=0x0800,
                        ip_proto=6,
                        ipv4_dst=pkt_ipv4.src,
                        tcp_dst=pkt_tcp.src_port
                    ) 
        
                    g_id = 3
                    if in_port == 4:
                        g_id = 4
                    actions = [parser.OFPActionGroup(
                        group_id=g_id
                    )]
                    self.add_flow_2(datapath, 0, 700, match, actions)
                elif pkt_udp:
                    # set up connection for reaching the host
                    match = parser.OFPMatch(
                        ipv4_src=pkt_ipv4.src,
                        ipv4_dst=pkt_ipv4.dst,
                        eth_type=0x0800,
                        ip_proto=17,
                        udp_src=pkt_udp.src_port,
                        udp_dst=pkt_udp.dst_port
                    )
                    serverNumber = 1 + (self.connection_counter % 2)
                    self.logger.info('[Border] Client %s is directed to internal server %d on datapath %d' %(pkt_ipv4.src, serverNumber, dpid))
                    actions = [
                        parser.OFPActionGroup(
                            group_id=serverNumber
                        )
                    ]
                    self.add_flow_2(datapath, 0, 1000, match, actions)
        
                    # install reverse flow for server traffic following exactly the incoming route
                    match = parser.OFPMatch(
                        in_port=serverNumber,
                        eth_type=0x0800,
                        ip_proto=17,
                        ipv4_dst=pkt_ipv4.src,
                        udp_dst=pkt_udp.dst_port
                    ) 
        
                    g_id = 3
                    if in_port == 4:
                        g_id = 4
                    actions = [parser.OFPActionGroup(
                        group_id=g_id
                    )]
                    self.add_flow_2(datapath, 0, 700, match, actions)

            else:
                # reply icmp
                icmp_reply_pkt = packet.Packet()
                icmp_reply_pkt.add_protocol(ethernet.ethernet(ethertype=eth.ethertype, dst=src, src=self.server_address['mac']))
                icmp_reply_pkt.add_protocol(ipv4.ipv4(dst=pkt_ipv4.src, 
                                            src=self.server_address['ip'], 
                                            proto=pkt_ipv4.proto))
                icmp_reply_pkt.add_protocol(icmp.icmp(type_=icmp.ICMP_ECHO_REPLY,
                                                        code=icmp.ICMP_ECHO_REPLY_CODE,
                                                        csum=0,
                                                        data=pkt_icmp.data))
                icmp_reply_pkt.serialize()
                actions = [parser.OFPActionOutput(in_port)]
                out = parser.OFPPacketOut(datapath=datapath,
                                buffer_id=ofproto.OFP_NO_BUFFER,
                                in_port=ofproto.OFPP_CONTROLLER,
                                actions=actions,
                                data=icmp_reply_pkt.data
                                )
                datapath.send_msg(out)
        return

    def handle_arp_in(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        arp_pkt = self.arp_parse(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        if datapath.id == 2:
            self.logger.info('oops!')
        self.logger.info("arp for [%s][%s] from [%s][%s]", dst, arp_pkt.dst_ip, src, arp_pkt.src_ip) 
        if arp_pkt.dst_ip == "10.1.2.1" and arp_pkt.opcode == arp.ARP_REQUEST:
            self.logger.info("arp sent looking for server, by UE[%s]", arp_pkt.src_ip)
            # Create reply packet
            arp_reply_pkt = packet.Packet()
            # Add ethernet frame
            arp_reply_pkt.add_protocol(ethernet.ethernet(ethertype=eth.ethertype, dst=src, src=self.server_address['mac']))
            # Add arp payload
            arp_reply_pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                               src_mac=self.server_address['mac'],
                                               src_ip=self.server_address['ip'],
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
        elif arp_pkt.dst_ip == "10.1.2.1" and arp_pkt.opcode == arp.ARP_REPLY:
            self.logger.info("arp sent to server, by UE[%s]", arp_pkt.src_ip)
            # Create reply packet
            arp_reply_pkt_1 = packet.Packet()
            # Add ethernet frame
            arp_reply_pkt_1.add_protocol(ethernet.ethernet(ethertype=eth.ethertype, dst=self.internal_servers['1']['mac'], src=src))
            # Add arp payload
            arp_reply_pkt_1.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                               src_mac=arp_pkt.src_mac,
                                               src_ip=arp_pkt.src_ip,
                                               dst_mac=self.internal_servers['1']['mac'],
                                               dst_ip=self.internal_servers['1']['ip']
            ))
            arp_reply_pkt_1.serialize()
            actions = [parser.OFPActionOutput(port=1)]
            out = parser.OFPPacketOut(datapath=datapath,
                            buffer_id=ofproto.OFP_NO_BUFFER,
                            in_port=ofproto.OFPP_CONTROLLER,
                            actions=actions,
                            data=arp_reply_pkt_1.data)
            datapath.send_msg(out)
            #############################################################
            arp_reply_pkt_2 = packet.Packet()
            # Add ethernet frame
            arp_reply_pkt_2.add_protocol(ethernet.ethernet(ethertype=eth.ethertype, dst=self.internal_servers['2']['mac'], src=src))
            # Add arp payload
            arp_reply_pkt_2.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                               src_mac=arp_pkt.src_mac,
                                               src_ip=arp_pkt.src_ip,
                                               dst_mac=self.internal_servers['2']['mac'],
                                               dst_ip=self.internal_servers['2']['ip']
            ))
            arp_reply_pkt_2.serialize()
            actions = [parser.OFPActionOutput(port=2)]
            out = parser.OFPPacketOut(datapath=datapath,
                            buffer_id=ofproto.OFP_NO_BUFFER,
                            in_port=ofproto.OFPP_CONTROLLER,
                            actions=actions,
                            data=arp_reply_pkt_2.data)
            datapath.send_msg(out)

        elif (arp_pkt.src_ip == "10.1.2.2" or arp_pkt.src_ip == "10.1.2.3") and arp_pkt.opcode == arp.ARP_REQUEST:
            self.logger.info("arp sent looking for clients, by Server[%s]", arp_pkt.src_ip)
            # Create reply packet
            arp_proxy_pkt = packet.Packet()
            # Add ethernet frame
            arp_proxy_pkt.add_protocol(ethernet.ethernet(ethertype=eth.ethertype, dst='ff:ff:ff:ff:ff:ff', src=self.server_address['mac']))
            # Add arp payload
            arp_proxy_pkt.add_protocol(arp.arp(opcode=arp.ARP_REQUEST,
                                               src_mac=self.server_address['mac'],
                                               src_ip=self.server_address['ip'],
                                               dst_mac=arp_pkt.dst_mac,
                                               dst_ip=arp_pkt.dst_ip
            ))
            arp_proxy_pkt.serialize()
            actions = [parser.OFPActionOutput(port=3)] # can be port 3 or 4
            out = parser.OFPPacketOut(datapath=datapath,
                            buffer_id=ofproto.OFP_NO_BUFFER,
                            in_port=ofproto.OFPP_CONTROLLER,
                            actions=actions,
                            data=arp_proxy_pkt.data)
            datapath.send_msg(out)

        return

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
    
    def send_arp_from_server(self, parser, datapath, ofproto, in_port, dst_mac, dst_ip):
        # Create reply packet
        arp_reply_pkt = packet.Packet()
        # Add ethernet frame
        arp_reply_pkt.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_ARP, src=self.server_address['mac']))
        # Add arp payload
        arp_reply_pkt.add_protocol(arp.arp(opcode=arp.ARP_REQUEST,
                                               src_mac=self.server_address['mac'],
                                               src_ip=self.server_address['ip'],
                                               dst_mac=dst_mac,
                                               dst_ip=dst_ip
        ))
        arp_reply_pkt.serialize()
        actions = [parser.OFPActionOutput(in_port)]
        out = parser.OFPPacketOut(datapath=datapath,
                            buffer_id=ofproto.OFP_NO_BUFFER,
                            in_port=ofproto.OFPP_CONTROLLER,
                            actions=actions,
                            data=arp_reply_pkt.data)
        datapath.send_msg(out)
        return
    
    @set_ev_cls(ofp_event.EventOFPErrorMsg, MAIN_DISPATCHER)
    def handle_error(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofp = msg.datapath.ofproto
        self.logger.info(
        "EventOFPErrorMsg received on datapath %d\n"
        "version=%s, msg_type=%s, msg_len=%s, xid=%s\n"
        " `-- msg_type: %s\n"
        "OFPErrorMsg(type=%s, code=%s, data=b'%s')\n"
        " |-- type: %s\n"
        " |-- code: %s",
        datapath.id,
        hex(msg.version), hex(msg.msg_type), hex(msg.msg_len),
        hex(msg.xid), ofp.ofp_msg_type_to_str(msg.msg_type),
        hex(msg.type), hex(msg.code), b'00',#utils.binary_str(msg.data),
        ofp.ofp_error_type_to_str(msg.type),
        ofp.ofp_error_code_to_str(msg.type, msg.code))

