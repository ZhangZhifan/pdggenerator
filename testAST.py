
from __future__ import print_function
import sys	

sys.path.extend(['.', '..'])

from pycparser import parse_file, c_ast

NodeList = [];
EdgeList = [];

currParent = 0;
nodeCnt = 0;

class PrintVisitor(c_ast.NodeVisitor):
    def __init__(self):
        self.values = []
    
    def generic_visit(self, node):
        global currParent
        global nodeCnt
        
        addNode(node)
        lastParent = currParent
        currParent = nodeCnt    
        for c_name, c in node.children():
            self.visit(c)
        currParent = lastParent
        
def addNode(node):
    global nodeCnt
    global NodeList
    
    nodeCnt += 1;
    nodeName = 'Node'+str(nodeCnt);
    label = node.__class__.__name__+ ': '
    if node.attr_names:
        vlist = [getattr(node, n) for n in node.attr_names]
        attrstr = ', '.join('%s' % v for v in vlist)
        label += attrstr
    label = label.replace('\"', '\\\"')
    nodeStr = nodeName + '[label="' + label + '"];'
    NodeList.append(nodeStr)
    addEdge(nodeCnt)
    
def addEdge(nodeNum):
    global currParent
    global EdgeList
    edgeStr = 'Node'+str(currParent)+'->Node'+str(nodeNum)+';'
    EdgeList.append(edgeStr)

def generateDot(filename):
    ast = parse_file(filename)
    #ast.show()
    
    NodeList.append('Node0[label="START"]')
    v = PrintVisitor()
    v.visit(ast)
    
    graphStr = 'digraph G1{\n'
    for node in NodeList:
        graphStr += node + "\n"
    for edge in EdgeList:
        graphStr += edge + "\n"
    graphStr += "}"
    print(graphStr)
    
    

if __name__ == "__main__":
    if len(sys.argv) > 1:
        generateDot(sys.argv[1])
    else:
        print("Please provide a filename as argument")
