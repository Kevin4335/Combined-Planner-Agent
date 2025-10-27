# FormatAgent

The FormatAgent is an intelligent cypher query formatter and relevance analyzer that automatically processes all cypher queries generated during a human query session.

## Purpose

The FormatAgent analyzes the relevance of each cypher query to the original human question and orders them by relevance, providing additional insights about the query processing.

## How It Works

1. **Automatic Integration**: The FormatAgent is automatically called after all other agents (PankBaseAgent, GLKB_agent, TemplateToolAgent) complete their work.

2. **Cypher Query Analysis**: It receives:
   - The original human query
   - All cypher queries generated during the session
   - The final answer provided to the user

3. **Relevance Assessment**: It analyzes each cypher query based on:
   - Direct relevance to the human question
   - Data completeness for the answer
   - Logical flow in the reasoning process
   - Redundancy and unique value
   - Context matching

4. **Ordered Output**: Returns the cypher queries ordered from most relevant to least relevant.

## Architecture

The FormatAgent follows the same design patterns as other agents in the system:

- `ai_assistant.py`: Main agent logic
- `claude.py`: LLM integration and JSON formatting
- `utils.py`: Utility functions
- `prompts/`: Prompt templates
- `logs/`: Logging directory

## Integration

The FormatAgent is integrated into the main system through:

1. **Global Cypher Storage**: All cypher queries are stored in a global list (`current_cypher_queries`) during each human query session.

2. **Automatic Processing**: When the main PlannerAgent returns a response to the user, the FormatAgent is automatically called to process the collected cypher queries.

3. **Enhanced Output**: The FormatAgent's analysis is appended to the final response, providing additional context about the query processing.

## Files Modified

- `utils.py`: Added cypher query storage and FormatAgent function calls
- `ai_assistant.py`: Integrated FormatAgent into the main workflow
- `prompts/general_prompt.txt`: Updated to include FormatAgent information

## Usage

The FormatAgent works automatically - no manual intervention is required. It will process cypher queries whenever the main system processes a human query that generates cypher queries.
