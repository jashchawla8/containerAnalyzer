import json
import time
from confluent_kafka import Consumer, KafkaError

from src.feedback_generator import take_feedback
from src.llm import send_msg_to_llm

# Configure the Kafka consumer
conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'my-consumer-group',
    'auto.offset.reset': 'latest'
}
try:
    consumer = Consumer(conf)
except ValueError as e:
    print(f"Failed to create consumer: {e}")
    exit(1)
consumer.subscribe(['container_logs'])

feedback_file = 'llama_analysis_feedback.json'


def consume_logs():
    """Consume logs, send to Llama3.1, and save feedback."""
    while True:
        start_time = time.time()
        logs = []

        # Collect logs for 30 seconds
        while time.time() - start_time < 10:
            msg = consumer.poll(timeout=10.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(msg.error())
                    break

            # Add the message to logs
            logs.append(msg.value().decode('utf-8'))

        if logs:
            # Send logs to Llama3.1 for analysis
            #feedback = send_msg_to_llm(str(logs))
            chat_output = send_msg_to_llm(str(logs))
            print(chat_output)
            feedback_prompt = take_feedback()
            feedback_reply = send_msg_to_llm(feedback_prompt)
            print(feedback_reply)

            # Save the feedback
            #save_feedback(feedback)
            time.sleep(300)

def save_feedback(feedback_file, logs, initial_output, feedback_prompt):
    """Append feedback to a file."""
    with open(feedback_file, 'a') as f:
        f.write("Input logs supplied: \n")
        f.write(str(logs) + "\n")
        f.write(("recommendtaion provided by the LLM: \n"))
        f.write(initial_output + "\n")
        f.write("User response on the recommendation provided by the LLM" + "\n")
        f.write(feedback_prompt + "\n")

if __name__ == "__main__":
    consume_logs()