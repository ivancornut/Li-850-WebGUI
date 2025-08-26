from nicegui import ui
import serial
import time
import serial.tools.list_ports
import threading
import re
import pandas as pd
import sys

class Li_850_client():
    def __init__(self, port=None, baudrate=9600,timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection = None
        self.is_reading = False
        self.read_thread = None
        self.new_dataframe = True
        self.data_frame = None
        self.filename = None
        self.filename_exists = False
    
    def list_available_ports(self):
        """List all available serial ports"""
        ports = serial.tools.list_ports.comports()
        available_ports = []
        for port in ports:
            available_ports.append({'device': port.device,'name': port.name,'description': port.description})
        return available_ports

    def connect(self, port=None):
        if port:
            self.port = port
        if not self.port:
            raise ValueError("No port specified in this function or init")
        try:
            self.serial_connection = serial.Serial(port=self.port,baudrate=self.baudrate,timeout=self.timeout)
            print(f"Connected to {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect to {self.port}: {e}")
            return False

    def read_line(self):
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Serial port not connected")
            return None
        try:
            if self.serial_connection.in_waiting > 0:
                line = self.serial_connection.readline().decode('utf-8').strip()
                return line
        except Exception as e:
            print(f"Error reading from serial port: {e}")
        return None
    
    def disconnect(self):
        """Disconnect from the serial port"""
        self.stop_reading()
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print(f"Disconnected from {self.port}")

    def _continuous_read(self):
        """Internal method for continuous reading in a separate thread"""
        while self.is_reading and self.serial_connection and self.serial_connection.is_open:
            try:
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8').strip()
                    if line:
                        #print(f"Received: {line}")
                        print(self.extract_co2_h2o(line))
                        self.save_data_in_dataframe(values = self.extract_co2_h2o(line), finished = False)
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
            except Exception as e:
                print(f"Error in continuous read: {e}")
                break
    
    def start_continuous_reading(self):
        """Start reading continuously in a separate thread"""
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Serial port not connected")
            return False
            
        if self.is_reading:
            print("Already reading continuously")
            return False
        self.start_time = time.time()    
        self.is_reading = True
        self.read_thread = threading.Thread(target=self._continuous_read, daemon=True)
        self.read_thread.start()
        print("Started continuous reading")
        return True
    
    def stop_reading(self):
        """Stop continuous reading"""
        if self.is_reading:
            self.is_reading = False
            if self.read_thread:
                self.read_thread.join(timeout=10000)
            self.save_data_in_dataframe(finished = True)
            print("Stopped continuous reading")
    
    def extract_co2_h2o(self,xml_data):
        """
        Extract CO2 and H2O values from XML data, excluding those inside <raw> tags.
        
        Args:
            xml_data (str): XML string containing sensor data
            
        Returns:
            tuple: (co2_value, h2o_value) as floats
        """
        # Remove the <raw>...</raw> section to avoid extracting values from it
        cleaned_data = re.sub(r'<raw>.*?</raw>', '', xml_data, flags=re.DOTALL)
        
        # Extract CO2 value
        co2_match = re.search(r'<co2>(.*?)</co2>', cleaned_data)
        co2_value = float(co2_match.group(1)) if co2_match else None
        
        # Extract H2O value  
        h2o_match = re.search(r'<h2o>(.*?)</h2o>', cleaned_data)
        h2o_value = float(h2o_match.group(1)) if h2o_match else None
    
        return (co2_value, h2o_value)

    def save_data_in_dataframe(self,values=None,finished = False):
        if finished == True:
            if self.data_frame is not None:
                self.data_frame.to_csv("data/"+self.filename,index_label='rcrd_nb')
                self.data_frame = None
                self.filename_exists=False
                self.filename = None
                return None
            else:
                return None
        if values[0] is not None and values[1] is not None:
            if self.new_dataframe:
                dict_values = {"elapsed_time": time.time()-self.start_time,"CO2_ppm":values[0], "H2O":values[1]}
                self.data_frame = pd.DataFrame(dict_values,index = [0])
                self.record_number = 1
            else:
                dict_values = {"elapsed_time": time.time()-self.start_time,"CO2_ppm":values[0], "H2O":values[1]}
                self.data_frame = pd.concat([self.data_frame,pd.DataFrame(dict_values, index =[self.record_number])])
                self.data_frame.to_csv("data/"+self.filename,index_label='rcrd_nb')
                self.record_number = self.record_number+1
            self.new_dataframe = False

reader = Li_850_client(port = "/dev/ttyACM0", baudrate=9600, timeout=1)
    
def connect_device():
    reader.connect()
    connect_button.enabled = False
    disconnect_button.enabled = True
    if reader.filename_exists == True:
        start_button.enabled = True
    else:
        start_button.enabled = False
def disconnect_device():
    reader.disconnect()
    disconnect_button.enabled = False
    disconnect_button.text = "Disconnect"
    connect_button.enabled = True
    line_updates.active = False
def start_reading():
    reader.start_continuous_reading()
    disconnect_button.enabled = True
    disconnect_button.text = "Disconnect and stop"
    connect_button.enabled = False
    start_button.enabled = False
    line_updates.active = True
def get_values():
    if filename_input.value is None:
        reader.filename = "fake_data.csv"
    else:
        reader.filename = filename_input.value
    reader.filename_exists = True

def update_line_plot():
    if reader.data_frame is not None:
        line_plot.figure['data'][0]['x'] = reader.data_frame['elapsed_time'].tolist()
        line_plot.figure['data'][0]['y'] = reader.data_frame['CO2_ppm'].tolist()
        line_plot.update_figure(line_plot.figure)


filename_input = ui.input('Enter filename', placeholder='filename') 
ui.button('Save filename', on_click=get_values)
connect_button = ui.button("Connect",on_click=connect_device)
disconnect_button = ui.button("Disconnect",on_click=disconnect_device)
start_button = ui.button("Start Measurements", on_click=start_reading)
disconnect_button.enabled = False
start_button.enabled = False

line_updates = ui.timer(5, update_line_plot, active=False)
line_plot = plot = ui.plotly({'data': [{'x': [0],'y': [0],'type': 'scatter','mode': 'lines+markers','name': 'data'}],'layout': {'title': 'CO2 concentration'}})

try:
    ui.run()     
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    reader.disconnect()
