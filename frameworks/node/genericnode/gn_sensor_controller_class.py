from global_imports import *
from gn_global_definition_section import get_instance_id,  add_to_thread_buffer,  buffered_msg,  msg_to_nc, \
start_communication_with_nc_event,  data_type,  sensor_thread_list, \
config_file_name, logger, wait_time_for_next_msg, reply_type
from sensor_plugin import sensor_plugin_class
from config_file_functions import initialize_config_file, ConfigObj


##################################################################################
# Registers sensors again even if they are registered once, to change later on
##################################################################################



# sensor_controller (object of sensor_controller_class): Processes msgs related to sensors
class sensor_controller_class(threading.Thread):
    
        
    ############################################################################## 
    def __init__(self, thread_name):
        threading.Thread.__init__(self)
        self.thread_name = thread_name                                                              # used by logging module for printing messages related to this thread
        self.daemon = True
        self.input_buffer = Queue.Queue(maxsize=1000)                                                           # stores messages sent by buffer_mngr_class, main_class
        self.main_thread = ''
        self.buffer_mngr = ''
        self.sensor_msg_delimiter = str(unichr(12))
        logger.debug("Thread "+self.thread_name+" Initialized."+ "\n\n")
    
        
    ############################################################################## 
    def pass_thread_address(self, main_thread, buffer_mngr): 
        self.main_thread = main_thread
        self.buffer_mngr = buffer_mngr               
        logger.debug("Addresses of main_thread and buffer_mngr saved."+ "\n\n")
    
        
    ############################################################################## 
    # Runs forever    
    def run(self):
        try:
            logger.debug("Starting " + self.thread_name+ "\n\n")
            plugin_obj = sensor_plugin_class(self.input_buffer)
            # Import new sensor files if any
            plugin_obj.plugin_sensors()
            wait_time = time.time() + wait_time_for_next_msg
            wait_time_set = 1
            while True:
                # Puts all the sensor msgs in its input_buffer to sensor_controller's input_buffer by converting them in proper tuple format
                plugin_obj.get_sensor_msgs()
                # Checks if any unprocessed msg is in the input buffer
                while not self.input_buffer.empty():
                    #logger.debug("Waiting for registration to be successful.."+ "\n\n")
                    if start_communication_with_nc_event.is_set():
                        item = self.input_buffer.get()
                        logger.debug("Msg received."+ "\n\n")
                        # process the msg
                        self.process_msg(item)
                        self.input_buffer.task_done()
                    # set time to remain attentive for next 5 ms
                    wait_time = time.time() + wait_time_for_next_msg
                    #print "short sleep snsr"
                    time.sleep(0.0001)
                if wait_time > time.time():
                    #print "short sleep snsr"
                    time.sleep(0.0001)
                else:
                    #print "long sleep snsr"
                    time.sleep(0.1)
        except Exception as inst:
            logger.critical("Exception: " + str(inst)+ "\n\n")
            self.run()
        finally:
            self.close()
    
        
    ##############################################################################     
    # item: buffered_msg tuple
    def process_msg(self, item):
        logger.debug('Msg being processed..'+ "\n\n")
        if item.internal_msg_header == msg_to_nc:
            if item.msg_type == reply_type or self.buffer_mngr.bfr_for_in_to_out_msgs.empty():
                logger.debug('Received sensor msg.'+ "\n\n")
                if item.msg_type == data_type:
                    self.send_data_msg(item)
                    # clear the event to signal that the output buffer won't be full when the data msg is sent by buffer_mngr so 
            else:
                self.input_buffer.put(item)
            logger.debug("Length of input bfr of sensor_controller:"+str(self.input_buffer.qsize()))
                
        
    ##############################################################################         
    # item: buffered_msg tuple        
    def send_data_msg(self, item):
        data_payload = DataPayload()
        data_payload.sens_id = item.msg[0]
        data_payload.read_tm = item.msg[1]
        data_payload.inst_id = get_instance_id()
        ret = True
        for reading_name, reading_type, reading_value, reading_unit, reading_note in zip(item.msg[2], item.msg[3], item.msg[4], item.msg[5], item.msg[6]):
            ret = (ret and data_payload.add_item(reading_name, reading_type, reading_value, reading_unit, reading_note))
        if not ret:
            logger.critical("Error in packing data....................................")
        logger.debug("DATA PAYLOAD:" + str(data_payload) + "\n\n")
        self.send_to_buffer_mngr(data_type, item.reply_id, [data_payload])
        logger.debug("Data msg sent to bufr mngr to send to NC." + "\n\n")
    

    ############################################################################## 
    # Adds msg to the buffer_mngr's buffer
    def send_to_buffer_mngr(self, msg_type, reply_id, msg):
        buff_msg = buffered_msg(msg_to_nc, msg_type, None, reply_id, msg)                     
        # Sends msg to buffer_mngr by adding to bfr_for_in_to_out_msgs
        add_to_thread_buffer(self.buffer_mngr.bfr_for_in_to_out_msgs, buff_msg, "Buffer Mngr")
        logger.debug("Msg sent to buffer_mngr." + "\n\n")
        
    
    # Called by main_thread to join all threads before exiting
    ##############################################################################     
    def close(self):
        for thread in sensor_thread_list:
            thread.join(1)
        logger.info("All per sensor threads exited."+ "\n\n")
    
    
    ##############################################################################  
    def __del__(self):
        print self, 'Sensor Controller object died'
   