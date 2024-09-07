FROM python:3.12.5
LABEL authors="ikaialai"

WORKDIR /workspace/

COPY ./requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./app ./
