# Project
## Task 1 - Appplication Architecture Design
> Hello, I am contacting you on behalf of Jäppinen Ltd. I am gathering proposals for PoC where we would use AI for data quality management. 

> **Why?**  We need this solution for data profiling, so that our non-technical users can ask questions like how many fields are empty, or if there are any outliers present. Basically, so that the user can interact with the data and get answers for simple data questions. 

> **How?**  We will collect data from various sources into a SQL database and then utilize AI as “data analyst”. Users will ask questions about data via UI, and AI will do SQL queries and other analysis. This will likely require use of Generative AI. 

From my point of view the best set-up for this kind of a tool would be a internal web page with a single background server tending to most of the users requests. The probable amount of users as well as the data don't necessitate any kind of scalable service as each request shouuld be able to be handled by single server.

### Frontend
Web frontend of the persons flavour. I recommend Vue or plain HTML,CSS,JS for simplicity. Session would be handled by the client that would store chat information in local storage. Depending on the client's internal network setup auth would or wouldn't be needed.

### Backend
A python fastapi server but could be any framework or library. The server itself would be structured to be run from a docker container for portability as well as ease of updating, maintenence and general DevOps.

The server itself will expose several API endpoints to which the web frontend will connect to. Also by exposing the API endpoints to the whole local network the chat with database could be implemented in other applications used by the employees. If need be auth can also be implemented.

How aproximately the architecture should be structured you can find here:

``` mermaid
architecture-beta
    group userSpace(internet)[User Space]
    group serverSpace(cloud)[Client Intranet]
    
    service website(internet)[Web Frontend] in serverSpace
    service server(cloud)[Python Server] in serverSpace
    service database(database)[SQL Database] in serverSpace
    service user(internet)[User] in userSpace

    server:B <--> T:database 
    server:R <--> L:website
    user:L --> R:website

```

### Technology
The project is rather flexible in regards to which technology we choose to use but here is my proposal of the applications tech stack.

#### Frontend
 - Vue.js frontend hosted on a quick and easy node webserver.

#### Backend
 - Docker to host the servers image and keep it running.
 - FastAPI python http server framework for the api structure.
 - pyodbc package to interact with the SQL server
 - Pandas package to process the data retrived from the DB

### Hard Requirements
The project isn't resource intensive however it will require a server to host probably three running docker images for the server, db and the web. 
