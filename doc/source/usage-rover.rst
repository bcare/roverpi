.. usage-rover-label:

====================
Usage : On the Rover
====================

This page explains how to configure and use roverpi's rover-side code.

.. usage-rover-hardware-label:

Hardware and GPIO
=================

Drive pins
----------

roverpi was originally developped for a 4WD chassis with tracks (a "tank" with two motors per track), but can be 
made to work with other kinds of drives. The rover-side code can be configured
so that you define which and how the GPIO pins of the raspberry pi are used.

The code assumes that each motor of your drive can be controlled using at least two GPIO pins :

* a "direction" pin that sets the direction of rotation (clockwise / counter-clockwise) with
 a digital output (0 or 1)
* a "power" pin that sets the power/speed of rotation with a PWM (`Pulse-width Modulation <https://en.wikipedia.org/pulse_width_modulation>`_) output.

roverpi uses Software PWM thanks to *RPi.GPIO* and *wiringpi* excellent libraries, so you can use any GPIO pin of the raspberry pi as a power pin.

In its current version, **roverpi assumes that left-side motors share the same power pin, and likewise for right-side motors** . Future versions might release this assumption and offer a more flexible GPIO configuration, don't hesitate to contact me if you are interested in this feature.

.. warning::
   I don't recommend that you use the power pins to **directly** power the motors !


Video
-----

The raspberry pi is able to capture video using the Pi Camera Module on the CSI port, or even a standard USB webcam. This can be used to see on the client PC what the rover sees.

roverpi's rover-side code does not offer video streaming capabilities, but the client is able to acces and render a web page with a video stream. Rather than implementing myself a clumsy streaming server, I chose to use eLinux's excellent `RPi-WebCam-Interface <http://elinux.org/RPi-Cam-Web-Interface>`_ software on my rover's raspberry pi to serve the video stream from the Pi Camera Module on a web page, and point my client software to this page.

.. usage-rover-gpio-permissions-label:

System settings
===============

roverpi does not require any special permissions to run, **but the user with which you connect on the raspberry pi and execute the program might not have the permissions to use the GPIO pins**. I personnally recommend that **you don't use the default ``pi`` user on the raspberry pi to run roverpi's code**, for the sake of security. the ``pi`` user has elevated privileges by default, and you shouldn't trust the code I wrote to run with root privileges.

Make sure that the user you intend to login with to run roverpi on the raspberry pi is in the ``gpio`` UNIX group :

.. code-block:: bash

	$> sudo usermod -aG gpio <username>

The final step to make GPIO pins available is to export them. This will create files in ``/dev`` that users in the ``gpio`` group can use to write/read the pins.

There is a bash script shipped with roverpi that will automatically export the GPIO pins you define in a configuration file for you :

.. code-block:: bash

	$> bash roverpi/tools/export_required_pins.sh <path_to_configuration_file>


This script uses the ``gpio`` command that ships with the package ``wiringpi``.


.. usage-rover-config-label:

Configuration
=============

The rvserver.py script requires a configuration file path as a commandline argument.
The configuration file is loaded using ``pyblibconfig2``, so each string value must be double-quoted, and float values must be explicitly defined (e.g. by typing ``0.0`` and not ``0``).

You may find a configuration file example ``config_example.txt`` in the ``roverserver/configs`` folder :

.. code-block:: ini
	:caption: config_example.txt

###################################################
# Roverpi server (rover-side) configuration example
###################################################

### Configuration files are loaded using pylibconfig2
### Comments are prefixed by #
### Strings should be double-quoted ("")


######################
### Network settings :
######################


network =
{
	### This section is mandatory.

	### Listening address accepting 
	### client connections :
	### (e.g. "127.0.0.1" for
	### local connections only
	### or 192.168.X.X for LAN connections)
	address = "192.168.0.10" ;

	### Listening port :
	port = 63000 ;
}


###############
### Internals :
###############

internals =
{
		### Currently unused but might in future versions,
		### not required.
}

####################
### Drive settings :
####################

drive = 
{
	

	### define the available speeds presets :
	### (in percent, any value greater than 100 
	### will be decreased to 100 automatically)
	### Each value defines the percentage
	### of the PWM duty cycle w.r.t the PWM period
	### that will be used when the speed setting
	### is selected.

	### Default speeds :
	#speeds = (10,20,50,100);
	
	### Drive vectors :

	vectors =
	{
	
		### A drive vector consists of 6 values
		### that determines how the wheels/tracks
		### move when a drive command is sent to the rover.
		### These are optionals, the rover server code
		### includes default values (see below).

		### The expected values are :
		### (PWM_LEFT, PWM_RIGHT, DIR_ForLeft, DIR_ForRight, \
		###	DIR_RearLeft, DIR_RearRight),
		### meaning :	

		### PWM_LEFT :  float between 0.0 and 1.0
		### 		 Fraction of power applied to the left 
		###			 side trains (1.0 being the maximum 
		### 		 defined by the current speed setting selected

		### PWM_RIGHT : float between 0.0 and 1.0
		### 		 Fraction of power applied to the right 
		###			 side trains (1.0 being the maximum 
		### 		 defined by the current speed setting selected

		### DIR_ForLeft : integer 0 or 1
		###				Output value on the GPIO pin
		###				that will determine the direction
		###				of rotation of the forward left 
		###				motor.

		### DIR_ForRight : integer 0 or 1
		###				Output value on the GPIO pin
		###				that will determine the direction
		###				of rotation of the forward right 
		###				motor.

		### DIR_RearLeft : integer 0 or 1
		###				Output value on the GPIO pin
		###				that will determine the direction
		###				of rotation of the forward right
		###				motor.

		### DIR_RearRight : integer 0 or 1
		###				Output value on the GPIO pin
		###				that will determine the direction
		###				of rotation of the forward right
		###				motor.

		### These are the defaults, 
		### They are set based on the
		### 4WD tracked chassis I used
		### to build my rover.

        #north = (1.0,1.0,1,1,0,0) ;
        #north_east = (0.8,0.2,1,1,0,0) ;
        #east = (1.0,1.0,1,0,0,1) ;
        #south_east = (0.5,0.2,0,0,1,1) ;
        #south = (1.0,1.0,0,0,1,1) ;
        #south_west = (0.2,0.8,0,0,1,1) ;
        #west = (1.0,1.0,0,1,1,0) ;
        #north_west = (0.2,0.5,1,1,0,0) ;
        #full_stop = (0,0,0,0,0,0) ;

	}
}

##################
## GPIO settings :
##################


gpio = {
	 
	 ### GPIO settings determine how the software
	 ### will transmit orders to the GPIO Pins
	 ### based on commands received from the client.

	 ### roverpi uses software PWM to emulate
	 ### PWM on the raspberry pi's non-PWM
	 ### pins.
	 ### pwm_freq determines the frequency
	 ### of the PWM duty cycle
	 ### Software PWM cannot go faster than
	 ### 50kHZ, sub-kHz values are usually
	 ### a good choice.

	 #pwm_freq = 500 ; #default PWM frequency in Hz

	 ### GPIO maps :
	 ### Here you can define which pins
	 ### you use on the raspberry pi
	 ### to control your motors.
	 ### roverpi uses the BCM numbering scheme.

	 ### pin that controls the power sent
	 ### to the left-side motors :
	 pin_pwm_left = 20;
	 
	 ### pin that controls the power sent
	 ### to the right-side motors :
	 pin_pwm_right = 21;

	 ### pins that control the direction
	 ### of motors
	 pin_direction_left_forward = 6;
	 pin_direction_right_forward = 13;
	 pin_direction_left_rear = 19 ;
	 pin_direction_right_rear = 26;
	 
	 ### pin that switches on/off 
	 ### headlights :
	 ### (not implemented yet in software,
	 ### but available in my own rover)
	 pin_headlights = 16 ;
 }


Launching the roverpi server
============================

To start listening for a connection, launch the roverpi server :

.. code-block:: bash
				
	$> python roverpi/roverserver/rvserver.py

As long as this command is running, you rover will listen for incoming connections, and if the connection is successful, will execute the command received from the clients. You may start the roverpi client on your PC and attempt to connect to the rover.


Recap example
=============

Let's recap : you downloaded roverpi from github onto the raspberry pi on your rover. You edited a configuration file, specifying the pins you use in your harwdware setup, and the networking parameters.

The startup procedure is :

1. export the GPIO pins :
   .. code-block:: bash
	  
		bash roverpi/tools/export_required_pins.sh <path_to_config_file>

2. Launch the server that will receive commands :
   .. code-block:: bash
				  
		python roverpi/roverserver/rvserver.py <path_to_config_file>

3. On the PC you'll use to control the rover, start the roverpi client


4. When you are done, terminate the python command running the server with Ctrl-C and shut the raspberry pi down.


.. usage-rover-securing-label:

Securing the connection to the rover with SSH
=============================================

roverpi does not include secure networking features such as SSH or TLS. However it is possible to easily encrypt your connection to the rover (remote commands and video) using SSH port forwarding. You may configure the rover-side program to listen only on local connections by setting :

.. code-block:: ini
			
	network = {
				address = "127.0.0.1" ;
				port = 63000 ;
			  }


Then, on your client PC, you may use SSH to forward the port that listens for connections on the rover to another local port on your client PC. Let's say your rover listens for connections locally on port 63000 and you want to forward this port to your client PC's local port 64000. Open a terminal and launch the command :

.. code-block:: bash

   $> ssh -N -L 64000:localhost:63000 user@<rover IP>

The ``-N`` means "don't run any command, just conect" and the "-L" enables local port forwarding. ``user@<rover IP>`` is what you'll typically use to connecto to your rover's raspberry pi with SSH.

As long as this command is running (you may interrupt it with Ctrl-C), all data sent to your client PC's port 64000 will be securely forwarded to your rover's port 63000 through a SSH tunnel. Connections from other hosts will be refused as the rover only "listens to itself" anyway.

If you also have set up a web page with the video stream from your rover that only listens for local connections, you may use the same technique to securely connect to this webpage through SSH. Make sure to use differents ports than the ports you set for roverpi's rover-side program.
