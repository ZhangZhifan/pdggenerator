# -*- coding: utf-8 -*-  
import sys
sys.path.extend(['.', '..'])
from pycparser import parse_file, c_ast, c_generator
from graph.pdg_graph import GraphNode, GraphEdge, ControlGraph, NodeType
from pdg_generator.varParser import get_var_from_decl, VarVisitor

class NodeContext(object):

    class CType(object):
        function = 0
        loop = 1
        branch = 2
        switch = 3

    """docstring for NodeContext

        control_head: 当前控制块的头部节点
        control_end: 当前控制块的结束节点
        loop_head: 循环头
        loop_end: 循环结束，用于接受break
        last_nodes: 之前的节点集合，用于从集合到当前节点挂控制流
        control_type: 当前控制块的类型，用于区分break在loop和switch
    """

    control_head = None
    control_end = None
    loop_head = None
    loop_end = None
    last_nodes = []
    control_type = None
    loop_next = None
    switch_end = None


    def __init__(self, _chead=None, _cend=None, _lhead=None, _lend=None, _lnode=None, _lnext=None, _sEnd=None):
        self.control_head = _chead
        self.control_end = _cend
        self.loop_head = _lhead
        self.loop_end = _lend
        self.last_nodes = _lnode if _lnode else []
        self.loop_next = _lnext
        self.switch_end = _sEnd

    def refresh_context_last_node(self, _new_list):
        """ 将context中的最后流节点更新成新的节点列表 """
        self.last_nodes = _new_list
        
    def add_context_last_node(self, _new_node):
        """ 将context中最后流节点列表添加一个新的new_node """
        self.last_nodes.append(_new_node)

    def get_copy():
        ret = NodeContext(self.control_head, self.control_end,
                          self.loop_head, self.loop_end,
                          self.last_nodes, self.control_type,
                          self.loop_next)



class ControlVisitor(c_ast.NodeVisitor):

    _code_generator = c_generator.CGenerator()

    node_context = NodeContext()
    node_list = []
    var_dict = {} # 变量表，存储<变量名，变量对象>的对

    def __init__(self):
        self.node_cnt = 0

        self.start_node = self.create_new_node("ENTRY", None, NodeType.entry)

        # 初始化上下文为start节点
        self.node_context.control_head = self.start_node
        self.node_context.last_node = [self.start_node]

    def create_new_node(self, tag, astNode=None, typ=NodeType.default):
        """ 提供节点tag和对应语法树节点，创建一个PDG节点

            tag作为名字标记/显示在节点上
            如果提供了AST节点，则将以节点为根的子树转成C代码，添加到tag中
        """

        node_tag = '' if not tag else (tag + ' ')
        self.node_cnt += 1
        
        if astNode:
            node_tag += self._code_generator.visit(astNode)

        new_node = GraphNode(self.node_cnt, node_tag)
        new_node.nodeType = typ
        self.node_list.append(new_node)

        return new_node
    
    def get_var_from_name(self, varName):
        if not varName in self.var_dict:
            return None
        return self.var_dict[varName]

    def get_var_set(self, node):
        """ 根据语法树节点获得其包含的变量，返回(主变量, 变量集)的二元组 """

        varset = set()
        mainvar = set()
        if node:
            var_visitor = VarVisitor(self.var_dict)
            var_visitor.visit(node)
            varset = var_visitor.var_set
            mainvar = var_visitor.var_main

        return (mainvar, varset)

    def add_control_flow(self, _from_list, _to):
        """ 将from_list中的节点连接控制流到to """
        if not _to:
            return
        for node in _from_list:
            node.addControlFlow(_to)

    def add_control_dependence(self, _from, _to):
        """ 连接from到to的控制依赖 """
        if not _from or not _to:
            return
        _from.addControlDepend(_to)

    def visit_Decl(self, node):
        """ 处理声明语句

            __slots__ = ('name', 'quals', 'storage', 'funcspec', 'type', 'init', 'bitsize', 'coord', '__weakref__')
            是最基本的处理流程，即：
                创建节点，
                计算变量
                从控制块连接控制依赖
                从上一句或控制块到当前的控制流
                X: 递归子节点
        """

        curr_node = self.create_new_node("Decl", node, NodeType.decl)

        self.add_control_flow(self.node_context.last_nodes, curr_node)
        self.node_context.refresh_context_last_node([curr_node])
        
        self.add_control_dependence(self.node_context.control_head, curr_node)

        # 将声明的变量加入符号表
        var = get_var_from_decl(node)
        if not var.name in self.var_dict: 
            self.var_dict[var.name] = var

        # 更新def和use
        defvar = self.get_var_from_name(node.name)
        # 获得声明初始化部分所使用到的变量列表
        # main可能为None
        (mainvar, usevarset) = self.get_var_set(node.init)
        curr_node.add_def_var(defvar)
        if mainvar:
            curr_node.add_use_var(mainvar)
        for var in usevarset: 
            curr_node.add_use_var(var)

        return curr_node

    def visit_Assignment(self, node):
        """ 赋值语句

            Assignment: [op, lvalue*, rvalue*]
            流程同声明语句
        """
        curr_node = self.create_new_node("Assign", node, NodeType.assign)
        
        self.add_control_flow(self.node_context.last_nodes, curr_node)
        self.node_context.refresh_context_last_node([curr_node])

        self.add_control_dependence(self.node_context.control_head, curr_node)

        # 更新def和use
        # 左值被def，如果是数组访问的话，数组头被def，其他被use
        # 右值被use
        (leftmain, leftset) = self.get_var_set(node.lvalue)
        (rightmain, rightset) = self.get_var_set(node.rvalue)
        # 左值的main被def，其他如果有的话，被use
        curr_node.add_def_var(leftmain)
        # 右值的main被use
        curr_node.add_use_var(rightmain)
        # 其余的被use
        for var in leftset | rightset:
            curr_node.add_use_var(var)

        return curr_node
        
    def visit_FuncDef(self, node):
        """ 函数声明语句

            __slots__ = ('decl', 'param_decls', 'body', 'coord', '__weakref__')
            需要保存当前context，创建新的context替代
            结束后还原context
        """

        curr_node = self.create_new_node("Function", node.decl, NodeType.control)
        end_node = self.create_new_node("Function End", None, NodeType.end)
        # self.add_control_dependence(curr_node, end_node)

        # 更新控制流和控制依赖
        self.add_control_flow(self.node_context.last_nodes, curr_node)
        self.add_control_dependence(self.node_context.control_head, curr_node)

        # 函数使用全新的上下文
        new_context = NodeContext(curr_node, end_node)
        new_context.refresh_context_last_node([curr_node])
        new_context.control_type = NodeContext.CType.function

        # 保存当前上下文，切换到新的上下文
        saved_context = self.node_context
        self.node_context = new_context

        # 递归子节点
        self.generic_visit(node.body)

        # 子节点完成，将子节点的流末端节点引到函数结束节点
        self.add_control_flow(self.node_context.last_nodes, end_node)

        # 还原上下文
        self.node_context = saved_context
        self.node_context.refresh_context_last_node([end_node])

        return curr_node

    def visit_While(self, node):
        """ while节点

            循环头的变量全部为use
         """

        curr_node = self.create_new_node("While", node.cond, NodeType.control)
        end_node = self.create_new_node("While End", None, NodeType.end)
        #self.add_control_dependence(curr_node, end_node)

        #循环最后，控制流从循环头指向循环结束节点
        self.add_control_flow([curr_node], end_node)

        # 挂控制流和控制依赖
        self.add_control_flow(self.node_context.last_nodes, curr_node)
        self.add_control_dependence(self.node_context.control_head, curr_node)

        # 创建新的上下文
        new_context = NodeContext(curr_node, end_node, curr_node, end_node, [curr_node])
        new_context.control_type = NodeContext.CType.loop
        new_context.switch_end = self.node_context.switch_end

        # 替换上下文
        saved_context = self.node_context
        self.node_context = new_context

        # 递归
        self.generic_visit(node)

        self.add_control_flow(self.node_context.last_nodes, curr_node)

        #还原上下文
        self.node_context = saved_context
        self.node_context.refresh_context_last_node([end_node])

        # while的变量全部是使用
        mainvar, varset = self.get_var_set(node.cond)
        curr_node.add_use_var(mainvar)
        for var in varset:
            curr_node.add_use_var(var)

        return curr_node

    def visit_If(self, node):
        """ if语句 


        """

        curr_node = self.create_new_node("If", node.cond, NodeType.control)
        end_node = self.create_new_node("If End", None, NodeType.end)

        # 挂控制流和控制依赖
        self.add_control_flow(self.node_context.last_nodes, curr_node)
        self.add_control_dependence(self.node_context.control_head, curr_node)

        # 创建新的上下文
        # if更新control的head和end，但是保持现有的loop的head和end
        new_context = NodeContext(curr_node, end_node, 
                                  self.node_context.loop_head,
                                  self.node_context.loop_end,
                                  self.node_context.last_nodes,
                                  self.node_context.loop_next,
                                  self.node_context.switch_end)
        new_context.refresh_context_last_node([curr_node])
        new_context.control_type = self.node_context.control_type

        saved_context = self.node_context
        self.node_context = new_context

        # 递归true分支
        self.visit(node.iftrue)
        self.add_control_flow(self.node_context.last_nodes, end_node)

        if node.iffalse :
            # 重建当前if的context给false分支用
            false_context = NodeContext(curr_node, end_node, 
                                  saved_context.loop_head,
                                  saved_context.loop_end,
                                  saved_context.last_nodes,
                                  saved_context.loop_next)
            false_context.refresh_context_last_node([curr_node])
            false_context.control_type = saved_context.control_type

            self.node_context = false_context
            self.visit(node.iffalse)
            self.add_control_flow(self.node_context.last_nodes, end_node)
        else:
            # 如果if没有else，则存在从if直接到后面的控制流，隐式else
            self.add_control_flow([curr_node], end_node)

        self.node_context = saved_context
        self.node_context.refresh_context_last_node([end_node])

        # if的变量全部是使用
        mainvar, varset = self.get_var_set(node.cond)
        curr_node.add_use_var(mainvar)
        for var in varset:
            curr_node.add_use_var(var)

        return curr_node

        return curr_node

    def visit_For(self, node):
        """ For 语句

            __slots__ = ('init', 'cond', 'next', 'stmt', 'coord', '__weakref__')
            init改在for前，next追加在stmt后，cond同while，所有语句依赖cond
        """

        self.visit(node.init)

        curr_node = self.create_new_node("For", node.cond, NodeType.control)
        end_node = self.create_new_node("For End", None, NodeType.end)
        
        # continue target用于接收循环内的continue
        # 所有continue的控制流指向这里，再指向for的next语句
        continueTarget = self.create_new_node("Continue Target", None, NodeType.end)

        self.add_control_flow(self.node_context.last_nodes, curr_node)
        self.add_control_dependence(self.node_context.control_head, curr_node)
        #循环最后，控制流从循环头指向循环结束节点
        self.add_control_flow([curr_node], end_node)

        # 新的上下文
        # 记录for的next节点，供内部的continue连接
        new_context = NodeContext(curr_node, end_node, curr_node, end_node, [curr_node])
        new_context.control_type = NodeContext.CType.loop
        new_context.loop_next = continueTarget
        new_context.switch_end = self.node_context.switch_end

        saved_context = self.node_context
        self.node_context = new_context

        # 递归
        self.visit(node.stmt)

        # 控制流指向next节点
        self.add_control_flow(self.node_context.last_nodes, continueTarget)
        # 新控制流从continuetarget开始
        self.node_context.refresh_context_last_node([continueTarget])
        # 递归访问next节点
        next_node = self.visit(node.next)
        # next节点控制流回到循环头
        self.add_control_flow(self.node_context.last_nodes, curr_node)
        # next节点依赖于循环头
        # self.add_control_dependence(curr_node, next_node)

        # 还原上下文
        self.node_context = saved_context;
        self.node_context.refresh_context_last_node([end_node])

        # for的变量全部是使用
        mainvar, varset = self.get_var_set(node.cond)
        curr_node.add_use_var(mainvar)
        for var in varset:
            curr_node.add_use_var(var)

        return curr_node


    # switch
    # 类似if
    def visit_Switch(self, node):
        """
            switch 的cond是switch的变量，stmt是case和default的集合
            递归下去访问case和default

            Switch: [cond*, stmt*]
        """

        curr_node = self.create_new_node("Switch", node.cond, NodeType.control)
        end_node = self.create_new_node("Switch End", None, NodeType.end)

        # 挂控制流和控制依赖
        self.add_control_flow(self.node_context.last_nodes, curr_node)
        self.add_control_dependence(self.node_context.control_head, curr_node)
        # 创建新的上下文
        # switch更新control的head和end，但是保持现有的loop的head和end
        # switch更新controltype
        new_context = NodeContext(curr_node, end_node, 
                                  self.node_context.loop_head,
                                  self.node_context.loop_end,
                                  self.node_context.last_nodes,
                                  self.node_context.loop_next)
        new_context.refresh_context_last_node([curr_node])
        new_context.switch_end = end_node
        new_context.control_type = NodeContext.CType.switch

        saved_context = self.node_context
        self.node_context = new_context

        # 递归子节点
        self.visit(node.stmt)

        # 子节点的控制流挂到end由case语句完成，switch不参与，只挂最后一个
        self.add_control_flow(self.node_context.last_nodes, end_node)
        # 还原上下文
        self.node_context = saved_context
        self.node_context.refresh_context_last_node([end_node])

        # def和use
        # switch的变量全部是使用
        mainvar, varset = self.get_var_set(node.cond)
        curr_node.add_use_var(mainvar)
        for var in varset:
            curr_node.add_use_var(var)

        return curr_node

    # __slots__ = ('expr', 'stmts', 'coord', '__weakref__')
    def visit_Case(self, node):
        """ Case语句

            [expr*, stmts**]
            expr是case的node
            递归每个stmt
            如果case里有break，则控制流指向switch末尾，否则指向下一个case
        """

        curr_node = self.create_new_node("Case", node.expr, NodeType.control)
        end_node = self.create_new_node("Case End", None, NodeType.end)
        # 挂控制流，这里的控制流可能是上一个case的end
        # 或者上一个case有break，则控制流是switch头
        self.add_control_flow(self.node_context.last_nodes, curr_node)
        self.add_control_dependence(self.node_context.control_head, curr_node)

        # 创建新的上下文
        # case更新control的head和end，但是保持现有的loop的head和end
        # case保持controltype
        new_context = NodeContext(curr_node, end_node, 
                                  self.node_context.loop_head,
                                  self.node_context.loop_end,
                                  self.node_context.last_nodes,
                                  self.node_context.loop_next,
                                  self.node_context.switch_end)
        new_context.refresh_context_last_node([curr_node])
        new_context.control_type = self.node_context.control_type

        saved_context = self.node_context
        self.node_context = new_context

        hasBreak = False
        
        # 递归每个stmt，
        for child in node.stmts:
            res = self.visit(child)
            if res and res == True:
                hasBreak = True

        # 如果stmt里有直接的break（不在任何控制快中)
        # 则下一个case不获得控制流
        # 否则下一个case【可能】获得控制流，则case的end指向下一个case
        self.add_control_flow(self.node_context.last_nodes, end_node)
        # 还原上下文
        self.node_context = saved_context
        self.node_context.refresh_context_last_node([end_node])

        # def和use
        # case的变量全部是使用
        mainvar, varset = self.get_var_set(node.expr)
        curr_node.add_use_var(mainvar)
        for var in varset:
            curr_node.add_use_var(var)

        return curr_node


    def visit_Default(self, node):
        """ Default语句

            [stmts**]
            基本和case一样
        """

        curr_node = self.create_new_node("Default", None, NodeType.control)
        end_node = self.create_new_node("Default End", None, NodeType.end)
        # 挂控制流，这里的控制流可能是上一个case的end
        # 或者上一个case有break，则控制流是switch头
        self.add_control_flow(self.node_context.last_nodes, curr_node)
        self.add_control_dependence(self.node_context.control_head, curr_node)

        # 创建新的上下文
        # case更新control的head和end，但是保持现有的loop的head和end
        # case保持controltype
        new_context = NodeContext(curr_node, end_node, 
                                  self.node_context.loop_head,
                                  self.node_context.loop_end,
                                  self.node_context.last_nodes,
                                  self.node_context.loop_next,
                                  self.node_context.switch_end)
        new_context.refresh_context_last_node([curr_node])
        new_context.control_type = self.node_context.control_type

        saved_context = self.node_context
        self.node_context = new_context

        hasBreak = False
        
        # 递归每个stmt，
        for child in node.stmts:
            res = self.visit(child)
            if res and res == True:
                hasBreak = True

        # 如果stmt里有直接的break（不在任何控制快中)
        # 则下一个case不获得控制流
        # 否则下一个case【可能】获得控制流，则case的end指向下一个case
        self.add_control_flow(self.node_context.last_nodes, end_node)
        # 还原上下文
        self.node_context = saved_context
        self.node_context.refresh_context_last_node([end_node])

        return curr_node


    # break 
    # 自身依赖于上一级，
    def visit_Break(self, node):
        """ 处理break语句

            对于循环中的break
            循环头依赖这个break
            break控制流从上级来，指向循环end
            同样break清空last_nodes
        """

        curr_node = self.create_new_node("Break", node, NodeType.control)
        # 循环中的break
        if self.node_context.control_type is NodeContext.CType.loop:
            self.add_control_flow(self.node_context.last_nodes, curr_node)
            self.add_control_flow([curr_node], self.node_context.loop_end)

            self.add_control_dependence(curr_node, self.node_context.loop_head)
            self.add_control_dependence(self.node_context.control_head, curr_node)

            self.node_context.refresh_context_last_node([])

        # switch中的break
        if self.node_context.control_type is NodeContext.CType.switch:
            self.add_control_flow(self.node_context.last_nodes, curr_node)
            self.add_control_flow([curr_node], self.node_context.switch_end)

            self.add_control_dependence(self.node_context.control_head, curr_node)

            self.node_context.refresh_context_last_node([])

        return True

    def visit_Continue(self, node):
        """ continue （只出现在循环中）


            循环头依赖这个continue
            continue的控制流从上级而来，指向所在循环头
            continue使得条件后的语句不再从continue获得流
            所以continue应当清空last_nodes
        """

        curr_node = self.create_new_node("Continue", node, NodeType.control)

        self.add_control_flow(self.node_context.last_nodes, curr_node)
        if self.node_context.loop_next:
            self.add_control_flow([curr_node], self.node_context.loop_next)
        else:
            self.add_control_flow([curr_node], self.node_context.loop_head)
        
        self.add_control_dependence(curr_node, self.node_context.loop_head)
        self.add_control_dependence(self.node_context.control_head, curr_node)

        self.node_context.refresh_context_last_node([])

    # FuncCall 语句
    def visit_FuncCall(self, node):
        """ FuncCall: [name*, args*] """

        curr_node = self.create_new_node(None, node, NodeType.call)
        self.add_control_flow(self.node_context.last_nodes, curr_node)
        self.node_context.refresh_context_last_node([curr_node])

        self.add_control_dependence(self.node_context.control_head, curr_node)

        # 对于函数，只认为scanf会对变量有写操作
        mainvar, varset = self.get_var_set(node.args)
        if (node.name.name == 'scanf'):
            curr_node.add_def_var(mainvar)
            for var in varset:
                curr_node.add_def_var(var)
        else:
        # funcall的变量全部是使用
            curr_node.add_use_var(mainvar)
            for var in varset:
                curr_node.add_use_var(var)

        return curr_node

    # return 语句
    def visit_Return(self, node):
        
        curr_node = self.create_new_node(None, node, NodeType.control)
        self.add_control_flow(self.node_context.last_nodes, curr_node)
        self.add_control_dependence(self.node_context.control_head, curr_node)

def get_ast(filename):
    ast = parse_file(filename)
    return ast

def getControlGraphFromVisitor(cdsv):
    cg = ControlGraph(cdsv.node_list, cdsv.var_dict)
    return cg

def generate_control_graph_dot(filename, debugmode=False):
    
    graph = generate_control_graph(filename)

    ret = graph.printAllControlGraphDot()

    if debugmode:
        print "var_dict"
        print cdsv.var_dict
        for node in cdsv.node_list:
            if len(node.defVars) or len(node.useVars):
                ret += 'Node: ' + node.content + '\n'
                ret += 'def: ' + node.get_def_list() + '\n'
                ret += 'use: ' + node.get_use_list() + '\n'

    return ret

def generate_control_graph(filename):
    # get AST
    ast = get_ast(filename)
    # use visitor
    cdsv = ControlVisitor()
    cdsv.visit(ast)

    graph = getControlGraphFromVisitor(cdsv)

    return graph

if __name__ == "__main__":
    if len(sys.argv) > 2:
        print generate_control_graph_dot(sys.argv[1], True)
    elif len(sys.argv) > 1:
        print generate_control_graph_dot(sys.argv[1])
    else:
        print("Please provide a filename as argument")