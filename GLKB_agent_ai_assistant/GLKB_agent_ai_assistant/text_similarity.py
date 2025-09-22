import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
from bert_score import score
import logging
logging.getLogger("transformers").setLevel(logging.ERROR)
import torch
from bleurt_pytorch import BleurtConfig, BleurtForSequenceClassification, BleurtTokenizer
import json
# from moverscore_v2 import get_idf_dict, word_mover_score

torch.set_default_device('cpu')

GROUND_TRUTH_PATH = '/Users/jtc/Desktop/文件/UMich/WI2025/bio-lab/glkb_dataset/final_2000_grok_thinking_less_relationship_20250417_with_answer_20250421.json'
INPUT_PATH = 'final_2000_grok_thinking_less_relationship_20250417_glkb_gpt_20250421.json'
INPUT_PATH_2 = 'final_2000_grok_thinking_less_relationship_20250417_gpt_direct_20250421_4.json'

SYMBOLS = '.!?,;:'


def bleu(text1: str, text2: str) -> float:
    text1 = text1.lower()
    text2 = text2.lower()
    for symbol in SYMBOLS:
        text1 = text1.replace(symbol, '')
        text2 = text2.replace(symbol, '')
    text1_tokens = text1.split(' ')
    text2_tokens = text2.split(' ')
    # print(text1_tokens)
    # print(text2_tokens)
    return sentence_bleu([text1_tokens], text2_tokens, smoothing_function=SmoothingFunction().method1)


def rouge(text1: str, text2: str) -> float:
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = scorer.score(text1, text2)
    return scores["rougeL"].fmeasure


def bert_score(text1: str, text2: str) -> float:
    s = score([text1], [text2], lang='en', model_type='roberta-large', num_layers=17, verbose=False, device='mps')[2].item()
    return (s - 0.8) * 5


config = BleurtConfig.from_pretrained('lucadiliello/BLEURT-20-D12')
model = BleurtForSequenceClassification.from_pretrained('lucadiliello/BLEURT-20-D12')
tokenizer = BleurtTokenizer.from_pretrained('lucadiliello/BLEURT-20-D12')
model.eval()


def bleurt(text1: str, text2: str) -> float:
    with torch.no_grad():
        inputs = tokenizer([text1], [text2], padding='longest', return_tensors='pt')
        res = model(**inputs).logits.flatten().tolist()
        return res[0]


def compare_glkb_gpt_results(abstract_to_ground_truth, results, func: callable):
    total = 0.0
    for item in results:
        answer = item["glkb_gpt"]["final_answer"]
        truth = abstract_to_ground_truth[item["input"]['abs']]
        total += func(answer, truth)
    return total / len(results)

def compare_gpt_direct_results(abstract_to_ground_truth, results, func: callable):
    total = 0.0
    for item in results:
        answer = item["gpt_direct"]
        truth = abstract_to_ground_truth[item["input"]['abs']]
        total += func(answer, truth)
    return total / len(results)


if __name__ == '__main__':
    ground_truth_data = json.loads(open(GROUND_TRUTH_PATH).read())
    abstract_to_ground_truth = {}
    for item in ground_truth_data:
        abs = item['abs']
        gt = item['answer']
        abstract_to_ground_truth[abs] = gt
    input_data = json.loads(open(INPUT_PATH).read())
    input_data_2 = json.loads(open(INPUT_PATH_2).read())
    gpt_direct_bleu = compare_gpt_direct_results(abstract_to_ground_truth, input_data_2, bleu)
    gpt_direct_rouge = compare_gpt_direct_results(abstract_to_ground_truth, input_data_2, rouge)
    glkb_gpt_bleu = compare_glkb_gpt_results(abstract_to_ground_truth, input_data, bleu)
    glkb_gpt_rouge = compare_glkb_gpt_results(abstract_to_ground_truth, input_data, rouge)
    print(f"GPT Direct BLEU: {gpt_direct_bleu}")
    print(f"GPT Direct ROUGE: {gpt_direct_rouge}")
    print(f"GLKB GPT BLEU: {glkb_gpt_bleu}")
    print(f"GLKB GPT ROUGE: {glkb_gpt_rouge}")