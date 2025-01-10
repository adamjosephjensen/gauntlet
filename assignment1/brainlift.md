note: I have no idea what a brainlift is. This is my working notes on the project.

# todo
- [ ] Plan initial approach
# personas

# core requirements

# user stories

# technical planning

## architecture

## data model

# Development build

Plan to use one lean dockerfile and different docker-compose files for dev and prod.

To run the dev build if you have made changes to the Dockerfile or docker-compose.dev.yml:
```
docker-compose -f docker-compose.dev.yml up --build
```

The --build flag in the docker-compose up command tells Docker to rebuild the images before starting the containers. Here's what it does specifically:
- Without --build: Docker will use cached images if they exist
- With --build: Docker will rebuild the images fresh, ensuring you have the latest version of your code and dependencies
- Do you need it?
  - If you've made changes to your Dockerfile or source code, then yes
  - If you're running the containers for the first time, yes
If nothing has changed and you just want to start existing containers, no (you can just use docker-compose -f docker-compose.dev.yml up)

# Environment notes
I needed to install postgress using brew.
```
brew update
brew install postgresql
```

Then I installed docker and docker-compose.
```
brew install docker
brew install docker-compose
```
