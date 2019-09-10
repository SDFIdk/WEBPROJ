FROM continuumio/miniconda3:4.7.10

RUN conda update -n base -c defaults conda
RUN pip --version

COPY ./environment.yaml ./
COPY /api/* ./

RUN ["/bin/bash", "-c", "conda init bash"]
RUN ["/bin/bash", "-c", "conda env create -f environment.yaml"]
RUN ["/bin/bash", "-c", "activate webproj"]

RUN ["/bin/bash", "-c", "python --version"]
