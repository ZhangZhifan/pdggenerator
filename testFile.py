# -*- coding: utf-8 -*-  
import sys
import os
import commands


def generatePNG(filename, option=None):
    testFilePath = 'testcase/'
    firstName = filename.split('.')[0]
    filename = testFilePath + filename
    cdsDotFileName = testFilePath + firstName + '.cds.dot'
    cdsPngFileName = testFilePath + firstName + '.cds.png'
    print(filename + " > " + cdsDotFileName + " > " + cdsPngFileName)
    os.system('python ./pdg_generator/main.py ' + filename + ' ' + ' '.join(option) + ' > ' + cdsDotFileName)
    os.system('dot -Tpng -o ' + cdsPngFileName + ' ' + cdsDotFileName)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        generatePNG(sys.argv[1], sys.argv[2:])
    else:
        print("Please provide a filename as argument")