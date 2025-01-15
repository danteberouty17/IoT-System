import socket
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import os

load_dotenv()

def connect_to_mongo():
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI not found in .env file")
    client = MongoClient(mongo_uri)
    db_name = os.getenv("DB_NAME", "test") # Default to "test"
    return client[db_name]

def fetch_all_devices(db):
    # Fetches all documents with "customAttributes.type" == "DEVICE"
    return list(db["Database_metadata"].find({"customAttributes.type": "DEVICE"}))

def extract_sensors_from_device(device_doc):

    device_type = device_doc.get("customAttributes", {}).get("type", "")
    device_name = device_doc.get("customAttributes", {}).get("name", "")
    device_uid = device_doc.get("assetUid")
    sensors = []
        
    # Iterate over children of the device, looking for boards and their sensors
    top_children = device_doc.get("customAttributes", {}).get("children", [])
    for board in top_children:
        if board.get("customAttributes", {}).get("type", "").upper() == "BOARD":
            board_children = board.get("customAttributes", {}).get("children", [])
            for sensor in board_children:
                if sensor.get("customAttributes", {}).get("type", "").upper() == "SENSOR":
                    sensors.append({
                        "uid": sensor["assetUid"],
                        "name": sensor["customAttributes"]["name"],
                        "device_name": device_name,
                        "device_type": device_type,
                        "device_uid": device_uid
                    })
    return sensors

def fetch_all_sensors(db):
    devices = fetch_all_devices(db)
    all_sensors = []
    for d in devices:
        all_sensors.extend(extract_sensors_from_device(d))
    return all_sensors

def identify_sensor_type(sensor_name):
    name_lower = sensor_name.lower()
    if "moisture" in name_lower:
        return "moisture"
    elif "water flow" in name_lower:
        return "water_flow"
    elif "ammeter" in name_lower:
        return "electricity"
    return None

def filter_sensors(all_sensors, device_keyword, sensor_type=None):
    """
    Filter sensors by device keyword 
    """
    filtered_sensors = []
    for sensor in all_sensors:
        if device_keyword.lower() in sensor["device_name"].lower():
            if sensor_type is None or identify_sensor_type(sensor["name"]) == sensor_type:
                filtered_sensors.append(sensor)
    return filtered_sensors

def get_sensor_values_for_devices(collection, device_uids, sensor_list, time_filter=None):
    query = {"payload.parent_asset_uid": {"$in": device_uids}}
    if time_filter:
        query["time"] = time_filter

    # Group sensor names by device_uid for quick lookup
    sensor_names_by_device = {}
    for sensor in sensor_list:
        sensor_names_by_device.setdefault(sensor["device_uid"], set()).add(sensor["name"])

    values = []
    for doc in collection.find(query):
        payload = doc.get("payload", {})
        device_uid = payload.get("parent_asset_uid")
        if device_uid in sensor_names_by_device:
            for sensor_name in sensor_names_by_device[device_uid]:
                if sensor_name in payload:
                    try:
                        values.append(float(payload[sensor_name]))
                    except (ValueError, TypeError):
                        pass
    return values

def handle_query(query_number, db):
    collection = db["Database_virtual"]
    all_sensors = fetch_all_sensors(db)

    if query_number == '1':
        # Average moisture in last 3 hours for all Fridges
        moisture_sensors = filter_sensors(all_sensors, "fridge", "moisture")
        
        if not moisture_sensors:
            return "No moisture sensors found for Fridges."
        fridge_device_uids = list({s["device_uid"] for s in moisture_sensors})
        print(f"Query 1: Number of fridges: {len(fridge_device_uids)}") # Count of unique fridges
        
        now = datetime.now(timezone.utc)
        time_filter = {"$gte": now - timedelta( hours= 3 ), "$lte": now}
        values = get_sensor_values_for_devices(collection, fridge_device_uids, moisture_sensors, time_filter=time_filter)
        
        if values:
            return f"Average moisture across all fridges (last 3 hrs): { sum(values) / len(values):.2f}%"
        return "Error"

    elif query_number == '2':
        # Average water flow for all Smart Dishwashers
        water_sensors = filter_sensors(all_sensors, "smart dishwasher", "water_flow")
        
        if not water_sensors:
            return "No water flow sensors found for Smart Dishwashers."
        dishwasher_device_uids = list({s["device_uid"] for s in water_sensors})
        print(f"Query 2: Number of smart dishwashers: {len(dishwasher_device_uids)}")  # count of unique dishwashers
        
        values = get_sensor_values_for_devices(collection, dishwasher_device_uids, water_sensors)
        if values:
            return f"Average water consumption per cycle: {sum(values) / len(values):.2f} liters"
        return "Error"

    if query_number == '3':
        # Which device consumed the most electricity?
        electricity_sensors = [s for s in all_sensors if identify_sensor_type(s["name"]) == "electricity"]
        if not electricity_sensors:
            return "No electricity sensors found."
        device_names_by_uid = {s["device_uid"]: s["device_name"] for s in electricity_sensors}
        device_uids = list(device_names_by_uid.keys())

        print(f"Query 3: Number of devices included in the calculation: {len(device_uids)}")  # Log the number of devices

        # Sum electricity consumption for each device
        consumption = {uid: 0.0 for uid in device_uids}
        total_instances = 0  # Track the number of instances included

        query = {"payload.parent_asset_uid": {"$in": device_uids}}
        for doc in collection.find(query):
            payload = doc.get("payload", {})
            device_uid = payload.get("parent_asset_uid")
            for sensor in electricity_sensors:
                if sensor["device_uid"] == device_uid and sensor["name"] in payload:
                    try:
                        consumption[device_uid] += float(payload[sensor["name"]])
                        total_instances += 1  # Increment the instance count
                    except (ValueError, TypeError):
                        pass

        print(f"Query 3: Number of instances included in the calculation: {total_instances}")  # Log the total instances

        if not any(consumption.values()):
            return "No electricity consumption data found."
        max_device_uid = max(consumption, key=consumption.get)
        
        return f"{device_names_by_uid[max_device_uid]} consumed the most electricity: {consumption[max_device_uid]:.2f} kWh"


    else:
        return "Invalid query."

def echo_server():
    db = connect_to_mongo()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_ip = '0.0.0.0'
    server_port = int(input("Enter the port number to bind the server: "))

    try:
        server_socket.bind((server_ip, server_port))
        server_socket.listen(1)
        print(f"Server is listening on port {server_port}")

        while True:
            conn, addr = server_socket.accept()
            try:
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    query = data.decode().strip()
                    response = handle_query(query, db)
                    conn.sendall(response.encode())
            except Exception as e:
                print(f"Error: {e}")
            finally:
                conn.close()
    except KeyboardInterrupt:
        print("Shutting down server.")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    echo_server()
