FROM python:3.8-slim-buster

WORKDIR /avito

COPY . .

RUN pip install flask aiohttp psycopg2-binary requests

CMD python main.py
