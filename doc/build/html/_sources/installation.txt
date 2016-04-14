============
Installation
============

.. _installation-rover-label:

Installation on the rover
=========================

Roverpi's rover-side code requires a few dependencies. There is no compiled
executable for the server, to run the code just execute the main script with a
python 2.7 interpreter.

Prerequisites
-------------

Hardware and OS
~~~~~~~~~~~~~~~

roverpi was developped and tested on the Raspberry Pi 3, but should work on any
Raspberry Pi SoC version (if you tried it and it failed, `please let me know
<mailto:bertrand.care@gmail.com>`_). If you want video streaming, you may use
the Raspberry Pi camera module, or, provided you can set it up on your system, a
USB webcam. See :ref:`installation-rover-video-label` for more information.

roverpi was developped and tested on raspbian Jessie. If you tried it on another
OS on the raspberry Pi, please let me know if it works.

Python packages
~~~~~~~~~~~~~~~

Install the following packages :

* `wiringpi (system package) <http://wiringpi.com/download-and-install/>`_ (available with ``apt-get``)
* `wiringPi2 (python package) <http://wiringpi.com/download-and-install/>`_ (available with ``pip``)
* `RPi.GPIO <https://pythonhosted.org/RPIO/#installation>`_ (available with ``pip`` or ``apt-get``)
* `pylibconfig2 <https://pypi.python.org/pypi/pylibconfig2/0.2.5>`_ (available with ``pip``)

.. _installation-rover-video-label:

Video support
~~~~~~~~~~~~~

The rover-side code does not feature built-in video streaming (and works
perfectly without any video hardware). You can however setup a third-party
software to enable streaming from the raspberry pi and serve the video stream
through an HTTP(S) page, for example with eLinux's excellent
`RPi-WebCam-Interface <http://elinux.org/RPi-Cam-Web-Interface>`_ The
client-side code is able to browse the web, in order to fetch the video feed you
can simply specifiy the URL of the streaming page in the client and roll with
it.

Installation
------------

Get the source from github :

.. code-block:: bash

	$> git clone https://github.com/bcare/roverpi.git

You can also download a `zip archive of the repository
<https://github.com/bcare/roverpi/archive/master.zip>`_.

The rover-side code is contained in the folders ``roverserver``,
``rovercommons`` and ``tools``. You may delete the ``roverclient`` folder on the
rover if you wish.

There is nothing specific to do once you fetched the sources and installed the
dependencies. You should create and edit a configuration file according to your
raspberry pi setup (for example which GPIO pins you want to use) and your
preferences (see :ref:`config-rover-label`_ and :ref:`usage-rover-label`_).

Your system user on the raspberry pi might not have the permissions to use the
GPIO Pins. There is a bash script that automatically reads a configuration file
and calls wiringpi's ``gpio export`` command to make the pins available :

.. code-block:: bash

	$> bash roverpi/tools/export_required_pins <path_to_config_file>

You can then launch the server that will receive the commands from the client
using :

.. code-block:: bash

	$> cd roverpi/roverserver $> python rvserver.py <path_to_config_file>

See :doc:`/usage-rover` .

Installation of the client
==========================

Standalone executable
---------------------

Standalone executable requiring no installation at all are available for
GNU/Linux and Windows (32btit, but also works on 64bit systems). Just download
the executable and launch it, that's it, it already includes all the
dependencies and does not require any decompressing (it doesn't even require
that python is installed on your system).

Check the download page :

From the sources
----------------

Prerequisites
~~~~~~~~~~~~~

In order to run the client-side code, you will require the following
dependencies

System packages
+++++++++++++++

Install python 2.7 if you don't have it already (on windows select the 32bit
version).

Python packages
+++++++++++++++

The client requires the following python packages :

* ``wxPython`` 3.0.2 or greater (GTK flavor on GNU/Linux)
* ``pyGTK`` 2.24 or greater
* ``pylibconfig2``

Make sure to get `wxpython 3.0.2 <http://wxpython.org/download.php>`_ or
greater. On windows, make sure to install the 32bit version ``win32-py27``. Most
GNU/Linux distributions should include ``wxpython`` in their main package
manager, you'll need ``wxpython`` with GTK widgets. For instance on a
Debian/Ubuntu-like, install the package ``python-wxgtk3.0`` or greater.

You will need ``pyGTK 2.24``. There are `All-in-One installers available for
windows <http://www.pygtk.org/downloads.html>`_, pick the 2.24 (or greater)
32bit for Python 2.7 version). On GNU/Linux, ``pygtk`` is available through most
distribution's package managers, for instance on a Debian/Ubuntu-like with the
package ``python-pygtk2``.


``pylibconfig2`` is available using ``pip`` both on windows and GNU/Linux.


Installation
~~~~~~~~~~~~

Get the source from github :

.. code-block:: bash

	$> git clone https://github.com/bcare/roverpi.git

You can also download a `zip archive of the repository
<https://github.com/bcare/roverpi/archive/master.zip>`_.

The client-side code is contained in the folders ``roverclient`` and
``rovercommons``. You may delete the other folders on your client PC if you
wish.

There is nothing else to do, just execute the file ``roverclient/rvclient.py``
with python (you may provide the path to a configuration file as an argument,
but it is not required,  the client loads an example configuration by default) :

 .. code-block:: bash

	$> cd roverpi/roverclient $> python rvclient.py [<path_to_config_file>]

See :ref:`usage-client-label`_.
