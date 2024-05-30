import time
import psutil
import argparse

def terminate_tor_process(ports):
    """
    Finds the Tor process and stops it
    :param ports: the port numbers on which Tor is listening
    """
    # Iterate on the processes
    for proc in psutil.process_iter(['pid', 'name']):
        # Check if process name is tor
        if proc.info['name'] == 'tor':

            # Iterate over connections for this process
            for conn in proc.connections(kind='inet'):

                # Check if the connection is listening on the specified port
                if conn.laddr.port in ports:
                    print(f"Terminating Tor process with PID {proc.info['pid']} listening on port {conn.laddr.port}")
                    proc.terminate()

                    # Give the process some time to clean up
                    time.sleep(5)
                    if proc.is_running():
                        print(f"Process did not terminate in time, force killing the process.")
                        proc.kill()
                    return

    print(f"No Tor process found listening on ports {ports}")

if __name__ == "__main__":
    # Create an argument parser
    parser = argparse.ArgumentParser(description="Manage seeds and cookies")

    # Add arguments
    parser.add_argument("port1", help="The port number on which Tor control port are listening")
    parser.add_argument("port2", help="The port number on which Tor socks port are listening")

    # Parse the command-line arguments
    args = parser.parse_args()

    if args.port1 and args.port2:
        port1 = int(args.port1)
        port2 = int(args.port2)
        ports = [port1, port2]
        terminate_tor_process(ports)
    else:
        print("Please provide the ports number on which Tor are listening")
        raise TypeError("Missing one or more required arguments")