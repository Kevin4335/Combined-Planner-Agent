import json
import traceback
from typing import Tuple
from _thread import start_new_thread
from queue import Queue
import time
from random import randint
import sys
import requests
from langchain_community.vectorstores import Neo4jVector
from langchain_huggingface import HuggingFaceEmbeddings
from neo4j import GraphDatabase
import os 

embedding_function = HuggingFaceEmbeddings(
    model_name='Alibaba-NLP/gte-large-en-v1.5',
    model_kwargs={'trust_remote_code': True,
                  'device':'cpu'}
)  # device_map="auto"


def process_document(content: str, metadata: dict = None) -> dict:
    result = {
        'abstract': None,
        'title': None,
        'pubmedid': None,
        'score': metadata.get('score', 0) if metadata else 0
    }
    lines = content.split('\n')
    for line in lines:
        if line.startswith('abstract: '):
            result['abstract'] = line.replace('abstract: ', '', 1)
        elif line.startswith('title: '):
            result['title'] = line.replace('title: ', '', 1)
        elif line.startswith('pubmedid: '):
            result['pubmedid'] = line.replace('pubmedid: ', '', 1)
            
    return result


def semantic_search(query: str, limit: int = 10) -> list:
    results = abstract_store.similarity_search(query, k=limit)
    results = [process_document(result.page_content, result.metadata) for result in results]
    return results


def run_cypher_2(command: str, parameters = None, timeout: int = 60):
    config = {"timeout": timeout}
    return driver_2.execute_query(command, parameters, **config)



__all__ = ['run_functions']


def run_functions(functions: list[dict]) -> str:
    q = Queue()
    results = []
    num = len(functions)
    for i in range(0, len(functions)):
        name = functions[i]['name']
        input = functions[i]['input']
        func = eval(name)
        start_new_thread(lambda _func, _input, _index: q.put(_func(_input, _index + 1)), (func, input, i))
    while (q.qsize() < num):
        time.sleep(0.2)
    while (q.qsize() > 0):
        results.append(q.get())
    results.sort(key=lambda x: int(x.split('.')[0]))
    result = ''.join(results)
    return result    

def pankbase_api_query(input: str, index: int) -> str:
    '''
    Output the messages needed to return to claude, including function name and
    input, and status, and error (if any). Will handle error and timeout, promise
    to return in 60 seconds.
    '''
    q = Queue()
    start_new_thread(_pankbase_api_query, (input, q))
    start = time.time()
    while (time.time() - start < 60):
        time.sleep(0.2)
        if (q.qsize() == 1):
            break
    size = q.qsize()
    result = f'{index}. PankbaseAPI query: {str([input])[1:-1]}\n'
    if (size == 0):
        result += f'Status: timeout\n'
        result += f'Error: Cannot get the result from PankbaseAPI in 60 seconds\n\n'
        return result
    success, res = q.get(block=False)
    if (success == False):
        result += f'Status: error\n'
        result += f'Error: {str([res])[1:-1]}\n\n'
        return result
    result += f'Status: success\n'
    res = res[:15000]  # Limit response size
    result += f'Result: {res}\n\n'
    return result

def clean_cypher_for_json(cypher: str) -> str:
    """
    Clean Cypher query for JSON submission to Pankbase API.
    """
    
    cleaned = ' '.join(cypher.split())
    cleaned = cleaned.replace('"', '\"').replace("'", '\"')
    return cleaned

def _pankbase_api_query(input: str, q: Queue) -> None:
    try:
        
        os.environ['NEO4J_SCHEMA_PATH'] = 'text_to_cypher/data/input/neo4j_schema.json'
        sys.path.append('text_to_cypher/src')
        
        from .text_to_cypher.src.text2cypher_agent import Text2CypherAgent

        agent = Text2CypherAgent()

        cypher_result = agent.respond(input)
        
        cleaned_cypher = clean_cypher_for_json(cypher_result)

        print(f"DEBUG: Sending Cypher query: {cleaned_cypher}")
        
        response = requests.post(
            'HTTPS://vcr7lwcrnh.execute-api.us-east-1.amazonaws.com/development/api',
            headers={'Content-Type': 'application/json'},
            json={'query': cleaned_cypher},
            timeout=60
        )
        
        # print(f"DEBUG: Response status code: {response.status_code}")
        # print(f"DEBUG: Response headers: {response.headers}")
        print(f"DEBUG: Response text: {response.text}")
        
        response.raise_for_status()
        
        if not response.text.strip():
            q.put((False, "Empty response from Pankbase API"))
            return
        
        # Check if response starts with "Error:" (API error format)
        if response.text.strip().startswith("Error:"):
            q.put((False, f"Pankbase API Error: {response.text}"))
            return
            
        try:
            result = response.json()
            combined = {
                "cypher_query": cleaned_cypher,
                "api_result": result
            }
            q.put((True, json.dumps(combined, ensure_ascii=False)))
        except json.JSONDecodeError as e:
            q.put((False, f"Invalid JSON response from API: {response.text}"))
    except Exception as e:
        err_msg = traceback.format_exc()
        print(err_msg, file=sys.stderr)
        if (len(err_msg) > 2000):
            first = err_msg[:1000]
            second = err_msg[-1000:]
            err_msg = first + ' ...  ' + second
        q.put((False, err_msg))

def test_a():
    a = 0
    b = 1
    c = b / a


def test_b():
    x = 4
    test_a()
    y = 5


def test_c():
    v = 8
    try:
        test_b()
    except:
        error_msg = traceback.format_exc()
        print(error_msg)
        print(len(error_msg))
    u = 10


if __name__ == "__main__":
    # Test Pankbase API functionality
    result = pankbase_api_query("Get detailed information for gene CFTR", 1)
    print(result)
