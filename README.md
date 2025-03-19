# LLM-Order-Bias

## Overview
This project explores how the order of code impacts the performance of Large Language Models (LLMs) in Fault Localization (FL). It employs various experiments to evaluate order bias, segmented input processing, and the effectiveness of different ordering strategies. The project utilizes the OpenAI API and LangChain for prompt-based fault localization.

## Requirements
- **OpenAI API**: Ensure you have access and a valid API key.
- **LangChain**: Install it via `pip install langchain`.

## All data and results related to this work can be found here
https://zenodo.org/records/15048201

## How to Run

### 1. **Run Experiments**
   - Use `order_test.py` to evaluate different input orders:
     ```bash
     python order_test.py --project_name <PROJECT_NAME> --bug_id <BUG_ID> --tech <TECH> --take <TAKE>
     ```
     - `PROJECT_NAME`: The name of the project (e.g., `Lang`).
     - `BUG_ID`: The bug number.
     - `TECH`: The approach (e.g., `perfect`, `worst`, or any other metric).
     - `TAKE`: Specifies the experiment run (e.g., iteration count).

   - Use `order_test_split.py` to run experiments with segmented inputs:
     ```bash
     python order_test_split.py --project_name <PROJECT_NAME> --bug_id <BUG_ID> --tech <TECH> --take <TAKE>
     ```

### 2. **Calculate Results**
   - Use `calculate_top_k.py` to compute Top-K accuracy for the standard experiments:
     ```bash
     python calculate_top_k.py
     ```
   - Use `calculate_top_k_split.py` to compute Top-K accuracy for segmented experiments:
     ```bash
     python calculate_top_k_split.py
     ```

### 3. **Batch Execution**
   - To facilitate running multiple experiments, use the provided shell scripts:
     - `fault_localization.sh`: Runs fault localization for a single experiment.
     - `fault_localization_batch.sh`: Automates batch execution of fault localization experiments.

## Project Structure
- **`data/`**: Contains all the input data and experiment results.
- **`scripts/`**: Includes all Python scripts for running experiments and calculating results.
- **`fault_localization.sh` and `fault_localization_batch.sh`**: Shell scripts to streamline experiment execution.

## Additional Notes
1. Ensure all dependencies are installed before running the scripts.
2. Experiment results are stored in the `data` folder for easy reference.
3. Modify the script arguments as needed to customize the experiments.

