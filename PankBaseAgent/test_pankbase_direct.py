# test_pankbase_direct.py
from .utils import pankbase_api_query, clean_cypher_for_json

if __name__ == "__main__":
    # Natural-language input; function will generate Cypher internally
    res = pankbase_api_query("Get detailed information for gene CFTR", 1)
    print(res)
    
    # import sys
    # import os 
    # os.environ['NEO4J_SCHEMA_PATH'] = 'text-to-cypher/data/input/neo4j_schema.json'
    # sys.path.append('text-to-cypher/src')

    # from text2cypher_agent import Text2CypherAgent

    # # Create agent instance
    # agent = Text2CypherAgent()

    # # Query it directly
    # cypher_result = agent.respond("Find information about the CFTR gene")
    # print(clean_cypher_for_json(cypher_result))