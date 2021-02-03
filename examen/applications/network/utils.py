import paramiko, getpass, time, netifaces, re, os, pygal
from pexpect import pxssh
from django.core.files import File
from graphviz import Digraph
from orderedset import OrderedSet
from paramiko import SSHClient
from .models import Interface

 
path = os.getcwd() + '/static/img/'

max_buffer = 65535
wait = 2

def clear_buffer(connection):
    if connection.recv_ready():
        return connection.recv(max_buffer)

def ssh_login( address, username, password, time=10 ):
    try:
        session = pxssh.pxssh() 
        session.login( address, username, password, auto_prompt_reset=False, login_timeout=time )
        return session
    
    except pxssh.ExceptionPxssh as e:
        print("pxssh failed on login.")
        print(e)

def make_ssh_conexion( address, ssh_user='cisco', ssh_pass='cisco' ):
    time = 10
    session = ssh_login( address, ssh_user, ssh_pass )
    while session == None:
        time+=2
        print('Trying again ...')
        session = ssh_login( address, ssh_user, ssh_pass, time )
    print('ssh conexion stablished successfully')
    return session

def updateHostNames( session, hostname ):
    commands = [
        'configure terminal',
        f'hostname {hostname}',
        'exit'
    ]

    for command in commands:
        session.sendline(command)
        session.expect('#')
    
    # Closing the ssh connection
    session.logout()
    print('The interface was updated in GNS3')

def getNetworkID(address):
    network = address.split('.')
    last_byte =  int(network[-1])
    # Even
    if last_byte%2 == 0:
        network[-1] = str(last_byte-2)
    # Odd
    else:
        network[-1] = str(last_byte-1)
    
    return '.'.join(network)

""" 
This function retrieves the prompt of all of the router neighbours according to the neighbour addresses list
"""
def findHostNames( routers ):
    router_interfaces = { }
    for router in routers:
        interfacesFA = routers[router].get('router_interfaces')
        router_interfaces[router] = [ interfacesFA[interfaceFA].get('ip') for interfaceFA in interfacesFA ]

    for device in routers:
        hostnames = []
        # Retrieving all the neighbours addresses for this device
        addresses = routers[device].get('neighbours_addresses')
        for address in addresses:
            for router, interfaces in router_interfaces.items():
                # If the router is different from the target device
                if device != router:
                    if address in interfaces:
                        hostnames.append(router)
                        break
        routers[device]['neighbours_hostname'] = hostnames

def searchTopology():
    # Retrieving the local gateway
    gateway = netifaces.gateways()['default'][2][0]
    # Credentials
    username = 'cisco'
    password = 'cisco'
    # Commands
    route_table       = 'show ip route'
    router_id         = 'show ip ospf interface | include Router ID'
    router_interfaces = 'show ip ospf interface brief'
    router_hostname   = 'sh running-config brief | include hostname'
    router_LAN        = 'sh ip route | include /24 is directly'
    # Variables
    routers         = dict()
    # neighbours      = dict()
    routers_information = dict()
    devices = [gateway]
    routers_interfaces_ip = []

    for device in devices:
        session = make_ssh_conexion( device, username, password)
        # Retrieving the hostname
        session.sendline(router_hostname)
        session.expect('#')
        # print(f'Comando anterior al prompt: {session.before}')
        hostname = session.before.decode('utf-8')
        router = re.findall('hostname (R[0-9])', hostname)[0]
        # If the router is already in the list of routers, close the ssh connection
        if router in routers:
            print(f'The router {router} is already visited')
            session.logout()
            continue
        print(f'Router hostname: {router}')
        # Retrieving the Router ID
        session.PROMPT = b'1' # Reiniciamos el prompt
        session.sendline(router_id)
        session.expect('#')
        #print(f'Comando anterior al prompt: {session.before}')
        _id = session.before.decode('utf-8')
        r_id =  re.findall( 'Router ID ([0-9.]+)', _id )[0]
        print(f'{router} ID: {r_id}')
        # Retrieving the Router Information
        session.PROMPT = b'1' # Reiniciamos el prompt
        session.sendline(router_interfaces)
        session.expect('#')
        print(f'Getting all the interfaces for the router: {router}')
        #print(f'Comando anterior al prompt: {session.before}')
        info_router_interfaces = session.before.decode('utf-8')
        interfaces      = re.findall( 'Fa(\S+)', info_router_interfaces )
        ip_interfaces   = re.findall( '([0-9.]+)/[2-9]+', info_router_interfaces )
        mask_interfaces = [ mask for mask in re.findall( '/([0-9]+)', info_router_interfaces) if int(mask)>=8 ]
        
        # Retreiving the routing table
        session.PROMPT = b'1' # Reiniciamos el prompt
        session.sendline(route_table)
        session.expect('#')
        print(f'Getting the route table for the router: {router}')
        #print(f'Comando anterior al prompt: {session.before}')
        table = session.before.decode('utf-8')
        addresses = list( OrderedSet( re.findall( 'via ([0-9.]+),', table ) ) )
        routers[router] = addresses
        # Retreiving the Router LAN
        session.PROMPT = b'1' # Reiniciamos el prompt
        session.sendline(router_LAN)
        session.expect('#')
        print(f'Getting the LAN for the router: {router}')
        #print(f'Comando anterior al prompt: {session.before}')
        command_lan = session.before.decode('utf-8')
        lan = re.findall('([0-9.]+)/24', command_lan)[0]
        # Adding new devices to search
        routers_interfaces_ip.extend( ip_interfaces )
        # Deleting duplicate and already visited addresses
        devices.extend( add for add in addresses if add not in routers_interfaces_ip )
        # Closing the ssh connection
        session.logout()

        # Gathering all the obtained data 
        data_interfaces = dict()

        for interface, address, mask in zip(interfaces, ip_interfaces, mask_interfaces):
            data_interfaces[ 'Fa'+ interface ] = {
                'ip'   : address,
                'mask' : '255.255.255.0' if mask == '24' else '255.255.255.252' 
            }

        routers_information[router] = {
            'neighbours_addresses': routers[router],
            'router_id'           : r_id,
            'router_LAN'          : lan,
            'router_hostname'     : router,
            'router_interfaces'   : data_interfaces
        }

    print('Finding all the hostnames for every single Router')
    findHostNames( routers_information )
    return routers_information

def registerSSHUser(username, password, router_address, flag = ''):
    default_user = 'cisco'
    default_pass = 'cisco'
    commands = ['enable\n', 'config t\n', f'{flag} username {username} privilege 15 password {password}\n', 'end\n']
    connection = SSHClient()
    connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connection.connect(router_address, username=default_user, password=default_pass, look_for_keys=False, allow_agent=False)
    new_connection = connection.invoke_shell()
    output = clear_buffer(new_connection)
    time.sleep(wait)
    for command in commands:
        new_connection.send(command)
        time.sleep(wait)
    # Closing the ssh connection    
    new_connection.close()

def drawTopologyDiagram(routers):
    diagram = Digraph (comment='Network')
    for router in routers:
        diagram.attr('node', shape='doublecircle', fillcolor='blue:cyan', style='filled')        
        diagram.node(router)
        # Adding the LAN for this router
        lan = routers[router].get('router_LAN')
        diagram.attr('node', shape='box', fillcolor='red:pink', style='filled')
        # Creating the edge with the Router and their LAN
        diagram.edge( router, lan, label = 'LAN' )
        
        neighbours_addresses = routers[router].get('neighbours_addresses')
        neighbours_hostnames = routers[router].get('neighbours_hostname')
        # Obtaining all the interfaces
        interfaces_and_networks = []
        # Router interfaces
        dict_interfaces = routers[router].get('router_interfaces')
        # Looking in every single interface of the router
        for interface in dict_interfaces.keys():
            int_ip   = dict_interfaces[interface].get('ip') 
            int_mask = '24' if dict_interfaces[interface].get('mask') == '255.255.255.0' else '30'
            int_name = 'Fa'+ interface[-3] + interface[-2] + interface[-1] 
            # Looking in every single address of the router's neighbour a match with the network id
            for address, hostname in zip(neighbours_addresses,neighbours_hostnames):
                if getNetworkID(address) == getNetworkID(int_ip):
                    interfaces_and_networks.append( ( int_name, int_ip.split('.')[-1], int_mask, getNetworkID(address), hostname, router ) )                  
        
        for info in interfaces_and_networks:
            # Creating the node 
            diagram.attr('node', shape='box', fillcolor='red:yellow', style='filled')
            # Retrieveing the network id
            diagram.node( info[3] )
            # Creating the first edge
            diagram.edge( info[5], info[3] , label = info[0]+'\n'+'.'+info[1]+'/'+info[2] )
            # Creating the node for the neighbour
            diagram.attr('node', shape='doublecircle', fillcolor='blue:cyan', style='filled')        
            diagram.node( info[4] )
            # Creating the second edge
            diagram.edge( info[3], info[4] )

    diagram.render(filename=f'{path}/topology', format='png')
    

def createPlot(title, times, inOC_list, inPA_list, outOC_list, outPA_list, file_name):
    line_chart = pygal.Line()
    line_chart.title = title
    line_chart.x_labels = times
    line_chart.add('Octetos de Entrada', inOC_list)
    line_chart.add('Paquetes de Entrada', inPA_list)
    line_chart.add('Octetos de Salida', outOC_list)
    line_chart.add('Paquetes de Salida', outPA_list)
    file_path = f'{path}{file_name}.svg'
    line_chart.render_to_file(file_path)
    return (1, file_path)



def createPlots():
    # Retrieving only the fields in_oct, in_uPackets, out_oct, out_uPackets for all the interfaces in the database
        query_result1 = Interface.objects.values_list('in_oct', 'in_uPackets', 'out_oct', 'out_uPackets')
        # When you retrieve more than one field the following function returns a list of tuples
        query_result2 = Interface.objects.values_list('name', 'times')
        query_result3 = Interface.objects.values_list('id', flat = True)

        # Creating the Plot
        for tupla1, tupla2, interface_id in zip(query_result1, query_result2, query_result3):
            inOCList  = [ int(number) for number in tupla1[0].rstrip(',').split(',') ] 
            inPAList  = [ int(number) for number in tupla1[1].rstrip(',').split(',') ]
            outOCList = [ int(number) for number in tupla1[2].rstrip(',').split(',') ]
            outPAList = [ int(number) for number in tupla1[3].rstrip(',').split(',') ]
            name, times = tupla2
            file_name = '-'.join(name.split('/'))
            title     = name
            time_list = times.rstrip(',').split(',')
            valid, image_path = createPlot( title, time_list, inOCList, inPAList, outOCList, outPAList, file_name)  
            
            if valid == 1:
                print(f'The plot for the interface: {file_name} was created')
                # Saving the image in the database
                interface = Interface.objects.get(pk=interface_id)
                #print(f'Image Path: {image_path}')
                with open(image_path, 'rb') as f:
                    data = File(f)
                    interface.image.save(f'{file_name}.svg', data, True)
            else:
                print('Something went wrong')
        
        return 1
