# See https://github.com/tiangolo/meinheld-gunicorn-flask-docker
# for notes on how to use this particular Docker image.
#
# In summary: Make sure that a /app/main.py file with a Flask-object called
# 'app'  is present and everything should run smoothly with all the bells and
# whistles of a properly configured HTTP server

FROM tiangolo/meinheld-gunicorn-flask:python3.7

EXPOSE 5000

#ADD https://download.osgeo.org/proj/proj-datumgrid-europe-latest.tar.gz /proj
#ADD https://download.osgeo.org/proj/proj-datumgrid-north-america-latest.tar.gz /proj

ENV PROJ_LIB $PROJ_LIB:/proj

COPY /webproj /webproj/webproj
COPY /tests /webproj/tests
COPY /app /webproj/app
COPY /setup.py /webproj/setup.py
COPY /README.md /webproj/README.md
COPY /app/main.py /app/main.py


RUN pip install --upgrade pip
RUN pip install pyproj
RUN pip install flask-restplus
RUN pwd
RUN ls
RUN pip install /webproj
