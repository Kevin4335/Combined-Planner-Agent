import json
import time
from _thread import start_new_thread

import requests

from ai_assistant import chat_one_round
from cypher_agent import generate_cypher_query, run_cypher
from multi_thread_workers import map_infinite_retry
from utils import HIRN_ABSTRACT_SEARCH_URL

data = json.loads(open('/Users/jtc/Desktop/文件/UMich/WI2025/bio-lab/glkb_dataset/first_100_grok_thinking_less_relationship_by_grok_20250416.json').read())
num = len(data)


def test_cypher():
    cypher = generate_cypher_query("what is breast cancer")
    print(cypher)
    result = run_cypher(cypher)
    print(result)


def test_embedding():
    params = {
        "query": "gene TOP2A functions and mechanisms",
        "k": 5,
    }
    res = requests.get(HIRN_ABSTRACT_SEARCH_URL, params=params)
    res.raise_for_status()
    res = res.json()
    print(json.dumps(res, indent=2, ensure_ascii=False))


def process_question(question: str):
    history, answer = chat_one_round([], question)
    return "\n\n".join([message['content'] for message in history])


def safe_process_question(question):
    l = []
    start_new_thread(lambda: l.append(process_question(question)), ())
    for i in range(900):
        time.sleep(0.1)
        if len(l) > 0:
            return l[0]
    assert False


def search_test(data):
    all_question = [data[i]['json']['question'] for i in range(num)]
    results = map_infinite_retry(safe_process_question, all_question, max_workers=5, print_progress=True)
    results = [{'input': data[i], 'output': results[i]} for i in range(num)]
    return results

def search_test_2(data):
    all_question = [data[i]["less_relationship"] for i in range(num)]
    results = map_infinite_retry(safe_process_question, all_question, max_workers=5, print_progress=True)
    results = [{'input': data[i], 'output': results[i]} for i in range(num)]
    return results


def get_found_num(path: str):
    data = json.loads(open(path).read())
    num = 0
    for item in data:
        original_abs = item['input']['abs']
        output = item['output']
        original_abs = json.dumps(original_abs, ensure_ascii=False)[1:50]
        if original_abs in output:
            num += 1
    return num


if __name__ == "__main__":
    name = './first_100_grok_thinking_less_relationship_by_grok_20250416_results_20250416.json'
    result = search_test_2(data)
    open(name, 'w').write(json.dumps(result, indent=2, ensure_ascii=False))
    
    print(get_found_num(name))
    
    pass
