#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch, Host, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink, Intf
from mininet.log import setLogLevel, info
from subprocess import call
from mininet.topo import Topo
from mininet.util import decode
from optparse import OptionParser
from time import time
from select import poll, POLLIN
from subprocess import Popen, PIPE
import sys


class SdnTopo(Topo):
    def build(self):
        info('*** Add switches/APs\n')
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
        h1s1 = {'bw': 10}
        h2s1 = {'bw': 10}
        self.addLink(h1, s1, cls=TCLink, **h1s1)
        self.addLink(h2, s1, cls=TCLink, **h2s1)
        s1s2 = {'bw': 100}
        self.addLink(s1, s2, cls=TCLink, **s1s2)
        s2h3 = {'bw': 100}
        self.addLink(s2, h3, cls=TCLink, **s2h3)
        s2h4 = {'bw': 100}
        self.addLink(s2, h4, cls=TCLink, **s2h4)

def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option( '-t', '--simTime', dest='simTime',
                      default=10, help='simulation time' )
    parser.add_option( '-b', '--bash', dest='bash',
                      default=False, help='Show bash at the end of simulation' )
    parser.add_option( '-p', '--printClient', dest='printClient',
                      default=False, help='Print client throughput' )
    parser.add_option( '-o', '--outputFile', dest='outputFile',
                      default=None, help='Output to outputFile name' )
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

def testSDNNetworkPerformance(opts):
    time = int(opts.simTime)
    bash = bool(opts.bash)
    printClient = bool(opts.printClient)
    if opts.outputFile:
        sys.stdout = open(opts.outputFile, 'w')
    topo = SdnTopo()
    net = Mininet(topo=topo,
                  build=False,
                  ipBase='10.1.2.0/24')

    info('*** Adding controller\n')
    # External Ryu learning controller
    c1 = net.addController(name='c1',
                           controller=RemoteController,
                           protocol='tcp',
                           port=6653)

    info('*** Build and start network\n')
    net.build()
    net.start()
    info('*** Starting controllers\n')
    for controller in net.controllers:
        controller.start()

    info('*** Starting switches/APs\n')
    net.get('s2').start([c1])
    net.get('s1').start([c1])

    info('\n*** Post configure nodes\n')

    hosts = net.hosts
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
        if (printClient):
            outfiles[h] = '/tmp/' + h.name + '.out'
        else:
            outfiles[h] = '/dev/null'
        info('Start iperf client on ' + h.name + ' for ' + str(time) + ' seconds\n' )
        if h.name == 'h3':
            h.cmdPrint('iperf --client ', '10.1.2.2', ' --time ', time,
                        '--interval', 1,
                        '-B', h.IP() + ':' + str(clientPort),
                       '>', outfiles[ h ],
                        '&' )
        else:
            h.cmdPrint('iperf --client ', '10.1.2.3', ' --time ', time,
                        '--interval', 1,
                        '-B', h.IP() + ':' + str(clientPort),
                       '>', outfiles[ h ],
                        '&' )

    info('*** Monitoring output for ', time, "seconds\n") 
    for h, line in monitorFiles(outfiles, time+5, timeoutms=100):
        if h:
            info( '%s: %s\n' % (h.name, line) )
            if opts.outputFile:
                print( '%s: %s\n' % (h.name, line) )
                    
    for h in hosts:
        if h.name == 'h1' or h.name == 'h2':
            if bash:
                continue
        h.cmd('kill %iperf')
    if bash:
        CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    opts, args = parseOptions()
    testSDNNetworkPerformance(opts)
