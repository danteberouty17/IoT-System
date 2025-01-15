# E2E-IoT-System
Group project completed by Dante Berouty and Thomas Nguyen in Python. The system is comprised of a 
TCP Client, a TCP Server, the virtual device system created in Dataniz, and a MongoDB database. 
The virtual devices generate data from their sensors (i.e. sensor for refrigerator's electricity 
consumption). This data is then collected and stored in the database for each device in the system. 
Clients can make queries to the server which will then process the query into a request that is sent
to the database. The requested data is found then returned back to the client through the server, 
allowing the client to obtain things such as electricity consumption over the past 3 hours for a 
smart dishwasher. Currently the project can only handle 3 queries, since that was what was requested
for this project. However, since metadata is implemented, it makes it scalable for more requests and 
devices. It also allows for the ability to then convert this system for use on a real world system
rather than a virtually simulated one.