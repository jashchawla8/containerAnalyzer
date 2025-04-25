import json
import time
from confluent_kafka import Consumer, KafkaError

# Kafka Consumer configuration
conf = {
    'bootstrap.servers': 'localhost:9092',  # Kafka broker address
    'group.id': 'docker-stats-consumer',    # Consumer group ID
    'auto.offset.reset': 'earliest'         # Start reading at the earliest message
}
consumer = Consumer(conf)

# Kafka topic to consume from
kafka_topic = 'container_logs'
# Output file to save the logs
output_file = 'container_stats_logs.json'

def consume_and_save_to_file():
    """Consume messages from Kafka topic and save them to a file."""
    try:
        consumer.subscribe([kafka_topic])

        with open(output_file, 'a') as file:
            while True:
                msg = consumer.poll(timeout=1.0)  # Poll for new messages

                if msg is None:
                    continue  # No new message, continue polling
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition event
                        print("End of partition reached {0}/{1}"
                              .format(msg.topic(), msg.partition()))
                    else:
                        print("Error: {}".format(msg.error()))
                    continue

                # Deserialize message from Kafka
                message = json.loads(msg.value().decode('utf-8'))
                
                # Save message to file
                file.write(json.dumps(message) + '\n')
                file.flush()  # Immediately write data to disk

                # Optional: Print the message for monitoring purposes
                print(f"Consumed message: {message}")

                # Adjust the frequency as necessary
                time.sleep(1)  # Add delay if required

    except KeyboardInterrupt:
        print("Stopping consumer...")
    finally:
        # Close the consumer connection
        consumer.close()

if __name__ == "__main__":
    consume_and_save_to_file()
