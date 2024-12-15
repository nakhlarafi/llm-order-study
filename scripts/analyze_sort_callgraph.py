import json
import os
import sys
from collections import defaultdict, OrderedDict
from glob import glob


def load_call_graph(call_graph_path, include_types=None):
    """Load call graph data from a file and return it as an OrderedDict to preserve sequence."""
    if include_types is None:
        include_types = {'M', 'I', 'O', 'S', 'D'}  # Include all call types by default

    call_graph = OrderedDict()  # Using OrderedDict to preserve the call order

    with open(call_graph_path, 'r') as f:
        for line in f:
            if not line.startswith("M:"):
                continue
            parts = line.split()
            caller = parts[0][2:]  
            callee = parts[1][3:]  
            call_type = parts[1][1:2]  

            if call_type not in include_types:
                continue

            if caller not in call_graph:
                call_graph[caller] = []
            call_graph[caller].append(callee)

    return call_graph

def convert_dict_signature(signature):
    """Convert method signature from dictionary format to call graph format."""
    class_name, rest = signature.split(':', 1)
    method_name, args = rest.split('(', 1)
    args = args.split(')', 1)[0]

    arg_map = {
        'Z': 'Boolean', 'B': 'byte', 'C': 'char', 'S': 'short',
        'I': 'int', 'J': 'long', 'F': 'float', 'D': 'double', 'V': 'void',
        'Ljava/lang/String;': 'java.lang.String', 'Ljava/lang/Object;': 'java.lang.Object'
    }

    def transform_args(arg_str):
        if arg_str.startswith('['):
            return transform_args(arg_str[1:]) + "[]"
        for symbol, java_type in arg_map.items():
            if arg_str.startswith(symbol):
                return java_type
        return arg_str.replace('/', '.')

    args_list = []
    while args:
        found = False
        for symbol in arg_map:
            if args.startswith(symbol):
                args_list.append(transform_args(symbol))
                args = args[len(symbol):]
                found = True
                break
        if not found:
            obj_sig = args.split(';', 1)[0] + ';'
            args_list.append(transform_args(obj_sig))
            args = args[len(obj_sig):]

    args_str = ','.join(args_list)
    return f"{class_name}:{method_name}({args_str})"

def load_json_signatures(json_file):
    """Load the JSON file and create a mapping of converted signatures to original signatures."""
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    signature_map = {}
    for method in data.get("covered_methods", []):
        original_signature = method["method_signature"]
        converted_signature = convert_dict_signature(original_signature)
        signature_map[converted_signature] = original_signature

    return signature_map, data

def build_call_tree_dfs(call_graph, start_method, depth=0, max_depth=10, visited=None):
    """Recursively build a call tree starting from the specified method, preserving order in call graph."""
    if visited is None:
        visited = set()
    
    if start_method not in call_graph or start_method in visited or depth > max_depth:
        return []

    visited.add(start_method)

    tree = [start_method]
    for callee in call_graph[start_method]:
        tree += build_call_tree_dfs(call_graph, callee, depth + 1, max_depth, visited)

    visited.remove(start_method)
    return tree

from collections import deque

def build_call_tree_bfs(call_graph, start_method, max_depth=10):
    visited = set()
    queue = deque([(start_method, 0)])  # Queue stores tuples of (method, depth)
    tree = []

    while queue:
        current_method, depth = queue.popleft()

        if current_method in visited or depth > max_depth:
            continue

        visited.add(current_method)
        tree.append(current_method)

        # Add unvisited neighbors to the queue
        for callee in call_graph.get(current_method, []):
            if callee not in visited:
                queue.append((callee, depth + 1))

    return tree


def match_and_sort_methods(call_tree, signature_map, covered_methods):
    """Sort the covered methods based on the call tree sequence and reset method IDs."""
    ordered_methods = []
    matched_methods = set()

    # First, add methods in the order they appear in the call tree
    for method in call_tree:
        original_sig = signature_map.get(method)
        if original_sig:
            for covered_method in covered_methods:
                if covered_method["method_signature"] == original_sig and original_sig not in matched_methods:
                    ordered_methods.append(covered_method)
                    matched_methods.add(original_sig)
                    break

    # Then, add any methods not found in the call tree at the end
    for covered_method in covered_methods:
        if covered_method["method_signature"] not in matched_methods:
            ordered_methods.append(covered_method)

    # Re-assign unique method IDs sequentially from 0 based on the new order
    for idx, method in enumerate(ordered_methods):
        method["method_id"] = idx

    return ordered_methods



def process_project_versions(project_path, call_graph_base_path, output_base_path):
    """Process all versions in a project folder."""
    version_paths = glob(os.path.join(project_path, "*"))
    
    for version_path in version_paths:
        version = os.path.basename(version_path)
        json_files = glob(os.path.join(version_path, "test_*.json"))
        
        # Call graph file path based on project and version
        project_name = os.path.basename(os.path.dirname(project_path)).lower()
        call_graph_path = os.path.join(call_graph_base_path, f"{project_name}_{version}_b.txt")
        
        if not os.path.exists(call_graph_path):
            print(f"Call graph file not found for version {version}. Skipping.")
            continue
        
        # Load the call graph for the current version
        call_graph = load_call_graph(call_graph_path)
        for json_file in json_files:
            # Load test data and generate the starting method
            signature_map, test_data = load_json_signatures(json_file)
            start_method = test_data["test_name"].rsplit('.', 1)[0] + ':' + test_data["test_name"].rsplit('.', 1)[1] + '()'

            # Build the call tree
            # call_tree = build_call_tree_dfs(call_graph, start_method, max_depth=5)
            call_tree = build_call_tree_bfs(call_graph, start_method, max_depth=5)
            
            # Sort covered methods based on call sequence
            sorted_methods = match_and_sort_methods(call_tree, signature_map, test_data["covered_methods"])
            
            # Save the updated JSON with sorted methods
            output_path = os.path.join(output_base_path, os.path.relpath(json_file, project_path))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            test_data["covered_methods"] = sorted_methods
            with open(output_path, 'w') as f:
                json.dump(test_data, f, indent=4)
            print(f"Processed and saved {output_path}")


project = sys.argv[1]

# Paths for input project folder, call graph base folder, and output folder
project_path = f"../data/RankedData/{project}/perfect"
call_graph_base_path = f"../data/CallGraphs/{project}"
output_base_path = f"../data/RankedData/{project}/callgraph_bfs"

# Run the process
process_project_versions(project_path, call_graph_base_path, output_base_path)
