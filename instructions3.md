in the app, check for any legacy instance of user.group and remove all. 
update the dependencies.py to only have one function of is_user_in_group that checks if a user is in a group.
-- for the mocking, just print that you are mocking and set is_memeber to True.

note, that i already ran docker compsoe up db minio -d to set up the database and minio.
the app is running on the host machine, not the docker container.

I already did 
uv venv venv
source venv\Scripts\activate
uv pip install -r requirements.txt
