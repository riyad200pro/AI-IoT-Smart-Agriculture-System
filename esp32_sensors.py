from datetime import datetime
import time
import serial
import csv
import os

# Serial port configuration
SERIAL_PORT = '/dev/ttyUSB0'  # Adjust this to your actual port
BAUD_RATE = 115200

# CSV file configuration
CSV_FILE = "sensor_data.csv"
HEADER = ['Nitrogen', 'Phosphorus', 'Potassium', 
          'Air_Temp', 'Air_Humidity', 'Soil_Temp', 
          'Water_Level', 'pH_Value', 'DateTime']

# Sensor error messages
SENSOR_ERRORS = {
    'Nitrogen': "NPK Sensor Error (Nitrogen) - Check sensor connections",
    'Phosphorus': "NPK Sensor Error (Phosphorus) - Check sensor connections",
    'Potassium': "NPK Sensor Error (Potassium) - Check sensor connections",
    'Air_Humidity': "DHT11 Humidity Sensor Error - Check sensor connections",
    'Air_Temp': "DHT11 Temperature Sensor Error - Check sensor connections",
    'Soil_Temp': "DS18B20 Soil Temp Sensor Error - Check sensor connections",
    'Water_Level': "Water Level Sensor Error - Cannot control water motor! Check sensor immediately",
    'pH_Value': "pH Sensor Error - Check sensor connections and calibration"
}

def setup_csv_file():
    """Create CSV file with headers if it doesn't exist"""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)

def check_sensor_errors(sensor_data):
    """Check for NAN values and return appropriate error messages"""
    errors = []
    for sensor, value in sensor_data.items():
        if value is None or (isinstance(value, float) and value != value):  # Check for NAN
            errors.append(SENSOR_ERRORS.get(sensor, f"Unknown sensor error: {sensor}"))
    return errors

def parse_sensor_data(line):
    """
    Parse the serial data line into a dictionary
    Format from Arduino: N P K Humidity AirTemp SoilTemp WaterLevel pH
    """
    try:
        parts = line.split()
        
        # Handle "NAN" values for NPK sensors
        npk_values = []
        for val in parts[:3]:
            if val == 'NAN':
                npk_values.append(float('nan'))
            else:
                npk_values.append(float(val))
        
        # Extract other values
        data = {
            'Nitrogen': npk_values[0],
            'Phosphorus': npk_values[1],
            'Potassium': npk_values[2],
            'Air_Humidity': float(parts[3]),
            'Air_Temp': float(parts[4]),
            'Soil_Temp': float(parts[5]),
            'Water_Level': float(parts[6]),
            'pH_Value': float(parts[7]),
            'Date': parts[8]
        }
        
        # Check for sensor errors
        errors = check_sensor_errors(data)
        if errors:
            print("\n".join(errors))
            
            # Special case for water level sensor
            if 'Water_Level' in [e for e in errors if 'Water_Level' in SENSOR_ERRORS[e]]:
                print("!!CRITICAL!!: Cannot run water motor without water level data!!")
                print("Please check the Water_Level sensor immediately to maintain proper irrigation")
        
        return data
    
    except (IndexError, ValueError) as e:
        print(f"Error parsing line: {line} - {str(e)}")
        return None

def main():
    setup_csv_file()  # This will only write header if file doesn't exist
    
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser, \
            open(CSV_FILE, 'a', newline='') as csvfile:
            
            writer = csv.DictWriter(csvfile, fieldnames=HEADER)
            
            print("Starting sensor data collection. Press Ctrl+C to stop...")
            print(f"Data will be saved to {CSV_FILE}")
            print("System will alert you if any sensors report errors\n")
            
            while True:
                try:
                    # Read and decode serial line
                    line = ser.readline().decode('utf-8').strip()
                    if not line:
                        continue
                    
                    # Parse sensor data
                    sensor_data = parse_sensor_data(line)
                    if not sensor_data:
                        continue
                    
                    # Prepare CSV row
                    row = {
                        'Timestamp': datetime.now().date(),
                        'Nitrogen': sensor_data['Nitrogen'],
                        'Phosphorus': sensor_data['Phosphorus'],
                        'Potassium': sensor_data['Potassium'],
                        'Air_Humidity': sensor_data['Air_Humidity'],
                        'Air_Temp': sensor_data['Air_Temp'],
                        'Soil_Temp': sensor_data['Soil_Temp'],
                        'Water_Level': sensor_data['Water_Level'],
                        'pH_Value': sensor_data['pH_Value'],
                        'DateTime': sensor_data['Date']
                    }
                    
                    # Write to CSV
                    writer.writerow(row)
                    csvfile.flush()
                    
                    # Print success message
                    print(f"{datetime.now()} - Data recorded successfully")
                    print("-" * 50)  # Separator for readability
                    
                    # Wait before next reading
                    time.sleep(3)
                
                except UnicodeDecodeError:
                    print("Error decoding serial data, skipping...")
                    continue
                
    except KeyboardInterrupt:
        print("\nData collection stopped by user.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()