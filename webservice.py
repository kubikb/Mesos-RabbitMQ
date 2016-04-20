from flask import Flask, jsonify, request
import logging
import os
import psutil

# Function to determine if a process under a certain pid exists or not
def check_pid(pid):
    pid = int(pid)
    try:
        os.kill(pid, 0)
        return "RUNNING"
    except Exception, e:
        logging.debug("Error encountered when checking pid %s: %s!" %(pid, e))
        return "NOT RUNNING"

def check_child_pid(pid):
    try:
        p = psutil.Process(pid)
        child_pid = [child.pid for child in p.children(recursive=True)][0]
        logging.debug("Child process of %s has the pid %s" %(pid, child_pid))
        return check_pid(child_pid)
    except:
        logging.debug("Could not get pid of %s's child process" %(pid))
        return "NOT RUNNING"

# Dict to store process pids
process_pids = {"rabbitpid": "",
                "nodename": ""}

class WebService():

    app = Flask(__name__)

    def __init__(self, port, rabbit_pid, nodename):
        flask_logger = logging.getLogger("werkzeug")
        flask_logger.setLevel(logging.INFO)

        process_pids["rabbit"] = rabbit_pid
        process_pids["nodename"] = nodename

        self.app.run(host="0.0.0.0",
                     port=port)

    @staticmethod
    @app.route('/', methods=['GET'])
    def manage_calls():
        if request.method == "GET":
            running_processes = {"Node name": process_pids.get("nodename"),
                                 "RabbitMQ pid" : check_child_pid(process_pids.get("rabbit"))}

            if "NOT RUNNING" in running_processes.values():
                return jsonify(running_processes), 500
            else:
                return jsonify(running_processes), 200