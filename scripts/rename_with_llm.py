import asyncio
import json
import re
import os
import logging
import sys
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Setup logging
def setup_logging():
    logging.basicConfig(filename='error_log_renames.txt', level=logging.ERROR, 
                        format='%(asctime)s %(message)s')

# Count files in a directory
def count_files_in_directory(directory_path):
    file_count = 0
    for root, dirs, files in os.walk(directory_path):
        file_count += len(files)
    return file_count

# Load JSON data from a file
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Parse JSON file safely
def parse_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            else:
                raise ValueError("JSON file does not contain a valid dictionary.")
    except Exception as e:
        logging.error(f"Error parsing JSON file {file_path}: {e}")
        print(f"Error parsing JSON file {file_path}: {e}")
        return {}

# Remove markdown formatting if present
def clean_json_output(output):
    output = output.strip()
    if output.startswith("```"):
        lines = output.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        output = "\n".join(lines).strip()
    return output

# Extract method name from a method signature
def extract_method_name(method_signature):
    match = re.search(r':([^:(]+)\(', method_signature)
    method_name = match.group(1) if match else None
    return method_name if method_name and method_name != "<init>" else None

# Generate new method names using LLM with streamed output
async def generate_new_names(method_names):
    try:
        model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        unique_names = list(set(method_names))
        methods_str = ", ".join(unique_names)

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Rename the given method names with human-readable names for the following method names. Return a JSON object where each original method name is mapped to its new name."),
            ("user", "{methods}")
        ])

        final_prompt = prompt.invoke({"methods": methods_str})
        print(f"Generated Prompt: {final_prompt}")

        # Create a chain to stream the response
        chain = prompt | model | StrOutputParser()

        full_output = ""
        async for chunk in chain.astream({"methods": methods_str}):
            full_output += chunk
            print(chunk, end="", flush=True)  # Streaming output in real-time

        if not full_output.strip():
            raise ValueError("Model returned an empty response.")

        cleaned_output = clean_json_output(full_output)

        try:
            parsed_json = json.loads(cleaned_output)
            if not isinstance(parsed_json, dict):
                raise ValueError("Invalid JSON format: Expected a dictionary.")
            return parsed_json
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e} - Model output: {full_output}")
            print(f"JSON decode error: {e} - Model output: {full_output}")
            return {}

    except Exception as e:
        logging.error(f"Error in generate_new_names: {str(e)}")
        print(f"Error in generate_new_names: {str(e)}")
        return {}

# Main function that processes each test file and saves the output in a mirrored structure
async def main():
    setup_logging()

    # Expecting command line arguments: project_name, bug_id (version), tech (technique)
    if len(sys.argv) < 4:
        print("Usage: python rename_with_llm.py <project_name> <bug_id> <tech>")
        sys.exit(1)

    project_name = sys.argv[1]
    bug_id = sys.argv[2]
    tech = sys.argv[3]

    # Build the input folder path
    folder_path = f'../data/RankedData/{project_name}/{tech}/{bug_id}'
    number_of_test_files = count_files_in_directory(folder_path)
    print(f"Found {number_of_test_files} test files in {folder_path}")

    # Process each test file
    for test_id in range(number_of_test_files):
        try:
            file_path = f'{folder_path}/test_{test_id}.json'
            print(f"\nProcessing file: {file_path}")
            data = load_json(file_path)

            method_signatures = [method["method_signature"] for method in data["covered_methods"]]
            method_names = list(filter(None, (extract_method_name(sig) for sig in method_signatures)))
            print(f"Extracted Method Names: {method_names}")

            # Generate renamed methods using LLM
            name_mapping = await generate_new_names(method_names)
            if not name_mapping:
                print(f"\nError: Model did not return valid renamed methods for file test_{test_id}.json.")
                continue

            # Build output folder and path
            output_folder = f'../data/Output/RankedData_llmrename/{project_name}/{tech}/{bug_id}'
            os.makedirs(output_folder, exist_ok=True)
            output_path = f'{output_folder}/test_{test_id}.json'

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(name_mapping, f, indent=4)
            print(f"\nUpdated method names saved in {output_path}")

            # Re-read and parse the generated JSON file to verify its correctness
            parsed_output = parse_json_file(output_path)
            if parsed_output:
                print("Successfully parsed generated JSON file.")
            else:
                print("Failed to parse generated JSON file.")

        except Exception as e:
            logging.error(f"Error processing test file test_{test_id}.json: {str(e)}")
            print(f"Error processing test file test_{test_id}.json: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
