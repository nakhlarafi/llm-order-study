import json
import os
import shutil

def load_json(file_path):
    """Load a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(data, file_path):
    """Save the modified JSON back to file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def calculate_loc(method):
    """Calculate the lines of code (LOC) for a method."""
    method_body = method.get('method_body', '')
    return method_body.count('\n') + 1

def rank_methods_by_loc(sbfl_file, output_file):
    """Rank methods based on LOC and save the updated JSON file."""
    # Load the JSON file
    sbfl_data = load_json(sbfl_file)

    # Calculate LOC for each method and store it
    for method in sbfl_data['covered_methods']:
        method['loc'] = calculate_loc(method)

    # Sort methods by LOC in descending order and update method_id
    sbfl_data['covered_methods'].sort(key=lambda m: m['loc'], reverse=True)
    for i, method in enumerate(sbfl_data['covered_methods']):
        method['method_id'] = i  # Update method_id based on new order

    # Save the modified JSON data
    save_json(sbfl_data, output_file)
    print(f"Processed and saved {output_file}")

def process_all_tests_by_loc(base_dir, projects, techniques, output_base_dir):
    """Process all tests for multiple projects and techniques, rank methods by LOC, and save to the specified output directory."""
    for project in projects:
        for tech in techniques:
            print(f"Processing Project: {project}, Technique: {tech}")
            sbfl_dir = os.path.join(base_dir, project, tech)
            output_dir = os.path.join(output_base_dir, project, f'loc')

            # Copy the directory structure to the new folder (without files)
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            shutil.copytree(sbfl_dir, output_dir, dirs_exist_ok=True)

            # Iterate over bug ID directories
            for bug_id in os.listdir(sbfl_dir):
                sbfl_bug_dir = os.path.join(sbfl_dir, bug_id)
                output_bug_dir = os.path.join(output_dir, bug_id)

                # Iterate over the test JSON files in the sbfl directory
                for sbfl_file_name in os.listdir(sbfl_bug_dir):
                    sbfl_file = os.path.join(sbfl_bug_dir, sbfl_file_name)
                    output_file = os.path.join(output_bug_dir, sbfl_file_name)

                    # Process the JSON file to rank methods by LOC
                    rank_methods_by_loc(sbfl_file, output_file)

# Example usage:
# Define the base directory, projects, techniques, and output base directory
base_dir = '../data/RankedData'
output_base_dir = '../data/RankedData'
projects = ["Cli", "Math", "Csv", "Codec", "Gson", "JacksonCore", "JacksonXml", "Mockito", "Compress", "Jsoup", "Lang", "Time"]
techniques = ["perfect_callgraph"]

process_all_tests_by_loc(base_dir, projects, techniques, output_base_dir)
