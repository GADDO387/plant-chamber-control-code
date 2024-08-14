<?php
header('Content-Type: application/json');

$servername = "172.20.10.4";
$username = "Gaddo";
$password = "12345";
$dbname = "sensor_data";

// Create connection
$conn = new mysqli($servername, $username, $password, $dbname);

// Check connection
if ($conn->connect_error) {
    die(json_encode(['error' => 'Database connection failed: ' . $conn->connect_error]));
}

// Handle GET request to fetch data
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $sql = "SELECT id, temperature, humidity, luxvalue, datetime FROM DHT11 ORDER BY datetime DESC LIMIT 10";
    $result = $conn->query($sql);

    $data = array();
    if ($result->num_rows > 0) {
        while($row = $result->fetch_assoc()) {
            $data[] = $row;
        }
    }

    echo json_encode($data);
}

// Handle POST request to send the setpoint value to the Arduino
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $lux = intval($_POST['lux']);

    if ($lux >= 0 && $lux <= 255) {
        // Open the serial port
        $serial = fopen('/dev/ttyACM0', 'w+'); // Update the path to your serial port if needed

        if ($serial) {
            // Write the setpoint value to the serial port
            fwrite($serial, $lux . "\n");

            // Close the serial port
            fclose($serial);

            // Return a success message
            echo json_encode(['message' => 'Setpoint value sent successfully.']);
        } else {
            // Return an error message if the serial port couldn't be opened
            echo json_encode(['message' => 'Error: Unable to open serial port.']);
        }
    } else {
        // Return an error message if the value is out of range
        echo json_encode(['message' => 'Error: Please enter a value between 0 and 255.']);
    }
}

// Close the database connection
$conn->close();
?>

