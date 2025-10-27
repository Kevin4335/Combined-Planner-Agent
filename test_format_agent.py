#!/usr/bin/env python3
"""
Test script for the FormatAgent integration
"""

import sys
import os
sys.path.append('/home/kevin4335/research/PlannerAgent')

from ai_assistant import chat_one_round
from utils import reset_cypher_queries, get_all_cypher_queries, add_cypher_query

def test_format_agent_integration():
    """Test the FormatAgent integration"""
    print("Testing FormatAgent integration...")
    
    # Reset cypher queries
    reset_cypher_queries()
    
    # Simulate adding some cypher queries
    test_queries = [
        'MATCH (g:gene {name: "CFTR"}) RETURN g',
        'MATCH (g:gene)-[r]->(d:disease) WHERE d.name = "diabetes" RETURN g, d',
        'MATCH (g:gene) RETURN g LIMIT 10'
    ]
    
    for query in test_queries:
        add_cypher_query(query)
    
    print(f"Added {len(get_all_cypher_queries())} cypher queries")
    print("Cypher queries:", get_all_cypher_queries())
    
    # Test a simple question
    try:
        messages, response = chat_one_round([], "What genes are associated with diabetes?")
        print("\nResponse received:")
        print(response)
        print("\nTest completed successfully!")
        return True
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_format_agent_integration()
    if success:
        print("✅ FormatAgent integration test passed!")
    else:
        print("❌ FormatAgent integration test failed!")
