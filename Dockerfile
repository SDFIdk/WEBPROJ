FROM tiangolo/uwsgi-nginx-flask:python3.7

RUN pip install --upgrade pip
RUN pip install pyproj
RUN pip install flask-restful

COPY ./environment.yaml ./
COPY /api/* ./

RUN python api.py
