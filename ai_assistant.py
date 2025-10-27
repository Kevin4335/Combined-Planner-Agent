from claude import *
from utils import *
from typing import Tuple
from copy import deepcopy
import json


MAX_ITER = 5
PRINT_FUNC_CALL = True
PRINT_FUNC_RESULT = True
set_log_enable(True)


# pseudo code:

# MAX_ITER = 5
# messages = []
# model = <the_ai_assistant>  # This is you
#
# def user_input(question: str) -> str:
#     function_call_num = 0
#     messages.append({"role": "user", "content": question})
#     while True:
#         output = model.get_response(messages)
#         if (output.is_to_user):
#             messages.append({"role": "assistant", "content": output})
#             return output.text
#         else:
#             # to system
#             if (function_call_num == MAX_ITER):
#                 assert (False)  # This should not happen, because you should not do function callings when it reaches MAX_ITER
#             function_call_num += 1
#             messages.append({"role": "assistant", "content": output})
#             functions_list = output.functions
#             function_results = run_functions(functions_list)
#             messages.append({"role": "user", "content": function_results})


def chat_one_round(messages_history: list[dict], question: str) -> Tuple[list[dict], str]:
    '''
    return (messages_history, response)
    '''
    # Reset cypher queries for new human query
    reset_cypher_queries()
    
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
            # Before returning to user, call FormatAgent to process cypher queries
            cypher_queries = get_all_cypher_queries()
            if cypher_queries:
                # Extract the original question from the first message
                original_question = question.replace('====== From User ======\n', '')
                format_input = f"Human Query: {original_question}\n\nCypher Queries: {json.dumps(cypher_queries)}\n\nFinal Answer: {json.dumps(response['text'])}"
                format_result = format_agent_chat_one_round(format_input, 1)
                
                # Replace the response text with FormatAgent's formatted output
                response['text'] = format_result
            return (messages, response['text'])
        if (function_call_num == MAX_ITER):
            assert (False)  # Currently not handle this error
        function_call_num += 1
        print(f"{function_call_num}#############################{function_call_num}")

        if (PRINT_FUNC_CALL):
            print('\033[92m', end='')
            print('\nCalling Functions: \n')
            print(json.dumps(response, indent=2, ensure_ascii=False))
            print()
            print('\033[0m', end='')
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
        messages, response = chat_one_round(messages, question)
        print(f'\nResponse:\n\n{response}\n')
        


if __name__ == "__main__":
    with open("log.txt", "w") as f:
        pass

    chat_forever()
