from cypher_agent import generate_cypher_query, run_cypher
import requests
import json
from ai_assistant import chat_one_round
from _thread import start_new_thread
import time
from multi_thread_workers import map_infinite_retry

RESULT_DIR = './results_2000'
data = json.loads(open('/Users/jtc/Desktop/文件/UMich/WI2025/bio-lab/glkb_dataset/final_2000_grok_thinking_less_relationship_20250417.json').read())
num = len(data)


def to_4_digits(num: int):
    num = str(num)
    return '0' * (4 - len(num)) + num


def process_question(question: str):
    history, answer = chat_one_round([], question)
    return {'chat_history': history, 'final_answer': answer}


def safe_process_question(question):
    index, question = question
    name = f'{RESULT_DIR}/{to_4_digits(index)}.json'
    try:
        f = open(name)
        result = json.loads(f.read())
        f.close()
        return result
    except:
        pass
    l = []
    start_new_thread(lambda: l.append(process_question(question)), ())
    for i in range(900):
        time.sleep(0.1)
        if len(l) > 0:
            f = open(name, 'w')
            f.write(json.dumps(l[0], indent=2, ensure_ascii=False))
            f.close()
            return l[0]
    assert False


def search_test(data):
    all_question = [data[i]['json']['question'] for i in range(num)]
    results = map_infinite_retry(safe_process_question, all_question, max_workers=5, print_progress=True)
    results = [{'input': data[i], 'output': results[i]} for i in range(num)]
    return results

def search_test_2(data):
    all_question = [(i, data[i]["less_relationship"]) for i in range(num)]
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

def get_found_num_2(path: str):
    data = json.loads(open(path).read())
    num = 0
    for item in data:
        pmid = item['input']['pmid']
        history = item['output']['chat_history']
        output = "\n\n".join([message['content'] for message in history])
        if (pmid in output):
            num += 1
    return num


def pick_findable(input_path: str, output_path: str):
    data = json.loads(open(input_path).read())
    results = []
    for item in data:
        pmid = item['input']['pmid']
        history = item['output']['chat_history']
        output = "\n\n".join([message['content'] for message in history])
        if (pmid in output):
            results.append(item)
    open(output_path, 'w').write(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    # name = './final_2000_grok_thinking_less_relationship_20250417_results_20250417.json'
    # result = search_test_2(data)
    # open(name, 'w').write(json.dumps(result, indent=2, ensure_ascii=False))
    
    # print(get_found_num_2(name))
    
    pick_findable('./final_2000_grok_thinking_less_relationship_20250417_results_20250417.json', './final_2000_grok_thinking_less_relationship_20250417_results_20250417_findable.json')
    
    pass