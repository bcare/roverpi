# -*-coding: utf-8 -*-
import sys
import os

from multiprocessing import Manager, JoinableQueue
import socket
import select

import pylibconfig2 as pycfg

from slaveprocess import SlaveProcess


COMMS_QUEUE_RX_BURST_SIZE = 1
COMMS_QUEUE_TX_BURST_SIZE = 1

COMMS_RX_BUFF_SIZE = 256

PROCESS_EVENT_COMMS_ENABLE_TIMEOUT_S = 0.05


SOCKET_SELECT_TIMEOUT_S = 0.05

class CommProcess(SlaveProcess):
    def __init__(self,**kwargs):
        super(CommProcess, self).__init__(**kwargs)
        
        self.rover_port_command = kwargs['rover_port_command']
        self.rover_address = kwargs['rover_address']
        self.client_socket = None

        self.tx_lifo = kwargs['tx_lifo']
        
    def init_socket(self):
        self.events['server_disconnect'].clear()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
        if not sys.platform.startswith('win'):
            self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        ## set the socket to non-blocking
        #self.client_socket.setblocking(0)
        
    def close_connection(self):
        if self.client_socket is not None :
            self.client_socket.shutdown(socket.SHUT_RDWR)
            self.client_socket.close()
            
        self.events['server_disconnect'].set()
    
        self.client_socket = None

    def exit_with_retcode(self,retcode=0,msg='CommProcess exited normally'):
        self.queues['log'].put(msg)
        sys.exit(retcode)
        
    def connect_to_rover(self):
        retbool = False
        try:
            self.client_socket.connect((self.rover_address, self.rover_port_command))
            retbool = True
            msg = 'Successful connection to rover.'
        except Exception as e:
            msg = 'Failed to connect to rover : %s'%(e)
            self.events['server_disconnect'].set()
            retbool = False
            
        return retbool, msg

    def send_msg(self, msgstring):
        retbool, retmsg = True, 'OK'
        try:
            self.client_socket.send(msgstring)
        except Exception as e:
            retbool, retmsg = False, 'comms:error: in send_msg : %s'%e
        finally:
            return retbool, retmsg
        
    def send_from_tx_queue(self, burst_size):
        retbool, retmsg = True, 'OK'
        count = 0
        try:
            while ((count < burst_size) and (self.queues['tx'].empty()==False)):
                msg=self.queues['tx'].get()
                if msg:
                    self.queues['log'].put("comms:sending \"%s\"\n"%msg)
                    self.send_msg(msg)
                else:
                    self.queues['log'].put("comms:warning:empty msg !\n")
                self.queues['tx'].task_done()
                count += 1
        except Exception as e:
            retbool, retmsg = False, 'comms:error:in send_from_tx_queue: %s'%e
        finally:
            return retbool, retmsg


    def send_from_tx_lifo(self):
        retbool, retmsg = True, 'OK'
        try:
            if len(self.tx_lifo) > 0:
                msg=self.tx_lifo.pop()
                if msg:
                    self.queues['log'].put("comms:sending \"%s\"\n"%msg)
                    self.send_msg(msg)
                else:
                    self.queues['log'].put("comms:warning:empty msg !\n")
        except Exception as e:
            retbool, retmsg = False, 'comms:error:in send_from_tx_lifo: %s'%e
        finally:
            return retbool, retmsg
        
    def receive_data_from_rover(self):
        retbool, retmsg = True, 'OK'
        try:
            read_ready, write_ready, extra_condition = select.select([self.client_socket],[self.client_socket],[self.client_socket],SOCKET_SELECT_TIMEOUT_S)
            if read_ready:
                msg = self.client_socket.recv(COMMS_RX_BUFF_SIZE)
                if msg:
                    self.queues['rx'].put(msg)
                    ## debug
                    self.queues['log'].put(msg)
                else:
                    self.queues['log'].put('comms:received empty data from rover, assuming rover disconnected.\n')
                    self.close_connection()
        except Exception as e:
            retbool, retmsg = False, 'comms:error:in receive_data_from_rover: %s'%e
        finally:
            return retbool, retmsg
            

    def rxtx_loop(self):
        retbool, retmsg = True, 'OK'

        ### while comms are enabled, receive/transmit data
        while self.events['enable'].wait(PROCESS_EVENT_COMMS_ENABLE_TIMEOUT_S):
            

            ########### TX ##########
            
            retbool, retmsg = self.send_from_tx_queue(COMMS_QUEUE_TX_BURST_SIZE)
            if retbool != True:
                return retbool, retmsg

            retbool, retmsg = self.send_from_tx_lifo()
            if retbool != True:
                return retbool, retmsg
            
        
            ########### RX ##########
            
            retbool, retmsg = self.receive_data_from_rover()
            if retbool != True:
                return retbool, retmsg
            
        
            ### If we catch a server_disconnect event,
            ### break the loop and return False with msg
                
            if self.events['server_disconnect'].is_set():
                break
        
                
        return retbool, retmsg
            
    
    def run(self):

        self.queues['log'].put('comms:starting process...\n')
        
        retcode, retbool, retmsg = 0, True, 'comms:OK'
        
        ### init network ###
        
        self.init_socket()

        successful_connection = False
        
        ### try to connect to the rover :
        try:
            successful_connection, msg = self.connect_to_rover()
            ### Signal that whether we are connected to the rover:
            self.pipes['session'].send((successful_connection, msg))

        except Exception as e:
            
            retmsg = 'comms:exception while trying to connect to rover: %s\n'%e
            self.events['server_disconnect'].set()
            self.exit_with_retcode(-1,retmsg)

        if successful_connection:
            try:
                retcode, retbool, retmsg = 0, True, 'comms:OK'
                
                ###########################
                ######## Rx/Tx loop #######
                ###########################
                retbool, retmsg = self.rxtx_loop()
                
                
            except Exception as e:
                retmsg = 'comms:exception in run(): %s\n'%e
                self.events['server_disconnect'].set()
                retcode = -1
            finally:
                ########################
                ### Exit gracefully ####
                ########################
                self.close_connection()
                self.exit_with_retcode(0 if retbool else -1, retmsg.strip()+'\n')
        else:
            self.events['server_disconnect'].set()
            self.exit_with_retcode(-1, 'comms:error:could not connect to rover\n')

                

            
