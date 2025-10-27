from .claude import *
from .utils import *
from typing import Tuple
from copy import deepcopy
import json


MAX_ITER = 1
PRINT_FUNC_CALL = True
PRINT_FUNC_RESULT = True
set_log_enable(True)


def chat_one_round_format(messages_history: list[dict], question: str) -> Tuple[list[dict], str]:
    '''
    return (messages_history, response)
    FormatAgent processes cypher queries and returns formatted output
    '''
    question = question.strip()
    if (question == ''):
        question = '<empty>'
    question = '====== From User ======\n' + question
    messages = deepcopy(messages_history)
    messages.append({"role": "user", "content": question})
    function_call_num = 0
    while True:
        messages, response = chat_and_get_formatted(messages)
        if (response['to'] == 'user'):
            return (messages, response['text'])
        if (function_call_num == MAX_ITER):
            assert (False)  # Currently not handle this error
        function_call_num += 1
        if (PRINT_FUNC_CALL):
            print('\033[92m', end='')
            print('\nCalling Functions: \n')
            print(json.dumps(response, indent=2, ensure_ascii=False))
            print()
            print('\033[0m', end='')
        print("??????????????????????????????????????????????????")
        functions_result = run_functions(response['functions'])
        if (PRINT_FUNC_RESULT):
            print('\033[93m', end='')
            print('\nFunction results: \n')
            print(functions_result)
            print('\033[0m', end='')
        new_message = '====== From System ======\nThe results of function callings:\n' + functions_result + '\n'
        if (function_call_num == MAX_ITER):
            new_message += 'You already called functions 5 continuous times. Next message you must return to user.'
        else:
            func_num = MAX_ITER - function_call_num
            new_message += f'You can call functions {func_num} more times, after this you need to return to user.'
        messages.append({"role": "user", "content": new_message})


def chat_forever():
    messages = []
    while True:
        question = input('Your question: ')
        messages, response = chat_one_round_format(messages, question)
        print(f'\nResponse:\n\n{response}\n')


if __name__ == "__main__":
    chat_forever()
