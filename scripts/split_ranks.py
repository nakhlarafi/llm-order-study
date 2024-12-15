import json
import os
from pathlib import Path

def split_json_files(input_directory, base_output_directory, methods_per_split):
    # Walk through all files in the specified input directory
    for root, dirs, files in os.walk(input_directory):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as json_file:
                    data = json.load(json_file)

                # Split the 'covered_methods' list into chunks of specified size
                covered_methods = data.get('covered_methods', [])
                total_methods = len(covered_methods)
                if total_methods == 0:
                    print(f"No methods found in {file_path}. Skipping.")
                    continue

                # Create chunks with the specified number of methods per split
                chunks = [covered_methods[i:i + methods_per_split] for i in range(0, total_methods, methods_per_split)]

                # Get the relative path of the current file's directory to maintain the same structure
                relative_dir = Path(root).relative_to(input_directory)

                # Save each chunk into a new JSON file
                for index, chunk in enumerate(chunks):
                    # Prepare new data dictionary with modified covered_methods
                    new_data = data.copy()
                    new_data['covered_methods'] = chunk

                    # Construct the output directory based on the base output directory and the relative directory
                    output_directory = Path(base_output_directory) / relative_dir

                    # Create output directory if it does not exist
                    os.makedirs(output_directory, exist_ok=True)

                    # Determine new file name and save path
                    new_file_name = f"{Path(file).stem}_{index}.json"
                    new_file_path = output_directory / new_file_name

                    # Write the chunk to a new JSON file
                    with open(new_file_path, 'w') as new_json_file:
                        json.dump(new_data, new_json_file, indent=4)

                    print(f"Data saved to {new_file_path}")

def process_projects_and_techniques(projects, techniques, base_input_dir, base_output_dir, methods_per_split):
    """Process all projects and techniques."""
    for project in projects:
        for technique in techniques:
            print(f"Processing Project: {project}, Technique: {technique}")
            input_dir = os.path.join(base_input_dir, project, technique)
            output_dir = os.path.join(base_output_dir, project, technique)
            if os.path.exists(input_dir):
                split_json_files(input_dir, output_dir, methods_per_split)
            else:
                print(f"Input directory does not exist: {input_dir}")

if __name__ == "__main__":
    # List of projects and techniques
    projects = ["Cli", "Math", "Csv", "Codec", "Compress", "Gson", "JacksonCore", "JacksonXml", "Mockito", "Jsoup", "Lang", "Time"]
    techniques = ["perfect_callgraph", "random"]

    methods_per_split = 40
    
    base_input_directory = '../data/RankedData'
    base_output_directory = f'../data/RankedDataSplit/{methods_per_split}'

    # Process all projects and techniques
    process_projects_and_techniques(projects, techniques, base_input_directory, base_output_directory, methods_per_split)
