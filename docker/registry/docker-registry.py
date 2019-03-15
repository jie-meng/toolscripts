import sys
import json
import os.path

# definitions 
HOST_IP = "host_ip"

gDefaultConfg = {}

# functions
def scriptPath():
    return os.path.dirname(os.path.abspath(__file__))

def getHostIp():
    global gDefaultConfg
    hostIp = gDefaultConfg.get(HOST_IP) 
    if hostIp == None:
        print('please input host ip:')
        hostIp = input()

    return hostIp

def setDefaultConfig():
    global gDefaultConfg
    print('please input registry host ip:')
    gDefaultConfg[HOST_IP] = input()

    with open(scriptPath() + '/default_config.json', 'w') as conf:
        json.dump(gDefaultConfg, conf, indent = 4)

def loadDefaultConfig():
    global gDefaultConfg
    with open(scriptPath() + '/default_config.json') as conf:
        gDefaultConfg = json.load(conf)

def startRegistry():
    #print('please set registry mapping absolute path:')
    #mappingPath = input()
    #if not os.path.isdir(mappingPath):
    #    print('this path does not exists')
    #    sys.exit(-1) 
    mappingPath = '/opt/data/registry'

    configPath = scriptPath() + '/config.yml'

    os.system('sudo docker run -d -p 5000:5000 -v {0}:/var/lib/registry -v {1}:/etc/docker/registry/config.yml --restart-always -name registry registry:2'.format(mappingPath, configPath))

def checkCatalog():
    os.system('curl http://{0}:5000/v2/_catalog'.format(getHostIp()))

def checkImageTagList():
    hostIp = getHostIp()
    print('please input image name:')
    imageName = input()
    os.system('curl http://{0}:5000/v2/{1}/tags/list'.format(hostIp, imageName))

def initFuncDict(dict):
    dict[0] = setDefaultConfig 
    dict[1] = startRegistry
    dict[2] = checkCatalog
    dict[3] = checkImageTagList

def main():
    loadDefaultConfig()

    print('Please input selection:')
    menu = '0. default config\n'
    menu += '1. start registry\n'
    menu += '2. check catalog\n'
    menu += '3. check image tag list\n'
    print(menu)

    funcDict = dict()
    initFuncDict(funcDict)
    sel = int(input())

    funcDict[sel]()

if __name__ == "__main__":
    main()

