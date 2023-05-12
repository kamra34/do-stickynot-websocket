# Real-Time Sticky Note Application
This repository contains  the AWS implementation of real-time sticky note web application built using Python, Flask, and SQLite. The application allows users to create and manage their notes, groups, and members with different roles.

## Local setup

1. Clone the repository.
2. Install Docker.
3. Build the Docker image: `docker build -t aws-stickynote .`
4. Run the Docker container: `docker run -p 5000:5000 aws-stickynote`

To see more details and features, see my other repository:
https://github.com/kamra34/Dockerized-StickyNote

## Link to the application

The application is live at: [AWS Elastic Beanstalk Dockerized StickyNote](http://aws-stickynote.eba-dmpa84bq.eu-north-1.elasticbeanstalk.com/login)

## Deployment to AWS Elastic Beanstalk

The application is deployed using AWS Elastic Beanstalk. Instructions for deploying an application on AWS Elastic Beanstalk can be found in the AWS Elastic Beanstalk [Documentation](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/welcome.html).
