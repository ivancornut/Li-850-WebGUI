# Li-850-WebGUI
A webgui for the Li-850 IRGA to be used in the field for soil and trunk respiration with a raspberry pi 3 and smartphone.
The aim is to make measurement as simple as possible while guaranteeing high data quality and traceability. The code is compatible with an associated SHT45 sensor for aitr temperature and relative humidity to log local conditions during your measurements.

You can:
- Enter a user so data is traceable
- Connect to a Li-850 using the USB serial port of the raspberry Pi 3 
- Name file with automatic datetime suffix
- Start a measurement
- Stop a measurement (with automatic download of the generated csv to your phone)

## Installation
First install necessary python modules on the raspberry pi:
```
sudo apt install python-dev
```
Create a python virtual env: 
```
python -m venv my_env
```
Then activate and install the libraries:
```
source my_env/bin/activate
pip install pandas nicegui pyserial
```
Download this repository:
```
git clone https://github.com/ivancornut/Li-850-WebGUI
```
Enter the directory:
```
cd Li-850-WebGUI
```
Create a data directory:
```
mkdir data
```

## Automatic startup on launch
Soon ...

## Graphical interface
<img width="436" height="968" alt="image" src="https://github.com/user-attachments/assets/7f92d5a8-94ea-448f-bf75-61c71066104a" />

