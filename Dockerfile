FROM python:3.10-buster
RUN mkdir /app
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
EXPOSE 5000
ENTRYPOINT ["/app/docker-entrypoint.sh"]