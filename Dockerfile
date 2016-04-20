FROM ubuntu:trusty

MAINTAINER Balint Kubik (kubikbalint@gmail.com)

# Default URLs
ENV RABBIT_MQ_DEB_URL "https://www.rabbitmq.com/releases/rabbitmq-server/v3.6.1/rabbitmq-server_3.6.1-1_all.deb"

# Install Rabbit MQ and enable RabbitMQ's management tool
RUN sudo apt-get install -y wget
RUN sudo echo 'deb http://www.rabbitmq.com/debian/ testing main' >> /etc/apt/sources.list && \
    wget https://www.rabbitmq.com/rabbitmq-signing-key-public.asc && \
    sudo apt-key add rabbitmq-signing-key-public.asc && \
    sudo apt-get update && \
    sudo apt-get install -y rabbitmq-server
RUN sudo rabbitmq-plugins enable rabbitmq_management

# Install Python and relevant libraries
RUN apt-get install -y python python-pip python-dev
RUN pip install flask docopt psutil

# Add necessary files
RUN mkdir /predix-rabbit
ADD *py /predix-rabbit/

# Expose ports
EXPOSE 5000
EXPOSE 5672
EXPOSE 4369
EXPOSE 25672
EXPOSE 5672
EXPOSE 5671
EXPOSE 15672
EXPOSE 61613
EXPOSE 61614
EXPOSE 1883
EXPOSE 8883

# SOme cleanin'
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set Erlang cookie and access control
RUN echo "ERLANGCOOKIE" > /var/lib/rabbitmq/.erlang.cookie
RUN chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie
RUN chmod 400 /var/lib/rabbitmq/.erlang.cookie

# Enable clients to connect from hosts other than localhost
RUN echo "[{rabbit, [{loopback_users, []}]}]." > /etc/rabbitmq/rabbitmq.config

# Entrypoint script
ENTRYPOINT ["python", "/predix-rabbit/start-rabbitmq.py"]
