FROM python:3.8.1-slim

RUN apt-get update && apt-get install catdoc

RUN mkdir /install
WORKDIR /install
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

WORKDIR /workshop
COPY applications ./applications
COPY common ./common
COPY crud ./crud
COPY model ./model
COPY app.py app.py
COPY respcode.py respcode.py
COPY start.sh ./start.sh
RUN chmod a+x start.sh

CMD [ "./start.sh" ]