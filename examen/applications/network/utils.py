import paramiko, getpass, time, netifaces, re, os
from paramiko import SSHClient
from graphviz import Digraph
from orderedset import OrderedSet
 
path = os.getcwd() + '/static/img/'
max_buffer = 65535
wait = 2

def clear_buffer(connection):
    if connection.recv_ready():
        return connection.recv(max_buffer)

""" 
This function retrieves the prompt of the neighbor router of an specific one 
"""
def findNeighbour(address, user, password):
    connection = SSHClient()
    connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connection.connect(address, username=user, password=password, look_for_keys=False, allow_agent=False)
    new_connection = connection.invoke_shell()
    output = clear_buffer(new_connection)
    
    new_connection.send("terminal length 0\n")
    time.sleep(wait)
    new_connection.send("sh running-config brief | include hostname\n")
    time.sleep(3)
    name = new_connection.recv(max_buffer).decode('utf-8')
    router = re.findall('hostname (R[0-9])', name)[0]
    # Closing the ssh connection
    new_connection.close()
    return router

def searhTopology():
    # Retrieving the local gateway
    gateway = netifaces.gateways()['default'][2][0]
    # Credentials
    username = 'admin'
    password = 'firulais'
    # Commands
    route_table       = 'show ip route\n'
    router_id         = 'show ip ospf interface\n'
    router_interfaces = 'show ip ospf interface brief\n'
    # Variables
    routers = {}
    routers_information = {}
    neighbours = {}
    devices = [gateway]

    for device in devices:
        connection = SSHClient()
        connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connection.connect(device, username=username, password=password, look_for_keys=False, allow_agent=False)

        new_connection = connection.invoke_shell()
        output = clear_buffer(new_connection)

        new_connection.send("terminal length 0\n")
        time.sleep(wait)
        new_connection.send("sh running-config brief | include hostname\n\n")
        time.sleep(3)
        name = new_connection.recv(max_buffer).decode('utf-8')
        router = re.findall('hostname (R[0-9])', name)[0]
        # If the router is already in the list of routers, close the ssh connection
        if router in routers:
            print(f'The router {router} is already visited')
            new_connection.close()
            continue

        # Retrieving the Router ID
        new_connection.send(router_id)
        time.sleep(wait)
        info_router_id = new_connection.recv(max_buffer).decode('utf-8')
        r_id =  re.findall( 'Router ID ([0-9.]+)', info_router_id )[0]
        print(f'{router} ID: {r_id}')
        # Retrieving all the Router FastEthernet Interfaces
        new_connection.send(router_interfaces)
        time.sleep(wait)
        info_router_interfaces = new_connection.recv(max_buffer).decode('utf-8')
        interfaces      = re.findall( 'Fa(\S+)', info_router_interfaces )
        ip_interfaces   = re.findall( '([0-9.]+)/[2-9]+', info_router_interfaces )
        mask_interfaces = [ mask for mask in re.findall( '/([0-9]+)', info_router_interfaces) if int(mask)>=8 ]
        # Retrieving the routing table
        new_connection.send(route_table)
        time.sleep(wait)
        table = new_connection.recv(max_buffer).decode('utf-8')
        addresses = list(OrderedSet( re.findall( 'via ([0-9.]+),', table ) ))
        # Adding new devices to search
        devices.extend(addresses)
        routers[router] = addresses
        # Deleting duplicate addresses
        list( OrderedSet(devices) )
        # Closing the ssh connection
        new_connection.close()
        print(f'Finding all the routers that are directly connected to this router {router}')
        neighbours[router] = [ findNeighbour(address, username, password) for address in routers[router] ]
        # Gathering all the obtained data 
        data_interfaces = dict()
        for interface, address, mask in zip(interfaces, ip_interfaces, mask_interfaces):
            data_interfaces['FastEthernet'+interface] = {
                'ip'   : address,
                'mask' : '255.255.255.0' if mask == '24' else '255.255.255.252' 
            }

        routers_information[router] = {
            'neighbours_addresses': routers[router],
            'neighbours_hostname' : neighbours[router],
            'router_id'           : r_id,
            'router_hostname'     : router,
            'router_interfaces'   : data_interfaces
        }
    return routers_information

def registerSSHUser(username, password, router_address, flag = ''):
    default_user = 'admin'
    default_pass = 'firulais'
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
    for router in routers.keys():
        diagram.attr('node', shape='doublecircle', fillcolor='blue:cyan', style='filled')        
        diagram.node(router)
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