import json
import os

def load_json(file_path):
    """Load a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(data, file_path):
    """Save the modified JSON back to file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def is_getter_or_setter(method_signature):
    """Check if a method is a getter or setter based on typical naming conventions."""
    getter_prefixes = ['get', 'is', 'has']
    setter_prefixes = ['set']
    
    method_name = method_signature.split(":")[-1].split('(')[0]
    return any(method_name.startswith(prefix) for prefix in getter_prefixes + setter_prefixes)

def count_lines_of_code(method_body):
    """Count the number of lines in the method body."""
    return len(method_body.split('\n'))

def find_method_body_and_loc(project_name, bug_id, method_signature, tech, ranked_data_base_dir):
    """Find the method body and line count for a specific method signature."""
    bug_dir = os.path.join(ranked_data_base_dir, project_name, tech, bug_id)
    
    # Check each test file in the bug directory
    for file_name in os.listdir(bug_dir):
        if file_name.endswith(".json"):
            file_path = os.path.join(bug_dir, file_name)
            test_data = load_json(file_path)
            
            for method in test_data.get('covered_methods', []):
                if method['method_signature'] == method_signature:
                    method_body = method.get('method_body', '')
                    lines_of_code = count_lines_of_code(method_body)
                    return method_body, lines_of_code
    return None, 0

def check_ground_truth_for_getter_setter(projects, ground_truth_base_dir, ranked_data_base_dir, tech, output_json_file):
    """Check ground truth files for getters and setters across multiple projects."""
    results = {}

    for project_name in projects:
        ground_truth_dir = os.path.join(ground_truth_base_dir, project_name)
        results[project_name] = {}

        # Iterate over bug ID files
        for bug_file_name in os.listdir(ground_truth_dir):
            bug_id = os.path.splitext(bug_file_name)[0]
            ground_truth_file = os.path.join(ground_truth_dir, bug_file_name)
            results[project_name][bug_id] = []

            # Check each method signature in the ground truth file
            with open(ground_truth_file, 'r') as f:
                for line in f:
                    method_signature = line.strip()
                    if is_getter_or_setter(method_signature):
                        # Find method body and count LOC
                        method_body, loc = find_method_body_and_loc(project_name, bug_id, method_signature, tech, ranked_data_base_dir)
                        if method_body:
                            results[project_name][bug_id].append({
                                "method_signature": method_signature,
                                "type": "getter" if any(method_signature.split(":")[-1].split('(')[0].startswith(prefix) for prefix in ['get', 'is', 'has']) else "setter",
                                "lines_of_code": loc
                            })

    # Save the results to the output JSON file
    with open(output_json_file, 'w') as json_file:
        json.dump(results, json_file, indent=4)

    print(f"Results saved to {output_json_file}")

# Example usage
projects = ["Cli", "Math", "Csv", "Codec", "Gson", "JacksonCore", "JacksonXml", "Mockito", "Compress", "Jsoup", "Lang", "Time"]
tech = "ochiai"  # Assuming you're using 'ochiai' directory
check_ground_truth_for_getter_setter(projects, '../data/BuggyMethods', '../data/RankedData', tech, '../data/Analysis/getter_setter_results.json')
