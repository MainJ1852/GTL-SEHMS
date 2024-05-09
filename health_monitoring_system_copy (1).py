'''
' GTL Supplemental Equipment Health Monitoring System
' Controller Code
' Last edited: 09/21/2023
'
' The purpose of this program is to collect the property (temperature, acceleration, and pressure) readings from each facility's Arduino, display the data for each
' facility on its own page using labels and graphs, and save the data onto a daily csv for future use. This Python script uses a GUI package called TKinter that's
' included in Python3's base package. Each class (besides the governing HealthMonitor class) correlates to one of the GUI's pages. The CSVs containing all the data for
' each day can be found in the HealthMonitorData folder.
'''

''' IMPORT STATEMENTS '''
# Imports TKinter libraries, used for general GUI window, frames, and widgets, as well as fonts, colors, etc.
import tkinter as tk
from tkinter import font as tkFont

# Matplotlib libraries for graphing and embedding into TKinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import pyplot as plt, animation

# Datetime library gets current time and date, time used for after command to get recursive function calls with a delay
import datetime as dt
import time

# Serial library used for communication b/w Raspberry Pi and Arduino boards
import serial
import RPi.GPIO as GPIO

# Os.path library is used in order to check if a file path already exists, csv library used for csv formatting
import os.path
import csv

# Itertools library is used for making counter that are incremented every time they are called (useful for fast graphing)
from itertools import count


'''
' HealthMonitor class creates instance of tkinter window. In the __init__ function, we:
'    > Define attributes to be used by all the pages
'    > Create a frame called 'frame_housing' that will act as a host for all the different pages of the program
'    > Create a dictionary called 'pages' that will hold all the instance of each page the program uses
'    > Switch to the home page by calling show_page function
'    > Call get_values
' In the show_page function, we:
'    > Currently, all the pages are stacked on top of each other. We begin by removing all the pages from the screen so only
'      one page is present and running at a time
'    > Select the target page from 'pages' dictionary
'    > Place the target page on the screen using grid()
' In the get_values function, we:
'    > Read in string data from Arduino boards and separate each data value as an element in a list
'    > Based on the data's tag, it's converted to float and appended to its corresponding data list
'    > Data lists are kept to a maximum size of 10 or 15 elements using pop()
'    > Call write_to_csv()
'    > Recursively call itself 10 times a second to ensure it won't miss any incoming data
' In the write_to_csv function, we:
'    > Check if the csv file named after today's date exists
'    > If not, create a header; if so, write a row of data separated by commas, each value truncated to 1-2 decimal places
'''
class HealthMonitor(tk.Tk):
    # __init__ function is always called when an instance of the class is created
    def __init__(self, *args, **kwargs):
        # Initiate super class (tkinter root window)
        tk.Tk.__init__(self, *args, **kwargs)
        
        # Design Properties
        self.title("GTL Health Monitoring System") # title
        self.geometry("1920x1080")
        
        self.font_directions = tkFont.Font(family = "Helvetica", size = 20) # fonts
        self.font_facility_title = tkFont.Font(family = "Helvetica", size = 27, weight = "bold")
        self.font_button = tkFont.Font(family = "Helvetica", size = 20)
        self.font_general_title = tkFont.Font(family = "Helvetica", size = 20, weight = "bold")
        self.font_data = tkFont.Font(family = "Helvetica", size = 20)
        
        self.color_button_bg = "#b0bcc2" # colors: light gray/blue
        
        # Keeps track of which facility Pi wants data from
        self.str_facility = '1'
        
        ''' DATA LISTS USED TO STORE INCOMING DATA FROM SERIAL '''
        # LRF
        self.thermo1A = []       # TC 1
        self.thermo1B = []       # TC 2
        self.accel1K_X = []      # ACC 1 (x-dir)
        self.accel1K_Y = []      # ACC 1 (y-dir)
        self.accel1K_Z = []      # ACC 1 (z-dir)
        self.pres1U = []         # PRES 1
        
        # VISE
        self.thermo2A = []       # TC 1
        self.thermo2B = []       # TC 2
        self.accel2K_X = []      # ACC 1 (x-dir)
        self.accel2K_Y = []      # ACC 1 (y-dir)
        self.accel2K_Z = []      # ACC 1 (z-dir)
        self.pres2U = []         # PRES 1
        
        # Time data lists (used for time label and graphing purposes)
        self.time = [] # Stores actual time, used for time label in upper left corner of pages and csv file
        self.LRF_thermo_time_count = [] # These counters represent the passing time, used in MatPlotLib graphs
        self.LRF_accel_pres_time_count = []
        self.VISE_thermo_time_count = []
        self.VISE_accel_pres_time_count = []
        
        # File name for csv
        self.filePath = "/home/GTL/HealthMonitorData/" + dt.datetime.now().strftime("%m-%d-%Y") + ".csv"
        
        # Frame to house all the pages
        frame_housing = tk.Frame(self)
        frame_housing.pack(side = "top", fill = "both", expand = True)
        
        # Dictionary to contain all the page instances
        self.pages = {}
        
        # Add new key-values (aka pages) to dictionary
        self.pages["Home"] = HomePage(parent = frame_housing, controller = self)
        self.pages["LRF"] = LRFPage(parent = frame_housing, controller = self)
        self.pages["Vise"] = VisePage(parent = frame_housing, controller = self)
        self.pages["TTF"] = TTFPage(parent = frame_housing, controller = self)
        self.pages["Compressor Pit"] = CompressorPitPage(parent = frame_housing, controller = self)
        
        # Open home page
        self.show_page("Home")
        
        # Function call to start requesting values
        self.request_values()
        
        
    # Function to switch to target page
    def show_page(self, target_page):
        # Closes any open pages fully
        for page in self.pages.values():
            page.is_open_page = False # This attribute is used to start/stop specific page functions whenever the page is open or closed
            page.grid_remove()
        
        # Opens target page
        new_page = self.pages[target_page]
        new_page.is_open_page = True
        new_page.start_up() # Calls main start up sequence that should happen every time page is opened
        new_page.grid(row = 0, column = 0, sticky = "NESW")
    
    
    # Pi sends out a byte to all Arduinos corresponding to which facility it wants data from. Only that facility's Arduino will respond by sending its data.
    def request_values(self):
        # Ping LRF Arduino for values
        GPIO.output(16, GPIO.HIGH) # HIGH = transmitting
        time.sleep(0.005)
        facility_byte = self.str_facility.encode()
        ser.write(facility_byte) # Send byte to desired facility
        time.sleep(0.005)
        GPIO.output(16, GPIO.LOW) # LOW = receiving
        
        self.after(90, self.get_values)
    
    
    # Reads from serial connection any incoming data and sorts each piece into its proper data list. This function also keeps the data lists maxed out at a certain
    # number of elements, calls the write_to_csv() function, and calls the request_values() function to repeat the whole process.
    def get_values(self):
        try:
            if ser.in_waiting > 0: # Checks is LRF serial port is sending any data
                input_string = ser.readline().decode("utf-8").strip() # Reads in string data
                str_list = input_string.split() # Split each value in string into its own list element
                
                # Gets current time, appends to a list
                current_time = dt.datetime.now().strftime('%H:%M:%S.%f')[0:-5]
                self.time.append(current_time)
            
                # Check which facility the data came from
                if (str_list[0].startswith('1')): # LRF
                    str_list[0] = str_list[0][1:] # Remove facility number from first data value
                    
                    # Change facility num so Pi asks other Arduino for data
                    self.str_facility = '2'
                    
                    for value in str_list:
                        # Checks tag of each element in str_list (tag is first character of each element), appends float data value to corresponding list
                        if value.startswith('A'):
                            self.LRF_thermo_time_count.append(next(LRF_thermo_counter)) # Increment thermo time, used for graphing alongside thermocouple data values
                            self.thermo1A.append(float(value[1:]))
                        elif value.startswith('B'):
                            self.thermo1B.append(float(value[1:]))
                        elif value.startswith('K'):
                            self.LRF_accel_pres_time_count.append(next(LRF_accel_pres_counter)) # Increment accel/pres time, used for graphing
                            accel1K_vals = value.split(',') # accel vals come grouped together, so have to separate and append individually
                            self.accel1K_X.append(float(accel1K_vals[0][1:]))
                            self.accel1K_Y.append(float(accel1K_vals[1]))
                            self.accel1K_Z.append(float(accel1K_vals[2])-9.81)
                        elif value.startswith('U'):
                            self.pres1U.append(float(value[1:]))
                        else:
                            print("No valid tag sent") # Prints if data value did not include a valid tag
                    
                    # Clean out old data values
                    if len(self.time) > 10:
                        self.time.pop(0)
            
                    if len(self.LRF_thermo_time_count) > 10:
                        self.LRF_thermo_time_count.pop(0)
                        self.thermo1A.pop(0)
                        self.thermo1B.pop(0)
            
                    if len(self.LRF_accel_pres_time_count) > 15:
                        self.LRF_accel_pres_time_count.pop(0)
                        self.accel1K_X.pop(0)
                        self.accel1K_Y.pop(0)
                        self.accel1K_Z.pop(0)
                        self.pres1U.pop(0)
                    
                elif (str_list[0].startswith('2')): # VISE
                    str_list[0] = str_list[0][1:] # Remove facility number from first data value
                    
                    # Change facility num so Pi asks other Arduino for data
                    self.str_facility = '1'
                    
                    for value in str_list:
                        # Checks tag of each element in str_list (tag is first character of each element), appends float data value to corresponding list
                        if value.startswith('A'):
                            self.VISE_thermo_time_count.append(next(VISE_thermo_counter)) # Increment thermo time, used for graphing alongside thermocouple data values
                            self.thermo2A.append(float(value[1:]))
                        elif value.startswith('B'):
                            self.thermo2B.append(float(value[1:]))
                        elif value.startswith('K'):
                            self.VISE_accel_pres_time_count.append(next(VISE_accel_pres_counter)) # Increment accel/pres time, used for graphing
                            accel2K_vals = value.split(',') # accel vals come grouped together, so have to separate and append individually
                            self.accel2K_X.append(float(accel2K_vals[0][1:]))
                            self.accel2K_Y.append(float(accel2K_vals[1]))
                            self.accel2K_Z.append(float(accel2K_vals[2]))
                        elif value.startswith('U'):
                            self.pres2U.append(float(value[1:]))
                        else:
                            print("No valid tag sent") # Prints if data value did not include a valid tag
                    
                    # Clean out old data values
                    if len(self.time) > 10:
                        self.time.pop(0)
            
                    if len(self.VISE_thermo_time_count) > 10:
                        self.VISE_thermo_time_count.pop(0)
                        self.thermo2A.pop(0)
                        self.thermo2B.pop(0)
            
                    if len(self.VISE_accel_pres_time_count) > 15:
                        self.VISE_accel_pres_time_count.pop(0)
                        self.accel2K_X.pop(0)
                        self.accel2K_Y.pop(0)
                        self.accel2K_Z.pop(0)
                        self.pres2U.pop(0)
                
                
                # Write data values to csv after every piece of equipment has had its data collected at least once
                if (len(self.thermo1A) > 0 and len(self.thermo2A) > 0):
                    self.write_to_csv()
                
                # Request new values
                self.request_values()
        except:
            print("Couldn't collect data") # If nothing in serial buffer or the function fails, this prevents the program from crashing due to an error
        
    
    # Writes data values to a csv file
    def write_to_csv(self):
        try:
            exists = os.path.isfile(self.filePath) # Checks if file path exists already
            if not exists: # If not, write headers
                with open(self.filePath, 'w') as log:
                    log.write("Time, Temp 1A [F], Temp 1B [F], Accel 1K_X [m/s^2], Accel1K_Y [m/s^2], Accel1K_Z [m/s^2], Pres 1U [psi], Temp 2A [F], Temp 2B [F], Accel 2K_X [m/s^2], Accel2K_Y [m/s^2], Accel2K_Z [m/s^2], Pres 2U [psi]\n")
            else: # If so, start writing in values
                with open(self.filePath, 'a') as log:
                    writer = csv.writer(log)
                    writer.writerow([self.time[-1], "%.2f" % self.thermo1A[-1], "%.2f" % self.thermo1B[-1], "%.2f" % self.accel1K_X[-1], "%.2f" % self.accel1K_Y[-1], "%.2f" % self.accel1K_Z[-1], "%.2f" % self.pres1U[-1], "%.2f" % self.thermo2A[-1], "%.2f" % self.thermo2B[-1], "%.2f" % self.accel2K_X[-1], "%.2f" % self.accel2K_Y[-1], "%.2f" % self.accel2K_Z[-1], "%.2f" % self.pres2U[-1]])               
        except:
            print("Can't save values to csv")
            
        
'''
' HomePage class defines the home page's design and functions. In the __init__ function, we:
'    > Declare attributes for color & font exclusive to the home page
'    > Place label widgets to give directions and provide users information
'    > Place button widgets to switch to the different facilities
' In the start_up function, we:
'    > Call check_serial
' In the check_serial function, we:
'    > Check if the serial connection to each facility is active (aka plugged in). If so, print it's on; otherwise, print off.
'      The IDE will throw an error too, and the labels and graphs will remain static. Data will also stop printing to the csv.
'''
class HomePage(tk.Frame):
    # __init__ function is always called when an instance of the class is created (in this case when the home page was added to the
    # pages dictionary in the HealthMonitor class)
    def __init__(self, parent, controller):
        # Initialize the frame widget this page is housed in
        tk.Frame.__init__(self, parent)
        self.controller = controller # controller refers to the master class HealthMonitor
        
        # Attributes & Design Properties
        self.is_open_page = False
        
        self.color_bg = "#95cfc4" # teal
        
        self.font_home_title = tkFont.Font(family = "Helvetica", size = 32, weight = "bold")
        self.font_button = tkFont.Font(family = "Helvetica", size = 25)
        
        # Design Configuration
        self.configure(bg = self.color_bg) # Sets background color for home screen
        
        # Widgets
        lbl_title = tk.Label(self, text = "Health Monitoring System", font = self.font_home_title, bg = self.color_bg)
        lbl_title.grid(row = 0, column = 1, rowspan = 2, columnspan = 2) # title
        
        self.lbl_serial_LRF = tk.Label(self, font = controller.font_directions) # label checking if LRF serial is on
        self.lbl_serial_LRF.configure(bg = self.color_bg)
        self.lbl_serial_LRF.grid(row = 0, column = 3, pady = 5, sticky = "NE")
        
        # This widget is no longer being used, pls delete and fix page spacing
        self.lbl_serial_vise = tk.Label(self, font = controller.font_directions) # label checking if Vise serial is on
        self.lbl_serial_vise.configure(bg = self.color_bg)
        self.lbl_serial_vise.grid(row = 1, column = 3, pady = 5, sticky = "NE")
        
        lbl_directions = tk.Label(self, text = "Choose which facility to monitor:", font = controller.font_directions, bg = self.color_bg)
        lbl_directions.grid(row = 2, column = 0, columnspan = 4, pady = 53) # directions
        
        btn_LRF = tk.Button(self, text = "LRF", font = self.font_button, width = 22, height = 12, command = lambda:controller.show_page("LRF"))
        btn_LRF.configure(bg = controller.color_button_bg)
        btn_LRF.grid(row = 3, column = 0, padx = 18, pady = 80) # buttons used for navigating to different pages
        
        btn_vise = tk.Button(self, text = "Vise", font = self.font_button, width = 22, height = 12, command = lambda:controller.show_page("Vise"))
        btn_vise.configure(bg = controller.color_button_bg)
        btn_vise.grid(row = 3, column = 1, padx = 16, pady = 80)
        
        btn_TTF = tk.Button(self, text = "TTF", font = self.font_button, width = 22, height = 12, command = lambda:controller.show_page("TTF"))
        btn_TTF.configure(bg = controller.color_button_bg)
        btn_TTF.grid(row = 3, column = 2, padx = 16, pady = 80)
        
        btn_CompressorPit = tk.Button(self, text = "Compressor Pit", font = self.font_button, width = 22, height = 12, command = lambda:controller.show_page("Compressor Pit"))
        btn_CompressorPit.configure(bg = controller.color_button_bg)
        btn_CompressorPit.grid(row = 3, column = 3, padx = 18, pady = 80)
        
        btn_quit = tk.Button(self, text = "Quit", width = 15, height = 4, font = self.font_button, command = exit) # quit button
        btn_quit.configure(bg = controller.color_button_bg)
        btn_quit.grid(row = 4, column = 3, padx = 17, pady = 10, sticky = "SE")
        
        lbl_wait = tk.Label(self, text = "Please wait for data values to compile...", font = controller.font_directions, bg = self.color_bg)
        lbl_wait.grid(row = 3, column = 0, columnspan = 4, padx = 10, pady = 10, sticky = "NSEW") # label that makes you wait for values to compile so that graphs don't throw an error with insufficient values
        
        self.after(9000, lbl_wait.grid_remove) # loading time
    
    
    # Function that runs every time the page is opened, every class except HealthMonitor has a start_up function    
    def start_up(self):
        self.check_serial()
    
    
    # Function for that checks if serial connections are still active
    def check_serial(self):
        # LRF serial
        try:
            if ser.in_waiting >= 0:
                self.lbl_serial_LRF["text"] = "Serial is ON."
            else:
                self.lbl_serial_LRF["text"] = "Serial is OFF."
        except:
            self.lbl_serial_LRF["text"] = "Serial is OFF."
            

'''
' LRFPage class contains all the temp, vibration, and pressure data for LRF supplemental machinery. In the __init__ function, we:
'     > Declare attributes such as color and fonts if applicable
'     > Create label widgets to categorize and display measurement data that are updated 5 times a second
'     > Set up axes and plots for thermocouple, accelerometer, and pressure transducer data
' In the start_up function, we:
'     > Call update_labels
'     > Begin animating the thermocouple, accelerometer, and pressure transducer graphs
' In the update_labels function, we:
'     > Updates time, temp, vibration, and pressure data labels 5 times a second
' In the update_thermo function, we:
'     > Set new line data for thermocouples, updates thermocouple graph once a second
' In the update_accel function, we:
'     > Set new line data for accelerometers, updates accelerometer graph ~5 times a second
' In the update_pres function, we:
'     > Set new line data for the pressure transducers, updates pressure graphs ~5 times a second
'''
class LRFPage(tk.Frame):
    # Called when first initialized by HealthMonitor class
    def __init__(self, parent, controller):
        # Initialize the frame widget this page is housed in
        tk.Frame.__init__(self, parent)
        self.controller = controller # refers to HealthMonitor class so this page can access the HealthMonitor class's attributes/functions too
        
        # Attributes & Design Properties
        self.is_open_page = False
        
        self.color_bg = "#ff7c78" #red
        
        # Design Configuration
        self.configure(bg = self.color_bg)
        
        # Widgets
        lbl_title = tk.Label(self, text = "LRF", font = controller.font_facility_title, bg = self.color_bg) #info
        lbl_title.grid(row = 0, column = 0, columnspan = 19, pady = 5)
        
        self.lbl_time = tk.Label(self, text = "Time goes here", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_time.grid(row = 0, column = 0, pady = 5, sticky = "NW")
        
        btn_home = tk.Button(self, text = "Home", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("Home"))
        btn_home.configure(bg = controller.color_button_bg) #menu
        btn_home.place(x = 400, y = 50)
        #btn_home.grid(row = 1, column = 6, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        btn_vise = tk.Button(self, text = "Vise", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("Vise"))
        btn_vise.configure(bg = controller.color_button_bg) #menu
        btn_vise.place(x = 675, y = 50)
        #btn_vise.grid(row = 1, column = 8, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        btn_TTF = tk.Button(self, text = "TTF", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("TTF"))
        btn_TTF.configure(bg = controller.color_button_bg) #menu
        btn_TTF.place(x = 950, y = 50)
        #btn_TTF.grid(row = 1, column = 10, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        btn_CompressorPit = tk.Button(self, text = "Compressor Pit", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("Compressor Pit"))
        btn_CompressorPit.configure(bg = controller.color_button_bg) #menu
        btn_CompressorPit.place(x = 1225, y = 50)
        #btn_CompressorPit.grid(row = 1, column = 12, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        lbl_hor_spacer1 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer1.grid(row = 1, column = 0, rowspan = 2, padx = 5, pady = 30)
        
        lbl_thermocouples = tk.Label(self, text = "Thermocouples", font = controller.font_general_title, bg = self.color_bg) #info
        lbl_thermocouples.grid(row = 3, column = 0, columnspan = 2, padx = 5, pady = 15, sticky = "W")
        
        self.lbl_thermo1A = tk.Label(self, text = "Thermocouple 1: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_thermo1A.grid(row = 4, column = 0, columnspan = 2, padx = 5, pady = 5, sticky = "W")
        
        self.lbl_thermo1B = tk.Label(self, text = "Thermocouple 2: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_thermo1B.grid(row = 5, column = 0, columnspan = 2, padx = 5, pady = 5, sticky = "W")
        
        lbl_hor_spacer2 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer2.grid(row = 6, column = 0, padx = 5, pady = 20)
        
        lbl_accelerometers = tk.Label(self, text = "Accelerometers", font = controller.font_general_title, bg = self.color_bg) #info
        lbl_accelerometers.grid(row = 7, column = 0, columnspan = 2, padx = 5, pady = 15, sticky = "W")
        
        self.lbl_accel1K_X = tk.Label(self, text = "X: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_accel1K_X.grid(row = 8, column = 0, padx = 5, pady = 5, sticky = "W")
        
        self.lbl_accel1K_Y = tk.Label(self, text = "Y: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_accel1K_Y.grid(row = 9, column = 0, padx = 5, pady = 5, sticky = "W")
        
        self.lbl_accel1K_Z = tk.Label(self, text = "Z: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_accel1K_Z.grid(row = 10, column = 0, padx = 5, pady = 5, sticky = "W")
        
        lbl_hor_spacer3 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer3.grid(row = 11, column = 0, padx = 5, pady = 20)
        
        lbl_pres_sensors = tk.Label(self, text = "Pressure Sensors", font = controller.font_general_title, bg = self.color_bg) #info
        lbl_pres_sensors.grid(row = 12, column = 0, columnspan = 2, padx = 5, pady = 15, sticky = "W")
        
        self.lbl_pres1U = tk.Label(self, text = "Pressure 1: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_pres1U.grid(row = 13, column = 0, columnspan = 2, padx = 5, pady = 5, sticky = "W")
        
        lbl_hor_spacer4 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer4.grid(row = 14, column = 0, padx = 5, pady = 75)
        
        btn_quit = tk.Button(self, text = "Quit", width = 15, height = 2, font = controller.font_button, command = exit)
        btn_quit.configure(bg = controller.color_button_bg) #quit button
        btn_quit.grid(row = 15, column = 18, columnspan = 2, padx = 30, pady = 10, sticky = "W")
        
        lbl_vert_spacer1 = tk.Label(self, text = "", width = 5, bg = self.color_bg)
        lbl_vert_spacer1.grid(row = 3, column = 3, rowspan = 12, padx = 5)
        
        lbl_vert_spacer2 = tk.Label(self, text = "", width = 4, bg = self.color_bg)
        lbl_vert_spacer2.grid(row = 3, column = 19, rowspan = 10, padx = 5)
        
        # Thermocouple Plot Setup
        self.fig_thermo = plt.Figure(figsize = (15, 3), dpi = 100) # Create figure to hold plot
        self.ax_thermo = self.fig_thermo.add_subplot() # Create axes that is basically the variable to control all the graph's properties
        self.ax_thermo.set_title("LRF Temperatures", fontsize = 20)
        self.ax_thermo.set_xlabel("Time [s]", fontsize = 15)
        self.ax_thermo.set_ylabel("Temperature [F]", fontsize = 15)
        self.ax_thermo.set_ylim(65, 95) # Range of 65-95 degrees Fahrenheit shown on plot
        self.ax_thermo.tick_params(axis = 'x', labelbottom = False) # removes x-axis tick labels
        self.ax_thermo.tick_params(axis = 'y', labelsize = 12) # Adjust size for readability
        
        self.line_thermo1A, = self.ax_thermo.plot([], [], linewidth = 3, color = "orange", label = "TC 1") # create thermocouple lines here
        self.line_thermo1B, = self.ax_thermo.plot([], [], linewidth = 3, color = "blue", label = "TC 2")
        self.ax_thermo.legend(fontsize = 15)
        
        # Accelerometer Plot Setup
        self.fig_accel = plt.Figure(figsize = (8, 4.5), dpi = 100)
        self.ax_accel = self.fig_accel.add_subplot()
        self.ax_accel.set_title("LRF Vibrations", fontsize = 20)
        self.ax_accel.set_xlabel("Time [s]", fontsize = 15)
        self.ax_accel.set_ylabel("Acceleration [m/s^2]", fontsize = 15)
        self.ax_accel.set_ylim(-6, 6) # Range of +/- 6 m/s^2 shown on graph
        self.ax_accel.tick_params(axis = 'x', labelbottom = False)
        self.ax_accel.tick_params(axis = 'y', labelsize = 12)
        
        self.line_accel1K_X, = self.ax_accel.plot([], [], linewidth = 3, color = "red", label = 'X') # create accelerometer lines here
        self.line_accel1K_Y, = self.ax_accel.plot([], [], linewidth = 3, color = "green", label = 'Y')
        self.line_accel1K_Z, = self.ax_accel.plot([], [], linewidth = 3, color = "magenta", label = 'Z')
        self.ax_accel.legend(fontsize = 15)
        
        # Pressure Transducer Plot Setup
        self.fig_pres = plt.Figure(figsize = (6.88, 4.5), dpi = 100)
        self.ax_pres = self.fig_pres.add_subplot()
        self.ax_pres.set_title("LRF Pressure", fontsize = 20)
        self.ax_pres.set_xlabel("Time [s]", fontsize = 15)
        self.ax_pres.set_ylabel("Vacuum Pressure [psi]", fontsize = 15)
        self.ax_pres.set_ylim(0, 20) # Range of 0-20 psi shown on graph
        self.ax_pres.tick_params(axis = 'x', labelbottom = False)
        self.ax_pres.tick_params(axis = 'y', labelsize = 12)
        
        self.line_pres1U, = self.ax_pres.plot([], [], linewidth = 3, color = "black", label = "LRF Pres.") # create pressure lines here
        self.ax_pres.legend(fontsize = 15)
        
        # Plot Widgets
        self.canvas_thermo = FigureCanvasTkAgg(self.fig_thermo, self) # Converts MatPlotLib figure object into TKinter canvas object so it can be embedded into the GUI
        self.canvas_thermo.draw()
        self.canvas_thermo.get_tk_widget().grid(row = 3, column = 4, rowspan = 5, columnspan = 15, pady = 5, sticky = "W")
        
        self.canvas_accel = FigureCanvasTkAgg(self.fig_accel, self)
        self.canvas_accel.draw()
        self.canvas_accel.get_tk_widget().grid(row = 8, column = 4, rowspan = 7, columnspan = 8, pady = 5, sticky = "NW")
        
        self.canvas_pres = FigureCanvasTkAgg(self.fig_pres, self)
        self.canvas_pres.draw()
        self.canvas_pres.get_tk_widget().grid(row = 8, column = 12, rowspan = 7, columnspan = 7, padx = 12, pady = 5, sticky = "NW")
        
        
    # Runs every time the page is opened
    def start_up(self):
        self.after(500, self.update_labels)
        self.animate_thermo = animation.FuncAnimation(self.fig_thermo, self.update_thermo, interval = 1000, blit = True)
        self.animate_accel = animation.FuncAnimation(self.fig_accel, self.update_accel, interval = 160, blit = True)
        self.animate_pres = animation.FuncAnimation(self.fig_pres, self.update_pres, interval = 160, blit = True)
    
    
    # Updates the data labels on the current page                   
    def update_labels(self):
        self.lbl_time["text"] = self.controller.time[-1]
        self.lbl_thermo1A["text"] = "Thermocouple 1: " + "%.2f" % self.controller.thermo1A[-1] + " F"
        self.lbl_thermo1B["text"] = "Thermocouple 2: " + "%.2f" % self.controller.thermo1B[-1] + " F"
        self.lbl_accel1K_X["text"] = "X1: " + "%.2f" % self.controller.accel1K_X[-1] + " m/s^2"
        self.lbl_accel1K_Y["text"] = "Y1: " + "%.2f" % self.controller.accel1K_Y[-1] + " m/s^2"
        self.lbl_accel1K_Z["text"] = "Z1: " + "%.2f" % self.controller.accel1K_Z[-1] + " m/s^2"
        self.lbl_pres1U["text"] = "Pressure 1: " + "%.2f" % self.controller.pres1U[-1] + " psi"
        
        if self.is_open_page: # As long as LRF is the open page, keep updating labels
            self.after(200, self.update_labels)
    
    
    # Updates thermocouple graph every second
    def update_thermo(self, i):
        self.line_thermo1A.set_data(self.controller.LRF_thermo_time_count[-5:-1], self.controller.thermo1A[-5:-1])
        self.line_thermo1B.set_data(self.controller.LRF_thermo_time_count[-5:-1], self.controller.thermo1B[-5:-1])
        self.ax_thermo.set_xlim(self.controller.LRF_thermo_time_count[-5], self.controller.LRF_thermo_time_count[-1])
        
        return self.line_thermo1A, self.line_thermo1B
    
    
    # Updates accelerometer graph ~5 times a second
    def update_accel(self, i):
        self.line_accel1K_X.set_data(self.controller.LRF_accel_pres_time_count[-10:-1], self.controller.accel1K_X[-10:-1])
        self.line_accel1K_Y.set_data(self.controller.LRF_accel_pres_time_count[-10:-1], self.controller.accel1K_Y[-10:-1])
        self.line_accel1K_Z.set_data(self.controller.LRF_accel_pres_time_count[-10:-1], self.controller.accel1K_Z[-10:-1])
        self.ax_accel.set_xlim(self.controller.LRF_accel_pres_time_count[-10], self.controller.LRF_accel_pres_time_count[-1])
        
        # Experimenting with variable y-axis, would need updating labels though which blit can't handle
        #min_value = min(self.controller.accel1K_X + self.controller.accel1K_Y + self.controller.accel1K_Z)
        #max_value = max(self.controller.accel1K_X + self.controller.accel1K_Y + self.controller.accel1K_Z)
        #self.ax_accel.set_ylim(min_value - 2, max_value + 2)
    
        if not self.is_open_page: # when LRF no longer open page, stop animating graphs
            self.animate_thermo.event_source.stop() # stop thermo and pres here too, update_thermo too slow sometimes
            self.animate_accel.event_source.stop()
            self.animate_pres.event_source.stop()
    
        return self.line_accel1K_X, self.line_accel1K_Y, self.line_accel1K_Z
    
    
    # Updates pressure graph ~5 times a second
    def update_pres(self, i):
        self.line_pres1U.set_data(self.controller.LRF_accel_pres_time_count[-10:-1], self.controller.pres1U[-10:-1])
        self.ax_pres.set_xlim(self.controller.LRF_accel_pres_time_count[-10], self.controller.LRF_accel_pres_time_count[-1])
     
        return self.line_pres1U,
    

'''
' VISE PAGE
'''
class VisePage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        # Attributes
        self.is_open_page = False
        
        self.color_bg = "#42c1fc" #blue
        
        # Design
        self.configure(bg = self.color_bg)
        
        # Widgets
        lbl_title = tk.Label(self, text = "Vise", font = controller.font_facility_title, bg = self.color_bg) #info
        lbl_title.grid(row = 0, column = 0, columnspan = 19, pady = 5)
        
        self.lbl_time = tk.Label(self, text = "Time goes here", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_time.grid(row = 0, column = 0, pady = 5, sticky = "NW")
        
        btn_home = tk.Button(self, text = "Home", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("Home"))
        btn_home.configure(bg = controller.color_button_bg) #menu
        btn_home.place(x = 400, y = 50)
        #btn_home.grid(row = 1, column = 6, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        btn_LRF = tk.Button(self, text = "LRF", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("LRF"))
        btn_LRF.configure(bg = controller.color_button_bg) #menu
        btn_LRF.place(x = 675, y = 50)
        #btn_LRF.grid(row = 1, column = 8, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        btn_TTF = tk.Button(self, text = "TTF", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("TTF"))
        btn_TTF.configure(bg = controller.color_button_bg) #menu
        btn_TTF.place(x = 950, y = 50)
        #btn_TTF.grid(row = 1, column = 10, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        btn_CompressorPit = tk.Button(self, text = "Compressor Pit", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("Compressor Pit"))
        btn_CompressorPit.configure(bg = controller.color_button_bg) #menu
        btn_CompressorPit.place(x = 1225, y = 50)
        #btn_CompressorPit.grid(row = 1, column = 12, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        lbl_hor_spacer1 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer1.grid(row = 1, column = 0, rowspan = 2, padx = 5, pady = 30)
        
        lbl_thermocouples = tk.Label(self, text = "Thermocouples", font = controller.font_general_title, bg = self.color_bg) #info
        lbl_thermocouples.grid(row = 3, column = 0, columnspan = 2, padx = 5, pady = 15, sticky = "W")
        
        self.lbl_thermo2A = tk.Label(self, text = "Thermocouple 1: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_thermo2A.grid(row = 4, column = 0, columnspan = 2, padx = 5, pady = 5, sticky = "W")
        
        self.lbl_thermo2B = tk.Label(self, text = "Thermocouple 2: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_thermo2B.grid(row = 5, column = 0, columnspan = 2, padx = 5, pady = 5, sticky = "W")
        
        lbl_hor_spacer2 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer2.grid(row = 6, column = 0, padx = 5, pady = 20)
        
        lbl_accelerometers = tk.Label(self, text = "Accelerometers", font = controller.font_general_title, bg = self.color_bg) #info
        lbl_accelerometers.grid(row = 7, column = 0, columnspan = 2, padx = 5, pady = 15, sticky = "W")
        
        self.lbl_accel2K_X = tk.Label(self, text = "X: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_accel2K_X.grid(row = 8, column = 0, padx = 5, pady = 5, sticky = "W")
        
        self.lbl_accel2K_Y = tk.Label(self, text = "Y: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_accel2K_Y.grid(row = 9, column = 0, padx = 5, pady = 5, sticky = "W")
        
        self.lbl_accel2K_Z = tk.Label(self, text = "Z: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_accel2K_Z.grid(row = 10, column = 0, padx = 5, pady = 5, sticky = "W")
        
        lbl_hor_spacer3 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer3.grid(row = 11, column = 0, padx = 5, pady = 20)
        
        lbl_pres_sensors = tk.Label(self, text = "Pressure Sensors", font = controller.font_general_title, bg = self.color_bg) #info
        lbl_pres_sensors.grid(row = 12, column = 0, columnspan = 2, padx = 5, pady = 15, sticky = "W")
        
        self.lbl_pres2U = tk.Label(self, text = "Pressure 1: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_pres2U.grid(row = 13, column = 0, columnspan = 2, padx = 5, pady = 5, sticky = "W")
        
        lbl_hor_spacer4 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer4.grid(row = 14, column = 0, padx = 5, pady = 75)
        
        btn_quit = tk.Button(self, text = "Quit", width = 15, height = 2, font = controller.font_button, command = exit)
        btn_quit.configure(bg = controller.color_button_bg) #quit button
        btn_quit.grid(row = 15, column = 18, columnspan = 2, padx = 30, pady = 10, sticky = "W")
        
        lbl_vert_spacer1 = tk.Label(self, text = "", width = 5, bg = self.color_bg)
        lbl_vert_spacer1.grid(row = 3, column = 3, rowspan = 12, padx = 5)
        
        lbl_vert_spacer2 = tk.Label(self, text = "", width = 4, bg = self.color_bg)
        lbl_vert_spacer2.grid(row = 3, column = 19, rowspan = 10, padx = 5)
        
        # Thermocouple Plot Setup
        self.fig_thermo = plt.Figure(figsize = (15, 3), dpi = 100)
        self.ax_thermo = self.fig_thermo.add_subplot() 
        self.ax_thermo.set_title("Vise Temperatures", fontsize = 20)
        self.ax_thermo.set_xlabel("Time [s]", fontsize = 15)
        self.ax_thermo.set_ylabel("Temperature [F]", fontsize = 15)
        self.ax_thermo.set_ylim(65, 95)
        self.ax_thermo.tick_params(axis = 'x', labelbottom = False) # removes x-axis tick labels
        self.ax_thermo.tick_params(axis = 'y', labelsize = 12)
        
        self.line_thermo2A, = self.ax_thermo.plot([], [], linewidth = 3, color = "orange", label = "TC 1") # create thermocouple lines here
        self.line_thermo2B, = self.ax_thermo.plot([], [], linewidth = 3, color = "blue", label = "TC 2")
        self.ax_thermo.legend(fontsize = 15)
        
        # Accelerometer Plot Setup
        self.fig_accel = plt.Figure(figsize = (8, 4.5), dpi = 100)
        self.ax_accel = self.fig_accel.add_subplot()
        self.ax_accel.set_title("Vise Vibrations", fontsize = 20)
        self.ax_accel.set_xlabel("Time [s]", fontsize = 15)
        self.ax_accel.set_ylabel("Acceleration [m/s^2]", fontsize = 15)
        self.ax_accel.set_ylim(-6, 6)
        self.ax_accel.tick_params(axis = 'x', labelbottom = False)
        self.ax_accel.tick_params(axis = 'y', labelsize = 12)
        
        self.line_accel2K_X, = self.ax_accel.plot([], [], linewidth = 3, color = "red", label = 'X') # create accelerometer lines here
        self.line_accel2K_Y, = self.ax_accel.plot([], [], linewidth = 3, color = "green", label = 'Y')
        self.line_accel2K_Z, = self.ax_accel.plot([], [], linewidth = 3, color = "magenta", label = 'Z')
        self.ax_accel.legend(fontsize = 15)
        
        # Pressure Transducer Plot Setup
        self.fig_pres = plt.Figure(figsize = (6.88, 4.5), dpi = 100)
        self.ax_pres = self.fig_pres.add_subplot()
        self.ax_pres.set_title("Vise Pressure", fontsize = 20)
        self.ax_pres.set_xlabel("Time [s]", fontsize = 15)
        self.ax_pres.set_ylabel("Vacuum Pressure [psi]", fontsize = 15)
        self.ax_pres.set_ylim(0, 20)
        self.ax_pres.tick_params(axis = 'x', labelbottom = False)
        self.ax_pres.tick_params(axis = 'y', labelsize = 12)
        
        self.line_pres2U, = self.ax_pres.plot([], [], linewidth = 3, color = "black", label = "Vise Pres.")
        self.ax_pres.legend(fontsize = 15)
        
        # Plot Widgets
        self.canvas_thermo = FigureCanvasTkAgg(self.fig_thermo, self)
        self.canvas_thermo.draw()
        self.canvas_thermo.get_tk_widget().grid(row = 3, column = 4, rowspan = 5, columnspan = 15, pady = 5, sticky = "W")
        
        self.canvas_accel = FigureCanvasTkAgg(self.fig_accel, self)
        self.canvas_accel.draw()
        self.canvas_accel.get_tk_widget().grid(row = 8, column = 4, rowspan = 7, columnspan = 8, pady = 5, sticky = "NW")
        
        self.canvas_pres = FigureCanvasTkAgg(self.fig_pres, self)
        self.canvas_pres.draw()
        self.canvas_pres.get_tk_widget().grid(row = 8, column = 12, rowspan = 7, columnspan = 7, padx = 12, pady = 5, sticky = "NW")
        
    # Runs every time the page is opened
    def start_up(self):
        self.after(500, self.update_labels)
        self.animate_thermo = animation.FuncAnimation(self.fig_thermo, self.update_thermo, interval = 1000, blit = True)
        self.animate_accel = animation.FuncAnimation(self.fig_accel, self.update_accel, interval = 160, blit = True)
        self.animate_pres = animation.FuncAnimation(self.fig_pres, self.update_pres, interval = 160, blit = True)
    
    # Updates the data labels on the current page                   
    def update_labels(self):
        self.lbl_time["text"] = self.controller.time[-1]
        self.lbl_thermo2A["text"] = "Thermocouple 1: " + "%.2f" % self.controller.thermo2A[-1] + " F"
        self.lbl_thermo2B["text"] = "Thermocouple 2: " + "%.2f" % self.controller.thermo2B[-1] + " F"
        self.lbl_accel2K_X["text"] = "X1: " + "%.2f" % self.controller.accel2K_X[-1] + " m/s^2"
        self.lbl_accel2K_Y["text"] = "Y1: " + "%.2f" % self.controller.accel2K_Y[-1] + " m/s^2"
        self.lbl_accel2K_Z["text"] = "Z1: " + "%.2f" % self.controller.accel2K_Z[-1] + " m/s^2"
        self.lbl_pres2U["text"] = "Pressure 1: " + "%.2f" % self.controller.pres2U[-1] + " psi"
        
        if self.is_open_page: # As long as LRF is the open page, keep updating labels
            self.after(200, self.update_labels)
    
    # Updates thermocouple graph every second
    def update_thermo(self, i):
        self.line_thermo2A.set_data(self.controller.VISE_thermo_time_count[-5:-1], self.controller.thermo2A[-5:-1])
        self.line_thermo2B.set_data(self.controller.VISE_thermo_time_count[-5:-1], self.controller.thermo2B[-5:-1])
        self.ax_thermo.set_xlim(self.controller.VISE_thermo_time_count[-5], self.controller.VISE_thermo_time_count[-1])
        
        return self.line_thermo2A, self.line_thermo2B
    
    # Updates accelerometer graph ~5 times a second
    def update_accel(self, i):
        self.line_accel2K_X.set_data(self.controller.VISE_accel_pres_time_count[-10:-1], self.controller.accel2K_X[-10:-1])
        self.line_accel2K_Y.set_data(self.controller.VISE_accel_pres_time_count[-10:-1], self.controller.accel2K_Y[-10:-1])
        self.line_accel2K_Z.set_data(self.controller.VISE_accel_pres_time_count[-10:-1], self.controller.accel2K_Z[-10:-1])
        self.ax_accel.set_xlim(self.controller.VISE_accel_pres_time_count[-10], self.controller.VISE_accel_pres_time_count[-1])
        
        # Experimenting with variable y-axis, would need updating labels though which blit can't handle
        #min_value = min(self.controller.accel1K_X + self.controller.accel1K_Y + self.controller.accel1K_Z)
        #max_value = max(self.controller.accel1K_X + self.controller.accel1K_Y + self.controller.accel1K_Z)
        #self.ax_accel.set_ylim(min_value - 2, max_value + 2)
    
        if not self.is_open_page: # when LRF no longer open page, stop animating graphs
            self.animate_thermo.event_source.stop() # stop thermo and pres here too, update_thermo too slow sometimes
            self.animate_accel.event_source.stop()
            self.animate_pres.event_source.stop()
    
        return self.line_accel2K_X, self.line_accel2K_Y, self.line_accel2K_Z
    
    # Updates pressure graph ~5 times a second
    def update_pres(self, i):
        self.line_pres2U.set_data(self.controller.VISE_accel_pres_time_count[-10:-1], self.controller.pres2U[-10:-1])
        self.ax_pres.set_xlim(self.controller.VISE_accel_pres_time_count[-10], self.controller.VISE_accel_pres_time_count[-1])
     
        return self.line_pres2U,
    

'''
' TTF PAGE
'''
class TTFPage(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        # Attributes
        self.is_open_page = False
        
        self.color_bg = "#decd31" #yellow
        
        # Design
        self.configure(bg = self.color_bg)
        
        # Widgets
        lbl_title = tk.Label(self, text = "TTF", font = controller.font_facility_title, bg = self.color_bg) #info
        lbl_title.grid(row = 0, column = 0, columnspan = 19, pady = 5)
        
        self.lbl_time = tk.Label(self, text = "Time goes here", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_time.grid(row = 0, column = 0, pady = 5, sticky = "NW")
        
        btn_home = tk.Button(self, text = "Home", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("Home"))
        btn_home.configure(bg = controller.color_button_bg) #menu
        btn_home.place(x = 400, y = 50)
        #btn_home.grid(row = 1, column = 6, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        btn_LRF = tk.Button(self, text = "LRF", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("LRF"))
        btn_LRF.configure(bg = controller.color_button_bg) #menu
        btn_LRF.place(x = 675, y = 50)
        #btn_LRF.grid(row = 1, column = 8, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        btn_Vise = tk.Button(self, text = "Vise", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("Vise"))
        btn_Vise.configure(bg = controller.color_button_bg) #menu
        btn_Vise.place(x = 950, y = 50)
        #btn_TTF.grid(row = 1, column = 10, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        btn_CompressorPit = tk.Button(self, text = "Compressor Pit", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("Compressor Pit"))
        btn_CompressorPit.configure(bg = controller.color_button_bg) #menu
        btn_CompressorPit.place(x = 1225, y = 50)
        #btn_CompressorPit.grid(row = 1, column = 12, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        lbl_hor_spacer1 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer1.grid(row = 1, column = 0, rowspan = 2, padx = 5, pady = 30)
        
        lbl_thermocouples = tk.Label(self, text = "Thermocouples", font = controller.font_general_title, bg = self.color_bg) #info
        lbl_thermocouples.grid(row = 3, column = 0, columnspan = 2, padx = 5, pady = 15, sticky = "W")
        
        self.lbl_thermo1A = tk.Label(self, text = "Thermocouple 1: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_thermo1A.grid(row = 4, column = 0, columnspan = 2, padx = 5, pady = 5, sticky = "W")
        
        self.lbl_thermo1B = tk.Label(self, text = "Thermocouple 2: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_thermo1B.grid(row = 5, column = 0, columnspan = 2, padx = 5, pady = 5, sticky = "W")
        
        lbl_hor_spacer2 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer2.grid(row = 6, column = 0, padx = 5, pady = 20)
        
        lbl_accelerometers = tk.Label(self, text = "Accelerometers", font = controller.font_general_title, bg = self.color_bg) #info
        lbl_accelerometers.grid(row = 7, column = 0, columnspan = 2, padx = 5, pady = 15, sticky = "W")
        
        self.lbl_accel1K_X = tk.Label(self, text = "X: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_accel1K_X.grid(row = 8, column = 0, padx = 5, pady = 5, sticky = "W")
        
        self.lbl_accel1K_Y = tk.Label(self, text = "Y: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_accel1K_Y.grid(row = 9, column = 0, padx = 5, pady = 5, sticky = "W")
        
        self.lbl_accel1K_Z = tk.Label(self, text = "Z: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_accel1K_Z.grid(row = 10, column = 0, padx = 5, pady = 5, sticky = "W")
        
        lbl_hor_spacer3 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer3.grid(row = 11, column = 0, padx = 5, pady = 20)
        
        lbl_pres_sensors = tk.Label(self, text = "Pressure Sensors", font = controller.font_general_title, bg = self.color_bg) #info
        lbl_pres_sensors.grid(row = 12, column = 0, columnspan = 2, padx = 5, pady = 15, sticky = "W")
        
        self.lbl_pres1U = tk.Label(self, text = "Pressure 1: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_pres1U.grid(row = 13, column = 0, columnspan = 2, padx = 5, pady = 5, sticky = "W")
        
        lbl_hor_spacer4 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer4.grid(row = 14, column = 0, padx = 5, pady = 75)
        
        btn_quit = tk.Button(self, text = "Quit", width = 15, height = 2, font = controller.font_button, command = exit)
        btn_quit.configure(bg = controller.color_button_bg) #quit button
        btn_quit.grid(row = 15, column = 18, columnspan = 2, padx = 30, pady = 10, sticky = "W")
        
        lbl_vert_spacer1 = tk.Label(self, text = "", width = 5, bg = self.color_bg)
        lbl_vert_spacer1.grid(row = 3, column = 3, rowspan = 12, padx = 5)
        
        lbl_vert_spacer2 = tk.Label(self, text = "", width = 4, bg = self.color_bg)
        lbl_vert_spacer2.grid(row = 3, column = 19, rowspan = 10, padx = 5)
        
        # Thermocouple Plot Setup
        self.fig_thermo = plt.Figure(figsize = (15, 3), dpi = 100)
        self.ax_thermo = self.fig_thermo.add_subplot()
        self.ax_thermo.set_title("TTF Temperatures", fontsize = 20)
        self.ax_thermo.set_xlabel("Time [s]", fontsize = 15)
        self.ax_thermo.set_ylabel("Temperature [F]", fontsize = 15)
        self.ax_thermo.set_ylim(65, 95)
        self.ax_thermo.tick_params(axis = 'x', labelbottom = False) # removes x-axis tick labels
        self.ax_thermo.tick_params(axis = 'y', labelsize = 12)
        
        self.line_thermo1A, = self.ax_thermo.plot([], [], linewidth = 3, color = "orange", label = "TC 1") # create thermocouple lines here
        self.line_thermo1B, = self.ax_thermo.plot([], [], linewidth = 3, color = "blue", label = "TC 2")
        self.ax_thermo.legend(fontsize = 15)
        
        # Accelerometer Plot Setup
        self.fig_accel = plt.Figure(figsize = (8, 4.5), dpi = 100)
        self.ax_accel = self.fig_accel.add_subplot()
        self.ax_accel.set_title("TTF Vibrations", fontsize = 20)
        self.ax_accel.set_xlabel("Time [s]", fontsize = 15)
        self.ax_accel.set_ylabel("Acceleration [m/s^2]", fontsize = 15)
        self.ax_accel.set_ylim(-6, 6)
        self.ax_accel.tick_params(axis = 'x', labelbottom = False)
        self.ax_accel.tick_params(axis = 'y', labelsize = 12)
        
        self.line_accel1K_X, = self.ax_accel.plot([], [], linewidth = 3, color = "red", label = 'X') # create accelerometer lines here
        self.line_accel1K_Y, = self.ax_accel.plot([], [], linewidth = 3, color = "green", label = 'Y')
        self.line_accel1K_Z, = self.ax_accel.plot([], [], linewidth = 3, color = "magenta", label = 'Z')
        self.ax_accel.legend(fontsize = 15)
        
        # Pressure Transducer Plot Setup
        self.fig_pres = plt.Figure(figsize = (6.88, 4.5), dpi = 100)
        self.ax_pres = self.fig_pres.add_subplot()
        self.ax_pres.set_title("TTF Pressure", fontsize = 20)
        self.ax_pres.set_xlabel("Time [s]", fontsize = 15)
        self.ax_pres.set_ylabel("Vacuum Pressure [psi]", fontsize = 15)
        self.ax_pres.set_ylim(0, 20)
        self.ax_pres.tick_params(axis = 'x', labelbottom = False)
        self.ax_pres.tick_params(axis = 'y', labelsize = 12)
        
        self.line_pres1U, = self.ax_pres.plot([], [], linewidth = 3, color = "black", label = "TTF Pres.")
        self.ax_pres.legend(fontsize = 15)
        
        # Plot Widgets
        self.canvas_thermo = FigureCanvasTkAgg(self.fig_thermo, self)
        self.canvas_thermo.draw()
        self.canvas_thermo.get_tk_widget().grid(row = 3, column = 4, rowspan = 5, columnspan = 15, pady = 5, sticky = "W")
        
        self.canvas_accel = FigureCanvasTkAgg(self.fig_accel, self)
        self.canvas_accel.draw()
        self.canvas_accel.get_tk_widget().grid(row = 8, column = 4, rowspan = 7, columnspan = 8, pady = 5, sticky = "NW")
        
        self.canvas_pres = FigureCanvasTkAgg(self.fig_pres, self)
        self.canvas_pres.draw()
        self.canvas_pres.get_tk_widget().grid(row = 8, column = 12, rowspan = 7, columnspan = 7, padx = 12, pady = 5, sticky = "NW")
        
    # Runs every time the page is opened
    def start_up(self):
        self.after(500, self.update_labels)
        self.animate_thermo = animation.FuncAnimation(self.fig_thermo, self.update_thermo, interval = 1000, blit = True)
        self.animate_accel = animation.FuncAnimation(self.fig_accel, self.update_accel, interval = 160, blit = True)
        self.animate_pres = animation.FuncAnimation(self.fig_pres, self.update_pres, interval = 160, blit = True)
    
    # Updates the data labels on the current page                   
    def update_labels(self):
        self.lbl_time["text"] = self.controller.time[-1]
        self.lbl_thermo1A["text"] = "Thermocouple 1: " + "%.2f" % self.controller.thermo1A[-1] + " F"
        self.lbl_thermo1B["text"] = "Thermocouple 2: " + "%.2f" % self.controller.thermo1B[-1] + " F"
        self.lbl_accel1K_X["text"] = "X1: " + "%.2f" % self.controller.accel1K_X[-1] + " m/s^2"
        self.lbl_accel1K_Y["text"] = "Y1: " + "%.2f" % self.controller.accel1K_Y[-1] + " m/s^2"
        self.lbl_accel1K_Z["text"] = "Z1: " + "%.2f" % self.controller.accel1K_Z[-1] + " m/s^2"
        self.lbl_pres1U["text"] = "Pressure 1: " + "%.2f" % self.controller.pres1U[-1] + " psi"
        
        if self.is_open_page: # As long as LRF is the open page, keep updating labels
            self.after(200, self.update_labels)
    
    # Updates thermocouple graph every second
    def update_thermo(self, i):
        self.line_thermo1A.set_data(self.controller.LRF_thermo_time_count[-5:-1], self.controller.thermo1A[-5:-1])
        self.line_thermo1B.set_data(self.controller.LRF_thermo_time_count[-5:-1], self.controller.thermo1B[-5:-1])
        self.ax_thermo.set_xlim(self.controller.LRF_thermo_time_count[-5], self.controller.LRF_thermo_time_count[-1])
        
        return self.line_thermo1A, self.line_thermo1B
    
    # Updates accelerometer graph ~5 times a second
    def update_accel(self, i):
        self.line_accel1K_X.set_data(self.controller.LRF_accel_pres_time_count[-10:-1], self.controller.accel1K_X[-10:-1])
        self.line_accel1K_Y.set_data(self.controller.LRF_accel_pres_time_count[-10:-1], self.controller.accel1K_Y[-10:-1])
        self.line_accel1K_Z.set_data(self.controller.LRF_accel_pres_time_count[-10:-1], self.controller.accel1K_Z[-10:-1])
        self.ax_accel.set_xlim(self.controller.LRF_accel_pres_time_count[-10], self.controller.LRF_accel_pres_time_count[-1])
        
        # Experimenting with variable y-axis, would need updating labels though which blit can't handle
        #min_value = min(self.controller.accel1K_X + self.controller.accel1K_Y + self.controller.accel1K_Z)
        #max_value = max(self.controller.accel1K_X + self.controller.accel1K_Y + self.controller.accel1K_Z)
        #self.ax_accel.set_ylim(min_value - 2, max_value + 2)
    
        if not self.is_open_page: # when LRF no longer open page, stop animating graphs
            self.animate_thermo.event_source.stop() # stop thermo and pres here too, update_thermo too slow sometimes
            self.animate_accel.event_source.stop()
            self.animate_pres.event_source.stop()
    
        return self.line_accel1K_X, self.line_accel1K_Y, self.line_accel1K_Z
    
    # Updates pressure graph ~5 times a second
    def update_pres(self, i):
        self.line_pres1U.set_data(self.controller.LRF_accel_pres_time_count[-10:-1], self.controller.pres1U[-10:-1])
        self.ax_pres.set_xlim(self.controller.LRF_accel_pres_time_count[-10], self.controller.LRF_accel_pres_time_count[-1])
     
        return self.line_pres1U,
  
  
'''
' COMPRESSOR PIT PAGE
'''
class CompressorPitPage(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        # Attributes
        self.is_open_page = False
        
        self.color_bg = "#5efc56" #lime green
        
        # Design
        self.configure(bg = self.color_bg)
        
        # Widgets
        lbl_title = tk.Label(self, text = "Compressor Pit", font = controller.font_facility_title, bg = self.color_bg) #info
        lbl_title.grid(row = 0, column = 0, columnspan = 19, pady = 5)
        
        self.lbl_time = tk.Label(self, text = "Time goes here", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_time.grid(row = 0, column = 0, pady = 5, sticky = "NW")
        
        btn_home = tk.Button(self, text = "Home", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("Home"))
        btn_home.configure(bg = controller.color_button_bg) #menu
        btn_home.place(x = 400, y = 50)
        #btn_home.grid(row = 1, column = 6, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        btn_LRF = tk.Button(self, text = "LRF", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("LRF"))
        btn_LRF.configure(bg = controller.color_button_bg) #menu
        btn_LRF.place(x = 675, y = 50)
        #btn_LRF.grid(row = 1, column = 8, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        btn_Vise = tk.Button(self, text = "Vise", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("Vise"))
        btn_Vise.configure(bg = controller.color_button_bg) #menu
        btn_Vise.place(x = 950, y = 50)
        #btn_TTF.grid(row = 1, column = 10, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        btn_TTF = tk.Button(self, text = "TTF", width = 15, height = 2, font = controller.font_button, command = lambda:controller.show_page("TTF"))
        btn_TTF.configure(bg = controller.color_button_bg) #menu
        btn_TTF.place(x = 1225, y = 50)
        #btn_TTF.grid(row = 1, column = 12, columnspan = 2, padx = 10, pady = 20, sticky = "EW")
        
        lbl_hor_spacer1 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer1.grid(row = 1, column = 0, rowspan = 2, padx = 5, pady = 30)
        
        lbl_thermocouples = tk.Label(self, text = "Thermocouples", font = controller.font_general_title, bg = self.color_bg) #info
        lbl_thermocouples.grid(row = 3, column = 0, columnspan = 2, padx = 5, pady = 15, sticky = "W")
        
        self.lbl_thermo1A = tk.Label(self, text = "Thermocouple 1: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_thermo1A.grid(row = 4, column = 0, columnspan = 2, padx = 5, pady = 5, sticky = "W")
        
        self.lbl_thermo1B = tk.Label(self, text = "Thermocouple 2: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_thermo1B.grid(row = 5, column = 0, columnspan = 2, padx = 5, pady = 5, sticky = "W")
        
        lbl_hor_spacer2 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer2.grid(row = 6, column = 0, padx = 5, pady = 20)
        
        lbl_accelerometers = tk.Label(self, text = "Accelerometers", font = controller.font_general_title, bg = self.color_bg) #info
        lbl_accelerometers.grid(row = 7, column = 0, columnspan = 2, padx = 5, pady = 15, sticky = "W")
        
        self.lbl_accel1K_X = tk.Label(self, text = "X: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_accel1K_X.grid(row = 8, column = 0, padx = 5, pady = 5, sticky = "W")
        
        self.lbl_accel1K_Y = tk.Label(self, text = "Y: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_accel1K_Y.grid(row = 9, column = 0, padx = 5, pady = 5, sticky = "W")
        
        self.lbl_accel1K_Z = tk.Label(self, text = "Z: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_accel1K_Z.grid(row = 10, column = 0, padx = 5, pady = 5, sticky = "W")
        
        lbl_hor_spacer3 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer3.grid(row = 11, column = 0, padx = 5, pady = 20)
        
        lbl_pres_sensors = tk.Label(self, text = "Pressure Sensors", font = controller.font_general_title, bg = self.color_bg) #info
        lbl_pres_sensors.grid(row = 12, column = 0, columnspan = 2, padx = 5, pady = 15, sticky = "W")
        
        self.lbl_pres1U = tk.Label(self, text = "Pressure 1: ", font = controller.font_data, bg = self.color_bg) #data
        self.lbl_pres1U.grid(row = 13, column = 0, columnspan = 2, padx = 5, pady = 5, sticky = "W")
        
        lbl_hor_spacer4 = tk.Label(self, text = "", bg = self.color_bg)
        lbl_hor_spacer4.grid(row = 14, column = 0, padx = 5, pady = 75)
        
        btn_quit = tk.Button(self, text = "Quit", width = 15, height = 2, font = controller.font_button, command = exit)
        btn_quit.configure(bg = controller.color_button_bg) #quit button
        btn_quit.grid(row = 15, column = 18, columnspan = 2, padx = 30, pady = 10, sticky = "W")
        
        lbl_vert_spacer1 = tk.Label(self, text = "", width = 5, bg = self.color_bg)
        lbl_vert_spacer1.grid(row = 3, column = 3, rowspan = 12, padx = 5)
        
        lbl_vert_spacer2 = tk.Label(self, text = "", width = 4, bg = self.color_bg)
        lbl_vert_spacer2.grid(row = 3, column = 19, rowspan = 10, padx = 5)
        
        # Thermocouple Plot Setup
        self.fig_thermo = plt.Figure(figsize = (15, 3), dpi = 100)
        self.ax_thermo = self.fig_thermo.add_subplot()
        self.ax_thermo.set_title("Compressor Pit Temperatures", fontsize = 20)
        self.ax_thermo.set_xlabel("Time [s]", fontsize = 15)
        self.ax_thermo.set_ylabel("Temperature [F]", fontsize = 15)
        self.ax_thermo.set_ylim(65, 95)
        self.ax_thermo.tick_params(axis = 'x', labelbottom = False) # removes x-axis tick labels
        self.ax_thermo.tick_params(axis = 'y', labelsize = 12)
        
        self.line_thermo1A, = self.ax_thermo.plot([], [], linewidth = 3, color = "orange", label = "TC 1") # create thermocouple lines here
        self.line_thermo1B, = self.ax_thermo.plot([], [], linewidth = 3, color = "blue", label = "TC 2")
        self.ax_thermo.legend(fontsize = 15)
        
        # Accelerometer Plot Setup
        self.fig_accel = plt.Figure(figsize = (8, 4.5), dpi = 100)
        self.ax_accel = self.fig_accel.add_subplot()
        self.ax_accel.set_title("Compressor Pit Vibrations", fontsize = 20)
        self.ax_accel.set_xlabel("Time [s]", fontsize = 15)
        self.ax_accel.set_ylabel("Acceleration [m/s^2]", fontsize = 15)
        self.ax_accel.set_ylim(-6, 6)
        self.ax_accel.tick_params(axis = 'x', labelbottom = False)
        self.ax_accel.tick_params(axis = 'y', labelsize = 12)
        
        self.line_accel1K_X, = self.ax_accel.plot([], [], linewidth = 3, color = "red", label = 'X') # create accelerometer lines here
        self.line_accel1K_Y, = self.ax_accel.plot([], [], linewidth = 3, color = "green", label = 'Y')
        self.line_accel1K_Z, = self.ax_accel.plot([], [], linewidth = 3, color = "magenta", label = 'Z')
        self.ax_accel.legend(fontsize = 15)
        
        # Pressure Transducer Plot Setup
        self.fig_pres = plt.Figure(figsize = (6.88, 4.5), dpi = 100)
        self.ax_pres = self.fig_pres.add_subplot()
        self.ax_pres.set_title("Compressor Pit Pressure", fontsize = 20)
        self.ax_pres.set_xlabel("Time [s]", fontsize = 15)
        self.ax_pres.set_ylabel("Vacuum Pressure [psi]", fontsize = 15)
        self.ax_pres.set_ylim(0, 20)
        self.ax_pres.tick_params(axis = 'x', labelbottom = False)
        self.ax_pres.tick_params(axis = 'y', labelsize = 12)
        
        self.line_pres1U, = self.ax_pres.plot([], [], linewidth = 3, color = "black", label = "Comp. Pit Pres.")
        self.ax_pres.legend(fontsize = 15)
        
        # Plot Widgets
        self.canvas_thermo = FigureCanvasTkAgg(self.fig_thermo, self)
        self.canvas_thermo.draw()
        self.canvas_thermo.get_tk_widget().grid(row = 3, column = 4, rowspan = 5, columnspan = 15, pady = 5, sticky = "W")
        
        self.canvas_accel = FigureCanvasTkAgg(self.fig_accel, self)
        self.canvas_accel.draw()
        self.canvas_accel.get_tk_widget().grid(row = 8, column = 4, rowspan = 7, columnspan = 8, pady = 5, sticky = "NW")
        
        self.canvas_pres = FigureCanvasTkAgg(self.fig_pres, self)
        self.canvas_pres.draw()
        self.canvas_pres.get_tk_widget().grid(row = 8, column = 12, rowspan = 7, columnspan = 7, padx = 12, pady = 5, sticky = "NW")
        
    # Runs every time the page is opened
    def start_up(self):
        self.after(500, self.update_labels)
        self.animate_thermo = animation.FuncAnimation(self.fig_thermo, self.update_thermo, interval = 1000, blit = True)
        self.animate_accel = animation.FuncAnimation(self.fig_accel, self.update_accel, interval = 160, blit = True)
        self.animate_pres = animation.FuncAnimation(self.fig_pres, self.update_pres, interval = 160, blit = True)
    
    # Updates the data labels on the current page                   
    def update_labels(self):
        self.lbl_time["text"] = self.controller.time[-1]
        self.lbl_thermo1A["text"] = "Thermocouple 1: " + "%.2f" % self.controller.thermo1A[-1] + " F"
        self.lbl_thermo1B["text"] = "Thermocouple 2: " + "%.2f" % self.controller.thermo1B[-1] + " F"
        self.lbl_accel1K_X["text"] = "X1: " + "%.2f" % self.controller.accel1K_X[-1] + " m/s^2"
        self.lbl_accel1K_Y["text"] = "Y1: " + "%.2f" % self.controller.accel1K_Y[-1] + " m/s^2"
        self.lbl_accel1K_Z["text"] = "Z1: " + "%.2f" % self.controller.accel1K_Z[-1] + " m/s^2"
        self.lbl_pres1U["text"] = "Pressure 1: " + "%.2f" % self.controller.pres1U[-1] + " psi"
        
        if self.is_open_page: # As long as LRF is the open page, keep updating labels
            self.after(200, self.update_labels)
    
    # Updates thermocouple graph every second
    def update_thermo(self, i):
        self.line_thermo1A.set_data(self.controller.LRF_thermo_time_count[-5:-1], self.controller.thermo1A[-5:-1])
        self.line_thermo1B.set_data(self.controller.LRF_thermo_time_count[-5:-1], self.controller.thermo1B[-5:-1])
        self.ax_thermo.set_xlim(self.controller.LRF_thermo_time_count[-5], self.controller.LRF_thermo_time_count[-1])
        
        return self.line_thermo1A, self.line_thermo1B
    
    # Updates accelerometer graph ~5 times a second
    def update_accel(self, i):
        self.line_accel1K_X.set_data(self.controller.LRF_accel_pres_time_count[-10:-1], self.controller.accel1K_X[-10:-1])
        self.line_accel1K_Y.set_data(self.controller.LRF_accel_pres_time_count[-10:-1], self.controller.accel1K_Y[-10:-1])
        self.line_accel1K_Z.set_data(self.controller.LRF_accel_pres_time_count[-10:-1], self.controller.accel1K_Z[-10:-1])
        self.ax_accel.set_xlim(self.controller.LRF_accel_pres_time_count[-10], self.controller.LRF_accel_pres_time_count[-1])
        
        # Experimenting with variable y-axis, would need updating labels though which blit can't handle
        #min_value = min(self.controller.accel1K_X + self.controller.accel1K_Y + self.controller.accel1K_Z)
        #max_value = max(self.controller.accel1K_X + self.controller.accel1K_Y + self.controller.accel1K_Z)
        #self.ax_accel.set_ylim(min_value - 2, max_value + 2)
    
        if not self.is_open_page: # when LRF no longer open page, stop animating graphs
            self.animate_thermo.event_source.stop() # stop thermo and pres here too, update_thermo too slow sometimes
            self.animate_accel.event_source.stop()
            self.animate_pres.event_source.stop()
    
        return self.line_accel1K_X, self.line_accel1K_Y, self.line_accel1K_Z
    
    # Updates pressure graph ~5 times a second
    def update_pres(self, i):
        self.line_pres1U.set_data(self.controller.LRF_accel_pres_time_count[-10:-1], self.controller.pres1U[-10:-1])
        self.ax_pres.set_xlim(self.controller.LRF_accel_pres_time_count[-10], self.controller.LRF_accel_pres_time_count[-1])
     
        return self.line_pres1U,
        
        
'''
' PROGRAM EXECUTION BEGINS HERE
'''
# Initialize GPIO pins
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(16, GPIO.OUT, initial = GPIO.LOW) # Start in receiving mode (good practice, don't want multiple devices in transmitting mode at once)

# Begin serial connection
try:
    ser = serial.Serial("/dev/ttyAMA0", 115200, timeout = 1) # tries opening serial port to LRF Arduino board
except:
    print("Serial port not connected.")

# Creates count objects that are used for graphing purposes
LRF_thermo_counter = count()
LRF_accel_pres_counter = count()
VISE_thermo_counter = count()
VISE_accel_pres_counter = count()

# Creates HealthMonitor object, starts up the GUI
root = HealthMonitor()

# This calls a loop that will continuously update the GUI and wait for any user input
root.mainloop()