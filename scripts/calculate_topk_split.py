import json
import os
from collections import defaultdict
import sys
import pandas as pd



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
            results['top_1'] += 1
            found_top_1_bugs.append(bug_id)
        else:
            missed_top_1_bugs.append(bug_id)

        if found_top_3:
            results['top_3'] += 1
            found_top_3_bugs.append(bug_id)
        else:
            missed_top_3_bugs.append(bug_id)

        if found_top_5:
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
    if os.path.exists(test_file_path):
        with open(test_file_path, 'r') as json_file:
            data = json.load(json_file)
        for method in data.get('covered_methods', []):
            method_signatures_map[method['method_id']] = method['method_signature']
    return method_signatures_map

def save_top_k_results_to_json(output_data, output_json_file):
    combined_results = defaultdict(lambda: defaultdict(dict))

    # Iterate through the collected results and store them in a structured JSON format
    for i in range(len(output_data["Project"])):
        project = output_data["Project"][i]
        technique = output_data["Technique"][i]
        
        combined_results[project][technique] = {
            "Top-1": output_data["Top-1"][i],
            "Top-3": output_data["Top-3"][i],
            "Top-5": output_data["Top-5"][i],
            "Top-10": output_data["Top-10"][i]
        }

    # Save the combined results to a JSON file
    with open(output_json_file, 'w') as json_file:
        json.dump(combined_results, json_file, indent=4)

    print(f"Top-k results saved to {output_json_file}")


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

    final_output = {
        "project_name": project_name,
        "bugs": merged_data
    }
    return final_output

output_type = sys.argv[1]
buckets = sys.argv[2]
# List of projects and techniques
projects = ["Cli", "Math", "Csv", "Codec", "Compress", "Gson", "JacksonCore", "JacksonXml", "Mockito", "Jsoup", "Lang", "Time"]
# techniques = ["one", "half", "zero", "minus_half", "minus_one"]
# techniques=["ochiai", "depgraph", "execution", "random", "wo_gettersetter_execution", "wo_gettersetter_ochiai", "wo_gettersetter_depgraph", "wo_gettersetter_random", "wo_gettersetter_perfect_callgraph", "perfect_callgraph", "loc"]
techniques = ["perfect_callgraph", "random"]

# Create an Excel file with 5 tabs and save the results
output_data = defaultdict(list)

for project_name in projects:
    for technique in techniques:
        txt_files_directory = f'../data/BuggyMethods/{project_name}'
        reasoning_path = f'../data/Output/{output_type}/{buckets}/{project_name}/{technique}'
        processed_dir = f'../data/RankedData/{project_name}/{technique}'
        
        # Merge JSON files
        merged_data = merge_json_files(reasoning_path, txt_files_directory, project_name, processed_dir)
        
        # Calculate results
        results, missed_top_1_bugs, missed_top_3_bugs, missed_top_5_bugs, missed_top_10_bugs, found_top_1_bugs, found_top_3_bugs = calculate_top_results_with_missed_bugs(merged_data)
        
        # Add results to output
        output_data["Project"].append(project_name)
        output_data["Technique"].append(technique)
        output_data["Split"].append(buckets)
        output_data["Top-1"].append(results['top_1'])
        output_data["Top-3"].append(results['top_3'])
        output_data["Top-5"].append(results['top_5'])
        output_data["Top-10"].append(results['top_10'])
        

# Create a DataFrame from the collected data
df = pd.DataFrame(output_data)

# Calculate totals for each technique across all projects
technique_totals = df.groupby("Technique")[["Top-1", "Top-3", "Top-5", "Top-10"]].sum().reset_index()

# Add a "Total" row for each technique
technique_totals["Project"] = "Total"
technique_totals["Split"] = buckets

# Reorder columns to match the original DataFrame structure
technique_totals = technique_totals[["Project", "Technique", "Split", "Top-1", "Top-3", "Top-5", "Top-10"]]

# Append the technique totals to the main DataFrame
df = pd.concat([df, technique_totals], ignore_index=True)

with pd.ExcelWriter(f'../data/Results/Split/Combined_{output_type}_{buckets}.xlsx', engine='xlsxwriter') as writer:
    df.to_excel(writer, sheet_name='Results', index=False)


# Example usage after calculating the results:
save_top_k_results_to_json(output_data, f'top_k_results_combined_{output_type}.json')

print("Results saved to fault_localization_results.xlsx")
