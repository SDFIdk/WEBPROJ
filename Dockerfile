FROM tiangolo/meinheld-gunicorn-flask:python3.7

EXPOSE 5000

RUN pip install --upgrade pip
RUN pip install pyproj
RUN pip install flask-restful
RUN pip install flask-rest-api

COPY /api/api.py /app/main.py
COPY /api/data.json /app/data.json


