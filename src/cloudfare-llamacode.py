import requests
import json

API_BASE_URL = "https://api.cloudflare.com/client/v4/accounts/c886e2113615b3fe3a957a568dbb03cf/ai/run/"
headers = {"Authorization": "Bearer 0hpaiksD7YysCCWIFJdk1AzMkYtw3TRtJjw_pWeK"}

def run(model, inputs):
    input_data = { "messages": inputs }
    response = requests.post(f"{API_BASE_URL}{model}", headers=headers, json=input_data)
    return response.json()

def read_logs_from_file(log_file_path):
    with open(log_file_path, 'r') as file:
        logs = file.readlines()
    logs_content = ''.join(logs)
    return logs_content

def analyze_logs(log_file_path):
    logs = read_logs_from_file(log_file_path)

    inputs = [
        { "role": "system", "content": "You are a docker container analysis tool" },
        { "role": "user", "content": f"""
        Analyze the following logs and provide a summary with identified issues and recommendations. Structure your response in JSON format with the following keys:
        - issues: A list of detected issues.
        - recommendations: Suggestions to resolve the issues.
        - summary: A brief summary of the overall log condition.
        
        Logs: {logs}
        """}
    ]

    output = run("@cf/meta/llama-3-8b-instruct", inputs)
    return output

if __name__ == "__main__":
    log_file_path = 'container_stats_logs.json'  

    analysis_output = analyze_logs(log_file_path)
    print(analysis_output)
