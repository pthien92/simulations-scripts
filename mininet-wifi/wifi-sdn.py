#!/usr/bin/python

from mininet.node import RemoteController, OVSKernelSwitch, Host
from mininet.log import setLogLevel, info
from mn_wifi.net import Mininet_wifi
from mn_wifi.node import Station, OVSKernelAP
from mn_wifi.cli import CLI_wifi
from mininet.cli import CLI
from mn_wifi.link import wmediumd
from mininet.link import TCLink
from mn_wifi.wmediumdConnector import interference
from subprocess import call, Popen, PIPE
from mininet.topo import Topo
from mininet.util import decode
from optparse import OptionParser
from time import time
from select import poll, POLLIN

class SdnTopo(Topo):
    def build(self):
        info('*** Add switches/APs\n')
        s3 = self.addSwitch('s3', cls=OVSKernelSwitch)
        s2 = self.addSwitch('s2', cls=OVSKernelSwitch)
        s1 = self.addSwitch('s1', cls=OVSKernelSwitch)

        info('*** Add hosts/stations\n')
        h1 = self.addHost('h1', cls=Host, ip='10.1.2.2',
                     mac='00:00:00:00:00:08', defaultRoute=None)
        h2 = self.addHost('h2', cls=Host, ip='10.1.2.3',
                     mac='00:00:00:00:00:0a', defaultRoute=None)
        h3 = self.addHost('h3', cls=Host, ip='10.1.3.1', defaultRoute=None)
        h4 = self.addHost('h4', cls=Host, ip='10.1.3.2', defaultRoute=None)

        info('*** Add links\n')
        h1s1 = {'bw': 100}
        h2s1 = {'bw': 100}
        self.addLink(h1, s1, cls=TCLink, **h1s1)
        self.addLink(h2, s1, cls=TCLink, **h2s1)
        s1s2_1 = {'bw': 10}
        s1s2_2 = {'bw': 10}
        self.addLink(s1, s2, cls=TCLink, **s1s2_1)
        self.addLink(s1, s2, cls=TCLink, **s1s2_2)
        s2s3 = {'bw': 100}
        self.addLink(s2, s3, cls=TCLink, **s2s3)
        s3h3 = {'bw': 100}
        self.addLink(s3, h3, cls=TCLink, **s3h3)
        s3h4 = {'bw': 100}
        self.addLink(s3, h4, cls=TCLink, **s3h4)

def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option( '-t', '--simTime', dest='simTime',
                      default=10, help='simulation time' )
    parser.add_option( '-b', '--bash', dest='bash',
                      default=False, help='Show bash at the end of simulation' )
    parser.add_option( '-p', '--printClient', dest='printClient',
                      default=False, help='Print client throughput' )
    parser.add_option( '-n', '--nClient', dest='numClient',
                      default=8, help='Print client throughput' )
    options, args = parser.parse_args()
    return options, args

def monitorFiles( outfiles, seconds, timeoutms ):
    "Monitor set of files and return [(host, line)...]"
    devnull = open( '/dev/null', 'w' )
    tails, fdToFile, fdToHost = {}, {}, {}
    for h, outfile in outfiles.items():
        if outfile == '/dev/null':
            continue
        tail = Popen( [ 'tail', '-f', outfile ],
                      stdout=PIPE, stderr=devnull )
        fd = tail.stdout.fileno()
        tails[ h ] = tail
        fdToFile[ fd ] = tail.stdout
        fdToHost[ fd ] = h
    # Prepare to poll output files
    readable = poll()
    for t in tails.values():
        readable.register( t.stdout.fileno(), POLLIN )
    # Run until a set number of seconds have elapsed
    endTime = time() + seconds
    while time() < endTime:
        fdlist = readable.poll(timeoutms)
        if fdlist:
            for fd, _flags in fdlist:
                f = fdToFile[ fd ]
                host = fdToHost[ fd ]
                # Wait for a line of output
                line = f.readline().strip()
                yield host, decode( line )
        else:
            # If we timed out, return nothing
            yield None, ''
    for t in tails.values():
        t.terminate()
    devnull.close() # Not really necessary

def TestWifiSDNNetwork(opts):
    time = int(opts.simTime)
    bash = opts.bash
    printClient = bool(opts.printClient)
    net = Mininet_wifi(topo=None,
                       build=False,
                       link=wmediumd,
                       wmediumd_mode=interference,
                       ipBase='10.0.0.0/8')

    info( '*** Adding controller\n' )
    c1 = net.addController(name='c1',
                           controller=RemoteController,
                           protocol='tcp',
                           port=6653)

    c0 = net.addController(name='c0',
                           controller=RemoteController,
                           protocol='tcp',
                           port=6633)
    info('*** Add switches/APs\n')
    s3 = net.addSwitch('s3', cls=OVSKernelSwitch)
    s2 = net.addSwitch('s2', cls=OVSKernelSwitch)
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch)

    info('*** Add hosts/stations\n')
    h1 = net.addHost('h1', cls=Host, ip='10.1.2.2',
                 mac='00:00:00:00:00:08', defaultRoute=None)
    h2 = net.addHost('h2', cls=Host, ip='10.1.2.3',
                 mac='00:00:00:00:00:0a', defaultRoute=None)
    h3 = net.addHost('h3', cls=Host, ip='10.1.3.1', defaultRoute=None)
    h4 = net.addHost('h4', cls=Host, ip='10.1.3.2', defaultRoute=None)

    info('*** Add links\n')
    h1s1 = {'bw': 100}
    net.addLink(h1, s1, cls=TCLink, **h1s1)
    net.addLink(h2, s1)
    s1s2_1 = {'bw': 10}
    s1s2_2 = {'bw': 10}
    net.addLink(s1, s2, cls=TCLink, **s1s2_1)
    net.addLink(s1, s2, cls=TCLink, **s1s2_2)
    s2s3 = {'bw': 100}
    net.addLink(s2, s3, cls=TCLink, **s2s3)
    s3h3 = {'bw': 100}
    net.addLink(s3, h3, cls=TCLink, **s3h3)
    s3h4 = {'bw': 100}
    net.addLink(s3, h4, cls=TCLink, **s3h4)

    info( '*** Add switches/APs\n')
    ap2 = net.addAccessPoint('ap2', cls=OVSKernelAP, ssid='ap2-ssid',
                             channel='1', mode='g', position='308.0,576.0,0')
    ap1 = net.addAccessPoint('ap1', cls=OVSKernelAP, ssid='ap1-ssid',
                             channel='1', mode='g', position='819.0,529.0,0')

    info( '*** Add hosts/stations\n')

    sta1 = net.addStation('sta1', ip='10.0.0.1',
                           position='132.0,493.0,0')
    sta2 = net.addStation('sta2', ip='10.0.0.2',
                           position='182.0,612.0,0')
    sta3 = net.addStation('sta3', ip='10.0.0.3',
                           position='284.0,709.0,0')
    sta4 = net.addStation('sta4', ip='10.0.0.4',
                           position='491.0,700.0,0')
    sta5 = net.addStation('sta5', ip='10.0.0.5',
                           position='816.0,739.0,0')
    sta6 = net.addStation('sta6', ip='10.0.0.6',
                           position='906.0,691.0,0')
    sta7 = net.addStation('sta7', ip='10.0.0.7',
                           position='974.0,550.0,0')
    sta8 = net.addStation('sta8', ip='10.0.0.8',
                           position='965.0,392.0,0')

    info("*** Configuring Propagation Model\n")
    net.setPropagationModel(model="logDistance", exp=3)

    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    info( '*** Add links\n')
    net.addLink(ap2, sta1)
    net.addLink(ap2, sta2)
    net.addLink(ap2, sta3)
    net.addLink(ap2, sta4)
    net.addLink(ap1, sta5)
    net.addLink(ap1, sta6)
    net.addLink(ap1, sta7)
    net.addLink(ap1, sta8)
    # add ap1 and ap2 to switch 3
    
    s3ap2 = {'bw':100}
    net.addLink(s3, ap2, cls=TCLink , **s3ap2)
    s3ap1 = {'bw':100}
    net.addLink(s3, ap1, cls=TCLink , **s3ap1)

    net.plotGraph(max_x=1000, max_y=1000)

    info( '*** Starting network\n')
    net.build()
    net.start()
    info( '*** Starting controllers\n')
    for controller in net.controllers:
        controller.start()

    info( '*** Starting switches/APs\n')
    net.get('s2').start([c0])
    net.get('s3').start([c1])
    net.get('ap2').start([c1])
    net.get('ap1').start([c1])
    net.get('s1').start([c0])

    info( '\n*** Post configure nodes\n')

    
    hosts = net.stations
    outfiles = {}
    clientPort = 30000

    info('Start iperf server on h1 and h2\n')
    h1, h2 = net.get('h1', 'h2')
    outfiles[h1] = '/tmp/h1.out'
    outfiles[h2] = '/tmp/h2.out'
    h1.cmd('iperf --server > ' + outfiles[h1] + ' --interval 1 &')
    h2.cmd('iperf --server > ' + outfiles[h2] + ' --interval 1 &')

    info('*** Start testing\n')

    for h in hosts:
        if h.name == 'h1' or h.name == 'h2':
            continue
        clientPort += 1
        # if clientPort == 30003:
            # break
        if (printClient):
            outfiles[h] = '/tmp/' + h.name + '.out'
        else:
            outfiles[h] = '/dev/null'
        info('Start iperf client on ' + h.name + ' for ' + str(time) + ' seconds\n' )
        h.cmdPrint('iperf --client ', '10.1.2.1', ' --time ', time,
                    '--interval', 1,
                    '-B', h.IP() + ':' + str(clientPort),
                   '>', outfiles[ h ],
                    '&' )
    info('*** Monitoring output for ', time, "seconds\n") 
    for h, line in monitorFiles(outfiles, time+5, timeoutms=100):
        if h:
            info( '%s: %s\n' % (h.name, line) )
    for h in hosts:
        if h.name == 'h1' or h.name == 'h2':
            if bash:
                continue
        h.cmd('kill %iperf')
    if bash:
        CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    opts, args = parseOptions()
    TestWifiSDNNetwork(opts)

