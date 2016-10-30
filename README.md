# Call Graph Creator
Using clang and LLVM creates the call graph of C++ source file.

Clang allows to create the call graph of a c++ source file. The output graph is a dot file using the Graphviz language.
The graph contains the calls to all the functions, in particular alse the low level one producing for even simple file a huge number of nodes and edges.
This work provides a tool to simplify the graph structure automatically eliminating undesired nodes and edges and also simplifying the nodes' label.

To use in Linux install clang and llvm. What is important is that both clang and llvm are of the same version.

`$ sudo apt-get install llvm`

This install llvm version 3.4 in ubuntu 14.04 and 3.8 in ubuntu 16.04. So to install clang

`$ sudo apt-get install clang-3.[4/8]`

To run the script

`$ chmod +x create_call_graph.py`

To display the help

`$ ./create_call_graph.py --help` 


