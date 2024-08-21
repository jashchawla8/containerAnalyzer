import docker
import json
import time
from confluent_kafka import Producer

# Initialize Docker client
client = docker.from_env()

# Configure the Kafka producer
conf = {
    'bootstrap.servers': 'localhost:9092',  # Adjust for your Kafka broker
    'client.id': 'docker-stats-producer'
}
producer = Producer(conf)


def delivery_report(err, msg):
    """Delivery callback to confirm the message delivery."""
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")


def send_container_stats_to_kafka(container_name, kafka_topic):
    """Retrieve Docker container stats and send them to a Kafka topic."""
    try:
        container = client.containers.get(container_name)

        # Get container stats
        stats = container.stats(stream=False)  # Get a snapshot of the stats

        # Prepare the message to send to Kafka
        message = {
            'container_name': container_name,
            'cpu_usage': stats['cpu_stats']['cpu_usage']['total_usage'],
            'memory_usage': stats['memory_stats']['usage'],
            'memory_limit': stats['memory_stats']['limit'],
            'timestamp': time.time()
        }

        # Serialize message as JSON
        serialized_message = json.dumps(message)

        # Send the message to Kafka
        producer.produce(kafka_topic, value=serialized_message, callback=delivery_report)
        producer.flush()  # Ensure message is sent

    except Exception as e:
        print(f"Error retrieving or sending stats for container {container_name}: {str(e)}")


if __name__ == "__main__":
    container_name = 'kafka'  # Replace with your container name
    kafka_topic = 'container_logs'  # Kafka topic to send the stats to

    while True:
        send_container_stats_to_kafka(container_name, kafka_topic)
        time.sleep(5)  # Send stats every 5 seconds
