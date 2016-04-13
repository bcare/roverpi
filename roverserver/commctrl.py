import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"../rovercommons")))

from time import sleep

from multiprocessing import Process, Queue, Pipe, Event, JoinableQueue
import socket
import select

from slaveprocess import SlaveProcess

SOCKET_SELECT_TIMEOUT_S = 0.1

COMMS_QUEUE_TX_BURST_SIZE = 1

COMMS_RX_BUFF_SIZE = 256

PROCESS_EVENT_ENABLE_COMMS_TIMEOUT_S = 0.05
PROCESS_EVENT_CLIENT_DISCONNECT_TIMEOUT_S = 0.05


class CommProcess(SlaveProcess):
    def __init__(self,**kwargs):
        super(CommProcess, self).__init__(**kwargs)

        ## Networking :

        self.network_port = kwargs['port']
        self.network_address = kwargs['address']

      
        
        ## debug :
        self.debugfilepath = None
        if 'debug_log' in kwargs:
            self.debugfilepath=kwargs['debug_log']

            ## clear the debug log.
            open(self.debugfilepath, 'w').close()
            

    def debug_log(self, msg):
        if self.debugfilepath is not None:
            with open(self.debugfilepath, 'a') as file:
                file.write(msg)

    def init_sockets(self):
        self.remote_connection = None
        self.server_socket = None
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT,1)

        self.server_socket.setblocking(0)

        self.server_socket.bind((self.network_address, self.network_port))
        self.server_socket.listen(1)

        self.queues['log'].put('comms:listening for connexions on port %d address %s...'%(self.network_port, self.network_address))
        
        
    def accept_connection(self):
            
        self.remote_connection, self.remote_address = self.server_socket.accept()
        if self.remote_connection is not None:
            self.remote_connection.setblocking(0)
            return True
        else:
            return False
        

    def wait_for_client_connection(self):
        ret=False
        
        while self.events['enable_comms'].wait(PROCESS_EVENT_ENABLE_COMMS_TIMEOUT_S):
            
            try:

                read_ready, write_ready, extra_condition = select.select([self.server_socket],[self.server_socket],[self.server_socket],SOCKET_SELECT_TIMEOUT_S)

                if read_ready:
                    ret=self.accept_connection()
                    if not ret:
                        msg = 'comms:error:while waiting for client connection : could not accept client connection.\n'
                        self.queues['log'].put(msg)
                    return ret
                        
                #else:
                    #msg = 'comms:error:while waiting for client connect: socket not read-ready\n'
                    #self.queues['log'].put(msg)
                    #return False

                if extra_condition:
                    msg='comms:error: socket in extra_condition while waiting for client, aborting\n'
                    self.queues['log'].put(msg)
                    self.debug_log(msg)
                    return False
                
            except Exception as e:
                msg = 'comms:error: select failed while waiting for client connection, something went wrong (%s)\n'%e
                self.queues['log'].put(msg)
                self.debug_log(msg)
                return False
        ## If we reached this return at the exit of the loop,
        ## it means enable_comms was cleared, so return False
        return False


    def send_from_tx_queue(self, burst_size=1):
        count = 0
        while ((count < burst_size) and (self.queues['tx_msg'].empty()==False)):
            msg=self.queues['tx_msg'].get()
            self.remote_connection.send(msg)
            self.queues['tx_msg'].task_done()
            count+=1
            
            
    def rxtx_loop(self):

        
        self.queues['log'].put('comms:starting Rx/Tx loop...')

        self.debug_log("start rxtx loop\n")
           
        try:

            while self.events['enable_comms'].wait(PROCESS_EVENT_ENABLE_COMMS_TIMEOUT_S):

                while True:
                    read_ready, write_ready, exceptional_condition = select.select([self.server_socket,self.remote_connection], \
                                                                                   [self.remote_connection], \
                                                                                   [self.remote_connection], \
                                                                                   SOCKET_SELECT_TIMEOUT_S)
                    
                    ## if any socket is in exceptional_condition:
                    if exceptional_condition:
                        self.queues['log'].put("comms:exceptional condition on server socket ...\n")
                        return False
                        
                    ## if there is data available :
                    if self.remote_connection in read_ready:
                        data = self.remote_connection.recv(COMMS_RX_BUFF_SIZE)
                        if data:
                            self.debug_log("received data %s\n"%data)
                            self.queues['rx_msg'].put(data.strip())
                        else:
                            ## client most probably dropped the connection
                            self.queues['log'].put("comms:client disconnected.\n")
                            self.debug_log("received 0 data, client must have dropped the connection.\n")
                            return True
                        
                    ## if there is data to be sent :
                    if self.queues['tx_msg'].empty()==False:
                        if self.remote_connection in write_ready:
                            self.send_from_tx_queue(burst_size=COMMS_QUEUE_TX_BURST_SIZE)
                        else:
                            self.queues['log'].put('comms:socket not write-ready, something went wrong, aborting.\n')
                            return False

        except Exception as e:
            ### select failed, something went wrong, most probably the client disconnected.
            self.debug_log("error select %s\n"%e)
            self.queues['log'].put("comms:error: exception in rxtx loop, shutting down network (%s).\n"%e)
            return False
        
        ## end because comms disabled, not client disconnected
        return True
                
            

    def close_connections(self):

        self.events['client_disconnect'].set()
        
        ### shudown : clear any pending data
        ### while close : release the socket
        ### close DOES NOT IMPLY that any pending data
        ### is cleared. The system actually keeps it
        ### So make sure to call shutdown if you want
        ### to flush any pending data BEFORE closing.
        if self.remote_connection is not None:
            self.remote_connection.shutdown(socket.SHUT_RDWR)
            self.remote_connection.close()
            self.remote_connection=None
            
        if self.server_socket is not None:
            self.server_socket.shutdown(socket.SHUT_RDWR)
            self.server_socket.close()
            self.server_socket=None


    def exit_with_retcode(self, retcode=0, msg='comms:process exiting normally'):
        self.queues['log'].put(msg)
        self.close_connections()
        sys.exit(retcode)
            


        
    def run(self):

        self.queues['log'].put('comms:starting...')

       
        ####################   Main loop   #########################
        
        while self.events['enable_comms'].wait(PROCESS_EVENT_ENABLE_COMMS_TIMEOUT_S):

            self.events['client_disconnect'].clear()
            
            ########## Socket init ##############
       
            try:
                self.init_sockets()
            except Exception as e:
                msg = "comms:error:exception while starting to listen on (%s,%d):%s\n"%(self.network_address, self.network_port, e)
                self.exit_with_retcode(-1,msg)

            ########## wait for clients (until comms are disabled) #######
            try:
                
                successful_connection = self.wait_for_client_connection()
            except Exception as e:
                msg = "comms:error: exception while waiting for connections:%s\n"%e
                self.exit_with_retcode(-1,msg)
                
            retcode = -1
            if successful_connection:

                ####### Received client connection #####
                
                self.queues['log'].put("comms:accepted connection from (%s,%s)\n"%self.remote_address)
                self.events['client_disconnect'].clear()

                retcode = -1
                try:

                    ######### RXTX LOOP ##########
                    retcode = 0 if self.rxtx_loop() else -1
                    ##############################
                    
                    
                    
                except Exception as e:
                    msg = "comms:exception while in rxtx loop: %s\n"%e
                    self.queues['log'].put(msg)
                    self.exit_with_retcode(retcode,msg)
                
            else:
                msg = 'comms:error:could not accept connection.\n'
                self.exit_with_retcode(retcode, msg)

            self.events['client_disconnect'].set()
            
            if retcode!=0:
                self.exit_with_retcode(retcode,'comms:error in rxtx loop.\n')


if __name__ == "__main__":


    debug_log_path = "debug_log.txt"
    
    def pop_queue(queue):
        res=queue.get()
        queue.task_done()
        return res


    def flush_queue(queue):
        res = []
        while queue.empty()==False:
            res.append(queue.get())
        return res
    
    event_enable_comms = Event()
    event_client_disconnect = Event()

    event_client_disconnect.clear()
    
    queue_rx = JoinableQueue()
    queue_tx = JoinableQueue()
    queue_log = JoinableQueue()
    test_commprocess = CommProcess(port=8080,address='127.0.0.1',events={'enable_comms':event_enable_comms,'client_disconnect':event_client_disconnect},queues={'tx_msg':queue_tx,'rx_msg':queue_rx,'log':queue_log},debug_log=debug_log_path)

    retcode = 0
    
    try:
        
        event_enable_comms.set()
        
        event_enable_comms.set()
        test_commprocess.start()

        while True:
          
                
            if queue_log.empty()==False:
                print pop_queue(queue_log)
                
            if queue_rx.empty()==False:
                msg = pop_queue(queue_rx)
                print msg
                queue_tx.put("echoing %s\n"%msg)

            ## check if client disconnected :
            if event_client_disconnect.wait(PROCESS_EVENT_CLIENT_DISCONNECT_TIMEOUT_S):
                

                ## check if the commprocess is still alive :
                if not test_commprocess.is_alive():
                    ## what happened ?
                    commprocess_retcode = test_commprocess.exitcode
                    print "commproc retcode:",commprocess_retcode
                    if commprocess_retcode != 0:
                        msg = 'Comm process exited with retcode %d, aborting\n'%commprocess_retcode
                        queue_log.put(msg)
                        sys.stderr.write(msg)
                        break

                ## empty the queues regardless of what happened :
                print 'remaining logs :'
                print '\n'.join(flush_queue(queue_log))
                print 'remaning rx :'
                print '\n'.join(flush_queue(queue_rx))
                print 'remaining tx :'
                print '\n'.join(flush_queue(queue_tx))

            
    except KeyboardInterrupt as e:
        sys.stderr.write("Catched keyboard interrupt.\n")
        event_enable_comms.clear()
        if test_commprocess.is_alive():
            test_commprocess.join()
        ## empty the queues :
        print '\n'.join(flush_queue(queue_log))
        print '\n'.join(flush_queue(queue_rx))
        flush_queue(queue_tx)
        ## exceptionnally, since it's our way to close the debug server
        retcode=0

    except Exception as e:
        sys.stderr.write("Error: %s\n"%e)
        retcode=-1

    finally:
        event_enable_comms.clear()
        test_commprocess.join()
        queue_log.put("Client disconnected.\n")
        ## empty the queues :
        print '\n'.join(flush_queue(queue_log))
        print '\n'.join(flush_queue(queue_rx))
        flush_queue(queue_tx)
        sys.exit(retcode)
            
