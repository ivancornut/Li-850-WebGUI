from nicegui import ui
import serial
import time
import serial.tools.list_ports
import threading
import re
import pandas as pd
from datetime import datetime

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
        self.recording = False
        self.CO2_conc = None
        self.is_connected = False
        self.user = "None"
    
    def list_available_ports(self):
        """List all available serial ports"""
        ports = serial.tools.list_ports.comports()
        available_ports = []
        for port in ports:
            available_ports.append({'device': port.device,'name': port.name,'description': port.description})
        return available_ports
    
    def list_available_ports_in_list(self):
        """List all available serial ports"""
        ports = serial.tools.list_ports.comports()
        available_ports = []
        for port in ports:
            if "/dev/ttyS" not in port.device:
                available_ports.append(port.device)
        return available_ports

    def connect(self, port=None):
        if port:
            self.port = port
        if not self.port:
            raise ValueError("No port specified in this function or init")
        try:
            self.serial_connection = serial.Serial(port=self.port,baudrate=self.baudrate,timeout=self.timeout)
            print(f"Connected to {self.port} at {self.baudrate} baud")
            self.is_connected = True
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
    
    def stop_recording(self):
        self.recording = False
    
    def disconnect(self):
        """Disconnect from the serial port"""
        self.stop_reading()
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print(f"Disconnected from {self.port}")
        self.CO2_conc = None
        self.is_connected = False

    def _continuous_read(self):
        """Internal method for continuous reading in a separate thread"""
        while self.is_reading and self.serial_connection and self.serial_connection.is_open:
            try:
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8').strip()
                    if line:
                        #print(f"Received: {line}")
                        self.CO2_conc = self.extract_co2_h2o(line)[0]
                        if self.recording:
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
        self.is_reading = True
        self.serial_connection.reset_input_buffer() # flush the serial input to avoid getting any old values
        self.read_thread = threading.Thread(target=self._continuous_read, daemon=True)
        self.read_thread.start()
        print("Started continuous reading")
        return True
    
    def update_full_filename(self):
        now = datetime.now()
        datetime_string = f"_{now.year:04d}_{now.month:02d}_{now.day:02d}_{now.hour:02d}_{now.minute:02d}.csv"
        self.full_filename = self.filename+datetime_string

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

        # Extract cell pressure
        press_match = re.search(r'<cellpres>(.*?)</cellpres>', cleaned_data)
        press_value = float(press_match.group(1)) if press_match else None

        # Extract cell temperature
        temp_match = re.search(r'<celltemp>(.*?)</celltemp', cleaned_data)
        temp_value = float(temp_match.group(1)) if temp_match else None

        #print(co2_value,h2o_value,press_value,temp_value)
        return (co2_value, h2o_value, press_value, temp_value)

    def save_data_in_dataframe(self,values=None,finished = False):
        if finished == True:
            if self.data_frame is not None:
                self.data_frame.to_csv("data/"+self.full_filename,index_label='rcrd_nb')
                self.data_frame = None
                self.filename_exists=False
                #self.filename = None
                self.record_number = 1
                self.new_dataframe = True
                return None
            else:
                return None
        if values[0] is not None and values[1] is not None:
            if self.new_dataframe:
                self.start_time = time.time()
                dict_values = {"elapsed_time": time.time()-self.start_time,"CO2_ppm":values[0], "H2O":values[1],
                               "Cell_pressure":values[2],"Cell_temp":values[3],"user":self.user}
                self.data_frame = pd.DataFrame(dict_values,index = [0])
                self.record_number = 1
            else:
                dict_values = {"elapsed_time": time.time()-self.start_time,"CO2_ppm":values[0], "H2O":values[1],
                               "Cell_pressure":values[2],"Cell_temp":values[3],"user":self.user}
                self.data_frame = pd.concat([self.data_frame,pd.DataFrame(dict_values, index =[self.record_number])])
                self.data_frame.to_csv("data/"+self.full_filename,index_label='rcrd_nb')
                self.record_number = self.record_number+1
            self.new_dataframe = False

reader = Li_850_client(port = "/dev/ttyACM0", baudrate=9600, timeout=1)
    
def connect_device():
    print(port_select.value)
    if port_select.value is not None:
        reader.connect(port=port_select.value)
        if reader.is_connected:
            reader.start_continuous_reading()
            connect_button.enabled = False
            disconnect_button.enabled = True
            connection_label.set_text("Is connected to "+port_select.value)
            value_updates.active = True
            if reader.filename_exists == True:
                start_button.enabled = True
            else:
                start_button.enabled = False
            measure_expansion.open()
        else:
            connection_label.set_text("Unable to connect to port "+port_select.value+", try again")
    else:
        connection_label.set_text("No port selected, try again")

def disconnect_device():
    start_button.enabled = False
    CO2_label.set_text("")
    reader.disconnect()
    disconnect_button.enabled = False
    disconnect_button.text = "Disconnect"
    connect_button.enabled = True
    line_updates.active = False
    connection_label.set_text("Not connected")

def start_reading():
    reader.recording = True
    disconnect_button.enabled = False
    CO2_label.set_text("")
    value_updates.active  =False
    #disconnect_button.text = "Disconnect and stop"
    connect_button.enabled = False
    start_button.enabled = False
    line_updates.active = True
    stop_button.enabled = True
    user_save_button.enabled = False
    reader.start_continuous_reading()
    connect_expansion.close()
    

def stop_reading():
    reader.recording = False
    disconnect_button.enabled = True
    connect_button.enabled = False
    start_button.enabled = True
    user_save_button.enabled = True
    stop_button.enabled = False
    reader.stop_reading()
    reader.update_full_filename()
    filename_label.text = "Filename updated for next: "+ reader.full_filename
    connect_expansion.open()

def update_CO2_value():
    if reader.is_connected:
        #print(reader.CO2_conc)
        if reader.CO2_conc is not None:
            CO2_label.set_text(f"Current CO2: {reader.CO2_conc:.1f} ppm")

def get_values():
    if filename_input.value is None:
        reader.filename = "fake_data.csv"
    else:
        reader.filename = filename_input.value
    reader.filename_exists = True
    reader.update_full_filename()
    filename_label.text = "Current filename: "+ reader.full_filename
    if reader.is_connected:
        start_button.enabled = True

def update_line_plot():
    if reader.data_frame is not None:
        line_plot.figure['data'][0]['x'] = reader.data_frame['elapsed_time'].tolist()
        line_plot.figure['data'][0]['y'] = reader.data_frame['CO2_ppm'].tolist()
        line_plot.update_figure(line_plot.figure)

def refresh_ports():
    port_select.set_options(reader.list_available_ports_in_list())

def save_user():
    print(user_input.value)
    if user_input.value is not None and user_input.value != "":
        reader.user = user_input.value
        connect_button.enabled = True
        connect_expansion.open()
        user_expansion.close()

ui.html('<h1>Li-850 GUI interface<h1>').style(' font-weight: bold; font-size: 3rem')
with ui.expansion('User').style('color: #888; font-weight: bold; font-size: 2rem') as user_expansion:
    with ui.row():
        user_input = ui.input("Enter User", placeholder='User')
        user_save_button = ui.button('Save User', on_click=save_user)

with ui.expansion('Connection').style('color: #888; font-weight: bold; font-size: 2rem') as connect_expansion:
    with ui.card():
        ui.label("The ports should be:").style('color: #888; font-size: 0.75rem')
        ui.label(" - On linux: /dev/ttyACM...     - On Windows: COM...").style('color: #888; font-size: 0.75rem')
        with ui.row():
            port_select = ui.select(options=reader.list_available_ports_in_list(), with_input=True)
            refresh_button = ui.button("Refresh available ports",on_click=refresh_ports)
        with ui.row():
            connect_button = ui.button("Connect to Li-850",on_click=connect_device)
            disconnect_button = ui.button("Disconnect",on_click=disconnect_device)
        with ui.row():
            connection_label = ui.label("Not Connected").style('color: #888; font-weight: bold; font-size: 1.2rem')
        CO2_label = ui.label("").style('color: #099427; font-weight: bold; font-size: 1.5rem')

with ui.expansion('Measurement').style('color: #888; font-weight: bold; font-size: 2rem') as measure_expansion:
    with ui.card():
        with ui.row(): 
            filename_input = ui.input('Enter filename', placeholder='filename').props("size=30").style('background-color: #f8f8f8;font-size: 1.2rem')
            ui.button('Save filename', on_click=get_values)
        filename_label = ui.label('No filename yet').style('color: #888; font-weight: bold; font-size: 1.5rem')
        with ui.row():
            start_button = ui.button("Start Measurement", on_click=start_reading, color = '#099427', icon='start').style("color:black")
            stop_button = ui.button("Stop Measurement", on_click=stop_reading, color  ='#910617', icon='stop').style("color:black")
        line_plot = ui.plotly({'data': [{'x': [0],'y': [0],'type': 'scatter','mode': 'lines+markers','name': 'data'}],
                                    'layout': {'title': 'Real time data','xaxis': {'title':{'text':'Time (s)'} },
                                                'yaxis': {'title':{'text':'CO2 concentration (ppm)'} }}})

disconnect_button.enabled = False
start_button.enabled = False
stop_button.enabled = False
connect_button.enabled = False
user_expansion.open()

value_updates = ui.timer(5, update_CO2_value, active=False)
line_updates = ui.timer(5, update_line_plot, active=False)


try:
    ui.run()     
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    reader.disconnect()
