# README.md

# Streamlit System Monitor

This project is a Streamlit-based system monitor application that provides real-time insights into system performance metrics. It utilizes various libraries to gather and visualize data about CPU usage, memory consumption, and other system statistics.

## Project Structure

```
.
├── app
│   ├── Home.py
│   ├── pages
│   │   ├── alerts_history.py
│   │   ├── network_analysis.py
│   │   └── system_details.py
│   └── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── readme.md

```

## Getting Started

### Prerequisites

- Docker
- Docker Compose

### Building the Docker Image

To build the Docker image, navigate to the project directory and run:

```bash
docker build -t streamlit-monitor .
```

### Running the Application

To run the application using Docker Compose, execute the following command:

```bash
sudo docker-compose up
```

This will start the application and make it accessible at `http://localhost:8501`.

### Stopping the Application

To stop the application, press `CTRL+C` in the terminal where the Docker Compose command is running, or run:

```bash
docker-compose down
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.