#!/bin/bash

# Arrays for projects and bug counts

projects=("Lang" "Math" "Csv" "Codec" "Gson" "JacksonCore" "JacksonXml" "Mockito" "Cli" "Compress" "Jsoup" "Time")
# projects=("Math" "Csv" "Codec" "Gson" "JacksonCore" "JacksonXml" "Mockito" "Cli" "Compress" "Jsoup")
# projects=("Time" "Lang")
bug_counts=(65 106 16 18 18 26 6 38 40 47 93 27)
# bug_counts=(27 65)

# # Techniques for distracting rules and other ranked methods
# techniques=("ochiai" "depgraph" "execution" "perfect_callgraph" "random" "wo_gettersetter_execution" "wo_gettersetter_ochiai" "wo_gettersetter_depgraph" "wo_gettersetter_random" "wo_gettersetter_perfect_callgraph")

# # Ei koyda baki asilo kina check korar jonno
# techniques=("wo_gettersetter_execution" "wo_gettersetter_ochiai" "wo_gettersetter_depgraph" "wo_gettersetter_random" "wo_gettersetter_perfect_callgraph")

# Techniques for Kendall Tau
# techniques=("one" "half" "zero" "minus_half" "minus_one")
# techniques=("perfect_callgraph")

# Techniques for experiments w/o test execution
techniques=("perfect_callgraph" "random")
# techniques=("loc")
# techniques=("callgraph_bfs" "callgraph_dfs")

# Loop through each technique
# Define your arrays (assuming they are already defined in your script)
# projects=("Project1" "Project2" "Project3")
# bug_counts=(10 15 20)
# techniques=("technique1" "technique2" "technique3")

# Loop through each project index
for i in "${!projects[@]}"
do
    project=${projects[$i]}
    bug_count=${bug_counts[$i]}
    echo "Processing project: $project with bug count up to $bug_count"

    # Now loop through each technique for the current project
    for technique in "${techniques[@]}"
    do
        echo "Processing technique: -------- $technique --------- for project: ------ $project ------"

        # Run the scripts for versions 1 through the bug count for the current project
        for version in $(seq 1 $bug_count)
        do
            echo "Running test for project: $project, version: $version, technique: $technique"
            # Uncomment the script you want to run
            # python order_test.py ${project} ${version} ${technique} 2
            python order_test_split.py ${project} ${version} ${technique} 40
            # python order_test_split_chat.py ${project} ${version} ${technique} 50
            # python order_test_split_chat_summarize.py ${project} ${version} ${technique} 50
            # python order_test_wo_stacktrace.py ${project} ${version} ${technique}
            # python order_test_kendall_tau.py ${project} ${version} ${technique}
            # python order_test_wo_execution.py ${project} ${version} ${technique}
            # python order_test_kendall_tau_wo_execution.py ${project} ${version} ${technique}
        done
    done
done

echo "All projects and techniques processed."
