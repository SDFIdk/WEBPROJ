FROM tiangolo/meinheld-gunicorn-flask:python3.7

EXPOSE 5000

RUN pip install --upgrade pip
RUN pip install pyproj
RUN pip install flask-restplus

COPY /webproj/api.py /app/main.py
COPY /webproj/data.json /app/data.json

ENV FLASK_APP /app/main.py
ENV FLASK_ENV development
ENTRYPOINT ["flask", "run", "--host", "0.0.0.0", "--port", "5000"]
