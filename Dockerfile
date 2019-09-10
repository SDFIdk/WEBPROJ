FROM continuumio/miniconda3:latest


COPY ./environment.yaml ./
COPY /api/* ./

RUN ["/bin/bash", "-c", "conda init bash"]
RUN ["/bin/bash", "-c", "conda env create -f environment.yaml"]
RUN ["/bin/bash", "-c", "activate webproj"]

