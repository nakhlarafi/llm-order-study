import json
import os
import shutil
import sys

def load_json(file_path):
    """Load a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(data, file_path):
    """Save the modified JSON back to file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def get_method_signatures(covered_methods):
    """Extract method signatures from the covered_methods list."""
    return {method['method_signature'] for method in covered_methods}

def filter_execution_methods(sbfl_file, execution_file, output_file):
    # Load the JSON files
    sbfl_data = load_json(sbfl_file)
    execution_data = load_json(execution_file)

    # Get method signatures from the SBFL file
    sbfl_signatures = get_method_signatures(sbfl_data['covered_methods'])

    # Filter methods in execution data that are also in sbfl_signatures
    execution_data['covered_methods'] = [
        method for method in execution_data['covered_methods']
        if method['method_signature'] in sbfl_signatures
    ]

    # fix the method_id of the methods
    for i, method in enumerate(execution_data['covered_methods']):
        method['method_id'] = i

    # Save the modified execution file to the new location
    save_json(execution_data, output_file)

def process_all_tests(base_dir):
    """Process all tests in the specified directory and save them in a new structure."""
    sbfl_dir = os.path.join(base_dir, 'ochiai')
    execution_dir = os.path.join(base_dir, 'processed_by_execution_withoutline')
    output_execution_dir = os.path.join(base_dir, 'execution')

    # Copy the directory structure to the new folder (without files)
    if os.path.exists(output_execution_dir):
        shutil.rmtree(output_execution_dir)
    shutil.copytree(execution_dir, output_execution_dir, dirs_exist_ok=True)

    # Iterate over bug ID directories
    for bug_id in os.listdir(sbfl_dir):
        sbfl_bug_dir = os.path.join(sbfl_dir, bug_id)
        execution_bug_dir = os.path.join(execution_dir, bug_id)
        output_bug_dir = os.path.join(output_execution_dir, bug_id)

        # Ensure the corresponding bug directory exists in both sbfl and execution directories
        if not os.path.exists(execution_bug_dir):
            continue

        # Iterate over the test JSON files in the sbfl directory
        for sbfl_file_name in os.listdir(sbfl_bug_dir):
            sbfl_file = os.path.join(sbfl_bug_dir, sbfl_file_name)
            execution_file = os.path.join(execution_bug_dir, sbfl_file_name)
            output_file = os.path.join(output_bug_dir, sbfl_file_name)

            # Ensure the corresponding test JSON file exists in the execution directory
            if os.path.exists(execution_file):
                filter_execution_methods(sbfl_file, execution_file, output_file)

proj = sys.argv[1]
# Example usage:
process_all_tests(f'../data/RankedData/{proj}')