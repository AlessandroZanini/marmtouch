from netifaces import interfaces, ifaddresses, AF_INET
def get_network_interfaces():
    all_addresses = {}
    for interface_name in interfaces():
        addresses = [
            interface['addr'] 
            for interface in ifaddresses(interface_name).setdefault(AF_INET, [{'addr':'No IP addr'}] )
        ]
        all_addresses[interface_name] = ' '.join(addresses)
    return all_addresses