#!/bin/python

# -*- coding: utf-8 -*-

#### Built-in modules :
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"../rovercommons")))

from datetime import datetime
import time
import traceback
from multiprocessing import Process, JoinableQueue, Pipe, Manager, Lock, Condition, Event
#import RPi.GPIO as rpio

#### Third-party modules :
import pylibconfig2 as pycfg



#### Custom modules :
import enginectrl
import commctrl
from slaveprocess import SlaveProcess



#rpio.setmode(rpio.BCM)

######################
# Debugging/Traceback
######################


######################
### Logging facility :
######################

class LogProcess(SlaveProcess):
    def __init__(self,logfilepath='/tmp/rover.log', override=False, **kwargs):
        super(LogProcess, self).__init__(**kwargs)
        self.override = override
        self.logfilepath = os.path.abspath(os.path.expandvars(os.path.expanduser(logfilepath)))

    def run(self):
        if self.override == True:
            openmode='w'
        else:
            openmode='a'

        with open(self.logfilepath, openmode) as file:
            while self.events['enable_log'].is_set():
                if self.queues['log'].empty() == False:
                    msg=self.queues['log'].get()
                    file.write(':'.join(['Rover',datetime.now().strftime("%Y/%m/%d-%H:%M:%S"),msg])+'\n')
                    self.queues['log'].task_done()


#####################
### Rover Master :
#####################
                    
class RoverMaster():
    def __init__(self,**kwargs):

        ## config
        self.config = pycfg.Config()
        self.config.read_file(kwargs['configfilepath'])

        ###########################
        ## Multiprocessin Objects :
        ###########################
                
        ## Queues :
        
        self.queue_rx_msg = JoinableQueue()
        self.queue_tx_msg = JoinableQueue()

        self.queue_drive_cmd = JoinableQueue()
        self.queue_master_cmd = JoinableQueue()

        self.queue_log = JoinableQueue()
        
        ## Events :

        # logging :
        self.event_log_enable = Event()
        
        # commcontrol sync :
        self.event_comm_enable = Event()
        self.event_comm_client_disconnect = Event()

        # drive sync :
        self.event_drive_enable = Event()

        ## Managers :
        
        self.manager_drive_status = None

        ######################
        #### Slave Processes :
        ######################

        ## create log ctrl :
        self.logctrl = LogProcess(name='rover-log',logfilepath='log.txt', override=True, queues={'log':self.queue_log},events={'enable_log':self.event_log_enable})
        
        ## create comm ctrl :
        self.commctrl = commctrl.CommProcess(name='rover-comms', \
                                             port=self.config.network.port, \
                                             address=self.config.network.address, \
                                             queues={'rx_msg':self.queue_rx_msg,'tx_msg':self.queue_tx_msg,'log':self.queue_log},\
                                             events={'enable_comms':self.event_comm_enable,'client_disconnect':self.event_comm_client_disconnect})


        #######################
        ##### Drive Control :
        #######################

        ## It's now included in the master proces
        ## since software PWM does not work well in child processes...
        
        ## create engine ctrl :
        ## THIS IS NOT A PROCESS
        ## But we'll still use queues, they are handy.
        self.drivectrl = enginectrl.DriveCtrl(name='rover-drive',config=self.config,queues={'log':self.queue_log,'tx_msg':self.queue_tx_msg})      
        

        ### Command dispatcher dict: 
        self.dict_dispatch = { 'D' : self.queue_drive_cmd, 'M':self.queue_master_cmd }

        self.master_commands = {'quit':self.cmd_quit}



    ####### Log Process
    
    def launch_log(self):
        self.logctrl.start()
        self.event_log_enable.set()

    def close_log(self,timeout=0):
        self.event_log_enable.clear()
        if self.logctrl.is_alive():
            self.logctrl.join(timeout)
        
    ####### Comms Process
            
    def launch_comms(self):
        ## signal to the commctrl that it should listen
        self.event_comm_enable.set()
        self.event_comm_client_disconnect.clear()
        ## start :
        self.commctrl.start()        

    def close_comms(self,timeout=0):
        self.event_comm_enable.clear()
        if self.commctrl.is_alive():
            self.commctrl.join(timeout)
            time.sleep(0.5)

            
    ####### Command dispatcher
    
    
    def dispatch_cmd(self, data):
        if len(data) > 1:
            if data[0] in self.dict_dispatch:
                self.dict_dispatch[data[0]].put(data)

    ####### Master Commands 

    ### All cmd_<method> command methods must return True or False
    ### depending on whether execution should continue or not.
    
    def cmd_quit(self,timeout=0):

        ## stop the engines :
        self.drivectrl.shutdown()
        
        ## close all slave processes
        self.close_comms(timeout)
        # No logs after this point
        self.close_log(timeout)


        ## stop execution :
        return False

    
    def execute_master_cmd(self,raw_cmd):
        """ Must returns True or False (False implies that the master loop stops)"""
        cmd = raw_cmd[1:] # remove the prefix
        if cmd in self.master_commands:
            return self.master_commands[cmd]()
        else:
            return False
        return True

    ###### Support

    def empty_queues_except_log(self):
        ## don't empty the logs, we still use it !
        for queue in [self.queue_rx_msg, self.queue_tx_msg, self.queue_drive_cmd, self.queue_master_cmd]:
            while queue.empty()==False:
                queue.get()
                queue.task_done()

    ###### Main loop
    
    def master_loop(self):
        goon=True
        
        ### launch slave processes :
        
        rvmaster.launch_log()
        rvmaster.launch_comms()

        self.queue_log.put('master:starting master loop.')

        exitcode=0
        try:
            while goon==True:
                    
                if self.queue_rx_msg.empty() == False:
                    data = self.queue_rx_msg.get()
                    self.queue_log.put("master:received \"%s\""%(data))
                    self.dispatch_cmd(data)
                    self.queue_rx_msg.task_done()
                
                if self.queue_drive_cmd.empty() == False:
                    cmd = self.queue_drive_cmd.get()
                    self.drivectrl.execute_drive_cmd(cmd)
                    self.queue_drive_cmd.task_done()
                    
                if self.queue_master_cmd.empty() == False:
                    cmd = self.queue_master_cmd.get()
                    goon = self.execute_master_cmd(cmd)
                    self.queue_master_cmd.task_done()

                ## client disconnected, get back to listening state:
                if self.event_comm_client_disconnect.is_set():
                    ## what happened ?
                    if not self.commctrl.is_alive():
                        commprocess_retcode = self.commctrl.exitcode
                        if commprocess_retcode != 0:
                            msg = 'master:comm process exited with retcode %d, aborting\n'%commprocess_retcode
                            self.queue_log.put(msg)
                            sys.stderr.write(msg)
                            break
                        else:
                            ### relaunch comms :
                            self.launch_comms()
                    
                    
        except KeyboardInterrupt as e:
            msg='master:catched KeyboardInterrupt, shutting down:%s'%e.message
            goon=False
            self.queue_log.put(msg)
            sys.stderr.write(msg+'\n')
            time.sleep(2) ## give the log process some time to empty the log queue
            exitcode=-1
        except Exception as e:
            goon=False
            msg = 'master:exception in master process, shutting down:%s'%e.message
            self.queue_log.put(msg)
            sys.stderr.write(msg+'\n')
            a,b,tb = sys.exc_info()
            traceback.print_tb(tb)
            time.sleep(2) ## give the log process some time to empty the log queue
            exitcode=-2
            self.cmd_quit(2)
        finally:
            sys.exit(exitcode)
            

                

############################################################
####             Main program starts here             ######
############################################################


rvmaster=RoverMaster(configfilepath=sys.argv[1])

### Start dispatching commands :

rvmaster.master_loop()
            
