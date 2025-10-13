#!/usr/bin/env python3
import json
import uuid
import sys

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from .text2cypher_utils import get_env_variable
from .schema_loader import get_schema, get_schema_hints, get_simplified_schema


load_dotenv()

# Single shared history store for all providers
_SHARED_HISTORY = ChatMessageHistory()

# SYSTEM_RULES = (
#     "You are a Cypher-generating assistant. Follow these rules:\n"
#     "1. Use *only* the node labels, relationship types and property names that appear in the JSON schema.\n"
#     "2. If the user is revising a previous Cypher draft, update that draft; otherwise, generate a fresh query.\n"
#     "3. Respond with **Cypher only** – no commentary or explanation.\n"
#     "4. Return the minimal Cypher query that directly satisfies the request. Do not add relationships or extra OPTIONAL MATCHes unless explicitly asked for.\n"
#     "5. When the user mentions a label/relationship/property absent from the schema, first map it to the closest existing element (exact synonym, substring, or highest-similarity fuzzy match). Ask for clarification only if multiple matches are equally plausible, offering up to three suggestions.\n"
#     "6. Your cypher query must return a graph as node- and edge- lists, such as with the example below"
#     """
#     MATCH(n1)-[r1]->(n2)  #any query you want, n1… n99, r1…r99
#     WITH   collect(DISTINCT n1)+ collect(DISTINCT n2)AS nodes,
#     collect(DISTINCT r1)AS edges
#     RETURN nodes, edges;
#     """

# )
SYSTEM_RULES = (
# SYSTEM_RULES = (
    """
You are a Cypher-generating assistant for a biomedical knowledge graph. Follow these rules strictly:

**Core Rules:**
1. Use ONLY the node labels, relationship types, and property names from the provided JSON schema.
2. If the user is revising a previous Cypher query, update that draft; otherwise, generate a fresh query.
3. Respond with **Cypher only** – no commentary, explanation, or markdown formatting.
4. Return the minimal Cypher query that directly satisfies the request. Do not add relationships or OPTIONAL MATCHes unless explicitly asked.
5. When the user mentions a label/relationship/property absent from the schema, map it to the closest existing element (exact synonym, substring, or fuzzy match). Ask for clarification only if multiple matches are equally plausible, offering 2-3 suggestions.

**MANDATORY OUTPUT FORMAT:**
6. EVERY query must return results as node and edge lists using this exact pattern:
   - For queries WITH relationships:
     MATCH (n1)-[r1]->(n2)
     WHERE ...  // your filters here
     WITH collect(DISTINCT n1) + collect(DISTINCT n2) AS nodes,
          collect(DISTINCT r1) AS edges
     RETURN nodes, edges;
   
   - For queries WITHOUT relationships (node-only):
     MATCH (n1:Label)
     WHERE ...  // your filters here
     WITH collect(DISTINCT n1) AS nodes,
          [] AS edges
     RETURN nodes, edges;

**Few-Shot Examples:**

Example 1 - Basic relationship query:
User: "Show genes that regulate other genes"
MATCH (g1:gene)-[r:regulation]->(g2:gene)
WITH collect(DISTINCT g1) + collect(DISTINCT g2) AS nodes,
     collect(DISTINCT r) AS edges
RETURN nodes, edges;

Example 2 - Filtered relationship query:
User: "Find upregulated genes in beta cells with log2 fold change > 2"
MATCH (g:gene)-[r:Differential_Expression]->(ct:cell_type)
WHERE ct.name = 'beta cell' AND r.UpOrDownRegulation = 'up' AND r.Log2FoldChange > 2
WITH collect(DISTINCT g) + collect(DISTINCT ct) AS nodes,
     collect(DISTINCT r) AS edges
RETURN nodes, edges;

Example 3 - Multi-hop query:
User: "Show SNPs, the genes they affect, and cell types where those genes are expressed"
MATCH (s:snp)-[r1:fine_mapped_eQTL]->(g:gene)-[r2:expression_level]->(ct:cell_type)
WITH collect(DISTINCT s) + collect(DISTINCT g) + collect(DISTINCT ct) AS nodes,
     collect(DISTINCT r1) + collect(DISTINCT r2) AS edges
RETURN nodes, edges;

Example 4 - Node-only query:
User: "Find the CFTR gene"
MATCH (g:gene {{name: "CFTR"}})
WITH collect(DISTINCT g) AS nodes,
     [] AS edges
RETURN nodes, edges;

Example 5 - Node-only with filter:
User: "Get all genes on chromosome 6"
MATCH (g:gene)
WHERE g.chr = 'chr6'
WITH collect(DISTINCT g) AS nodes,
     [] AS edges
RETURN nodes, edges;

Example 6 - Multiple match clauses:
User: "Find genes that regulate other genes and are differentially expressed"
MATCH (g1:gene)-[r1:regulation]->(g2:gene)
MATCH (g1)-[r2:Differential_Expression]->(ct:cell_type)
WITH collect(DISTINCT g1) + collect(DISTINCT g2) + collect(DISTINCT ct) AS nodes,
     collect(DISTINCT r1) + collect(DISTINCT r2) AS edges
RETURN nodes, edges;

Example 7 - Complex filtering:
User: "SNPs linked to genes that are effector genes for diabetes"
MATCH (s:snp)-[r1:fine_mapped_eQTL]->(g:gene)-[r2:effector_gene]->(o:ontology)
WHERE o.name CONTAINS 'diabetes'
WITH collect(DISTINCT s) + collect(DISTINCT g) + collect(DISTINCT o) AS nodes,
     collect(DISTINCT r1) + collect(DISTINCT r2) AS edges
RETURN nodes, edges;

**Critical Reminders:**
- ALL node variables from MATCH clauses must be in the nodes collection (use + to concatenate)
- ALL relationship variables from MATCH clauses must be in the edges collection
- ALWAYS use DISTINCT in collect() statements
- Apply WHERE filters BEFORE the WITH clause
- The final RETURN must be exactly: RETURN nodes, edges;
- For node-only queries, use [] AS edges (empty list)
- Never return anything other than nodes and edges
"""
)


def make_llm(provider: str = "openai"):
    """Return a Chat instance for the specified provider."""
    if provider == "openai":
        return ChatOpenAI(
            base_url=get_env_variable("OPENAI_API_BASE_URL"),
            api_key=get_env_variable("OPENAI_API_KEY"),
            model=get_env_variable("OPENAI_API_MODEL"),
            temperature=get_env_variable("OPENAI_API_TEMP")
        )
    elif provider == "google":
        return ChatGoogleGenerativeAI(
            model=get_env_variable("GOOGLE_MODEL"),
            google_api_key=get_env_variable("GOOGLE_API_KEY"),
            temperature=0
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")

class Text2CypherAgent:
    """Single‑LLM agent that remembers conversation context + schema."""

    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self.schema_json = get_simplified_schema()
        self.schema_str = json.dumps(self.schema_json, indent=2)
        self.hints = get_schema_hints()
        
        # Build system prompt with schema and optional hints
        whole_schema = self.schema_str.replace('{', '{{').replace('}', '}}')
        system_prompt = SYSTEM_RULES + "\n### Schema\n" + whole_schema
        
        if self.hints:
            hints_str = json.dumps(self.hints, indent=2).replace('{', '{{').replace('}', '}}')
            system_prompt += "\n\n### Schema Hints\n" + hints_str

        self.llm = make_llm(provider)
        self.session_id = "shared"  # All agents use same session for shared history

        # build prompt template with history placeholder
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{user_input}")
        ])

        chain_core = self.prompt | self.llm

        def get_history(session_id: str):
            return _SHARED_HISTORY

        self.chain = RunnableWithMessageHistory(
            chain_core,
            get_history,
            input_messages_key="user_input",
            history_messages_key="history",
        )

    # def respond(self, user_text: str) -> str:
    #     result = self.chain.invoke(
    #         {"user_input": user_text},
    #         config={"configurable": {"session_id": self.session_id}}
    #     )
    #     return result.content.strip().strip("` ")
    def respond(self, user_text: str) -> str:
        result = self.chain.invoke(
            {
                "user_input": user_text,
                "name": "PankBaseAgent"  # or whatever name your template expects
            },
            config={"configurable": {"session_id": self.session_id}}
        )
        return result.content.strip().strip("` ")

    def get_history(self) -> list[dict[str, str]]:
        """Return chat history as list of {role, content} dicts."""
        messages = []
        for m in _SHARED_HISTORY.messages:
            role = "assistant" if getattr(m, "type", "") == "ai" else "user"
            messages.append({"role": role, "content": m.content})
        return messages

    def clear_history(self) -> None:
        """Clear the shared history."""
        global _SHARED_HISTORY
        _SHARED_HISTORY = ChatMessageHistory()

if __name__ == "__main__":
    try:
        agent = Text2CypherAgent()
    except EnvironmentError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        while True:
            txt = input("You> ").strip()
            if not txt:
                continue
            print(agent.respond(txt) + "\n")
    except (KeyboardInterrupt, EOFError):
        print()