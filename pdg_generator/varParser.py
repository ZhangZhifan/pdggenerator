# -*- coding: utf-8 -*-  

import sys
sys.path.extend(['.', '..'])
from pycparser import parse_file, c_ast, c_generator, c_parser

class Variable(object):
    """ 变量类，记录变量名称和类型等 """
    name = "";
    vType = "";

    def __init__(self, _n, _t):
        self.name = _n
        self.vType = _t

    def __str__(self):
        return 'Type: '+ self.vType + ' Name: ' + self.name  

    def __repr__(self):
        return '<' + self.__str__() + '>'


class VarVisitor(c_ast.NodeVisitor):
    """ 根据AST节点，获得节点内所使用的所有变量 

        # 对于在赋值语句左侧出现的数组访问，数组属于def，而下标属于use，main用于存储数组，下标放在set中
        # 本visitor不对语句级node做处理
        # 访问到的第一个数组可能是def，放在main中，其余都是使用，放在set中
    """

    var_set = None
    
    var_main = None  
    var_dict = None

    def __init__(self, _var_dict):
        self.var_dict = _var_dict
        self.var_set = set();

    def visit_ID(self, node):
        if node.name and node.name in self.var_dict:
            if not self.var_main:
                self.var_main = self.var_dict[node.name]
            else:
                self.var_set.add(self.var_dict[node.name])

    def visit_ArrayRef(self, node):
        if node.name:
            self.visit(node.name)
        if node.subscript:
            self.visit(node.subscript)


def get_type(decl):
    """ 根据AST的声明节点获得其类型

        @param 声明节点
        @return 字符串 描述其类型
    """
    typ = type(decl)

    if typ == c_ast.TypeDecl:
        return get_type(decl.type)
    elif typ == c_ast.Typename or typ == c_ast.Decl:
        return get_type(decl.type)
    elif typ == c_ast.IdentifierType:
        return ''.join(decl.names)
    elif typ == c_ast.PtrDecl:
        return get_type(decl.type)+'*'
    elif typ == c_ast.ArrayDecl:
        arr = get_type(decl.type)
        if decl.dim: 
            arr += '[%s]' % decl.dim.value

        return arr

    elif typ == c_ast.FuncDecl:
        if decl.args:
            params = [get_type(param) for param in decl.args.params]
            args = ', '.join(params)
        else:
            args = ''

        return (get_type(decl.type)+' function(%s)' % (args))

def get_var_from_decl(decl):
    """ 根据AST的声明节点，获得一个变量对象
    """

    varName = decl.name
    varType = get_type(decl)

    return Variable(varName, varType);

if __name__ == "__main__":
    if len(sys.argv) > 1:
        c_decl  = sys.argv[1]
    else:
        c_decl = "int func(int a, int b);"

    parser = c_parser.CParser()
    node = parser.parse(c_decl, filename='<stdin>')
    if (not isinstance(node, c_ast.FileAST) or
        not isinstance(node.ext[0], c_ast.Decl)
        ):
        print "Not a valid declaration"

    var = get_var_from_decl(node.ext[0])
    print var.name, var.vType