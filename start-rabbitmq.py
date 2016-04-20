import os
import logging
import defaults
from docopt import docopt
from marathonobject import MarathonObject
from rabbitmqobject import RabbitMQObject
from webservice import WebService
import time

# Setup logging
logging.basicConfig(format='[%(levelname)s] %(asctime)s %(name)s %(filename)s:%(lineno)s - %(message)s',
                    level=logging.DEBUG)

if __name__ == '__main__':

    doc = """start-rabbitmq.py - Start Predix-RabbitMQ

    Usage:
        start-rabbitmq.py (-h | --help)
        start-rabbitmq.py --marathon_url=<marathon_url> [--marathon_auth=<marathon_auth>] [--mesos_url=<mesos_url>] [--rabbit_nodename=<rabbit_nodename>][--erlang_cookie=<erlang_cookie>] [--retry_count=<retry_count>] [--retry_interval=<retry_interval>]

    Options:
        -h, --help                                          show this screen
        -v, --verbose                                       verbose output
        -q, --quiet                                         do not show output, only errors
        --marathon_url=<marathon_url>                       REQUIRED: Marathon's URL
        --marathon_auth=<marathon_auth>                     HTTP Authentication info for Marathon. For example: adminUser:topP1ssw0rd
        --mesos_url=<mesos_url>                             The Mesos master's URL. Default value is Marathon's URL with Marathon's port (assumed to be 8080) replaced with 5050.
        --rabbit_nodename=<rabbit_nodename>                 Name of the rabbit node. It has to be the same for all nodes in the cluster [default: rabbit].
        --erlang_cookie=<erlang_cookie>                     An alphanumeric Erlang cookie. Can be of any size and has to be the same for all nodes in the cluster [default: ERLANGCOOKIE].
        --retry_count=<retry_count>                         The maximum number of attempts to cluster with another node [default: 10].
        --retry_interval=<retry_interval>                   The number of seconds to wait before reattempting to cluster with another node [default: 2].
    """

    # Parse docopt arguments
    args = docopt(doc, help=True, version=None)
    logging.info("Received the following arguments:")
    [logging.info("%s:%s" %(k,v)) for k,v in args.iteritems()]
    marathon_url = args.get("--marathon_url")
    marathon_auth = args.get("--marathon_auth")
    mesos_url = args.get("--mesos_url")
    if mesos_url == None:
        mesos_url = marathon_url.replace("8080","5050")

    # Initialize MarathonObject
    marathon = MarathonObject(marathon_url=marathon_url,
                              marathon_auth=marathon_auth,
                              mesos_url=mesos_url)
    marathon.modify_etc_hosts()


    # Initialize RabbitMQObject
    rabbit_nodename = args.get("--rabbit_nodename")
    erlang_cookie = args.get("--erlang_cookie")
    rabbit = RabbitMQObject(rabbit_nodename=rabbit_nodename,
                            erlang_cookie=erlang_cookie)
    logging.info("Starting RabbitMQ instance in progress...")

    # Start server
    rabbit_pid = rabbit.start_rabbit_server()
    # Wait several secs until server is started
    time.sleep(15)
    rabbit.start_rabbit_app()
    logging.info("RabbitMQ instance successfully started!")

    # Add user
    rabbit.add_user("predix", "hare123")

    # Join cluster
    master_hosts = marathon.find_master_hosts()
    if master_hosts != None:
        rabbit.stop_rabbit_app()
        # Loop until cluster has been successfully formed
        success = False
        for master_host in master_hosts:
            if success == False:
                success = rabbit.setup_cluster(master_host=master_host,
                                               retry_count=int(args.get("--retry_count")),
                                               retry_interval=int(args.get("--retry_interval")))
                logging.debug("Connecting to node %s got status: %s" %(master_host, success))
            else:
                logging.debug("Not attempting to join node %s to form cluster because one of the earlier attempts was successful" %master_host)
        if success  == False:
            # If cannot form cluster with any other nodes, stop trying and run in standalone
            logging.error("Could not connect to any other RabbitMQ node to form a cluster. Running in standalone...")
        # Start Rabbit app
        rabbit.start_rabbit_app()

    # Start WebService (mainly for Marathon HealthCheck)
    logging.debug("Starting webservice in progress...")
    WebService(5000, rabbit_pid, rabbit_nodename + "@" + os.environ.get("HOST"))