# -*- coding: utf-8 -*-  

import sys

sys.path.extend(['.', '..'])
from pycparser import parse_file, c_ast, c_generator
from PDGGenerator.graph.pdg_graph import *

generator = c_generator.CGenerator()


class CDSVisitor(c_ast.NodeVisitor):


    def __init__(self):
        self.values = []

        self.nodeCnt = 1

        self.startNode = GraphNode(1, "START")
        self.lastControlDepend = self.startNode
        # 记录循环头，用于continue回边
        self.lastLoopHead = None
        self.lastSwitch = None
        # 记录循环节点对应的break列表，元素是元组(循环节点，[break节点列表])
        self.breakInLoop = {}
        self.breakInSwitch = {}
        # break所在的位置，loop或switch
        self.breakPosition = ""

        self.lastFlow = [self.startNode]

        self.nodeList = [self.startNode]

    def createNewNode(self, tag, astNode = None):
        global generator
        pre = ""
        if (tag is not None and tag != ""):
            pre = tag + ": "
        self.nodeCnt += 1
        if astNode is None:
            return GraphNode(self.nodeCnt, pre)
        return GraphNode(self.nodeCnt, pre + generator.visit(astNode))

    def updateControlFlow(self, currNode):
        # 挂控制流并更新，将控制流其实节点更新为当前单一节点
        for flowNode in self.lastFlow:
            flowNode.addControlFlow(currNode)
        self.lastFlow = [currNode]
    
    # visit decl语句
    # 不再迭代下去，整个作为一个节点
    # __slots__ = ('name', 'quals', 'storage', 'funcspec', 'type', 'init', 'bitsize', 'coord', '__weakref__')
    def visit_Decl(self, node):
        currNode = self.createNewNode('Decl', node)
        currNode.addControlDepend(self.lastControlDepend)
        
        # 挂载控制流
        self.updateControlFlow(currNode)

        self.nodeList.append(currNode)


    # visit FuncDef 
    # 
    # __slots__ = ('decl', 'param_decls', 'body', 'coord', '__weakref__')
    def visit_FuncDef(self, node):
        currNode = self.createNewNode('Function', node.decl)
        currNode.addControlDepend(self.lastControlDepend)
        self.nodeList.append(currNode)

        # 保存当前的依赖父节点
        pastControlDepend = self.lastControlDepend
        self.lastControlDepend = currNode
        # 挂控制流
        self.updateControlFlow(currNode)

        # 递归visit
        self.visit(node.body)
        # 还原依赖父节点
        self.lastControlDepend = pastControlDepend

    # visit 赋值语句
    # 不再迭代
    def visit_Assignment(self, node):
        currNode = self.createNewNode('Assign', node)
        currNode.addControlDepend(self.lastControlDepend)
        # 挂控制流
        self.updateControlFlow(currNode)

        self.nodeList.append(currNode)

        

    # visit while语句
    # 内部所有语句依赖while
    def visit_While(self, node):
        # print('While: %s' % self.generator.visit(node.cond))
        currNode = self.createNewNode('While', node.cond)
        currNode.addControlDepend(self.lastControlDepend)
        self.nodeList.append(currNode)
        
        # 记录新的循环头
        pastLoopHead = self.lastLoopHead
        self.lastLoopHead = currNode
        # 保存当前的依赖父节点
        pastControlDepend = self.lastControlDepend
        self.lastControlDepend = currNode

        # 挂控制流
        self.updateControlFlow(currNode)

        # 设置break状态
        self.breakPosition = "loop"
        # 递归visit
        self.generic_visit(node)
        # 当循环结束时，循环最后语句控制流应当指向循环头
        # 当前节点就是循环头
        # lastControlDepend是循环头
        # 循环的完成通过循环头结束，控制流重新从循环头开始
        self.updateControlFlow(currNode)

        # 循环结束时，把循环内部的break全部加入self.lastFlow
        if currNode in self.breakInLoop:
            for breakNode in self.breakInLoop[currNode]:
                self.lastFlow.append(breakNode)
            self.breakInLoop.pop(currNode)
        # 还原循环头和控制块
        self.breakPosition = ""
        self.lastLoopHead = pastLoopHead
        self.lastControlDepend = pastControlDepend

    # visit if语句
    # 内部所有语句依赖if条件
    def visit_If(self, node):
        currNode = self.createNewNode('If', node.cond)
        self.nodeList.append(currNode)
        currNode.addControlDepend(self.lastControlDepend)

        # 保存当前的依赖父节点
        pastControlDepend = self.lastControlDepend
        self.lastControlDepend = currNode
        # 挂控制流
        self.updateControlFlow(currNode)
        
        # visit True分支
        self.visit(node.iftrue)
        # if的两个分支都应指向控制流下一节点，到这里lastFlow是True分支的最后一句，暂存之
        ifFlow = self.lastFlow
        self.lastFlow = [currNode]
        # visit False分支
        if (node.iffalse is not None):
            self.visit(node.iffalse)
            # 此时lastFlow记录了false分支的结束节点，将其和true分支的合并
            ifFlow.extend(self.lastFlow)
            self.lastFlow = ifFlow

                
        # 还原控制依赖点
        self.lastControlDepend = pastControlDepend

    # visit for语句
    # __slots__ = ('init', 'cond', 'next', 'stmt', 'coord', '__weakref__')
    # init改在for前，next追加在stmt后，cond同while，所有语句依赖cond
    def visit_For(self, node):
        # 在循环前添加循环变量初始化节点
        initNode = self.createNewNode('For-init', node.init)
        self.nodeList.append(initNode)
        initNode.addControlDepend(self.lastControlDepend)
        self.updateControlFlow(initNode)

        # 循环条件作为循环自身代表节点
        currNode = self.createNewNode("For", node.cond)
        self.nodeList.append(currNode)
        self.updateControlFlow(currNode)
        
        currNode.addControlDepend(self.lastControlDepend)

        # 记录新的循环头
        pastLoopHead = self.lastLoopHead
        self.lastLoopHead = currNode
        # 保存当前的依赖父节点
        pastControlDepend = self.lastControlDepend
        self.lastControlDepend = currNode
        # 记录break状态
        self.breakPosition = "loop"
        # 递归调用
        self.generic_visit(node.stmt)
        # 将循环变量的最后语句追加到循环体
        nextNode = self.createNewNode('For-next', node.next)
        self.nodeList.append(nextNode)
        nextNode.addControlDepend(self.lastControlDepend)
        # 最后的语句也要更新控制流
        self.updateControlFlow(nextNode)
        # 之后控制流回到循环头
        self.updateControlFlow(currNode)
        # 循环结束时，把循环内部的break全部加入self.lastFlow
        if currNode in self.breakInLoop:
            for breakNode in self.breakInLoop[currNode]:
                self.lastFlow.append(breakNode)
            self.breakInLoop.pop(currNode)
        # 还原循环头和控制块
        self.lastLoopHead = pastLoopHead
        self.lastControlDepend = pastControlDepend

    # switch
    # __slots__ = ('cond', 'stmt', 'coord', '__weakref__')
    # 类似if
    def visit_Switch(self, node):
        """
            switch 的cond是switch的变量，stmt是case和default的集合
            递归下去访问case和default

        """
        currNode = self.createNewNode("Switch: ", node.cond)
        self.nodeList.append(currNode)
        self.updateControlFlow(currNode)
        pastSwitch = self.lastSwitch
        self.lastSwitch = currNode

        currNode.addControlDepend(self.lastControlDepend)
        pastControlDepend = self.lastControlDepend
        self.lastControlDepend = currNode

        self.breakPosition = "switch"

        self.generic_visit(node.stmt)

        self.breakPosition = ""
        self.lastSwitch = pastSwitch
        self.lastControlDepend = pastControlDepend 


    # __slots__ = ('expr', 'stmts', 'coord', '__weakref__')
    def visit_Case(self, node):
        currNode = self.createNewNode("Case: ", node.expr)
        self.nodeList.append(currNode)
        # 记录switch头
        pastControlFlow = self.lastFlow
        pastControlDepend = self.lastControlDepend

        self.updateControlFlow(currNode)
        currNode.addControlDepend(self.lastControlDepend)
        self.lastControlDepend = currNode


        self.generic_visit(node)

        self.lastFlow = pastControlFlow
        self.lastControlDepend = pastControlDepend


    def visit_Default(self, node):
        currNode = self.createNewNode("Default ", None)
        self.nodeList.append(currNode)
        # 记录switch头
        pastControlFlow = self.lastFlow
        pastControlDepend = self.lastControlDepend

        self.updateControlFlow(currNode)
        currNode.addControlDepend(self.lastControlDepend)
        self.lastControlDepend = currNode

        self.generic_visit(node)

        self.lastFlow = pastControlFlow
        self.lastControlDepend = pastControlDepend

    # break 
    # 自身依赖于上一级，
    def visit_Break(self, node):
        """
            break的说明
            出现break时，break的控制流指向break所属的上一级循环结束后的下一语句
            如果没有下一语句，指向EXIT（todo）
            break出现在循环中或case中
            在循环中，break出现时，将外层循环标记为“内部有break”
            循环可能内部没有break，但是之前有未处理break，所以不能简单的把未处理break划给当前循环。
            内部有break的循环在结束时，将break信息交给【所在循环结束后，应当前往的语句】
            当循环结束时，循环把自己内部的所有未处理break添加到lastFlow

            在case中，
    
        """
        currNode = self.createNewNode(None, node)
        self.nodeList.append(currNode)
        currNode.addControlDepend(self.lastControlDepend)
        if self.breakPosition is "loop":    
            # 所在循环的循环头依赖这个break
            self.lastLoopHead.addControlDepend(currNode)
            # 在self.breakInLoop中，添加这个break
            if self.lastLoopHead not in self.breakInLoop:
                self.breakInLoop[self.lastLoopHead] = []
            self.breakInLoop[self.lastLoopHead].append(currNode)
        elif self.breakPosition is "switch":
            if self.lastSwitch not in self.breakInSwitch:
                self.breakInSwitch[self.lastSwitch] = []
            self.breakInSwitch[self.lastSwitch].append(currNode)
        
        

        # break的控制流从上级而来，break指向循环外第一个节点
        for flowNode in self.lastFlow:
            flowNode.addControlFlow(currNode)


    def visit_Continue(self, node):
        currNode = self.createNewNode(None, node)
        self.nodeList.append(currNode)
        currNode.addControlDepend(self.lastControlDepend)
        # 所在循环的循环头依赖这个continue
        self.lastLoopHead.addControlDepend(currNode)
        # continue的控制流从上级而来，指向所在循环头
        # continue使得条件后的语句不再从continue获得流
        for flowNode in self.lastFlow:
            flowNode.addControlFlow(currNode)   
        currNode.addControlFlow(self.lastLoopHead)


    # FuncCall 语句
    def visit_FuncCall(self, node):
        currNode = self.createNewNode('FuncCall', node)
        self.nodeList.append(currNode)
        currNode.addControlDepend(self.lastControlDepend)
        self.updateControlFlow(currNode)

    # return 语句
    def visit_Return(self, node):
        currNode = self.createNewNode('Return', node)
        self.nodeList.append(currNode)
        currNode.addControlDepend(self.lastControlDepend)
        self.updateControlFlow(currNode)

def getAST(filename):
    ast = parse_file(filename)
    return ast

def generateCDS(filename):
    # get AST
    ast = getAST(filename)
    # use visitor
    cdsv = CDSVisitor()
    cdsv.visit(ast)
    # for node in cdsv.nodeList:
    #    print node

    cds = ControlDependenceSubgraph()

    for node in cdsv.nodeList:
        cds.addNode(node)

    return cds.printDot(True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print generateCDS(sys.argv[1])
    else:
        print("Please provide a filename as argument")
