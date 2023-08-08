FROM python:3.11.3-slim-buster

COPY ./app /aqms-api/app
COPY ./pickles /aqms-api/pickles
COPY ./data /aqms-api/data
COPY ./main.py /aqms-api/main.py
COPY ./requirements.txt /aqms-api/requirements.txt

WORKDIR /aqms-api

RUN apt-get update
RUN apt-get -y install build-essential
RUN apt-get -y install python3-dev gcc libgdal-dev libspatialindex-dev
RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python", "./main.py"]

# docker build -t aqms-api .
# docker run -d -p 8000:8000 aqms-api
