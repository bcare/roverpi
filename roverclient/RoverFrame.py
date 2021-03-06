# -*- coding: utf-8 -*-
#
# generated by wxGlade 0.6.8 on Sat Mar 26 19:54:33 2016
#
import sys

        
import wx
import wx.html2

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode
# end wxGlade

from time import sleep

from multiprocessing import JoinableQueue, Queue, Event, Lock, Manager, Pipe

import pylibconfig2 as pycfg

from commontools import *
from clientsession import ClientSession, LogProcess
from widgetstates import WidgetState, StatesGroup

##############################
## Global internals
##############################

BASE_FOLDER = normalize_path(os.path.dirname(__file__))

if hasattr(sys, 'frozen'):
        ### if bundle :
        if hasattr(sys, '_MEIPASS'):
                meipass = sys._MEIPASS
        else:
                meipass = sys._MEIPASS2
        BASE_FOLDER = normalize_path(os.path.dirname(meipass+'/rvclient'))
        print "meipass",meipass

CONFIGS_PATH = os.path.join(BASE_FOLDER,'configs')
GUIDATA_PATH = os.path.join(BASE_FOLDER,'guidata')

DEFAULT_CONFIG_FILE = os.path.join(CONFIGS_PATH, 'config_example.txt')

WIDGET_STATES_FILES = ["initial.txt",\
                       "session_disconnected.txt",\
                       "session_connected.txt",\
                       "controls_on.txt",\
                       "video_on.txt",\
                       "video_off.txt"]


FETCH_RX_TIMER_PERIOD_MS = 200
TIMER_PERIOD_DRIVE_INPUT_MS = 80

KEYMAP_DEFAULT = {"drive":{\
                           wx.WXK_NUMPAD8 : "north",\
		           wx.WXK_NUMPAD9 : "north_east",\
		           wx.WXK_NUMPAD6 : "east",\
		           wx.WXK_NUMPAD3 : "south_east" ,\
		           wx.WXK_NUMPAD2 : "south",\
		           wx.WXK_NUMPAD1 : "south_west",\
		           wx.WXK_NUMPAD4 : "west",\
		           wx.WXK_NUMPAD7 : "north_west",\
		           wx.WXK_NUMPAD5 : "stop"}}


class RoverFrame(wx.Frame):
	def __init__(self, *args, **kwds):
		# begin wxGlade: RoverFrame.__init__
		kwds["style"] = wx.DEFAULT_FRAME_STYLE
		wx.Frame.__init__(self, *args, **kwds)

                # This is need it for WebkitGTK Panel with  wxPython2.8,
                # for 2.6 doesnt hurt
                self.SendSizeEvent()

                ############ Widgets #######################


                ### Config ###
                self.label_configfile = wx.StaticText(self, wx.ID_ANY, _("Client Configuration File"))
                self.textctrl_configfile = wx.TextCtrl(self, wx.ID_ANY, "")
                self.button_load_config = wx.Button(self, wx.ID_ANY, _("Load Configuration File"))
		self.sizer_config_staticbox = wx.StaticBox(self, wx.ID_ANY, _("Configuration"))

                ### Connection parameters ###

		self.label_connection_host = wx.StaticText(self, wx.ID_ANY, _("Rover Host"))
		self.textctrl_connection_host = wx.TextCtrl(self, wx.ID_ANY, "")
		self.label_connection_port_cmd = wx.StaticText(self, wx.ID_ANY, _("Port Command"))
		self.textctrl_connection_port_cmd = wx.TextCtrl(self, wx.ID_ANY, "")
		self.label_connection_video_url = wx.StaticText(self, wx.ID_ANY, _("URL Video"))
		self.textctrl_connection_video_url = wx.TextCtrl(self, wx.ID_ANY, "")

                ### Connection controls ###

		self.button_connection = wx.Button(self, wx.ID_ANY, _("Connection"))
		self.label_connection_status = wx.StaticText(self, wx.ID_ANY, _("Disconnected"))
		self.button_videofeed = wx.Button(self, wx.ID_ANY, _("Enable video"))
		self.button_take_control = wx.Button(self, wx.ID_ANY, _("Take control"))
		self.sizer_connection_staticbox = wx.StaticBox(self, wx.ID_ANY, _("Connection"))

                ### Drive controls ###

		self.button_headlights = wx.ToggleButton(self, wx.ID_ANY, _("Headlights OFF"))
		self.label_speed = wx.StaticText(self, wx.ID_ANY, _("Speed"), style=wx.ALIGN_CENTRE)
		self.slider_speed = wx.Slider(self, wx.ID_ANY, 0, 0, 10, style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS)


		self.sizer_drive_staticbox = wx.StaticBox(self, wx.ID_ANY, _("Drive controls"))

                ### Audio controls ###

		self.listctrl_audio_files = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_REPORT | wx.SUNKEN_BORDER)
		self.button_fetch_audio_files = wx.Button(self, wx.ID_ANY, _("Get list of audio files"))
		self.button_play_audio_file = wx.Button(self, wx.ID_ANY, _("Play selected audio file"))
		self.textctrl_tts = wx.TextCtrl(self, wx.ID_ANY, _("<Text to speech>"))
		self.button_tts_send = wx.Button(self, wx.ID_ANY, _("Send TTS"))
		self.button_tts_clear = wx.Button(self, wx.ID_ANY, _("Clear TTS"))
		self.sizer_audio_staticbox = wx.StaticBox(self, wx.ID_ANY, _("Audio controls"))

                ### Video ###

                self.webview_videofeed = wx.html2.WebView.New(self)

                ### Console ###

		self.textctrl_console = wx.TextCtrl(self, wx.ID_ANY, _("Rover Client GUI Console\n-----------------------------------------\n"), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP | wx.TE_WORDWRAP)

		self.textctrl_command_prompt = wx.TextCtrl(self, wx.ID_ANY, "")
		self.button_send_command = wx.Button(self, wx.ID_ANY, _("Send command"))
		self.button_clear_command = wx.Button(self, wx.ID_ANY, _("Clear"))

		
                #### Timers ####

                self.timer_drive_input = wx.Timer(self, wx.ID_ANY)
                self.timer_fetch_rx=wx.Timer(self, wx.ID_ANY)

                ##### wxGlade init ######

		self.__set_properties()
		self.__do_layout()
		# end wxGlade


                #######################################################
                ########               APP LOGIC               ########
                #######################################################

                ########### Multiprocessing objects ###############

                ### Events
                self.events = {}
                self.events['log_enable'] = Event()

                ### Queues
                self.queues = {}
                self.queues['log'] = JoinableQueue()
                self.queues['console'] = JoinableQueue()

                ############## Config  #################
                self.cfgfilepath = None
                self.cfg = None
                #self.load_config()

                ############## Session #################

                self.session = None

                ### Logprocess :
                
                self.logprocess = None
                             
                ############## Drive ###################

                self.dict_keymap = {}


                ############# State trackers ##########

                self.controls_on = False
                self.connected_once = False
                self.video_on = False
                self.config_loaded = False
                

                ###############################################
                ####             WIDGET STATES             ####
                ###############################################


                ########### States objects  ############

                
                self.saved_states = StatesGroup(widget_parent=self)

                for statefile in WIDGET_STATES_FILES:
                        filepath = normalize_path(os.path.join(GUIDATA_PATH,statefile))
                        print "fp gui :",filepath
                        self.saved_states.load_from_file(filepath)

                self.current_state = ''
                self.update_state("INITIAL")

                self.previous_direction = 'stop'
                self.current_drive_keys_down = {}

                ###### Special Permanent bindings : ######
                
                ## EVT_CLOSE always stays associated with self.cleanup() 
                self.Bind(wx.EVT_CLOSE, self.h_on_close)

                ## timer for getting Rx updates :
                self.Bind(wx.EVT_TIMER, self.h_on_timer_fetch_rx, self.timer_fetch_rx)
                
                ## timer for taking in drive input (
                self.Bind(wx.EVT_TIMER, self.h_on_timer_drive_input, self.timer_drive_input)


                ########## Final operations before firing up the GUI : #########
                if len(sys.argv) > 1:
                        original_cfg_file = normalize_path(sys.argv[1])
                else:
                        original_cfg_file = DEFAULT_CONFIG_FILE
                self.textctrl_configfile.SetValue(original_cfg_file)

	def __set_properties(self):
		# begin wxGlade: RoverFrame.__set_properties
		self.SetTitle(_("Rover Client GUI"))
		self.SetSize((1280, 960))
		self.SetBackgroundColour(wx.Colour(240, 240, 240))
		self.label_connection_host.SetMinSize((150, 20))
		self.label_connection_port_cmd.SetMinSize((150, 20))
		self.label_connection_video_url.SetMinSize((150, 20))
                self.textctrl_connection_host.SetMinSize((250, 20))
		self.textctrl_connection_port_cmd.SetMinSize((250, 20))
		self.textctrl_connection_video_url.SetMinSize((250, 20))
                
		self.webview_videofeed.SetMinSize((800, 600))
		# end wxGlade
            

	def __do_layout(self):
		# begin wxGlade: RoverFrame.__do_layout
		sizer_main = wx.BoxSizer(wx.HORIZONTAL)
		sizer_feedconsole = wx.BoxSizer(wx.VERTICAL)
		sizer_command = wx.BoxSizer(wx.HORIZONTAL)
		sizer_controls = wx.BoxSizer(wx.VERTICAL)
		self.sizer_audio_staticbox.Lower()
		sizer_audio = wx.StaticBoxSizer(self.sizer_audio_staticbox, wx.VERTICAL)
		sizer_text2speech = wx.BoxSizer(wx.VERTICAL)
		sizer_tts_actions = wx.BoxSizer(wx.HORIZONTAL)
		sizer_audio_actions = wx.BoxSizer(wx.HORIZONTAL)
		self.sizer_drive_staticbox.Lower()
		sizer_drive = wx.StaticBoxSizer(self.sizer_drive_staticbox, wx.VERTICAL)
		sizer_speed = wx.BoxSizer(wx.HORIZONTAL)
		self.sizer_connection_staticbox.Lower()
		sizer_connection = wx.StaticBoxSizer(self.sizer_connection_staticbox, wx.VERTICAL)
		gridsizer_connection_actions = wx.GridSizer(2, 2, 0, 0)
		sizer_connection_parameters = wx.BoxSizer(wx.VERTICAL)
		sizer_connection_video = wx.BoxSizer(wx.HORIZONTAL)
		sizer_connection_port_cmd = wx.BoxSizer(wx.HORIZONTAL)
		sizer_connection_host = wx.BoxSizer(wx.HORIZONTAL)
		self.sizer_config_staticbox.Lower()
		sizer_config = wx.StaticBoxSizer(self.sizer_config_staticbox, wx.VERTICAL)
		sizer_config.Add(self.label_configfile, 0, 0, 0)
		sizer_config.Add(self.textctrl_configfile, 0, wx.EXPAND, 0)
		sizer_config.Add(self.button_load_config, 0, 0, 0)
		sizer_controls.Add(sizer_config, 0, wx.EXPAND, 1)
		sizer_connection_host.Add(self.label_connection_host, 0, 0, 0)
		sizer_connection_host.Add(self.textctrl_connection_host, 1, wx.EXPAND, 0)
		sizer_connection_parameters.Add(sizer_connection_host, 1, 0, 0)
		sizer_connection_port_cmd.Add(self.label_connection_port_cmd, 0, 0, 0)
		sizer_connection_port_cmd.Add(self.textctrl_connection_port_cmd, 0, wx.EXPAND, 0)
		sizer_connection_parameters.Add(sizer_connection_port_cmd, 1, 0, 0)
		sizer_connection_video.Add(self.label_connection_video_url, 0, 0, 0)
		sizer_connection_video.Add(self.textctrl_connection_video_url, 1, wx.EXPAND | wx.ALIGN_RIGHT, 0)
		sizer_connection_parameters.Add(sizer_connection_video, 1, 0, 0)
		sizer_connection.Add(sizer_connection_parameters, 1, 0, 0)
		gridsizer_connection_actions.Add(self.button_connection, 0, wx.EXPAND, 0)
		gridsizer_connection_actions.Add(self.label_connection_status, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
		gridsizer_connection_actions.Add(self.button_videofeed, 0, wx.EXPAND, 0)
		gridsizer_connection_actions.Add(self.button_take_control, 0, wx.EXPAND, 0)
		sizer_connection.Add(gridsizer_connection_actions, 1, wx.EXPAND, 0)
		sizer_controls.Add(sizer_connection, 0, wx.EXPAND, 1)
		sizer_drive.Add(self.button_headlights, 0, 0, 0)
		sizer_speed.Add(self.label_speed, 0, 0, 0)
		sizer_speed.Add(self.slider_speed, 6, 0, 0)
		sizer_drive.Add(sizer_speed, 1, wx.EXPAND, 0)
		sizer_controls.Add(sizer_drive, 0, wx.EXPAND, 2)
		sizer_audio.Add(self.listctrl_audio_files, 1, wx.EXPAND, 0)
		sizer_audio_actions.Add(self.button_fetch_audio_files, 1, 0, 0)
		sizer_audio_actions.Add(self.button_play_audio_file, 0, 0, 0)
		sizer_audio.Add(sizer_audio_actions, 0, 0, 0)
		sizer_text2speech.Add(self.textctrl_tts, 0, wx.EXPAND, 0)
		sizer_tts_actions.Add(self.button_tts_send, 0, wx.EXPAND, 0)
		sizer_tts_actions.Add(self.button_tts_clear, 0, wx.EXPAND, 0)
		sizer_text2speech.Add(sizer_tts_actions, 1, wx.EXPAND, 0)
		sizer_audio.Add(sizer_text2speech, 0, wx.EXPAND, 0)
		sizer_controls.Add(sizer_audio, 1, wx.EXPAND, 2)
		sizer_main.Add(sizer_controls, 1, wx.EXPAND, 0)
		sizer_feedconsole.Add(self.webview_videofeed, 4, wx.EXPAND | wx.FIXED_MINSIZE, 0)
		sizer_feedconsole.Add(self.textctrl_console, 1, wx.EXPAND, 0)
		sizer_command.Add(self.textctrl_command_prompt, 2, wx.EXPAND, 0)
		sizer_command.Add(self.button_send_command, 0, 0, 0)
		sizer_command.Add(self.button_clear_command, 0, 0, 0)
		sizer_feedconsole.Add(sizer_command, 0, wx.EXPAND, 0)
		sizer_main.Add(sizer_feedconsole, 2, wx.EXPAND | wx.ALIGN_RIGHT, 0)
		self.SetSizer(sizer_main)
		self.Layout()

                
        ################ Init ################################################


        def load_keymap(self):
                ## load the default fist
                self.dict_keymap = KEYMAP_DEFAULT
                ## then load the keymap provided in the config file if any
                if self.cfg.lookup("keymap"):
                        kmgroup=self.cfg.get("keymap")
                        for acgrp_name in kmgroup.keys():
                                actiongroup = kmgroup.get(acgrp_name)
                                for key in actiongroup.keys():
                                        self.dict_keymap[acgrp_name][getattr(wx,"WXK_"+key)] = actiongroup.get(key)
                print self.dict_keymap
                

        def init_drive_key_tracker(self):
                self.current_drive_keys_down = dict([(key, False) for key in self.dict_keymap['drive'].values()])
                self.previous_direction = 'stop'
                
        ################ Internal widgets states / bindings updaters #########

        def update_state(self, newstate, uncommit=False):
                #print 'from *%s* to *%s*'%(self.current_state, newstate)
                if newstate != self.current_state:
                        if uncommit:
                                self.saved_states.uncommit(self.current_state)
                        self.saved_states.commit(newstate)
                        self.current_state = newstate

                                    
        ################ WIDGET EVENTS HANDLER ##########

        def h_on_idle(self, evt):
               self.update_gui()
        
        def h_on_load_config(self, evt):
                self.load_config()
                self.config_loaded = True
                self.logprocess_create()
                self.update_gui()
                #self.update_state('SESSION_DISCONNECTED')

                
        #### Connection controls 
                
        def h_on_close(self,evt):
                self.cleanup()

        def h_on_connect(self, evt):
                
                if self.session is not None:
                        self.session_close()
                        
                self.flush_console_queue_to_gui()
                ### Maybe the ports/host values changed
                ### update the config :
                self.cfg.network.address = str(self.textctrl_connection_host.GetValue())
                self.cfg.network.port_command = int(self.textctrl_connection_port_cmd.GetValue())
                self.cfg.network.video_url = str(self.textctrl_connection_video_url.GetValue())
                        
                self.session_create()
                self.session_connect()
                self.connected_once = True
                self.update_gui()
                
        
                

        def h_on_disconnect(self, evt):
                self.flush_console_queue_to_gui()
                if self.session is not None:
                        self.deactivate_drive_controls()
                        self.session_close()
                        self.session = None
                        
                self.update_gui()
                        
                        
        def h_on_take_control(self, evt):
                self.controls_on=True
                self.init_drive_key_tracker()
                self.activate_drive_controls()
                self.update_gui()

        def h_on_release_control(self, evt):
                self.controls_on=False
                self.deactivate_drive_controls()
                self.update_gui()

        def h_on_enable_videofeed(self, evt):
                ## update the config, maybe the user set another URL:
                self.cfg.network.video_url = str(self.textctrl_connection_video_url.GetValue())
                self.webview_videofeed.LoadURL(self.cfg.network.video_url)
                self.video_on = True
                self.update_gui()

        def h_on_disable_videofeed(self, evt):
                self.video_on = False
                self.webview_videofeed.LoadURL("")
                self.update_gui()

        #### Audio controls ####

        def h_on_play_audio_file(self, evt):
                pass

        def h_on_fetch_audio_files(self, evt):
                pass

        def h_on_tts_send(self, evt):
                pass

        def h_on_tts_clear(self, evt):
                pass

        #### Commands controls ####

        def h_on_clear_command(self, evt):
                self.textctrl_command_prompt.SetValue("")

        def h_on_send_command(self, evt):
                cmdstring = self.textctrl_command_prompt.GetValue()
                self.to_log_and_console("Sending command:\"%s\"\n"%cmdstring)
                self.session.comms_push_command(cmdstring)
                self.h_on_clear_command(None)

        def h_on_timer_fetch_rx(self, evt):
                ## Request a status update

                ## Update the GUI
                self.update_gui()
        
                
        
        #### keyboard controls ####


        def h_on_key_up(self, evt):
                keycode = evt.GetKeyCode()
                print "key up",keycode
                if keycode in self.dict_keymap['drive']:
                        self.current_drive_keys_down[self.dict_keymap['drive'][keycode]] = False
                        self.update_drive_command()
                evt.Skip()

        def h_on_key_down(self, evt):
                keycode = evt.GetKeyCode()
                print "key down", keycode
                
                self.timer_drive_input.Start(TIMER_PERIOD_DRIVE_INPUT_MS)

                ### hack : simply poll the state of the drive keys anytime a key is pressed
                for keycode in self.dict_keymap['drive']:
                        self.current_drive_keys_down[self.dict_keymap['drive'][keycode]] = wx.GetKeyState(keycode)
                        self.update_drive_command()
                evt.Skip()

        def h_on_timer_drive_input(self, evt):
                for keycode in self.dict_keymap['drive']:
                        self.current_drive_keys_down[self.dict_keymap['drive'][keycode]] = wx.GetKeyState(keycode)
                        self.update_drive_command()
        



        ################## ACTIONS #######################

        def update_gui(self):

                ret=False

                self.flush_console_queue_to_gui()
                

                if self.session is not None:
                        ret=self.session.analyze_received_messages(self.session.fetch_rx())
                        
                        ## are we still connected to the rover ?
                        if  (not self.session.is_rover_connected()) or (ret==False):
                                self.update_state("SESSION_DISCONNECTED")
                                self.timer_fetch_rx.Stop()
                        else:
                                self.timer_fetch_rx.Start(FETCH_RX_TIMER_PERIOD_MS)
                                if self.controls_on:
                                        self.update_state("CONTROLS_ON")
                                else:
                                        self.update_state("SESSION_CONNECTED")


                else:
                        self.update_state("SESSION_DISCONNECTED")


                if self.video_on:
                        self.update_state("VIDEO_ON")
                else:
                        self.update_state("VIDEO_OFF")
                        
                #print self.current_state
                        
                        

        def print_to_console(self, msg):
                self.textctrl_console.AppendText(msg)

        def to_log_and_console(self, msg):
                self.print_to_console(msg)
                self.queues['log'].put(msg)

        def flush_console_queue_to_gui(self):
                while self.queues['console'].empty()==False:
                        self.print_to_console(self.queues['console'].get())
                        self.queues['console'].task_done()

        def load_config(self):

                #### Logging might not be enabled yet at this stage so
                #### be careful where you send the log messages

                self.cfgfilepath = normalize_path(self.textctrl_configfile.GetValue())
                try:
                        self.cfg = pycfg.Config()
                        self.cfg.read_file(self.cfgfilepath)

                        self.print_to_console("Successfully loaded configuration file \"%s\".\n"%self.cfgfilepath)

                        #### Load network config ####

                        if self.cfg.lookup('network.address'):
                                #self.textctrl_host.Clear()
                                self.textctrl_connection_host.ChangeValue(self.cfg.network.address)
                        else:
                                self.print_to_console("No rover host address specified in config file.\n")

                        if self.cfg.lookup('network.port_command'):
                                #self.textctrl_port_cmd.Clear()
                                self.textctrl_connection_port_cmd.ChangeValue(str(self.cfg.network.port_command))
                        else:
                                self.print_to_console("No rover command port specified in config file.\n")

                        if self.cfg.lookup('network.video_url'):
                                self.textctrl_connection_video_url.ChangeValue(str(self.cfg.network.video_url))
                        else:
                                self.print_to_console("No rover video port specified in config file.\n")

                        #### Load Keymap ####
                        
                        self.load_keymap()

                        
                except Exception as e:
                        self.print_to_console('Error: could not load config file \"%s\" (%s).\n'%(self.cfgfilepath, e))

                

        def logprocess_create(self):
                ### The log process is independent and launched by the RoverFrame object to enable logging
                ### at early stages of the app execution (i.e. before the ClientSession is created).
				### Config should be loaded though.

                if self.logprocess is not None:
                        self.events['log_enable'].clear()

		if self.cfg.lookup('general.logfile'):
                        logfile=self.cfg.general.logfile
		else:
			logfile="log.txt"
                        
			logfile = normalize_path(logfile)

                overwrite = False
		if self.cfg.lookup('general.log_overwrite'):
			overwrite = self.cfg.general.log_overwrite
                        
                try:
                        self.logprocess = LogProcess(override=overwrite,logfilepath=logfile,queues={'log':self.queues['log']}, events={'log_enable':self.events['log_enable']})

                        self.logprocess.start()

                        self.events['log_enable'].set()
                        self.print_to_console('Logging to file \"%s\".\n'%logfile)
                        sleep(0.1)
                        self.queues['log'].put(self.textctrl_console.GetValue())
                        

                        
                except Exception as e:
                        self.print_to_console('Error: could not initiate logging : %s.\nTry and reload the configuration file ?\n'%e)
                        self.logprocess = None



        ###### Session actions ######

        def session_create(self):
                try:
                        self.session = ClientSession(cfg=self.cfg, queue_log=self.queues['log'],queue_console=self.queues['console'])
                        self.session.init_multiprocessing()
                        self.to_log_and_console("ClientSession object created.\n")
                        self.update_state("SESSION_DISCONNECTED")

                except Exception as e:
                        msg = 'Error: could not create ClientSession : %s\n'%e
                        self.queues['log'].put(msg)
                        self.print_to_console(msg)
                        self.session = None

        def session_connect(self):
                res, msg =self.session.comms_launch_process()

                self.to_log_and_console(msg)
                if res==False:
                        return

                if res==True:
                        res, msg = self.session.comms_enable()
                
                self.to_log_and_console(msg)
                
                if res==True:        
                        #self.update_state("SESSION_CONNECTED")
                        self.timer_fetch_rx.Start(FETCH_RX_TIMER_PERIOD_MS)
                                        
                else:
                        self.update_state("SESSION_DISCONNECTED")

                        
        def session_disconnect(self):
                msg = 'Disconnecting from rover...\n'
                self.to_log_and_console(msg)
                if self.session is not None:
                        self.session.comms_close()
                        
                                
        def session_close(self):
                msg = 'Closing ClientSession ...\n'
                self.to_log_and_console(msg)
                if self.session is not None:
                        self.session.close()
                self.session = None
                

        ############# Drive actions #######################

        def activate_drive_controls(self):
                ### enable the capture of keyboard:
                print "activate controls"
                self.Bind(wx.EVT_CHAR_HOOK, self.h_on_key_down)
                self.Bind(wx.EVT_KEY_UP, self.h_on_key_up)
                
        def deactivate_drive_controls(self):
                self.Bind(wx.EVT_CHAR_HOOK, None)
                self.Bind(wx.EVT_KEY_UP, None)
                self.timer_drive_input.Stop()
                
        def drive_keys_to_direction(self, dictkeys):
                lhs,rhs="",""
                if dictkeys["stop"] == True:
                        ## if it's stop, then stop right here
                        ## and return.
                        return "stop"
                

                ## override if "diagonal" keys are down,
                ## return right away :
                if dictkeys["north_west"] == True:
                        return "north_west"
                if dictkeys["north_east"] == True:
                        return "north_east"
                if dictkeys["south_east"] == True:
                        return "south_east"
                if dictkeys["south_west"] == True:
                        return "south_west"

                ## Else check if this is a combo :
                if dictkeys["north"]==True:
                        lhs="north"
                elif dictkeys["south"] == True:
                        lhs="south"

                if dictkeys["east"] == True:
                        rhs="east"
                elif dictkeys["west"] == True:
                        rhs="west"

                        
                if lhs:
                        if rhs:
                                return lhs+"_"+rhs
                        else:
                                return lhs
                else:
                        if rhs:
                                return rhs
                        else:
                                return "stop"

                        
        def update_drive_command(self):
                where = self.drive_keys_to_direction(self.current_drive_keys_down)
                if where != self.previous_direction:
                        self.previous_direction = where
                        ## if it's stop, send it anyway.
                        self.print_to_console("going %s\n"%where)
                        self.session.rover_drive(where)
        

        ############## CLEANUP ############################


        def cleanup(self):

                self.timer_fetch_rx.Stop()
                self.timer_drive_input.Stop()
                
                #### process cleanup ####
                
                self.session_close()

                while self.queues['log'].empty()==False:
                        print self.queues['log'].get()
                        self.queues['log'].task_done()
                
                self.events['log_enable'].clear()
                if self.logprocess is not None:
                        if self.logprocess.is_alive():
                                self.logprocess.join()

                
                ## Finally :
                self.Destroy()
                

# end of class RoverFrame
