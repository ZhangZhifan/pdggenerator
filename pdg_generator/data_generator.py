# -*- coding: utf-8 -*-  
import sys
sys.path.extend(['.', '..'])
from pycparser import parse_file, c_ast, c_generator
from graph.pdg_graph import GraphNode, GraphEdge, ControlGraph
from pdg_generator.varParser import get_var_from_decl, VarVisitor

def getGenAndKill(graph):
    """ 对一个控制图中的节点计算gen和kill集合 """

    # 一个dict存储每个变量被定义的节点列表
    genDict = {}

    def genDictInsert(var, node):
        if not var.name in genDict:
            genDict[var.name] = set()
        genDict[var.name].add(node)

    # 为所有的变量定义建立变量-定义节点的映射
    for node in graph.nodeList:
        for var in node.defVars:
            genDictInsert(var, node)
            node.gen.add(node)

    # 第二遍计算kill
    # node.kill = node定义的变量的所有定义位置 - 当前节点
    for node in graph.nodeList:
        for var in node.defVars:
            node.kill |= genDict[var.name] - set([node]) 

    # 之后循环计算IN和OUT集合
    changed = True
    while changed:
        changed = False
        for node in graph.nodeList:
            newInSet = set()
            for pre in node.preControlFlow:
                newInSet |= pre.outSet
            newOutSet = node.gen | (newInSet - node.kill)
            if newOutSet ^ node.outSet:
                # 两个集合不等，说明有变化
                changed = True
            node.inSet = newInSet
            node.outSet = newOutSet

    # 数据依赖
    for node in graph.nodeList:
        for dNode in node.inSet:
            for var in dNode.defVars:
                if var in node.useVars:
                    dNode.addDataDepend(node)


