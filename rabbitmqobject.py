import os
import logging
import subprocess, shlex
import multiprocessing
import defaults
import time

# Function to start RabbitMQ server
def start_rabbit_server(process_cmd):
    logging.debug("Starting RabbitMQ server with the following command: %s" %process_cmd)
    process_cmd = shlex.split(process_cmd)
    subprocess.Popen(process_cmd).wait()
    logging.error("RabbitMQ server stopped!")

class RabbitMQObject:

    own_host = None
    own_port = None
    own_dist_port = None
    own_epmd_port = None
    master_host = None
    master_port = None
    nodename = None
    nodename_short = None

    def __init__(self, rabbit_nodename, erlang_cookie):
        logging.debug("Initializing RabbitMQObject in progress...")
        # Obtain own host and ports
        own_host = os.environ["HOST"]
        self.own_host = own_host[:own_host.find(".")]
        own_ports = os.environ["PORTS"].split(",")
        self.own_port = own_ports[defaults.RABBIT_PORT_INDEX]
        logging.debug("Own hostname is %s and own port is %s" %(self.own_host, self.own_port))
        self.own_dist_port = own_ports[defaults.RABBIT_DIST_PORT_INDEX]
        logging.debug("RABBIT_DIST_PORT set to %s" %self.own_dist_port)
        self.own_epmd_port = own_ports[defaults.EPMD_PORT_INDEX]
        logging.debug("Erlang port mapper daemon's port set to %s" %self.own_epmd_port)
        self.nodename = rabbit_nodename + "@" + self.own_host
        self.nodename_short = rabbit_nodename
        logging.debug("Nodename set to %s" %self.nodename)
        # Set erlang cookie
    #     self.set_erlang_cookie(erlang_cookie)
    #
    # def set_erlang_cookie(self, erlang_cookie):
    #     logging.debug("Setting Erlang cookie (%s) in progress" %erlang_cookie)
    #     self.exec_rabbitmg_command(cmd = 'sudo echo "%s" > /var/lib/rabbitmq/.erlang.cookie' %erlang_cookie)
    #     self.exec_rabbitmg_command(cmd = 'sudo chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie')
    #     self.exec_rabbitmg_command(cmd = 'sudo chmod 400 /var/lib/rabbitmq/.erlang.cookie')
    #     logging.info("Erlang cookie (%s) successfully set!" %erlang_cookie)

    def exec_rabbitmg_command(self, cmd, replace_dict=None):
        logging.debug("Executing shell command in progress...")
        if replace_dict != None:
            for k,v in replace_dict.iteritems():
                cmd = cmd.replace(k, v)
        logging.debug("Executing the following shell command: %s" %cmd)
        cmd = shlex.split(cmd)
        p = subprocess.Popen(cmd)
        p.wait()
        if p.returncode != 0:
            raise Exception("Was not able to execute shell command! Received exit code %s"
                                %(p.returncode))
        logging.debug("Shell command has been successfully executed!")

    def start_rabbit_server(self):
        logging.debug("Starting RabbitMQ server in progress...")
        nodename = self.nodename
        start_rabbit_cmd = defaults.START_RABBIT_CMD.replace("{PORT}", self.own_port)
        start_rabbit_cmd = start_rabbit_cmd.replace("{NODENAME}", nodename)
        start_rabbit_cmd = start_rabbit_cmd.replace("{EPMD_PORT}", self.own_epmd_port)
        start_rabbit_cmd = start_rabbit_cmd.replace("{DIST_PORT}", self.own_dist_port)
        p = multiprocessing.Process(target=start_rabbit_server, args=(start_rabbit_cmd, ))
        p.start()
        rabbit_pid = p.pid
        logging.info("RabbitMQ server started (process pid: %s)!" %rabbit_pid)
        return rabbit_pid

    def start_rabbit_app(self):
        logging.debug("Starting RabbitMQ app in progress...")
        self.exec_rabbitmg_command(cmd = defaults.START_RABBIT_APP_CMD,
                                   replace_dict={"{NODENAME}": self.nodename,
                                                 "{EPMD_PORT}": self.own_epmd_port})
        logging.info("RabbitMQ app successfully started!")

    def stop_rabbit_app(self):
        logging.debug("Stopping RabbitMQ app in progress...")
        self.exec_rabbitmg_command(cmd = defaults.STOP_RABBIT_APP,
                                   replace_dict={"{NODENAME}": self.nodename,
                                                 "{EPMD_PORT}": self.own_epmd_port})
        logging.info("RabbitMQ app successfully stopped!")

    def join_master(self, master_nodename):
        logging.debug("Joining RabbitMQ master in progress...")
        self.exec_rabbitmg_command(cmd = defaults.JOIN_CLUSTER_CMD,
                                   replace_dict={"{NODENAME}": self.nodename,
                                                 "{EPMD_PORT}": self.own_epmd_port,
                                                 "{MASTER_NODE}": master_nodename})
        logging.info("RabbitMQ node successfully joined cluster!")

    def add_user(self, username, password):
        logging.info("Setting admin user for RabbitMQ in progress...")
        self.exec_rabbitmg_command(cmd = defaults.ADD_RABBIT_USER,
                                   replace_dict={"{NODENAME}": self.nodename,
                                                 "{EPMD_PORT}": self.own_epmd_port,
                                                 "{USERNAME}": username,
                                                 "{PASS}": password})
        self.exec_rabbitmg_command(cmd = defaults.SET_USER_TAGS,
                                   replace_dict={"{NODENAME}": self.nodename,
                                                 "{EPMD_PORT}": self.own_epmd_port,
                                                 "{USERNAME}": username})
        logging.info("Successfully added user %s to RabbitMQ. Password: %s" %(username, password))

    def setup_cluster(self, master_host, retry_count, retry_interval):
        if master_host != None:
            logging.info("Setting up cluster in progress...")
            master_nodename = "%s@%s" %(self.nodename_short,
                                        master_host[:master_host.find(".")])
            if master_nodename != self.nodename:
                logging.info("Joining cluster (%s) is in progress..." %master_nodename)

                i = 1 # Counter
                looping = True
                success = False
                while looping == True:
                    try:
                        self.join_master(master_nodename)
                        logging.info("RabbitMQ node successfully connected to the cluster!")
                        success = True
                        looping = False
                    except:
                        logging.info("Was not able to join node named %s. Retrying in %s..." %(master_nodename,
                                                                                               retry_interval))
                        time.sleep(retry_interval)
                        i += 1
                    if i >= retry_count:
                        logging.debug("Attempted unsuccessfully to form cluster with node named %s %s times" %(master_nodename, retry_count))
                        looping = False
                if success:
                    return True
                else:
                    return False
            else:
                return True