import json
import os
import random
from scipy.stats import kendalltau
from glob import glob

def controlled_swap(methods, swaps):
    """Perform a specific number of swaps on the method list."""
    for _ in range(swaps):
        i, j = random.sample(range(len(methods)), 2)
        methods[i], methods[j] = methods[j], methods[i]

def generate_versioned_orderings(methods, target_tau):
    """Generate a reordered list aiming to approximate the target Kendall Tau."""
    original_order = methods[:]
    
    if target_tau == 1.0:
        return original_order  # Perfect ranking
    elif target_tau == -1.0:
        return original_order[::-1]  # Full reverse

    # Start with a shuffled version and progressively adjust to reach target Kendall Tau
    reordered = original_order[:]
    max_iterations = 1000  # Limit to avoid excessive looping
    for _ in range(max_iterations):
        random.shuffle(reordered)  # Start with a random order
        tau, _ = kendalltau([m["method_id"] for m in original_order],
                            [m["method_id"] for m in reordered])
        if abs(tau - target_tau) < 0.05:  # Allow slight deviation
            return reordered
        elif tau < target_tau:
            # Increase concordance by reversing a pair of elements
            controlled_swap(reordered, 1)

    return reordered  # Return best approximation after max_iterations

def process_project_files(project_name, technique, target_tau_values):
    """Process all JSON test files for a given project and generate Kendall Tau versions."""
    base_path = f"../data/RankedData/{project_name}/{technique}"
    output_base = f"../data/KendallTau/{project_name}"

    # Find all version folders (1, 2, ...) and test JSON files within each version
    version_dirs = glob(os.path.join(base_path, "*"))
    
    for version_dir in version_dirs:
        version = os.path.basename(version_dir)
        json_files = glob(os.path.join(version_dir, "test_*.json"))

        # Process each JSON file in the current version folder
        for json_file in json_files:
            with open(json_file, 'r') as f:
                original_data = json.load(f)

            # Generate modified versions based on target Kendall Tau values
            for tau_label, target_tau in target_tau_values.items():
                reordered_methods = generate_versioned_orderings(original_data["covered_methods"], target_tau)
                
                # Reset method_ids based on the new order
                for idx, method in enumerate(reordered_methods):
                    method["method_id"] = idx
                
                # Define the output path and ensure the directory structure exists
                output_file = os.path.join(output_base, tau_label, version, os.path.basename(json_file))
                os.makedirs(os.path.dirname(output_file), exist_ok=True)

                # Save the reordered JSON file
                output_data = original_data.copy()
                output_data["covered_methods"] = reordered_methods
                with open(output_file, 'w') as f:
                    json.dump(output_data, f, indent=4)
                
                print(f"Generated {output_file} with target tau {target_tau}")

# Define projects and techniques
projects = ["Cli", "Math", "Csv", "Codec", "Compress", "Gson", "JacksonCore", "JacksonXml", "Mockito", "Jsoup", "Time"]
technique = "perfect_callgraph"

# Define target Kendall Tau values and corresponding folder names
target_tau_values = {
    "one": 1.0,
    "half": 0.5,
    "zero": 0.0,
    "minus_half": -0.5,
    "minus_one": -1.0
}

# Process each project
for project in projects:
    process_project_files(project, technique, target_tau_values)
