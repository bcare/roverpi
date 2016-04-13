# -*-coding: utf-8 -*-
import sys
import os
from time import sleep 

sys.path.append(os.path.abspath("../rovercommons"))



if sys.platform.startswith('win'):

    # Module multiprocessing is organized differently in Python 3.4+
    try:
        # Python 3.4+
        if sys.platform.startswith('win'):
            import multiprocessing.popen_spawn_win32 as forking
        else:
            import multiprocessing.popen_fork as forking
    except ImportError:
        import multiprocessing.forking as forking

    # First define a modified version of Popen.
    class _Popen(forking.Popen):
        def __init__(self, *args, **kw):
            if hasattr(sys, 'frozen'):
                # We have to set original _MEIPASS2 value from sys._MEIPASS
                # to get --onefile mode working.
                os.putenv('_MEIPASS2', sys._MEIPASS)
            try:
                super(_Popen, self).__init__(*args, **kw)
            finally:
                if hasattr(sys, 'frozen'):
                    # On some platforms (e.g. AIX) 'os.unsetenv()' is not
                    # available. In those cases we cannot delete the variable
                    # but only set it to the empty string. The bootloader
                    # can handle this case.
                    if hasattr(os, 'unsetenv'):
                        os.unsetenv('_MEIPASS2')
                    else:
                        os.putenv('_MEIPASS2', '')

    # Second override 'Popen' class with our modified version.
    forking.Popen = _Popen

from multiprocessing import Process, Queue, JoinableQueue, Event, Lock, Value, Manager, Pipe

from datetime import datetime

import pylibconfig2 as pycfg

from slaveprocess import SlaveProcess
from clientcomms import CommProcess


###########################
### global internals
###########################


FETCH_RX_BURST_SIZE = 1


######################
### Logging facility :
######################

class LogProcess(SlaveProcess):
    def __init__(self,logfilepath='/tmp/roverclient.log', override=False, **kwargs):
        super(LogProcess, self).__init__(**kwargs)
        self.override = override
        self.logfilepath = os.path.abspath(os.path.expandvars(os.path.expanduser(logfilepath)))

    def run(self):
        if self.override == True:
            tempfile = open(self.logfilepath, 'w')
            tempfile.close()

        while self.events['log_enable'].is_set():
            with open(self.logfilepath, 'a') as file:
                if self.queues['log'].empty() == False:
                    msg=self.queues['log'].get()
                    file.write(':'.join(['Rover',datetime.now().strftime("%Y/%m/%d-%H:%M:%S"),msg])+'\n')
                    self.queues['log'].task_done()
            sleep(0.1)

                    

class ClientSession():
    """ Manager object that manages the other subprocesses (comms, commands)
    and interfaces the GUI. This is NOT a process !"""

    def __init__(self,cfg,**kwargs):

        ##### Fetch basic args ######
       
        self.cfg = cfg


        ### log queue is provided by the caller
        self.queue_log = kwargs['queue_log']
        self.queue_console = kwargs['queue_console']
        
        ################################
        ### Session logic objects
        ################################

        self.dict_dispatch_rx = {}

        self.rover_status = {'headlights':False, \
                             'speed':0,\
                             'battery':100.0,\
                             'list_audio_files':[]}

        ################################
        ### Rover control objects
        ################################

        self.dict_rover_drive = {'stop':'DG5',\
                                 'north':'DG8',\
                                 'north_east':'DG9',\
                                 'east':'DG6', \
                                 'south_east':'DG3', \
                                 'south':'DG2', \
                                 'south_west':'DG1', \
                                 'west':'DG4', \
                                 'north_west':'DG7'}
        
        
    def init_multiprocessing(self):

        ######### Multiprocessing #########

        self.events = {}
        self.pipes = {}
        self.locks = {}
        self.queues = {}
        self.managers = {}
        
        
        ######## Events/Sync #########

        self.pipes['comms'] = Pipe()

        self.queues['cmd'] = JoinableQueue()
        self.queues['rx'] = JoinableQueue()
        self.queues['tx'] = JoinableQueue()
        self.queues['log'] = self.queue_log
        self.managers['videoframes'] = Manager().list()

        self.events['comms_enable'] = Event()
        self.events['comms_server_disconnect'] = Event()

        self.drive_lifo = Manager().list()


        ##############################
        ### Processes 
        ##############################

        #### Video : ####
        #self.videoproc = VideoProcess()


        #### Comms : ####
        self.commprocess = CommProcess(events={'enable':self.events['comms_enable'], 'server_disconnect':self.events['comms_server_disconnect']}, \
                                       queues={'log':self.queues['log'],'tx':self.queues['tx'], 'rx':self.queues['rx']},\
                                       pipes={'session':self.pipes['comms'][1]}, \
                                       tx_lifo=self.drive_lifo,
                                       rover_address=self.cfg.network.address,\
                                       rover_port_command=self.cfg.network.port_command)


    #################################
    ## Logging / support
    #################################

    def queue_to_log(self, msg):
        self.queues['log'].put(msg)

    def queue_to_console(self, msg):
        self.queue_console.put(msg)
        
    def queue_to_log_and_console(self, msg):
        self.queue_to_log(msg)
        self.queue_to_console(msg)
        
    #################################
    ## COMMS METHODS
    #################################
        
       
    def comms_launch_process(self):
        try:
            self.commprocess.start()
        except Exception as e:
            msg= 'error:could not launch Comms process : %s\n'%e
            self.queue_to_log(msg)
            self.events['comms_server_disconnect'].set()
            return False, msg
        
        msg = 'Comms process successfully launched.\n'
        return True, msg
    
    def comms_flush_rxtx_queues(self):
        while self.queues['rx'].empty()==False:
            self.queues['rx'].get()
        while self.queues['tx'].empty()==False:
            self.queues['tx'].get()
    
    def comms_enable(self):
        msg = 'Attempting connection to rover (%s,%s) ...\n'%(self.cfg.network.address,self.cfg.network.port_command)
        self.events['comms_enable'].set()

        ### Wait for status update from commprocess :
        result, msg = self.pipes['comms'][0].recv()

        if result == True:
            msg = 'Successfully connected to rover.\n'
            retbool = True
        else:
            msg = 'Error:could not connect to rover: %s\n'%msg.strip()
            self.events['comms_enable'].clear()
            retbool = False

        return retbool, msg         
                
    def comms_close(self):
        self.events['comms_enable'].clear()
        if self.commprocess.is_alive():
            self.commprocess.join()

        self.comms_flush_rxtx_queues()
        
        msg = 'Connection to rover closed.\n'
        self.queues['log'].put(msg)
        self.queue_console.put(msg)
        

    def comms_push_command(self, cmdstring):
        ### clean the command first
        cmd=cmdstring.strip()
        self.queues['tx'].put(cmd)

    def comms_push_drive_lifo(self, cmdstring):
        self.drive_lifo.append(cmdstring)

        
    def comms_fetch_rx(self):
        reslist = []
        count = 0
        while (count < FETCH_RX_BURST_SIZE) and (self.queues['rx'].empty()==False):
            reslist.append(self.queues['rx'].get())
            self.queues['rx'].task_done()
            count += 1
        return reslist

    ####################################################
    ## Session logic
    ####################################################
    
    def msgtreat_status(self, message):
        ## it's a status message:
        msg_body = message[1:]
        malformed=None
        if len(msg_suffix)>0:
            
            ## battery ?
            if msg_suffix[0] == 'B':
                battery_str = msg_body[:1]
                if battery_str:
                    self.rover_status['battery'] = float(msg_body[1:])
                else:
                    ## malformed battery status command :
                    malformed = "warning:malformed battery status message:\"%s\"\n"%message
                
            ## speed ?
            if msg_suffix[0] == 'S':
                speed_setting_str = msg_body[1:]
                if speed_setting_str:
                    self.rover_status['speed'] = int(speed_setting_str)
                else:
                    malformed = "warning:malformed speed setting status message:\"%s\"\n"%message
            
            ## headlights ?
            if msg_suffix[0] == 'H':
                headlight_str = msg_body[1:]
                if headlight_str:
                    headlight = headlight=='1'
                    self.rover_status['headlights']=headlight
                else:
                    malformed = "warning:malformed headlights status message:\"%s\"\n"%message

            
        if malformed is not None:
            self.queue_to_log_and_console(malformed)
            

    def msgtreat_default(self, message):
        ## by default, send it to the console queue
        self.queue_console.put(message)
    
    def analyze_received_messages(self,list_messages):
        ret=True
        for message in list_messages:
            if len(message)>0:
                msg0 = message[0]
                if msg0 in self.dict_dispatch_rx:
                    self.dict_dispatch_rx[msg0](message)
                else:
                    self.msgtreat_default(message)
            else:
                self.queue_to_log_and_console("warning: empty message received from rover:\"%s\"\n")
                ret=False

        return ret
            


    ####################################################
    ## Rover controls 
    ####################################################

    ##### Status / Accessory
    
    def rover_request_status_update(self):
        self.comms_push_command('SU')
        
    def rover_headlights_on(self):
        self.comms_push_command('H1')

    def rover_headlights_off(self):
        self.comms_push_command('H0')

    ##### Drive

    def rover_drive(self,where='stop'):
        #print "push command ",where
        self.comms_push_command(self.dict_rover_drive[where])
        #self.comms_push_drive_lifo(self.dict_rover_drive[where])
        
    def rover_flush_drive_lifo(self,keep=1):
        if keep==0:
            self.drive_lifo = []
        else:
            self.drive_lifo = self.drive_lifo[:-keep]
    
    ####################################################
    ## GUI Controls
    ####################################################

    def fetch_rx(self):
        reslist = []
        count = 0
        while (count < FETCH_RX_BURST_SIZE) and (self.queues['rx'].empty()==False):
            reslist.append(self.queues['rx'].get())
            self.queues['rx'].task_done()
            count += 1
        return reslist

    def fetch_console_messages(self):
        res=[]
        while self.queue_console.empty()==False:
            print 'something in console'
            res.append(self.queue_console.get())
            self.queue_console.task_done()
        return res

    def fetch_status_updates(self):
        pass

    def is_rover_connected(self):
        if self.events['comms_enable'].is_set():
            return not self.events['comms_server_disconnect'].is_set()
        else:
            return False
        
    
    def close(self):
        self.events['comms_enable'].clear()
        self.comms_flush_rxtx_queues()
        self.comms_close()

        
    
        

if __name__ == "__main__":
    
    cfgfilepath=sys.argv[1]

    cfg = pycfg.Config()
    cfg.read_file(cfgfilepath)
    cm = ClientMaster(cfg=cfg)
    cm.start()
    #cm.join()
    

    
