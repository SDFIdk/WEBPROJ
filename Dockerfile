FROM tiangolo/meinheld-gunicorn-flask:python3.7

EXPOSE 5000

RUN pip install --upgrade pip
RUN pip install pyproj
# RUN pip install flask-restful
RUN pip install flask-restful-swagger

COPY /webproj/api.py /app/main.py
COPY /webproj/data.json /app/data.json


