import docker
import json
import time
from confluent_kafka import Producer

client = docker.from_env()

conf = {
    'bootstrap.servers': 'localhost:9092', 
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

        stats = container.stats(stream=False)  

        message = {
            'container_name': container_name,
            'cpu_usage': stats['cpu_stats']['cpu_usage']['total_usage'],
            'memory_usage': stats['memory_stats']['usage'],
            'memory_limit': stats['memory_stats']['limit'],
            'timestamp': time.time()
        }
        print(message)

        serialized_message = json.dumps(message)

        producer.produce(kafka_topic, value=serialized_message, callback=delivery_report)
        producer.flush() 

    except Exception as e:
        print(f"Error retrieving or sending stats for container {container_name}: {str(e)}")


if __name__ == "__main__":
    container_name = 'kafka'  
    kafka_topic = 'container_logs' 

    while True:
        send_container_stats_to_kafka(container_name, kafka_topic)
        time.sleep(5)  

