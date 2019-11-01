#!/usr/bin/python

from mininet.node import RemoteController, OVSKernelSwitch, Host
from mininet.log import setLogLevel, info
from mn_wifi.net import Mininet_wifi
from mn_wifi.node import Station, OVSKernelAP
from mn_wifi.cli import CLI_wifi
from mn_wifi.link import wmediumd
from mininet.link import TCLink
from mn_wifi.wmediumdConnector import interference
from optparse import OptionParser
from time import time
from select import poll, POLLIN
from subprocess import call, Popen, PIPE
import sys
from mininet.util import decode

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

def testWifiSDNNetwork(opts):
    time = int(opts.simTime)
    bash = bool(opts.bash)
    printClient = bool(opts.printClient)
    if opts.outputFile:
        sys.stdout = open(opts.outputFile, 'w')
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

    info( '*** Add switches/APs\n')
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch)
    s2 = net.addSwitch('s2', cls=OVSKernelSwitch)
    s3 = net.addSwitch('s3', cls=OVSKernelSwitch)
    ap1 = net.addAccessPoint('ap1', cls=OVSKernelAP, ssid='ap1-ssid',
                             channel='1', mode='g', position='200.0,95.0,0')
    ap2 = net.addAccessPoint('ap2', cls=OVSKernelAP, ssid='ap2-ssid',
                             channel='1', mode='g', position='155.0,571.0,0')
    ap3 = net.addAccessPoint('ap3', cls=OVSKernelAP, ssid='ap3-ssid',
                             channel='1', mode='g', position='364.0,861.0,0')
    ap4 = net.addAccessPoint('ap4', cls=OVSKernelAP, ssid='ap4-ssid',
                             channel='1', mode='g', position='955.0,853.0,0')
    ap5 = net.addAccessPoint('ap5', cls=OVSKernelAP, ssid='ap5-ssid',
                             channel='1', mode='g', position='1523.0,831.0,0')
    ap6 = net.addAccessPoint('ap6', cls=OVSKernelAP, ssid='ap6-ssid',
                             channel='1', mode='g', position='1667.0,366.0,0')
    ap7 = net.addAccessPoint('ap7', cls=OVSKernelAP, ssid='ap7-ssid',
                             channel='1', mode='g', position='1250.0,115.0,0')
    ap8 = net.addAccessPoint('ap8', cls=OVSKernelAP, ssid='ap8-ssid',
                             channel='1', mode='g', position='761.0,48.0,0')
    ap9 = net.addAccessPoint('ap9', cls=OVSKernelAP, ssid='ap9-ssid',
                             channel='1', mode='g', position='653.0,466.0,0')
    ap10 = net.addAccessPoint('ap10', cls=OVSKernelAP, ssid='ap10-ssid',
                             channel='1', mode='g', position='1137.0,465.0,0')

    info( '*** Add hosts/stations\n')

    h1 = net.addHost('h1', cls=Host, ip='10.1.2.2',
                 mac='00:00:00:00:00:08', defaultRoute=None)
    h2 = net.addHost('h2', cls=Host, ip='10.1.2.3',
                 mac='00:00:00:00:00:0a', defaultRoute=None)
    h3 = net.addHost('h3', cls=Host, ip='10.1.3.1', defaultRoute=None)
    h4 = net.addHost('h4', cls=Host, ip='10.1.3.2', defaultRoute=None)

    sta1 = net.addStation('sta1', ip='10.0.0.1',
                           position='53.0,399.0,0')
    sta2 = net.addStation('sta2', ip='10.0.0.2',
                           position='4.0,611.0,0')
    sta3 = net.addStation('sta3', ip='10.0.0.3',
                           position='23.0,753.0,0')
    sta4 = net.addStation('sta4', ip='10.0.0.4',
                           position='210.0,457.0,0')
    sta5 = net.addStation('sta5', ip='10.0.0.5',
                           position='372.0,428.0,0')
    sta6 = net.addStation('sta6', ip='10.0.0.6',
                           position='188.0,337.0,0')
    sta7 = net.addStation('sta7', ip='10.0.0.7',
                           position='307.0,524.0,0')
    sta8 = net.addStation('sta8', ip='10.0.0.8',
                           position='409.0,515.0,0')
    sta9 = net.addStation('sta9', ip='10.0.0.9',
                           position='124.0,482.0,0')
    sta10 = net.addStation('sta10', ip='10.0.0.10',
                           position='5.0,514.0,0')
    sta11 = net.addStation('sta11', ip='10.0.0.11',
                           position='300.0,893.0,0')
    sta12 = net.addStation('sta12', ip='10.0.0.12',
                           position='453.0,878.0,0')
    sta13 = net.addStation('sta13', ip='10.0.0.13',
                           position='535.0,822.0,0')
    sta14 = net.addStation('sta14', ip='10.0.0.14',
                           position='594.0,872.0,0')
    sta15 = net.addStation('sta15', ip='10.0.0.15',
                           position='530.0,888.0,0')
    sta16 = net.addStation('sta16', ip='10.0.0.16',
                           position='484.0,817.0,0')
    sta17 = net.addStation('sta17', ip='10.0.0.17',
                           position='239.0,895.0,0')
    sta18 = net.addStation('sta18', ip='10.0.0.18',
                           position='155.0,906.0,0')
    sta19 = net.addStation('sta19', ip='10.0.0.19',
                           position='91.0,897.0,0')
    sta20 = net.addStation('sta20', ip='10.0.0.20',
                           position='486.0,756.0,0')
    sta21 = net.addStation('sta21', ip='10.0.0.21',
                           position='770.0,898.0,0')
    sta22 = net.addStation('sta22', ip='10.0.0.22',
                           position='747.0,816.0,0')
    sta23 = net.addStation('sta23', ip='10.0.0.23',
                           position='824.0,791.0,0')
    sta24 = net.addStation('sta24', ip='10.0.0.24',
                           position='852.0,839.0,0')
    sta25 = net.addStation('sta25', ip='10.0.0.25',
                           position='895.0,889.0,0')
    sta26 = net.addStation('sta26', ip='10.0.0.26',
                           position='1021.0,904.0,0')
    sta27 = net.addStation('sta27', ip='10.0.0.27',
                           position='1144.0,875.0,0')
    sta28 = net.addStation('sta28', ip='10.0.0.28',
                           position='1074.0,819.0,0')
    sta29 = net.addStation('sta29', ip='10.0.0.29',
                           position='1012.0,803.0,0')
    sta30 = net.addStation('sta30', ip='10.0.0.30',
                           position='962.0,778.0,0')
    sta31 = net.addStation('sta31', ip='10.0.0.31',
                           position='1344.0,867.0,0')
    sta32 = net.addStation('sta32', ip='10.0.0.32',
                           position='1328.0,820.0,0')
    sta33 = net.addStation('sta33', ip='10.0.0.33',
                           position='1391.0,737.0,0')
    sta34 = net.addStation('sta34', ip='10.0.0.34',
                           position='1442.0,686.0,0')
    sta35 = net.addStation('sta35', ip='10.0.0.35',
                           position='1563.0,721.0,0')
    sta36 = net.addStation('sta36', ip='10.0.0.36',
                           position='1653.0,760.0,0')
    sta37 = net.addStation('sta37', ip='10.0.0.37',
                           position='1663.0,833.0,0')
    sta38 = net.addStation('sta38', ip='10.0.0.38',
                           position='1597.0,879.0,0')
    sta39 = net.addStation('sta39', ip='10.0.0.39',
                           position='1442.0,892.0,0')
    sta40 = net.addStation('sta40', ip='10.0.0.40',
                           position='1425.0,842.0,0')
    sta41 = net.addStation('sta42', ip='10.0.0.41',
                           position='1500.0,467.0,0')
    sta42 = net.addStation('sta42', ip='10.0.0.42',
                           position='1512.0,467.0,0')
    sta43 = net.addStation('sta43', ip='10.0.0.43',
                           position='1664.0,512.0,0')
    sta44 = net.addStation('sta44', ip='10.0.0.44',
                           position='1563.0,418.0,0')
    sta45 = net.addStation('sta45', ip='10.0.0.45',
                           position='1568.0,286.0,0')
    sta46 = net.addStation('sta46', ip='10.0.0.46',
                           position='1614.0,141.0,0')
    sta47 = net.addStation('sta47', ip='10.0.0.47',
                           position='1677.0,185.0,0')
    sta48 = net.addStation('sta48', ip='10.0.0.48',
                           position='1698.0,118.0,0')
    sta49 = net.addStation('sta49', ip='10.0.0.49',
                           position='1684.0,268.0,0')
    sta50 = net.addStation('sta50', ip='10.0.0.50',
                           position='1590.0,209.0,0')
    sta51 = net.addStation('sta51', ip='10.0.0.51',
                           position='1359.0,160.0,0')
    sta52 = net.addStation('sta52', ip='10.0.0.52',
                           position='1409.0,98.0,0')
    sta53 = net.addStation('sta53', ip='10.0.0.53',
                           position='1523.0,49.0,0')
    sta54 = net.addStation('sta54', ip='10.0.0.54',
                           position='1394.0,26.0,0')
    sta55 = net.addStation('sta55', ip='10.0.0.55',
                           position='1243.0,23.0,0')
    sta56 = net.addStation('sta56', ip='10.0.0.56',
                           position='1097.0,33.0,0')
    sta57 = net.addStation('sta57', ip='10.0.0.57',
                           position='1105.0,97.0,0')
    sta58 = net.addStation('sta58', ip='10.0.0.58',
                           position='1176.0,65.0,0')
    sta59 = net.addStation('sta59', ip='10.0.0.59',
                           position='1316.0,85.0,0')
    sta60 = net.addStation('sta60', ip='10.0.0.60',
                           position='1315.0,34.0,0')
    sta61 = net.addStation('sta61', ip='10.0.0.61',
                           position='886.0,143.0,0')
    sta62 = net.addStation('sta62', ip='10.0.0.62',
                           position='886.0,53.0,0')
    sta63 = net.addStation('sta63', ip='10.0.0.63',
                           position='698.0,40.0,0')
    sta64 = net.addStation('sta64', ip='10.0.0.64',
                           position='579.0,68.0,0')
    sta65 = net.addStation('sta65', ip='10.0.0.65',
                           position='546.0,30.0,0')
    sta66 = net.addStation('sta66', ip='10.0.0.66',
                           position='554.0,111.0,0')
    sta67 = net.addStation('sta67', ip='10.0.0.67',
                           position='625.0,109.0,0')
    sta68 = net.addStation('sta68', ip='10.0.0.68',
                           position='633.0,32.0,0')
    sta69 = net.addStation('sta69', ip='10.0.0.69',
                           position='807.0,122.0,0')
    sta70 = net.addStation('sta70', ip='10.0.0.70',
                           position='890.0,189.0,0')
    sta71 = net.addStation('sta71', ip='10.0.0.71',
                           position='493.0,444.0,0')
    sta72 = net.addStation('sta72', ip='10.0.0.72',
                           position='541.0,507.0,0')
    sta73 = net.addStation('sta73', ip='10.0.0.73',
                           position='561.0,411.0,0')
    sta74 = net.addStation('sta74', ip='10.0.0.74',
                           position='618.0,372.0,0')
    sta75 = net.addStation('sta75', ip='10.0.0.75',
                           position='601.0,509.0,0')
    sta76 = net.addStation('sta76', ip='10.0.0.76',
                           position='635.0,582.0,0')
    sta77 = net.addStation('sta77', ip='10.0.0.77',
                           position='652.0,655.0,0')
    sta78 = net.addStation('sta78', ip='10.0.0.78',
                           position='729.0,581.0,0')
    sta79 = net.addStation('sta79', ip='10.0.0.79',
                           position='706.0,514.0,0')
    sta80 = net.addStation('sta80', ip='10.0.0.80',
                           position='715.0,426.0,0')
    sta81 = net.addStation('sta81', ip='10.0.0.81',
                           position='995.0,460.0,0')
    sta82 = net.addStation('sta82', ip='10.0.0.82',
                           position='1008.0,382.0,0')
    sta83 = net.addStation('sta83', ip='10.0.0.83',
                           position='1061.0,414.0,0')
    sta84 = net.addStation('sta84', ip='10.0.0.84',
                           position='1069.0,487.0,0')
    sta85 = net.addStation('sta85', ip='10.0.0.85',
                           position='1113.0,557.0,0')
    sta86 = net.addStation('sta86', ip='10.0.0.86',
                           position='1185.0,587.0,0')
    sta87 = net.addStation('sta87', ip='10.0.0.87',
                           position='1243.0,607.0,0')
    sta88 = net.addStation('sta88', ip='10.0.0.88',
                           position='1297.0,568.0,0')
    sta89 = net.addStation('sta89', ip='10.0.0.89',
                           position='1351.0,518.0,0')
    sta90 = net.addStation('sta90', ip='10.0.0.90',
                           position='1285.0,478.0,0')
    sta91 = net.addStation('sta91', ip='10.0.0.91',
                           position='63.0,183.0,0')
    sta92 = net.addStation('sta92', ip='10.0.0.92',
                           position='188.0,228.0,0')
    sta93 = net.addStation('sta93', ip='10.0.0.93',
                           position='267.0,169.0,0')
    sta94 = net.addStation('sta94', ip='10.0.0.94',
                           position='356.0,88.0,0')
    sta95 = net.addStation('sta95', ip='10.0.0.95',
                           position='290.0,53.0,0')
    sta96 = net.addStation('sta96', ip='10.0.0.96',
                           position='162.0,35.0,0')
    sta97 = net.addStation('sta97', ip='10.0.0.97',
                           position='51.0,50.0,0')
    sta98 = net.addStation('sta98', ip='10.0.0.98',
                           position='90.0,127.0,0')
    sta99 = net.addStation('sta99', ip='10.0.0.99',
                           position='115.0,239.0,0')
    sta100 = net.addStation('sta100', ip='10.0.0.100',
                           position='151.0,179.0,0')

    info("*** Configuring Propagation Model\n")
    net.setPropagationModel(model="logDistance", exp=3)

    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    info( '*** Add links\n')
    h1s1 = {'bw':100}
    net.addLink(h1, s1, cls=TCLink , **h1s1)
    net.addLink(h2, s1)
    s1s2_1 = {'bw':10}
    s1s2_2 = {'bw':10}
    net.addLink(s1, s2, cls=TCLink , **s1s2_1)
    net.addLink(s1, s2, cls=TCLink , **s1s2_2)
    s2s3 = {'bw':100}
    net.addLink(s2, s3, cls=TCLink , **s2s3)
    s3h3 = {'bw':100}
    net.addLink(s3, h3, cls=TCLink , **s3h3)
    s3h4 = {'bw':100}
    net.addLink(s3, h4, cls=TCLink , **s3h4)

    s3ap1 = {'bw':100}
    s3ap2 = {'bw':100}
    s3ap3 = {'bw':100}
    s3ap4 = {'bw':100}
    s3ap5 = {'bw':100}
    s3ap6 = {'bw':100}
    s3ap7 = {'bw':100}
    s3ap8 = {'bw':100}
    s3ap9 = {'bw':100}
    s3ap10 = {'bw':100}

    net.addLink(ap1, s3, **s3ap1)
    net.addLink(ap2, s3, **s3ap2)
    net.addLink(ap3, s3, **s3ap3)
    net.addLink(ap4, s3, **s3ap4)
    net.addLink(ap5, s3, **s3ap5)
    net.addLink(ap6, s3, **s3ap6)
    net.addLink(ap7, s3, **s3ap7)
    net.addLink(ap8, s3, **s3ap8)
    net.addLink(ap9, s3, **s3ap9)
    net.addLink(ap10, s3, **s3ap10)

    net.plotGraph(max_x=2000, max_y=1500)

    info( '*** Starting network\n')
    net.build()
    info( '*** Starting controllers\n')
    for controller in net.controllers:
        controller.start()

    info( '*** Starting switches/APs\n')
    net.get('ap1').start([c1])
    net.get('ap2').start([c1])
    net.get('ap3').start([c1])
    net.get('ap4').start([c1])
    net.get('ap5').start([c1])
    net.get('ap6').start([c1])
    net.get('ap7').start([c1])
    net.get('ap8').start([c1])
    net.get('ap9').start([c1])
    net.get('ap10').start([c1])
    net.get('s3').start([c1])
    net.get('s2').start([c0])
    net.get('s1').start([c0])

    info( '*** Post configure nodes\n')
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
        clientPort += 1
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
    for h, line in monitorFiles(outfiles, time+12, timeoutms=100):
        if h:
            info( '%s: %s\n' % (h.name, line) )
            if opts.outputFile:
                print( '%s: %s\n' % (h.name, line) )
                    
    for h in hosts:
        if h.name == 'h1' or h.name == 'h2':
            if bash:
                continue
        h.cmd('kill %iperf')

    if opts.bash:
        CLI_wifi(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    opts, args = parseOptions()
    testWifiSDNNetwork(opts)

