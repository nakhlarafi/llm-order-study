import asyncio
import sys
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import tiktoken
import re
import os
from collections import defaultdict
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
        self.system_template_first = "You will be given a failing test, stack_trace and the method it coveres. You have to rank the methods from most suspicious to least suspicious by analyzing these information. You should rank top 10 most suspicious methods. The output must be in the following JSON format:\n{json_output_format}"
        # self.system_template_corresponding = "You will be given the remaining covered methods by the failing testsalong with stack_trace. Previously you have ranked these methods from most suspicious to least suspicious:\n{previous_ranking}\n Now analyze rest of the given coverage information below and from here you should rank top 5 most suspicious methods. You should update your ranking based on your new observation. If you think the prvious ranking is fine you should keep them in the list. The output must be in the following JSON format:\n{json_output_format}"
        self.system_template_corresponding = "You are provided with the remaining covered methods identified by the failing tests, along with the stack trace. Previously, you ranked the following methods from most suspicious to least suspicious:\n{previous_ranking}\n Now, analyze the additional coverage information below. Based on this new data, update the ranking of the top 10 most suspicious methods. You may adjust the existing ranking if necessary, or retain it if no changes are warranted. Ensure that your final ranking reflects the latest observations.\nOutput the results in the following JSON format:\n{json_output_format}"

        self.user_template = "Here are the remaining coverage information: {coverage_info}"
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
        self.prompt_template_first = ChatPromptTemplate.from_messages(
            [("system", self.system_template_first), ("user", self.user_template)]
        )
        
        self.prompt_template_corresponding = ChatPromptTemplate.from_messages(
            [("system", self.system_template_corresponding), ("user", self.user_template)]
        )

    def get_prompt_template_first(self):
        return self.prompt_template_first
    
    def get_prompt_template_corresponding(self):
        return self.prompt_template_corresponding

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
    
    def append_and_save_final_json(self, contents, project_name, bug_id, test_id, path):
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

        # Create the new data structure to append
        new_data = {
            "project_name": project_name,
            "bug_id": bug_id,
            "test_id": test_id,
            "ans": json_objects,
            "final_full_answer": contents
        }

        # Check if the file exists
        if os.path.exists(path):
            # If it exists, load the current data
            with open(path, "r") as json_file:
                try:
                    existing_data = json.load(json_file)
                    # Ensure "combined_outputs" key exists
                    if "combined_outputs" not in existing_data:
                        existing_data["combined_outputs"] = []
                except json.JSONDecodeError:
                    existing_data = {"combined_outputs": []}
        else:
            # If the file doesn't exist, initialize a new structure
            existing_data = {"combined_outputs": []}

        # Append the new data to the "combined_outputs" list
        existing_data["combined_outputs"].append(new_data)

        # Ensure the directory exists
        dir_path = os.path.dirname(path)
        os.makedirs(dir_path, exist_ok=True)

        # Write the updated data back to the file
        with open(path, "w") as json_file:
            json.dump(existing_data, json_file, indent=4)

        print(f"Data appended and saved to {path}")
        return path



def count_split_tests(folder_path):
    test_files = defaultdict(list)
    
    # Walk through all files in the specified folder
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.json'):
                # Extract test name and its part index from the file name
                parts = file.split('_')
                if len(parts) > 2 and parts[-2].isdigit() and parts[-1].rstrip('.json').isdigit():
                    test_id = int(parts[-2])  # This assumes the format test_ID_PART.json
                    part_id = int(parts[-1].rstrip('.json'))
                    test_files[test_id].append(part_id)
    
    # Sort the part indices for each test
    for key in test_files:
        test_files[key].sort()

    return dict(test_files)

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


def extract_info_previous_rank(previous_original_ranking, previous_generated_ranked_data_path):
    text_content = ""

    # Load the original ranking data (covered methods)
    with open(previous_original_ranking, 'r') as original_file:
        original_data = json.load(original_file)

    # Load the generated ranked data (previously generated ranking)
    with open(previous_generated_ranked_data_path, 'r') as ranked_file:
        ranked_data = json.load(ranked_file)

    # Create a dictionary for quick lookup of covered methods
    covered_methods = {method['method_id']: method for method in original_data.get('covered_methods', [])}

    # Iterate over the ranked methods from the previous generated ranked data
    for ranked_method in ranked_data.get('ans', []):
        method_id = ranked_method.get('method_id')
        rank = ranked_method.get('rank')

        if method_id in covered_methods:
            method = covered_methods[method_id]
            text_content += f"Rank: {rank}\n"
            text_content += f"    Method Signature:\n{method['method_signature']}\n"
            text_content += f"    Method Body:\n{method['method_body']}\n"
            text_content += f"    Method ID:\n{method['method_id']}\n"
            text_content += "\n"
        else:
            # Include a placeholder for missing method information
            text_content += f"Rank: {rank}\n"
            text_content += f"    Method ID: {method_id} (Missing in covered_methods)\n"
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
    buckets = sys.argv[4]

    # Initialize handlers
    model_handler = ModelHandler()
    template_handler = TemplateHandler()
    parser_handler = OutputParser()

    # Get model, template, and parser
    model = model_handler.get_model()
    prompt_template_first = template_handler.get_prompt_template_first()
    prompt_template_corresponding = template_handler.get_prompt_template_corresponding()
    output_format = template_handler.get_output_format()
    parser = parser_handler.get_parser()

    folder_path = f'../data/RankedDataSplit/{buckets}/{project_name}/{tech}/{bug_id}'
    # number_of_test_files = count_files_in_directory(folder_path)
    number_of_test_files = count_split_tests(folder_path)

    for test_id in number_of_test_files.keys():
        print('-'*150)
        # exit()
        try:
            for split_id in number_of_test_files[test_id]:
                # Read the JSON file
                with open(f'{folder_path}/test_{test_id}_{split_id}.json', 'r') as file:
                    coverage_data_json = json.load(file)

                # Extract the information into a string
                coverage_data_txt = extract_info(coverage_data_json)
                if split_id == 0:
                    final_prompt = prompt_template_first.invoke({"coverage_info": coverage_data_txt, "json_output_format": output_format})
                    # print(final_prompt.to_string())
                else:
                    previous_original_ranking = f'../data/RankedData/{project_name}/{tech}/{bug_id}/test_{test_id}.json'
                    previous_generated_ranked_data_path = f'../data/Output/RankedDataSplit/{buckets}/RawOutput/{project_name}/{tech}/{bug_id}/test_{test_id}_{split_id-1}.json'
                    previous_coverage_data_txt = extract_info_previous_rank(previous_original_ranking, previous_generated_ranked_data_path)
                    
                    final_prompt = prompt_template_corresponding.invoke({"coverage_info": coverage_data_txt, "previous_ranking": previous_coverage_data_txt, "json_output_format": output_format})
                    # print('-'*100)
                    # print(final_prompt.to_string())
                    # exit()
                
                num_tokens = model_handler.num_tokens_from_string(final_prompt.to_string())
                print(f"Number of tokens: {num_tokens}")

                if num_tokens > 111600:  # Assuming 111616 is the max input token size for your model
                    raise ValueError(f"Input token size exceeded for {project_name}, {bug_id}, test_{test_id}")

                
                if split_id == 0:
                    chain = prompt_template_first | model | parser
                else:
                    chain = prompt_template_corresponding | model | parser

                # print(chain)
                # exit()
                full_output = ""
                if split_id == 0:
                    async for chunk in chain.astream({"coverage_info": coverage_data_txt, "json_output_format": output_format}):
                        full_output += chunk
                        print(chunk, end="", flush=True)
                else:
                    async for chunk in chain.astream({"previous_ranking": previous_coverage_data_txt, "coverage_info": coverage_data_txt, "json_output_format": output_format}):
                        full_output += chunk
                        print(chunk, end="", flush=True)
                raw_output_path = f'../data/Output/RankedDataSplit/{buckets}/RawOutput/{project_name}/{tech}/{bug_id}/test_{test_id}_{split_id}.json'
                parser_handler.parse_and_save_final_json(full_output, project_name, bug_id, test_id, raw_output_path)
                if number_of_test_files[test_id][-1] == split_id:
                    output_path = f'../data/Output/RankedDataSplit/{buckets}/{project_name}/{tech}/{bug_id}/test_{test_id}.json'
                    parser_handler.parse_and_save_final_json(full_output, project_name, bug_id, test_id, output_path)
        except Exception as e:
            # Log the error with details of the project, bug, and test ID
            error_message = f"Error for project: {project_name}, bug_id: {bug_id}, test_id: {test_id} - {str(e)}"
            logging.error(error_message)
            print(error_message)



# Run the main async function
if __name__ == "__main__":
    asyncio.run(main())
