# GTL-SEHMS
Code used for Arduinos and Raspberry Pi to control the Supplemental Equipment Health Monitoring System at the OSU Gas Turbine Laboratory.

three_arduinos_peripheral_one.ino corresponds to the LRF Arduino board. In its current form, it expects two thermocouples, one accelerometer, and one pressure transducer to be connected to the board.

three_arduinos_peripheral_two.ino corresponds to the VISE Arduino board. In its current form, it is sending dummy code to the Pi.

health_monitoring_system_copy.py is the code that begins upon start up of the Raspberry Pi. It can also be started by running the Thonny program located on the Desktop. Currently, only the LRF and VISE pages are operational, since they are the only ones with machines to monitor. The Compressor Pit and TTF are simply copies of the LRF page's data.

Reach out to main.619@buckeyemail.osu.edu if you have any questions about the code or SEHMS itself. Good luck!
