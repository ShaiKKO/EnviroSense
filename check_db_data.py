import psycopg2
import json
import os

def load_config():
    """Load database configuration from config file"""
    config_path = os.path.join('config', 'database.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def main():
    """Check data in database tables"""
    config = load_config()
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=config['writer_host'],
            port=config['port'],
            database=config['database'],
            user=config['username'],
            password=config['password']
        )
        
        cursor = conn.cursor()
        
        # Check devices
        cursor.execute("SELECT COUNT(*) FROM sensor.devices")
        device_count = cursor.fetchone()[0]
        print(f"Number of devices: {device_count}")
        
        if device_count > 0:
            cursor.execute("SELECT id, name, device_type, serial_number FROM sensor.devices LIMIT 5")
            devices = cursor.fetchall()
            print("\nSample devices:")
            for device in devices:
                print(f"  ID: {device[0]}, Name: {device[1]}, Type: {device[2]}, Serial: {device[3]}")
        
        # Check parameters
        cursor.execute("SELECT COUNT(*) FROM sensor.parameters")
        param_count = cursor.fetchone()[0]
        print(f"\nNumber of parameters: {param_count}")
        
        if param_count > 0:
            cursor.execute("SELECT id, name, code, unit FROM sensor.parameters LIMIT 5")
            parameters = cursor.fetchall()
            print("\nSample parameters:")
            for param in parameters:
                print(f"  ID: {param[0]}, Name: {param[1]}, Code: {param[2]}, Unit: {param[3]}")
        
        # Check sensor readings
        cursor.execute("SELECT COUNT(*) FROM sensor.sensor_readings")
        readings_count = cursor.fetchone()[0]
        print(f"\nNumber of sensor readings: {readings_count}")
        
        if readings_count > 0:
            cursor.execute("""
                SELECT sr.id, d.serial_number, p.name, sr.value, sr.timestamp 
                FROM sensor.sensor_readings sr
                JOIN sensor.devices d ON sr.device_id = d.id
                JOIN sensor.parameters p ON sr.parameter_id = p.id
                ORDER BY sr.timestamp DESC
                LIMIT 5
            """)
            readings = cursor.fetchall()
            print("\nSample readings:")
            for reading in readings:
                print(f"  ID: {reading[0]}, Device: {reading[1]}, Parameter: {reading[2]}, Value: {reading[3]}, Time: {reading[4]}")
        
    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
