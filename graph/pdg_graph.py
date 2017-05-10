# -*- coding: utf-8 -*-  
import sys

class NodeType:
    entry = -2
    exit = -1
    end = 0
    assign = 1
    decl = 2
    control = 3
    call = 4
    default = 100


class GraphNode:
    """
    依赖图中使用的节点类
    每个节点是一个简单语句
    其间存在依赖关系
    """
    # 包含属性：  id    节点代码   定义的变量  使用的    控制依赖于   数据依赖于   控制流
    def __init__(self, id, strLine):
        self.id = id
        self.content = strLine
        self.tokenList = []
        self.defVars = set([])
        self.useVars = set([])
        self.cDepends = []
        self.dDepends = []
        self.cFlow = []
        self.preControlFlow = [] #当前节点的前驱变量
        self.nodeType = NodeType.default

        self.gen = set()
        self.kill = set()
        self.inSet = set()
        self.outSet = set()
        
        #todo

    def __str__(self):
        return str(self.id) + ': ' +self.content

    def addControlDepend(self, node, tag = None):
        self.cDepends.append(GraphEdge(self, node, tag))

    def addDataDepend(self, node, tag = None):
        self.dDepends.append(GraphEdge(self, node, tag))

    def addControlFlow(self, node, tag = None):
        edge = GraphEdge(self, node, tag)
        self.cFlow.append(edge)
        node.preControlFlow.append(edge.fromNode)

    def addDataDepend(self, node, tag = None):
        edge = GraphEdge(self, node, tag)
        self.dDepends.append(edge)

    def add_def_var(self, var):
        if not var: return
        self.defVars.add(var)

    def add_use_var(self, var):
        if not var: return
        self.useVars.add(var)

    def get_dot(self, vMode=False):
        def escape(s):
            return (s.replace('\"', r'\"').replace('<', r'\<').replace('>', r'\>')
                     .replace(r'{', r'\{').replace(r'}', r'\}').replace(r' ', r'\ ')
                     .replace(r'|', r'\|'))

        nodeName = "Node" + str(self.id)
        code = str(self.id) + r': ' + escape(self.content)

        shape = 'shape=record'
        
        defVar = 'def: ' + ', '.join(v.name for v in self.defVars)
        useVar = 'use: ' + ', '.join(v.name for v in self.useVars)
        genSet = 'gen: ' + ', '.join(str(n.id) for n in self.gen)
        killSet = 'kill: ' + ', '.join(str(n.id) for n in self.kill)
        inSet = 'IN: ' + ', '.join(str(n.id) for n in self.inSet)
        outSet = 'OUT: ' + ', '.join(str(n.id) for n in self.outSet)

        attrList = [code]

        if vMode:
            attrList.append(inSet)
            attrList.append(outSet)
            attrList.append(defVar)
            attrList.append(useVar)

        label = 'label="{' + '|'.join(attrList) + '}"'
        nodeStr = nodeName + '[' + shape + ' ' + label + '];'
        
        return nodeStr

    def get_def_list(self):
        lst = []
        for var in self.defVars: lst.append(var.name)
        ret = ','.join(lst)
        return ret

    def get_use_list(self):
        lst = []
        for var in self.useVars: lst.append(var.name)
        ret = ','.join(lst)
        return ret

class GraphEdge:
    """
    边类
    以list记录边上的tag
    对控制依赖，记录T或F或无
    对数据依赖，记录到达的变量列表
    """
    __slot__ = ('fromNode', 'toNode', 'tag')
    def __init__(self, f, t, tag):
        self.fromNode = f
        self.toNode = t
        self.tag = []
        if tag is not None:
            self.tag.append(tag)

class ControlGraph:
    nodeList = None
    varDict = None
    
    def __init__(self, _nodeList=None, _varDict=None):
        if _nodeList:
            self.nodeList = _nodeList
        else:
            self.nodeList = []

        if _varDict:
            self.varDict = _varDict
        else:
            self.varDict = {}

    def addNode(self, node):
        self.nodeList.append(node)

    def _getNodeDot(self, noEndNode=True, vMode=False):
        """ 获得所有节点的dot表示 """
        graphStr = ''
        for node in self.nodeList:
            # 添加节点
            if noEndNode and node.nodeType is NodeType.end:
                continue
            nodeStr = node.get_dot(vMode)
            graphStr += nodeStr + '\n'
        return graphStr

    def _getCDEdgeDot(self):
        """ 获得所有控制依赖边的dot表示 """
        graphStr = ''
        for node in self.nodeList:
            for dependEdge in node.cDepends:
                fromName = "Node" + str(dependEdge.fromNode.id)
                toName = "Node" + str(dependEdge.toNode.id)
                edgeStr = fromName + "->" + toName + ";"
                graphStr += edgeStr + "\n"
        return graphStr

    def _getCFEdgeDot(self):
        """ 获得所有控制流边的dot表示 """
        graphStr = ''
        for node in self.nodeList:
             for flowEdge in node.cFlow:
                fromName = "Node" + str(flowEdge.fromNode.id)
                toName = "Node" + str(flowEdge.toNode.id)
                edgeStr = fromName + "->" + toName + " [style = dashed];"
                graphStr += edgeStr + "\n"
        return graphStr

    def _getDDEdgeDot(self):
        graphStr = ''
        for node in self.nodeList:
            for dependEdge in node.dDepends:
                fromName = "Node" + str(dependEdge.fromNode.id)
                toName = "Node" + str(dependEdge.toNode.id)
                edgeStr = fromName + "->" + toName + " [style = dotted];"
                graphStr += edgeStr + "\n"
        return graphStr   

    def printCDGraphDot(self, graphName='Control_Dependence_Graph'):
        graphStr = 'digraph '+graphName+'{\n'
        graphStr += self._getNodeDot()
        graphStr += self._getCDEdgeDot()
        graphStr += "}"
        return graphStr

    def printCFGraphDot(self, graphName='Control_Flow_Graph'):
        graphStr = 'digraph '+graphName+'{\n'
        graphStr += self._getNodeDot()
        graphStr += self._getCFEdgeDot()
        graphStr += "}"
        return graphStr

    def printAllControlGraphDot(self, graphName='Control_Graph', vMode=False):
        graphStr = 'digraph '+graphName+'{\n'
        graphStr += self._getNodeDot(True, vMode)
        graphStr += self._getCDEdgeDot()
        graphStr += self._getDDEdgeDot()
        # graphStr += self._getCFEdgeDot()
        graphStr += "}"
        return graphStr


if __name__ == "__main__":
    testNode = GraphNode(10, 'while(i <= 5)')
    help(GraphNode)
    print testNode