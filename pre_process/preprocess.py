# -*- coding: utf-8 -*-  
import sys
import abc
import copy
sys.path.extend(['.', '..'])
from pycparser import parse_file, c_parser, c_ast, c_generator
from pre_process import m_cgenerator

class PreProcess(object):
    """
    预处理类，使用装饰器
    多个预处理过程可嵌套

    """
    __metaclass__ = abc.ABCMeta

    parent = None

    def __init__(self, parentProcesser=None):
        self.parent = parentProcesser

    def doProcess(self, astNode):
        """
        对AST节点及其子树进行预处理
        @param 要处理的AST节点
        先调用parent进行处理
        """
        if self.parent and isinstance(self.parent, PreProcess):
            self.parent.doProcess(astNode)
        self.realProcess(astNode)    

    @abc.abstractmethod
    def realProcess(self, astNode):
        pass

class DoublePlus2Assign(PreProcess):
    """
        将++，+=等运算符转为一般表达式
    """

    def realProcess(self, astNode):
        # 判断节点类型
        if isinstance(astNode, c_ast.Assignment):
            op = astNode.op
            # 判断赋值是不是+=形式
            if len(op) > 1 and op[-1] is '=':
                newOp = op[:-1]
                newLeft = copy.deepcopy(astNode.lvalue)
                newRight = astNode.rvalue
                newExp = c_ast.BinaryOp(newOp, newLeft, newRight)
                astNode.op = '='
                astNode.rvalue = newExp

class AlwaysCompound(PreProcess):
    """
    结构块强行大括号
    """

    def realProcess(self, astNode):
        typ = type(astNode)

        
        def checkCompound(node):
            """
            检查一个节点是否是大括号的语句块
            """
            return node and not isinstance(node, c_ast.Compound)

        # if 语句
        if typ == c_ast.If:
            if checkCompound(astNode.iftrue):
                newCompound = c_ast.Compound([astNode.iftrue])
                astNode.iftrue = newCompound
            if checkCompound(astNode.iffalse):
                newFCompound = c_ast.Compound([astNode.iffalse])
                astNode.iffalse = newFCompound
        # For
        if typ == c_ast.For:
            if checkCompound(astNode.stmt):
                newCompound = c_ast.Compound([astNode.stmt])
                astNode.stmt = newCompound
        # While
        if typ == c_ast.While:
            if checkCompound(astNode.stmt):
                newCompound = c_ast.Compound([astNode.stmt])
                astNode.stmt = newCompound

class ProcessVisitor(c_ast.NodeVisitor):
    
    processer = None
    def __init__(self, processer=None):
        self.processer = processer


    def generic_visit(self, node):
        """
        generic_visit改为携带两个返回值，类型为([], [])
        分别为“需要在当前节点前插入的节点列表”
              “需要在当前节点后插入的节点列表”
        processer应当返回在处理时需要加入的节点列表

        visit不同种类的节点时，先调用generic_visit
        之后根据节点种类，找到应当插入的位置
            通常应为compound节点

        """
        if self.processer is None:
            return
        self.processer.doProcess(node)
        for c_name, c in node.children():
            self.visit(c)

def test():
    code = """
        void func(void)
        {
            for(i = 0; i < 10; i++) {
                if (a == 5)
                    continue;
                b = b + 1;
            }
        }
    """

    parser = c_parser.CParser()
    ast = parser.parse(code)
    print("Before:")
    ast.show()
    print("==================") 
    
    processer = DoublePlus2Assign(AlwaysCompound())
    pv = ProcessVisitor(processer)
    pv.visit(ast)

    print("==================") 
    print("After:")
    generator = m_cgenerator.PreprocessCGenerator()
    print(generator.visit(ast))

if __name__ == "__main__":
    test()
