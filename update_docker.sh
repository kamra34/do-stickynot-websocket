#!/bin/bash

docker stop $(docker ps -a -q)

#docker rm -f $(docker ps -a -q)
docker rm -f do-stickynote-websocket_container

docker build -t do-stickynote-websocket .

# Run the Docker container
docker run -d -p 5000:5000 -e FLASK_ENV=development -v ${PWD}/db:/app/db -e DATABASE_URI=sqlite:////app/db/users.db -e CREATE_TABLES=1 --name do-stickynote-websocket_container do-stickynote-websocket

#docker run -d -p 5000:5000 -e FLASK_ENV=development -v ${PWD}/db:/app/db -e DATABASE_URI=sqlite:////app/db/users.db -e CREATE_TABLES=1 --name do-stickynote-websocket_container do-stickynote-websocket && sleep 1 && docker exec -it do-stickynote-websocket_container flask database create-tables

# Wait for the container to start
#sleep 5

# Run the 'flask database create-tables' command inside the container
#docker exec -it do-stickynote-websocket_container flask database create-tables

# Output the container logs
docker logs -f do-stickynote-websocket_container


        