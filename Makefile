NAME = artfair/backend

.PHONY: build up stop logs enter 

build: docker-build 
up: docker-compose-up 
stop: docker-compose-stop 
logs: docker-compose-logs 
enter: docker-enter-backend
restart_backend: docker-restart_backend

docker-build:
	docker build -t "${NAME}" .

docker-compose-up:
	docker-compose up -d

docker-compose-stop:
	docker-compose stop

docker-compose-logs:
	docker-compose logs --tail=100 -f

docker-enter-backend:
	docker exec -it backend bash

docker-restart_backend:
	docker-compose up --build -d backend
