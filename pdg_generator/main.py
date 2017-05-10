# -*- coding: utf-8 -*-  
import sys
sys.path.extend(['.', '..'])
from graph.pdg_graph import GraphNode, GraphEdge, ControlGraph
from pdg_generator.control_generator import generate_control_graph
from pdg_generator.data_generator import getGenAndKill

def mainProcess(filename, optionList=None):
    vMode = False
    if optionList:
        for option in optionList:
            if option == '-v':
                vMode = True
    graph = generate_control_graph(filename)
    getGenAndKill(graph)

    return graph.printAllControlGraphDot('G', vMode)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print mainProcess(sys.argv[1], sys.argv[2:])
    else:
        print("Please provide a filename as argument")