import time
import socket

def get_ssid():
    """Get the current WiFi SSID"""
    try:
        # Try using iwgetid command
        result = subprocess.check_output(['iwgetid', '-r'], stderr=subprocess.DEVNULL)
        ssid = result.decode('utf-8').strip()
        return ssid if ssid else "Not Connected"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Not Connected"

def get_local_ip():
    """Get the local IP address"""
    try:
        # Create a socket connection to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to an external address (doesn't actually send data)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "No Connection"
        
 def main():    
    try:
        while True:
            # Get current network information
            ssid = get_ssid()
            local_ip = get_local_ip()
            print(ssid)
            print(local_ip)
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nExiting...")
        device.clear()

if __name__ == "__main__":
    main()
