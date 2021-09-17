# See https://github.com/tiangolo/meinheld-gunicorn-flask-docker
# for notes on how to use this particular Docker image.
#
# In summary: Make sure that a /app/main.py file with a Flask-object called
# 'app'  is present and everything should run smoothly with all the bells and
# whistles of a properly configured HTTP server

FROM tiangolo/meinheld-gunicorn-flask:python3.7

ENV WEBPROJ_LIB /proj

RUN mkdir /proj

ADD https://download.osgeo.org/proj/proj-datumgrid-europe-1.4.tar.gz /
ADD https://download.osgeo.org/proj/proj-datumgrid-north-america-1.2.tar.gz /

RUN tar -zxvf /proj-datumgrid-europe-1.4.tar.gz -C /proj \
    && tar -zxvf /proj-datumgrid-north-america-1.2.tar.gz -C /proj

RUN rm /proj-datumgrid-europe-1.4.tar.gz \
    && rm /proj-datumgrid-north-america-1.2.tar.gz

COPY /webproj /webproj/webproj
COPY /tests /webproj/tests
COPY /app /webproj/app
COPY /setup.py /webproj/setup.py
COPY /README.md /webproj/README.md
COPY /app/main.py /app/main.py

RUN pip install --upgrade pip
RUN pip install pyproj flash-restx flask-cors Werkzeug
RUN pip install /webproj
