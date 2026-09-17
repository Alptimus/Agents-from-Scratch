"""Legacy manual Gemini demo; not part of the active orchestrator flow."""

import os
import numpy as np
from google import genai
from google.genai.types import GenerateContentConfig, EmbedContentConfig, HarmCategory, HarmBlockThreshold, SafetySetting
from decouple import config

def parse_model_name(model_name):
    return model_name.lower().replace(" ", "-").replace("_", "-")

def get_simple_client(api_key_name):
    api_key = config(api_key_name)
    return genai.Client(api_key=api_key)

def calculate_tokens(client, prompt, model_name="gemini-2.5-flash"):
    total_tokens = client.models.count_tokens(
        model=model_name, contents=prompt
    )
    return total_tokens.total_tokens

def generate_content(client, prompt, model_name="gemini-2.5-flash"):
    model_name = parse_model_name(model_name)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=GenerateContentConfig(
            safety_settings=[
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=HarmBlockThreshold.BLOCK_NONE
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=HarmBlockThreshold.BLOCK_NONE
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=HarmBlockThreshold.BLOCK_NONE
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=HarmBlockThreshold.BLOCK_NONE
                )
            ]
        )
    )
    return response

def generate_embeddings(client, list_of_texts, embedding_model="gemini-embedding-001", task_type="SEMANTIC_SIMILARITY"):
    """
    Available Task Types:
    - SEMANTIC_SIMILARITY: Optimized to assess text similarity.
    - RETRIEVAL_DOCUMENT: Optimized for document search.
    - RETRIEVAL_QUERY: Optimized for general search queries.
    - QUESTION_ANSWERING: For questions in a question-answering system, optimized for finding documents that answer the question.
    """
    response = client.models.embed_content(
        model=embedding_model,
        contents=list_of_texts if isinstance(list_of_texts, list) else [list_of_texts],
        config=EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=768
        )
    )
    return np.array([np.array(emb.values) for emb in response.embeddings])


if __name__ == '__main__':
    model_name = "Gemini 2.5 Flash-Lite"
    model_name = parse_model_name(model_name)
    
    prompt = "Hello, how are you today?"
    
    client = get_simple_client("GOOGLE_API_KEY")
    response = generate_content(client, prompt, model_name)

    print(response.text.strip())