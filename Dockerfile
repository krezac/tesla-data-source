FROM python:3.8-alpine

EXPOSE 5000

MAINTAINER krezac@gmail.com

RUN apk add --no-cache --virtual .build-deps gcc g++ make libc-dev mariadb-dev build-base freetype-dev jpeg-dev zlib-dev && \
    apk add --no-cache mariadb-connector-c postgresql-dev python3-dev musl-dev

COPY . /app
WORKDIR /app

RUN pip install pipenv

RUN pipenv install --system --deploy

RUN apk del --purge .build-deps

CMD ["python", "app.py"]
