Perform an extensive technical check of the current setup and code base.

Assume there is only one external dependency not included in this repo, which must be set up by the user. This dependency provides the ability to call the authorization server.

In testing mode only, you may mock this function.

Otherwise, call the real authorization server.

Update app/dependencies.py accordingly.

Create a new function is_user_in_group(user, group) to check if a user belongs to a group. This is the one authorization function. 

For all database operations, log the user who made the edits.

Remove the groups field from the database for the User. 

Group membership and authorization must always be checked at runtime. You may cache these results for 15 minutes.

Choose a fun commit message name for this update.

Check if any files exceed 400 lines; if so, refactor them to be under 400 lines.

Add a feature to allow users to create and use API keys for image-related operations, including uploading images and retrieving image data, as exposed in the UI.

Avoid code duplication by providing automatic mapping where possible.

Change the Dockerfile to use fedora:latest as the base image.