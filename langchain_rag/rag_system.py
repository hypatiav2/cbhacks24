# langchain_rag/rag_system.py
from langchain.prompts import PromptTemplate
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks import (CallbackManagerForLLMRun,)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.messages import (AIMessage, BaseMessage)
from dotenv import load_dotenv
import requests
import os
import json

# Load environment variables
load_dotenv()
KINDO_API_KEY = os.getenv('KINDO_API_KEY')
HUGGING_FACE_API_KEY = os.getenv('HUGGING_FACE_API_KEY')

KINDO_API_BASE = "https://llm.kindo.ai/v1/chat/completions"
headers = {
    "api-key": KINDO_API_KEY,
    "content-type": "application/json",
}

role_map = {
    "human": "user",
    "ai": "assistant",
}

# Function to read a file
def read_prompt_file(filename):
    with open(filename, 'r') as file:
        return file.read()

class KindoAI(BaseChatModel):
    model_name: str

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] = None,
        **kwargs,
    ) -> ChatResult:
        api_messages = [{"role": role_map[m.type], "content": m.content} for m in messages]
        data = {"model": self.model_name, "messages": api_messages}

        response = requests.post(KINDO_API_BASE, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            message = AIMessage(content=content)
            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])
        else:
            raise ValueError(f"API request failed with status code {response.status_code}")
    
    @property
    def _llm_type(self) -> str:
        """Get the type of language model used by this chat model."""
        return self.model_name

# Function to generate RAG-based moderation responses
def moderate_conversation(conversation_text):
    print("conversation text is " + conversation_text)
    # Define prompt template for moderation
    # prompt_template = (
    #     "The following is a conversation context. Analyze the conversation transcript for grooming or manipulation "
    #     "behavior. Identify the potential predator and victim if any concerning behavior is present. Additionally, "
    #     "provide red flags in the conversation. Conversation: '{message`}'"
    # )
    
    # data = {
    #     "model": "groq/llama3-70b-8192",
    #     "messages": [{"role": "user", "content": prompt_template.format(message=conversation_text)}]
    # }
    
    # # Make the API call to the Kindo AI model
    # response = requests.post(KINDO_API_BASE, headers=headers, data=json.dumps(data))
    
    # if response.status_code == 200:
    #     return response.json().get("choices", [{}])[0].get("message", {}).get("content", "No response from the model.")
    # else:
    #     raise ValueError(f"API request failed with status code {response.status_code}")

    llm = KindoAI(model_name="groq/llama3-70b-8192")

    prompt_from_file = read_prompt_file('./prompt.txt')
    prompt = PromptTemplate(
        input_variables=["message"],
        template=prompt_from_file + "'{message}'"
    )

    context = ""
    message = conversation_text

    conversation_chain = prompt | llm 

    response = conversation_chain.invoke({"message": message})
    print(response.content)
    return response.content