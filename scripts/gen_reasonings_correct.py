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
        self.system_template = "You are given a ranked list of bug with test body, stack trace and covered methods that you ranked earlier. Here are the info\n{coverage_info}\n You should tell us why you ranked the methods in this order. We want to know why you think one methods is suspicious than the other. The output must be in the following JSON format:\n{json_output_format}"
        self.output_format = """
        ```json
        {
            "ranking": [
                {
                    "method_id": int,
                    "rank": int,
                    "reasoning": str
                }
            ],
            "description": "An overall reasoning for the ranking"
        }

        ```
        """
        self.prompt_template = ChatPromptTemplate.from_messages(
            [("system", self.system_template), ("user", "{coverage_info}")]
        )

    def get_prompt_template(self):
        return self.prompt_template

    def get_output_format(self):
        return self.output_format


class OutputParser:
    def __init__(self):
        self.parser = StrOutputParser()

    def get_parser(self):
        return self.parser

    def parse_and_save_final_json(self, contents, project_name, bug_id, test_id, path):
        json_ranking = []
        description = ""

        # Updated regex to match JSON objects or arrays enclosed in triple backticks
        json_block_pattern = re.compile(r'```json\n({[\s\S]*?})\n```|```json\n(\[[\s\S]*?\])\n```', re.MULTILINE)

        code_blocks = json_block_pattern.findall(contents)
        for block in code_blocks:
            json_block = block[0] if block[0] else block[1]  # Select the first group that matched

            try:
                # Clean up the block to remove markdown code block syntax
                clean_block = json_block.strip()

                # Handle Java code blocks within JSON strings
                clean_block = re.sub(r'```java\n([\s\S]*?)\n```', lambda m: repr(m.group(1)), clean_block)

                # Normalize JSON structure (ensure proper JSON formatting)
                clean_block = re.sub(r'([\{\s,])(\w+)(:)', r'\1"\2"\3', clean_block)

                # Parse the JSON data
                json_obj = json.loads(clean_block)
                if isinstance(json_obj, list):
                    json_ranking.extend(json_obj)  # Extend list of objects
                elif isinstance(json_obj, dict):
                    # Check if this dict contains the ranking array or description
                    if "ranking" in json_obj:
                        json_ranking.extend(json_obj.get("ranking", []))
                    if "description" in json_obj:
                        description = json_obj.get("description", "")
            except json.JSONDecodeError as e:
                print("JSON decode error:", e, "in block:", json_block)
                continue

        # Final JSON structure
        final_json = {
            "project_name": project_name,
            "bug_id": bug_id,
            "test_id": test_id,
            "ranking": json_ranking,
            "description": description,
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



def extract_method_ranked_bug_info(project_name, tech, bug_id, test_id, method_rankings):
    with open(f'../data/RankedData/{project_name}/{tech}/{bug_id}/test_{test_id}.json', 'r') as file:
        bug_data = json.load(file)
    
    # Sort the methods based on their rank (ascending order)
    sorted_methods = sorted(method_rankings.items(), key=lambda item: item[1])

    # Extract the method bodies and ranks
    method_bodies_rank_txt = ""
    method_bodies_rank_txt += "test_body:\n" + bug_data['test_body'] + "\n\n" + "stack_trace:"+"\n"+bug_data['stack_trace'] + "\n\nRanked Methods:\n"
    for method_id, rank in sorted_methods:
        method_body = bug_data['covered_methods'][method_id]['method_body']
        method_bodies_rank_txt += f"Rank: {rank}, Method_id: {method_id}\nMethod_body: {method_body}\n\n"
    
    return method_bodies_rank_txt


# Function to extract relevant information from bug data
def extract_info(project_name, tech, bug_id, test_id):
    # Read the JSON file
    with open(f'../data/Output/{project_name}/{tech}/{bug_id}/test_{test_id}.json', 'r') as file:
        ranked_data = json.load(file)
    
    # Extract method ids and rank from the ranked data in a dictionary
    method_rankings = {method['method_id']: method['rank'] for method in ranked_data['ans']}

    # extract method bodies from the bug data
    extracted_bug_info = extract_method_ranked_bug_info(project_name, tech, bug_id, test_id, method_rankings)
    return extracted_bug_info

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

    folder_path = f'../data/Output/{project_name}/{tech}/{bug_id}'
    number_of_test_files = count_files_in_directory(folder_path)

    for test_id in range(number_of_test_files):
        try:
            # Extract the information into a string
            ranked_data_txt = extract_info(project_name, tech, bug_id, test_id)
            final_prompt = prompt_template.invoke({"coverage_info": ranked_data_txt, "json_output_format": output_format})
            # print(final_prompt.to_string())
            num_tokens = model_handler.num_tokens_from_string(final_prompt.to_string())
            print(f"Number of tokens: {num_tokens}")

            if num_tokens > 111600:  # Assuming 111616 is the max input token size for your model
                raise ValueError(f"Input token size exceeded for {project_name}, {bug_id}, test_{test_id}")

            # Create the chain
            chain = prompt_template | model | parser
            full_output = ""
            # Use async for loop to stream output
            async for chunk in chain.astream({"coverage_info": ranked_data_txt, "json_output_format": output_format}):
                full_output += chunk
                print(chunk, end="", flush=True)
            output_path = f'../data/Reasonings/{project_name}/{tech}/{bug_id}/test_{test_id}.json'
            parser_handler.parse_and_save_final_json(full_output, project_name, bug_id, test_id, output_path)
        except Exception as e:
            # Log the error with details of the project, bug, and test ID
            error_message = f"Error for project: {project_name}, bug_id: {bug_id}, test_id: {test_id} - {str(e)}"
            logging.error(error_message)
            print(error_message)

# Run the main async function
if __name__ == "__main__":
    asyncio.run(main())
