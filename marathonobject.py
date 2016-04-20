import logging
import requests
import socket
import os
import random

class MarathonObject:

    marathon_url = None
    marathon_auth = None
    app_name = None
    group_name = None
    app_tasks = None
    mesos_url = None

    def __init__(self, marathon_url, marathon_auth, mesos_url):
        logging.debug("Marathon Object is being initialized...")
        if marathon_url[-1] == "/":
            self.marathon_url = marathon_url[:-1]
        else: self.marathon_url = \
            marathon_url
        logging.info("Marathon's url set to %s" %marathon_url)
        if marathon_auth != None:
            self.marathon_auth = tuple(marathon_auth.split(":"))
        else:
            self.marathon_auth = ("","")
        logging.info("Marathon's HTTP authentication info set to %s" %marathon_auth)
        if mesos_url[-1] == "/":
            self.mesos_url = mesos_url[:-1]
        else:
            self.mesos_url = mesos_url
        logging.info("Mesos master's url set to %s" %mesos_url)
        self.app_name = os.environ.get("MARATHON_APP_ID")
        logging.info("App name set to %s" % self.app_name)
        self.group_name = "/".join(self.app_name.split("/")[:-1])
        logging.info("Group name set to %s" %self.group_name)
        self.task_id = os.environ.get("MESOS_TASK_ID")
        logging.info("Task id set to %s" % self.task_id)
        logging.debug("Marathon Object successfully initialized!")

    def get_slaves_from_mesos(self):
        logging.debug("Obtaining list of Mesos slaves in progress...")
        try:
            r = requests.get("%s/state.json" %self.mesos_url)
            if r.status_code>=200 and r.status_code<300:
                slaves = r.json().get("slaves")
                if len(slaves) != 0 or slaves != None:
                    slave_names = [item.get("hostname") for item in slaves]
                    return slave_names
                else:
                    raise Exception("No slaves can be found for Mesos master on %s!" %self.mesos_url)
            else:
                raise Exception("Was not able to retrieve list of slaves from Mesos on %s. Response: %s" %(self.mesos_url,
                                                                                                            r.text))
        except Exception, e:
            raise Exception("Was not able to connect to Mesos (URL: %s) due to the following error: %s" %(self.mesos_url, e))

    def get_slave_hosts_and_ips(self):
        logging.debug("Obtaining IP addresses for Mesos slaves in progress...")
        slave_names = self.get_slaves_from_mesos()
        slave_data = map(lambda x: [socket.gethostbyname(x), x], slave_names)
        return slave_data

    def modify_etc_hosts(self):
        logging.info("Registering slave hosts in /etc/hosts in progress...")
        slave_data = self.get_slave_hosts_and_ips()
        slave_data = filter(lambda x: x[1] != os.environ['HOST'], slave_data)
        slave_data.append(["127.0.0.1", os.environ['HOST']])
        with open("/etc/hosts", "a") as f:
            for row in slave_data:
                joined_row = "\t".join(row)
                f.write(joined_row + "\n")
                logging.debug("Successfully added the following to /etc/hosts: %s" %joined_row )
        logging.info("Successfully modified /etc/hosts!")

    def get_app_tasks(self):
        logging.debug("Obtaining tasks for Marathon app named %s is in progress..." %self.app_name)
        url = "%s/v2/apps/%s" %(self.marathon_url,
                                self.app_name)
        try:
            r = requests.get(url, auth=self.marathon_auth)
            if r.status_code>=200 and r.status_code<300:
                app_data = r.json().get("app")
                tasks = app_data.get("tasks")
                if len(tasks) != 0:
                    return [item for item in tasks]
                else:
                    raise Exception("No tasks are running for app named %s!" %self.app_name)
            else:
                raise Exception("Was not able to retrieve data of Marathon app named %s. Marathon's response: %s" %(self.app_name,
                                                                                                                    r.text))
        except Exception, e:
            raise Exception("Was not able to connect to Marathon (URL: %s) due to the following error: %s" %(url, e))

    def find_master_hosts(self):
        logging.info("Obtaining running RabbitMQ instances (tasks) for Marathon app named %s in progress..." %self.app_name)
        tasks = self.get_app_tasks()
        if tasks[0].get("id") != self.task_id:
            master_hosts = [task.get("host") for task in tasks]
            logging.info("Found the following RabbitMQ hosts:")
            [logging.info(item) for item in master_hosts]
            return master_hosts
        else:
            logging.info("Current node is the 'master', therefore other nodes will attempt to connect to this instance first.")
            return None