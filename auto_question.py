#!/usr/bin/env python3
"""
Script that automatically asks a question and returns the answer.
"""
import sys
import logging
from docs_llm_scraper.agent import LlamaAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """
    Ask a predefined question to the documentation assistant.
    """
    print("Initializing the documentation assistant...")
    
    try:
        # Initialize agent with a model we know is available
        agent = LlamaAgent(
            docs_pkg_path="./docs-llm-pkg",
            model_id="accounts/fireworks/models/llama4-scout-instruct-basic",
            provider_id="fireworks",
            verbose=True
        )
        
        print("Ingesting documentation chunks...")
        agent.ingest_chunks()
        
        print("Creating agent and session...")
        llm_agent = agent.create_agent()
        session_id = agent.create_session(llm_agent)
        
        print(f"\n🤖 Welcome to the {agent.site_name} Documentation Assistant!")
        
        # Ask a predefined question
        question = "What vector database providers are supported by Llama Stack?"
        print(f"\nQuestion: {question}")
        print("Generating answer...")
        
        # Get response
        response = agent.chat(llm_agent, session_id, question)
        
        # Display response
        print(f"\nAnswer: {response}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())