FROM python:3.8-alpine

RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev

WORKDIR /avito

COPY . .

RUN pip install flask aiohttp psycopg2 requests

RUN echo "0 * * * * python /avito/check.py" >> /etc/crontabs/root

CMD crond -f
