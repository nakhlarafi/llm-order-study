import asyncio
import sys
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import tiktoken
import re
import os
import logging
from langchain_openai.chat_models.base import BaseChatOpenAI

# Setup logging to a file
logging.basicConfig(filename='error_log.txt', level=logging.ERROR, format='%(asctime)s %(message)s')

# Class for model handling
class ModelHandler:
    def __init__(self, model_name="gpt-4o-mini", temperature=0, encoding_name="cl100k_base"):
        self.model = ChatOpenAI(model=model_name, temperature=temperature)
        self.encoding_name = encoding_name

    def get_model(self):
        return self.model
    # Function to calculate the number of tokens in the string
    def num_tokens_from_string(self, string: str) -> int:
        encoding = tiktoken.get_encoding(self.encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens


# Class for prompt templates
class TemplateHandler:
    def __init__(self):
        self.system_template = "You will be given a failing test with stack trace and its covered methods. You have to rank the methods from most suspicious to least suspicious by analyzing these information. You should rank top 10 most suspicious methods. The output must be in the following JSON format:\n{json_output_format}"
        self.user_template = "Here are the coverage information: {coverage_info}"
        self.output_format = """
        ```json
        [
            {
                "method_id": int,
                "rank": int
            }
        ]
        ```
        """
        self.prompt_template = ChatPromptTemplate.from_messages(
            [("system", self.system_template), ("user", self.user_template)]
        )

    def get_prompt_template(self):
        return self.prompt_template

    def get_output_format(self):
        return self.output_format


# Class for parsing the model's output
class OutputParser:
    def __init__(self):
        self.parser = StrOutputParser()

    def get_parser(self):
        return self.parser
    def parse_and_save_final_json(self, contents, project_name, bug_id, test_id, path):
        json_objects = []
        # Updated regex to match JSON objects or arrays enclosed in triple backticks
        json_block_pattern = re.compile(r'```json\n\{[\s\S]*?\}\n```|```json\n\[[\s\S]*?\]\n```', re.MULTILINE)

        code_blocks = json_block_pattern.findall(contents)
        for block in code_blocks:
            try:
                # Clean up the block to remove markdown code block syntax
                clean_block = block.replace('```json\n', '').replace('\n```', '').strip()
                # Normalize JSON structure (ensure proper JSON formatting)
                clean_block = re.sub(r'^\{\n\s*\{', '{', clean_block)
                clean_block = re.sub(r'\}\n\s*\}$', '}', clean_block)
                clean_block = re.sub(r'([\{\s,])(\w+)(:)', r'\1"\2"\3', clean_block)
                # Parse the JSON data
                json_obj = json.loads(clean_block)
                if isinstance(json_obj, dict):
                    json_objects.append(json_obj)  # Append single object
                elif isinstance(json_obj, list):
                    json_objects.extend(json_obj)  # Extend list of objects
            except json.JSONDecodeError as e:
                print("JSON decode error:", e, "in block:", block)
                continue

        # Final JSON structure
        final_json = {
            "project_name": project_name,
            "bug_id": bug_id,
            "test_id": test_id,
            "ans": json_objects,
            "final_full_answer": contents
        }

        # File and directory handling
        file_path = path
        dir_path = os.path.dirname(file_path)
        os.makedirs(dir_path, exist_ok=True)

        # Write JSON data to file
        with open(file_path, "w") as json_file:
            json.dump(final_json, json_file, indent=4)
        
        print(f"Data saved to {file_path}")
        return file_path


# Function to extract relevant information from bug data
def extract_info(bug_data):
    text_content = ''
    text_content += f"Test Name: {bug_data['test_name']}\n"
    text_content += f"Test Body:\n{bug_data['test_body']}\n"
    text_content += f"\nStackTrace:\n{bug_data['stack_trace']}\n"
    text_content += "\nCovered Methods:\n"

    for method in bug_data['covered_methods']:
        text_content += f"    Method Signature:\n{method['method_signature']}\n"
        text_content += f"    Method Body:\n{method['method_body']}\n"
        text_content += f"    Method ID:\n{method['method_id']}\n"

    text_content += "\n"
    return text_content

def count_files_in_directory(directory_path):
    file_count = 0
    for root, dirs, files in os.walk(directory_path):
        file_count += len(files)
    return file_count


# Async function for the main logic
async def main():
    # Get command-line arguments
    project_name = sys.argv[1]
    bug_id = sys.argv[2]
    tech = sys.argv[3]

    # Initialize handlers
    model_handler = ModelHandler()
    template_handler = TemplateHandler()
    parser_handler = OutputParser()

    # Get model, template, and parser
    model = model_handler.get_model()
    prompt_template = template_handler.get_prompt_template()
    output_format = template_handler.get_output_format()
    parser = parser_handler.get_parser()

    folder_path = f'../data/KendallTau_Py/{project_name}/{tech}/{bug_id}'
    number_of_test_files = count_files_in_directory(folder_path)
    print(f"Number of test files: {number_of_test_files}")
    for test_id in range(number_of_test_files):
        try:
            # Read the JSON file
            with open(f'{folder_path}/test_{test_id}.json', 'r') as file:
                coverage_data_json = json.load(file)

            # Extract the information into a string
            coverage_data_txt = extract_info(coverage_data_json)
            final_prompt = prompt_template.invoke({"coverage_info": coverage_data_txt, "json_output_format": output_format})
            # print(final_prompt.to_string())
            # exit()
            num_tokens = model_handler.num_tokens_from_string(final_prompt.to_string())
            print(f"Number of tokens: {num_tokens}")

            if num_tokens > 111600:  # Assuming 111616 is the max input token size for your model
                raise ValueError(f"Input token size exceeded for {project_name}, {bug_id}, test_{test_id}")

            # Create the chain
            chain = prompt_template | model | parser

            # print(chain)
            # exit()
            full_output = ""
            # Use async for loop to stream output
            async for chunk in chain.astream({"coverage_info": coverage_data_txt, "json_output_format": output_format}):
                full_output += chunk
                print(chunk, end="", flush=True)
            output_path = f'../data/Output/KendallTau_Py_DeepSeek/{project_name}/{tech}/{bug_id}/test_{test_id}.json'
            parser_handler.parse_and_save_final_json(full_output, project_name, bug_id, test_id, output_path)
        except Exception as e:
            # Log the error with details of the project, bug, and test ID
            error_message = f"Error for project: {project_name}, bug_id: {bug_id}, test_id: {test_id} - {str(e)}"
            logging.error(error_message)
            print(error_message)



# Run the main async function
if __name__ == "__main__":
    asyncio.run(main())
