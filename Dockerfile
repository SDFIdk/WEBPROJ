# See https://github.com/tiangolo/meinheld-gunicorn-flask-docker
# for notes on how to use this particular Docker image.
#
# In summary: Make sure that a /app/main.py file with a Flask-object called
# 'app'  is present and everything should run smoothly with all the bells and
# whistles of a properly configured HTTP server

FROM tiangolo/meinheld-gunicorn-flask:python3.9

ENV WEBPROJ_LIB /proj

RUN mkdir /proj

COPY /webproj /webproj/webproj
COPY /tests /webproj/tests
COPY /app /webproj/app
COPY /setup.py /webproj/setup.py
COPY /README.md /webproj/README.md
COPY /app/main.py /app/main.py

# Running upgrade for security
RUN apt update -y && apt upgrade -y

RUN pip install --upgrade pip
RUN pip install "pyproj<3.4.0"
RUN pip install "flask>=2.1.0,<2.2.0"
RUN pip install flask-restx flask-cors
run pip install "Werkzeug>=2.1.0,<2.2.0"
RUN pip install /webproj
RUN pyproj sync --source-id dk_sdfe -v

