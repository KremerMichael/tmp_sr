#!/usr/bin/env python3.9

########################
# IMPORTS
########################
from tabulate import tabulate
import datetime
import json
import serial
import time


########################
# GENERICS
########################
port_linux='/dev/ttyACM0'
port_mac='/dev/tty.usbmodem11101'
ARDUINO = serial.Serial(port=port_linux, baudrate=9600, timeout=.1)


########################
# FUNCTIONS
########################
def write_read(x):
    ARDUINO.write(bytes(x, 'utf-8'))
    time.sleep(0.05)
    data = ARDUINO.readline()
    return data


########################
# SETUP
########################
# Setting up data file
file_raw = open("data_raw.txt","a")
file_washed = open("data_washed.txt","a")

# For automation
auto=False
grid_state = "OFF"
battery_state = "DISCONNECT"

# For washing data
Home0_last = 0
Home1_last = 0
Home2_last = 0
Home3_last = 0
Grid_last = 0
Charge_last = 0
Discharge_last =0

# For battery
battery_Ah = 90 
full = False
charge_list = []


########################
# START
########################
# Waiting for arduino
n=5
for i in range(n):
    print("waiting {}/{}".format(i,n))
    time.sleep(1)


########################
# MAIN LOOP
########################
while True:


    ########################
    # TIMING
    ########################
    # Pause a second
    time.sleep(2)
    # Get datetime for transaction
    now=datetime.datetime.now()
    date_=now.strftime("%m/%d/%Y")
    time_=now.strftime("%H:%M:%S")
    print(now)


    ########################
    # RUNNING MANNUALLY
    ########################
    if not auto:
        tx = input("Enter a number: ") # Taking input from user
        if tx == "auto":
            auto = True


    ########################
    # RUNNING AUTOMATICALLY
    ########################
    else: #in auto mode
        tx = "."
        # Need to turn grid on
        if grid_state == "OFF":
            tx = "gON"
            full = False
        # Need to charge battery
        elif now.hour > 8 and now.hour < 15:
            if full:
                battey_Ah = 90
                if battery_state != "DISCONNECT":
                    tx = "bDISCONNECT"
            elif battery_state != 'CHARGING':
                tx = "bCHARGE"
        # Need to stop discharging battery
        else:
            full = False
            if battery_Ah < 70:
                tx = "bDISCONNECT"
            else:
                if battery_state != "DISCHARGE":
                    tx = "bDISCHARGE"

    

    ########################
    # COMMUNICATE
    ########################
    rx = write_read(tx).decode('utf-8')
    print(rx) # printing the value

    
    ########################
    # INTERPRET DATA
    ########################
    if rx:
        try: # Try-except, arduino drops communication somtimes


            ########################
            # WASHING DATA
            ########################
            # Load json as a dictionary
            rx_dict = json.loads(rx)
            # Wash home data 
            if rx_dict['Home0'] < 0:
                Home0_washed = Home0_last
            else:
                Home0_washed = rx_dict['Home0']
                Home0_last = rx_dict['Home0']
            if rx_dict['Home1'] < 0:
                Home1_washed = Home1_last
            else:
                Home1_washed = rx_dict['Home1']
                Home1_last = rx_dict['Home1']
            if rx_dict['Home2'] < 0:
                Home2_washed = Home2_last
            else:
                Home2_washed = rx_dict['Home2']
                Home2_last = rx_dict['Home2']
            if rx_dict['Home3'] < 0:
                Home3_washed = Home3_last
            else:
                Home3_washed = rx_dict['Home3']
                Home3_last = rx_dict['Home3']
            # Wash power data
            if rx_dict['GRID'] == "OFF":
                Grid_washed = 0
                Grid_last = 0
            elif rx_dict['Grid'] < 0:
                Grid_washed = Grid_last
            else:
                Grid_washed = rx_dict['Grid']
                Grid_last = rx_dict['Grid']
            if rx_dict['BATTERY'] == "DISCONNECT":
                Charge_washed = 0
                Discharge_washed = 0
            elif rx_dict['BATTERY'] == "CHARGE":
                Discharge_washed = 0
                if rx_dict['Charge'] < 0:
                    Charge_washed = Charge_last
                else:
                    Charge_washed = rx_dict['Charge']
                    Charge_last = rx_dict['Charge']
            elif rx_dict['BATTERY'] == "DISCHARGE":
                Chrage_washed = 0
                if rx_dict['Discharge'] < 0:
                    Discharge_washed = Discharge_last
                else:
                    Discharge_washed = rx_dict['Discharge']
                    Discharge_last = rx_dict['Discharge']

            # Calculate solar power
            power_solar = (rx_dict['Home0'] + rx_dict['Home1'] + rx_dict['Home2'] + rx_dict['Home3'] + rx_dict['Charge']) - (rx_dict['Grid'] + rx_dict['Discharge'])
            power_solar_washed = (Home0_washed + Home1_washed + Home2_washed + Home3_washed + Charge_washed) - (Grid_washed + Discharge_washed)



            ########################
            # BATTERY STATE
            ########################
            #if not full:
            if rx_dict['BATTERY'] == 'DISCONNECT':
                # Do nothing
                battery_Ah = battery_Ah
                charge_list = []
            elif rx_dict['BATTERY'] == 'CHARGE':
                if len(charge_list) < 180:
                    charge_list.append(Charge_washed)
                    avg_charge = 1000000
                else:
                    charge_list.pop(0)
                    charge_list.append(Charge_washed)
                    avg_charge = sum(charge_list)/len(charge_list)
                if avg_charge < 1000:
                    battery_Ah = 90
                else:
                    charge_Wh = Charge_washed / (30 * 60 * 1000)
                    charge_Ah = charge_Wh / (rx_dict['Voltage']/1000)
                    battery_Ah = battery_Ah + charge_Ah
            elif rx_dict['BATTERY'] == 'DISCHARGE':
                charge_list = []
                discharge_Wh = Discharge_washed / (30 * 60 * 1000)
                discharge_Ah = discharge_Wh / (rx_dict['Voltage']/1000)
                battery_Ah = battery_Ah - discharge_Ah
            if battery_Ah == 90:
                full = True
            else:
                full = False
    

            # Write to file
            file_raw.write("{},{},{},{},{},{},{},{},{},{},{},{},{}\n".format(date_,time_,rx_dict['Home0'],rx_dict['Home1'],rx_dict['Home2'],rx_dict['Home3'],rx_dict['Grid'],rx_dict['Charge'],rx_dict['Discharge'],power_solar,rx_dict['BATTERY'],rx_dict['GRID'],rx_dict['Voltage'],battery_Ah))
            file_washed.write("{},{},{},{},{},{},{},{},{},{},{},{},{}\n".format(date_,time_,Home0_washed,Home1_washed,Home2_washed,Home3_washed,Grid_washed,Charge_washed,Discharge_washed,power_solar_washed,rx_dict['BATTERY'],rx_dict['GRID'],rx_dict['Voltage'],battery_Ah))

            ########################
            # MAKING TABLES
            ########################
            # Make a table for the state of relays
            grid_state = rx_dict['GRID']
            battery_state = rx_dict['BATTERY']
            relay_table = [['BATTERY', rx_dict['BATTERY']],['GRID', rx_dict['GRID']]]
            print(tabulate(relay_table, headers=['Relay', 'State'], tablefmt='orgtbl'))
            print()

            # Make a table for the power
            power_table = [['Home0', rx_dict['Home0'], Home0_washed], ['Home1', rx_dict['Home1'], Home1_washed], ['Home2', rx_dict['Home2'], Home2_washed], ['Home3', rx_dict['Home3'], Home3_washed], ['Grid', rx_dict['Grid'], Grid_washed], ['Charge', rx_dict['Charge'], Charge_washed], ['Discharge', rx_dict['Discharge'], Discharge_washed], ['Solar', power_solar, power_solar_washed]]
            print(tabulate(power_table, headers=['Name', 'Power_raw (mW)', 'Power_washed (mW)'], tablefmt='orgtbl'))
            print()

            # Print Battery info
            print("bus voltage: {}".format(rx_dict["Voltage"]/1000))
            print("battery Ah: {}".format(battery_Ah))
            print()
        
        # Catch communication error w/ arduino
        except:
            print("Lagging")
