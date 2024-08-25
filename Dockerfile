FROM python:3.12.5
LABEL authors="ikaialai"

WORKDIR /workplace/

COPY ./.env ./.env

COPY ./requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./app ./

ENTRYPOINT python3 ./main.py