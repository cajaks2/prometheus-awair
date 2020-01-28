FROM python:3
#from ubuntu:latest
#RUN apt-get update; apt-get upgrade -y
#RUN  apt-get install git -y 
#RUN apt-get install apt-utils -y 
#RUN apt-get install  python -y 
RUN pip install prometheus_client
RUN pip install argparse
RUN git clone https://github.com/netmanchris/pyawair.git
WORKDIR pyawair
RUN python setup.py install
ADD awair.py .
ENTRYPOINT [ "python" ]
CMD [ "awair.py" ]

