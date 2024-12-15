import json
import os
from collections import defaultdict
import sys


def calculate_top_results_with_missed_bugs(merged_data):
    results = {
        "top_1": 0,
        "top_3": 0,
        "top_5": 0,
        "top_10": 0
    }
    missed_top_1_bugs = []
    missed_top_3_bugs = []
    missed_top_5_bugs = []
    missed_top_10_bugs = []
    found_top_1_bugs = []
    found_top_3_bugs = []

    for bug_id, tests in merged_data['bugs'].items():
        found_top_1 = False
        found_top_3 = False
        found_top_5 = False
        found_top_10 = False
        
        for test_id, test_data in tests.items():
            method_signatures = test_data['method_signatures']
            ground_truth_methods = set(test_data['d4j_groundtruth'])
            
            # Calculate presence of ground truth methods in top 1, 3, and 5
            top_1_methods = method_signatures[:1]
            top_3_methods = method_signatures[:3]
            top_5_methods = method_signatures[:5]

            if ground_truth_methods.intersection(top_1_methods):
                found_top_1 = True
            if ground_truth_methods.intersection(top_3_methods):
                found_top_3 = True
            if ground_truth_methods.intersection(top_5_methods):
                found_top_5 = True
            if ground_truth_methods.intersection(method_signatures[:10]):
                found_top_10 = True

        if found_top_1:
            # print(bug_id)
            results['top_1'] += 1
            found_top_1_bugs.append(bug_id)
        else:
            missed_top_1_bugs.append(bug_id)

        if found_top_3:
            # print(bug_id)
            results['top_3'] += 1
            found_top_3_bugs.append(bug_id)
        else:
            missed_top_3_bugs.append(bug_id)

        if found_top_5:
            # print(bug_id)
            results['top_5'] += 1
        else:
            missed_top_5_bugs.append(bug_id)

        if found_top_10:
            results['top_10'] += 1
        else:
            missed_top_10_bugs.append(bug_id)

    return results, missed_top_1_bugs, missed_top_3_bugs, missed_top_5_bugs, missed_top_10_bugs, found_top_1_bugs, found_top_3_bugs


def map_method_ids_to_signatures(processed_dir, bug_id, test_id):
    method_signatures_map = {}
    test_file_path = os.path.join(processed_dir, f"{bug_id}", f"test_{test_id}.json")
    # print(test_file_path)
    if os.path.exists(test_file_path):
        with open(test_file_path, 'r') as json_file:
            data = json.load(json_file)
        for method in data.get('covered_methods', []):
            method_signatures_map[method['method_id']] = method['method_signature']
    # print(method_signatures_map)
    return method_signatures_map

def integrate_additional_signatures(merged_data, methodsig_path, processed_dir):
    for root, dirs, files in os.walk(methodsig_path):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    bug_id = str(data['bug_id'])
                    test_id = str(data['test_id'])
                    if bug_id in merged_data and test_id in merged_data[bug_id]:
                        existing_ids = set(merged_data[bug_id][test_id]['method_ids'])
                        for method_id in data['method_ids']:
                            if method_id not in existing_ids:
                                merged_data[bug_id][test_id]['method_ids'].append(method_id)
                except Exception as e:
                    print(f"Error processing methodsig file {file_path}: {e}")



def merge_json_files(reasoning_path, txt_files_directory, project_name, processed_dir):
    merged_data = defaultdict(lambda: defaultdict(lambda: {
        "method_ids": [],
        "method_signatures": [],
        "d4j_groundtruth": []
    }))

    for root, dirs, files in os.walk(reasoning_path):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                # print(file_path)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    bug_id = str(data['bug_id'])
                    test_id = str(data['test_id'])
                    for entry in data['ans']:
                        if entry['method_id'] not in merged_data[bug_id][test_id]['method_ids']:
                            merged_data[bug_id][test_id]['method_ids'].append(entry['method_id'])
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")

    # Map all method signatures after integrating all method IDs
    for bug_id in merged_data:
        for test_id in merged_data[bug_id]:
            method_signatures_map = map_method_ids_to_signatures(processed_dir, bug_id, test_id)
            for method_id in merged_data[bug_id][test_id]['method_ids']:
                method_signature = method_signatures_map.get(method_id, "Unknown Signature")
                merged_data[bug_id][test_id]['method_signatures'].append(method_signature)

    # Load ground truth signatures
    for bug_id, tests in merged_data.items():
        txt_file_path = os.path.join(txt_files_directory, f"{bug_id}.txt")
        if os.path.exists(txt_file_path):
            try:
                with open(txt_file_path, 'r') as txt_file:
                    ground_truth_signatures = [line.strip() for line in txt_file.readlines() if line.strip()]
                for test_id in tests:
                    merged_data[bug_id][test_id]['d4j_groundtruth'] = ground_truth_signatures
            except Exception as e:
                print(f"Error reading ground truth file {txt_file_path}: {e}")

    # Construct the final output
    final_output = {
        "project_name": project_name,
        "bugs": {}
    }
    for bug_id, tests in merged_data.items():
        final_output['bugs'][bug_id] = {}
        for test_id, data in tests.items():
            final_output['bugs'][bug_id][test_id] = {
                "method_ids": data['method_ids'],
                "method_signatures": data['method_signatures'],
                "d4j_groundtruth": data['d4j_groundtruth']
            }

    return final_output


# Example usage and file writing
project_name = sys.argv[1]
technique = sys.argv[2]
output_type = sys.argv[3]
buckets = sys.argv[4]
reasoning_path = f'../data/Output/{output_type}/{buckets}/{project_name}/{technique}'
processed_dir = f'../data/RankedData/{project_name}/{technique}'


txt_files_directory = f'../data/BuggyMethods/{project_name}'
result = merge_json_files(reasoning_path, txt_files_directory, project_name, processed_dir)

# Calculate the results
results, missed_top_1_bugs, missed_top_3_bugs, missed_top_5_bugs, missed_top_10_bugs, found_top_1_bugs, found_top_3_bugs = calculate_top_results_with_missed_bugs(result)

print("Top-1 Accuracy:", results['top_1'])
print("Top-3 Accuracy:", results['top_3'])
print("Top-5 Accuracy:", results['top_5'])
print("Top-10 Accuracy:", results['top_10'])

# print missed_top_1_bugs elements as str sperated by space
print("Missed Top-1 Bugs:", " ".join(missed_top_1_bugs))