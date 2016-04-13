
from multiprocessing import Process, JoinableQueue, Manager, Lock, Value, Event
import wiringpi as wp
import RPi.GPIO as rpio
from slaveprocess import SlaveProcess

import time


rpio.setmode(rpio.BCM)


class PMWProcess(Process):

    def __init__(self,**kwargs):
        super(PWMProcess, self).__init__(**kwargs)

        self.event_enable_pwm = kwargs['event_enable_pwm']
        self.event_terminate = kwargs['event_terminate']
        self.pwm_freq = kwargs['pwm_freq']
        self.pwm_duty = kwargs['pwm_duty']
        self.lock_freq = kwargs['lock_freq']
        self.pin = kwargs['pin']
        
        
    def run():

        while self.event_enable_pwm.is_set():
            start_clock = time.time()
            
            with self.lock_freq:
                pwm_freq = self.pwm_freq.value
                pwm_duty = self.pwm_duty.value
                
            period=1./pwm_freq
            
            

class DriveCtrl():

    def __init__(self, **kwargs):

       
        self.cfg = kwargs['config']
        

        self.queues = kwargs['queues']
        
        ## motor parameters :
        self.speeds = (10,20,50,100)

        if self.cfg.lookup('drive.speeds') is not None:
            self.speeds = tuple([max(100,x) for x in self.cfg.lookup('drive.speeds')])
            
        self.max_speed = max(self.speeds)
        self.nb_speeds = len(self.speeds)
        self.current_speed = self.speeds[0]
    
        self.queues['log'].put('drive:nb speeds : %d'%(self.nb_speeds))
                               
        ## pins :
        self.power_pins={'L':0,'R':0}       
        self.direction_pins = {'L':0,'R':0}
        self.monitor_pins={'LF':0,'LB':0,'RB':0,'RF':0}

        self.pin_power_left = 0
        self.pin_power_right = 0

        self.pin_direction_left = 0
        self.pin_direction_right = 0

        ## PWM options :
        if self.cfg.lookup('gpio.pwm_freq'):
            self.pwm_freq = float(self.cfg.gpio.pwm_freq)
        else:
            self.pwm_freq = 50.0
        
        ###################### DEFAULT DRIVE VECTORS #######################

        #################################
        # COMMANDS 
        #################################
        ## Drive commands :
        
        # North :                    
        #         _       _
        #     ^  | |_____| | ^         | |x| | 
        #     |  | |  ^  | | |         | | | |
        # 1.0 |  | |__^__| | | 1.0     | | | |
        #     |  |_|     |_| |
        #       
        
    
        # North East :                    
        #         _       _
        #     ^  | |_ _ _| |           | | |x| 
        #     |  | |  ^  | | ^         | | | |
        # 0.8 |  | |__^__| | | 0.2     | | | |
        #     |  |_|     |_| 
        #       
        
    
        # East :                    
        #         _       _
        #     ^  | |_____| | |         | | | | 
        #     |  | |  ^  | | |         | | |x|
        # 1.0 |  | |__^__| | |  1.0    | | | |
        #     |  |_|     |_| v
        #
        

        # South East :                    
        #         _       _
        #     |  | |_____| |           | | | | 
        #     |  | |  ^  | | |         | | | |
        # 1.0 |  | |__^__| | v  0.8    | | |x|
        #     v  |_|     |_| 
        #
        
        # South  :                    
        #         _       _
        #     |  | |_____| | |         | | | | 
        #     |  | |  ^  | | |         | | | |
        # 1.0 |  | |__^__| | |  1.0    | |x| |
        #     v  |_|     |_| v
        #
    
        # South West  :                    
        #         _       _
        #        | |_____| | |         | | | | 
        #        | |  ^  | | |         | | | |
        # 0.2 |  | |__^__| | |  0.8    |x| | |
        #     v  |_|     |_| v
        #
        
        # West  :                    
        #         _       _
        #     |  | |_____| | ^         | | | | 
        #     |  | |  ^  | | |         |x| | |
        # 1.0 |  | |__^__| | |  1.0    | | | |
        #     v  |_|     |_| |
        #
        
      
        # North West  :                    
        #         _       _
        #     ^  | |_____| | ^         |x| | | 
        #     |  | |  ^  | | |         | | | |
        # 0.2    | |__^__| | |  0.8    | | | |
        #        |_|     |_| |
        # 
        
        # Full stop :                    
        #         _       _
        #        | |_____| |           | | | | 
        #        | |  ^  | |           | |x| |
        # 0.0    | |__^__| |    0.0    | | | |
        #        |_|     |_|  
        #
    
    
        self.vec_north = (1.0,1.0,1,1,0,0)
        self.vec_north_east = (0.8,0.2,1,1,0,0)
        self.vec_east = (1.0,1.0,1,0,0,1)
        self.vec_south_east = (0.8,0.2,0,0,1,1)
        self.vec_south = (1.0,1.0,0,0,1,1)
        self.vec_south_west = (0.2,0.8,0,0,1,1)
        self.vec_west = (1.0,1.0,0,1,1,0)
        self.vec_north_west = (0.2,0.8,1,1,0,0)
        self.vec_full_stop = (0,0,0,0,0,0)

        self.load_drive_vectors()

        self.current_vector = self.vec_full_stop
        
        ## read the mapping of GPIO pins
        self.read_gpio_map_from_config()

        self.gpio_init()

        self.dict_steer = {'8':self.vec_north, \
                           '9':self.vec_north_east, \
                           '6':self.vec_east,\
                           '3':self.vec_south_east,\
                           '2':self.vec_south,\
                           '1':self.vec_south_west,\
                           '4':self.vec_west,\
                           '7':self.vec_north_west,\
                           '5':self.vec_full_stop}

        
    def load_drive_vectors(self):
        for vecname in ['north','north_east','east','south_east','south','south_west','west','north_west']:
            vecpath = 'drive.vectors.'+vecname
            #self.queues['log'].put('drive: loading drive vector %s'%vecpath)
            if self.cfg.lookup(vecpath) is not None:
                vecarray = self.cfg.lookup(vecpath)
                if len(vecarray) != 6:
                    self.queues['log'].put('drive:error: drive vector %s in config file'%(vecname))
                setattr(self,'vec_'+vecname, tuple([x for x in vecarray]))
        
        
        
                    

    def read_gpio_map_from_config(self):

        self.pin_power_left = self.cfg.gpio.pin_pwm_left
        self.pin_power_right = self.cfg.gpio.pin_pwm_right
        
        self.pin_direction_left_forward = self.cfg.gpio.pin_direction_left_forward
        self.pin_direction_right_forward = self.cfg.gpio.pin_direction_right_forward
        self.pin_direction_left_rear = self.cfg.gpio.pin_direction_left_rear
        self.pin_direction_right_rear = self.cfg.gpio.pin_direction_right_rear
        

    def gpio_init(self):
        
        wp.wiringPiSetupSys()

        # Set output for those pins :
        wp.pinMode(self.pin_power_left, wp.OUTPUT)
        wp.pinMode(self.pin_power_right, wp.OUTPUT)
        wp.pinMode(self.pin_direction_left_forward, wp.OUTPUT)
        wp.pinMode(self.pin_direction_right_forward, wp.OUTPUT)
        wp.pinMode(self.pin_direction_left_rear, wp.OUTPUT)
        wp.pinMode(self.pin_direction_right_rear, wp.OUTPUT)
        
        ## create the SoftPwm on power pins :     
        wp.softPwmCreate(self.pin_power_left, 0, self.max_speed)
        wp.softPwmCreate(self.pin_power_right, 0, self.max_speed)

        ## reset everyone :
        self.gpio_zero()

    def rpio_init(self):
        
        ## open pins for output :
        rpio.setup(self.pin_power_left, rpio.OUT)
        rpio.setup(self.pin_power_right, rpio.OUT)
        rpio.setup(self.pin_direction_left_forward, rpio.OUT)
        rpio.setup(self.pin_direction_right_forward, rpio.OUT)
        rpio.setup(self.pin_direction_left_rear, rpio.OUT)
        rpio.setup(self.pin_direction_right_rear, rpio.OUT)


        ## open pins for input :
        # disabled for now

        ## setup software pwm
        self.pwm_left = rpio.PWM(self.pin_power_left, self.pwm_freq)
        self.pwm_right = rpio.PWM(self.pin_power_right, self.pwm_freq)

        self.pwm_left.start(0)
        self.pwm_right.start(0)

        
    def gpio_zero(self):

        
        # set everyone to 0
        wp.softPwmWrite(self.pin_power_left, 0)
        wp.softPwmWrite(self.pin_power_right, 0)
        wp.digitalWrite(self.pin_direction_left_forward, 0)
        wp.digitalWrite(self.pin_direction_right_forward, 0)
        wp.digitalWrite(self.pin_direction_left_rear, 0)
        wp.digitalWrite(self.pin_direction_right_rear, 0)

    def rpio_zero(self):

        self.pwm_left.ChangeDutyCycle(0)
        self.pwm_right.ChangeDutyCycle(0)
        rpio.output(self.pin_direction_left_forward, 0)
        rpio.output(self.pin_direction_right_forward, 0)
        rpio.output(self.pin_direction_left_rear, 0)
        rpio.output(self.pin_direction_right_rear, 0)
        
        
        
    def gpio_steer(self, drive_vector):
        wp.softPwmWrite(self.pin_power_left, int(self.current_speed*drive_vector[0]))
        wp.softPwmWrite(self.pin_power_right, int(self.current_speed*drive_vector[1]))
        wp.digitalWrite(self.pin_direction_left_forward, drive_vector[2])
        wp.digitalWrite(self.pin_direction_right_forward, drive_vector[3])
        wp.digitalWrite(self.pin_direction_left_rear, drive_vector[4])
        wp.digitalWrite(self.pin_direction_right_rear, drive_vector[5])

        actual_vec = (int(self.current_speed*drive_vector[0]), int(self.current_speed*drive_vector[1]),drive_vector[2], drive_vector[3], drive_vector[4], drive_vector[5])
        msg='drive:steering, drive vector: %s, ppl %d ppr %d pdlf %d pdrf %d pdlr %d pdrr %d'%(str(actual_vec),self.pin_power_left, self.pin_power_right, self.pin_direction_left_forward, self.pin_direction_right_forward, self.pin_direction_left_rear, self.pin_direction_right_rear)
        self.queues['tx_msg'].put(msg)
        self.queues['log'].put(msg)
        
    def rpio_steer(self,drive_vector):
        
        self.pwm_left.ChangeDutyCycle(self.current_speed*drive_vector[0])
        self.pwm_right.ChangeDutyCycle(self.current_speed*drive_vector[1])
        rpio.output(self.pin_direction_left_forward, drive_vector[2])
        rpio.output(self.pin_direction_right_forward, drive_vector[3])
        rpio.output(self.pin_direction_left_rear, drive_vector[4])
        rpio.output(self.pin_direction_right_rear, drive_vector[5])
        
        actual_vec = (int(self.current_speed*drive_vector[0]), int(self.current_speed*drive_vector[1]),drive_vector[2], drive_vector[3], drive_vector[4], drive_vector[5])
        
        msg='drive:steering, drive vector: %s, ppl %d ppr %d pdlf %d pdrf %d pdlr %d pdrr %d\n'%(str(actual_vec),self.pin_power_left, self.pin_power_right, self.pin_direction_left_forward, self.pin_direction_right_forward, self.pin_direction_left_rear, self.pin_direction_right_rear)
        self.current_vector = drive_vector
        
        self.queues['tx_msg'].put(msg)
        self.queues['log'].put(msg)
        
       
    def rpio_cleanup(self):
        
        self.pwm_left.stop()
        self.pwm_right.stop()
        rpio.cleanup()    
    
    def execute_drive_cmd(self,raw_cmd):
        
        self.queues['log'].put("drive:executing cmd :%s"%raw_cmd)
        
        if len(raw_cmd)>2:
            
            if raw_cmd[1] == 'G':
                ## command 'DG[1-9]' : steering command
                if raw_cmd[2] in self.dict_steer:
                    self.gpio_steer(self.dict_steer[raw_cmd[2]])
                else:
                    self.queues['tx_msg'].put('drive:unknown steering command key \"%s\" (available : [1-9]).\n'%(raw_cmd[2]))

            elif raw_cmd[1] == 'S':
                ## command 'DS[0-9]' : change speed
                speed_setting = int(raw_cmd[2:])
                if speed_setting >= 0:
                    self.current_speed = self.speeds[min(self.nb_speeds-1,speed_setting)]
                    self.gpio_steer(self.current_vector)
                    self.queues['log'].put('drive:current speed set to %s'%(str(self.current_speed)))
                else:
                    self.queues['tx_msg'].put('drive:could not change speed setting to %d, must be positive'%(speed_setting))

        elif raw_cmd[1] == 'M':
            ## command 'DM' : requesting monitoring data
            pass
        else:
            self.queues['tx_msg'].put('drive:discarding malformed speed setting command \"%s\"\n'%raw_cmd)
            

    def checks(self, remote=False):

        ## check drive vectors :
        for vecname in ['north','north_east','east','south_east','south','south_west','west','north_west']:
            msg = 'drive:checking drive vector %s:%s'%(vecname,getattr(self,'vec_'+vecname).__repr__())
            self.queues['log'].put(msg)
            if remote:
                self.queues['tx_msg'].put(msg)

        ## check speed settings
        msg='drive:checking available speeds: %s'%(str(self.speeds))
        self.queues['log'].put(msg)
        if remote:
            self.queues['tx_msg'].put(msg)
                
        
    def shutdown(self):
        self.gpio_zero()
        #self.gpio_cleanup()
        self.queues['log'].put('drive:stop.')




if __name__ == "__main__":

    pwm_freq = 100
    pin_power_left = 16
    pin_power_right = 20
    pin_direction_left_forward = 6
    pin_direction_right_forward = 13
    pin_direction_left_rear = 19
    pin_direction_right_rear = 26
    
    rpio.setmode(rpio.BCM)
    
    ## open pins for output :
    rpio.setup(pin_power_left, rpio.OUT)
    rpio.setup(pin_power_right, rpio.OUT)
    rpio.setup(pin_direction_left, rpio.OUT)
    rpio.setup(pin_direction_right, rpio.OUT)
    
    ## open pins for input :
    # disabled for now
    
    ## setup software pwm
    pwm_left = rpio.PWM(pin_power_left, pwm_freq)
    pwm_right = rpio.PWM(pin_power_right, pwm_freq)
    
    pwm_left.start(50)
    pwm_right.start(50)

    current_cycle_up = 50
    current_cycle_down = 50
    goon=True
    periode=0.01
    step=1
    while goon:
        try:
            pwm_left.ChangeDutyCycle(current_cycle_up)
            pwm_right.ChangeDutyCycle(current_cycle_down)
            print current_cycle_up, current_cycle_down
            current_cycle_up = abs((current_cycle_up + step)%100)
            current_cycle_down = abs((current_cycle_down - step)%100)
            time.sleep(periode)
        except KeyboardInterrupt as e:
            goon=False


    rpio.cleanup()
    
