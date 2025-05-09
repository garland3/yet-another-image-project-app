 docker build -t labeler .
 # run with the env file. map to port 8002 to make sure there is no conflict with the other service
 <!-- docker run --env-file .env -p 8002:8000 labeler
 # use docker compose. but tell it to not use the override file.  -->
 docker compose  -f docker-compose.yml  up -d --build