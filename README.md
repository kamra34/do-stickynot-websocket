# Real-Time Sticky Note Application
This repository contains  the Digital Ocean Deployed version of real-time sticky note web application built using Python, Flask, and SQLite and with socketio websocket functionality. The application allows users to create and manage their notes, groups, and members with different roles. They can also see an eink-simulated board with live updates as soon as user add or updates notes.

## Local setup

1. Clone the repository.
2. Install Docker.
3. Run init_db.py to create "users.db" database.
4. create a folder named db and move users.db into that folder.
### Semi automated run
5. Run `bash ./update_docker.sh`
### Manual installation
5. Build the Docker image: `docker build -t do-stickynote-websocket .`
6. Run the Docker container: `docker run -d -p 5000:5000 -e FLASK_ENV=development -v ${PWD}/db:/app/db -e DATABASE_URI=sqlite:////app/db/users.db -e CREATE_TABLES=1 --name do-stickynote-websocket_container do-stickynote-websocket`
7. to see live logs you can run `docker logs -f do-stickynote-websocket_container`

To see more details and features, see my other repository:
https://github.com/kamra34/Dockerized-StickyNote

## Link to the application

The application is live at: [Digital Ocean Dockerized StickyNote with websocket](http://128.199.44.207:5000/login)

## Deployment to Digital Ocean

The application is deployed using Digital Ocean Docker server.
