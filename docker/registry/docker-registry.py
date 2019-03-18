import sys
import json
import os.path

# definitions 
PREFIX = 'prefix'
HOST = 'host'
PORT = 'port'

gDefaultConfg = {}

# functions
def scriptPath():
    return os.path.dirname(os.path.abspath(__file__))

def getPort():
    global gDefaultConfg
    port = gDefaultConfg.get(PORT) 
    if port == None:
        print('please input port')
        port = input()

    return port

def getHost():
    global gDefaultConfg
    host = gDefaultConfg.get(HOST)
    if host == None:
        print('please input host')
        host = input()

    return host

def getPrefix():
    global gDefaultConfg
    prefix = gDefaultConfg.get(PREFIX)
    if prefix == None:
        print('is https? (y/n)')
        isHttps = input()
        if isHttps.lower().startswith('y'):
            return 'https'
        else:
            return 'http'

    return prefix 

def getImage():
    print('please input image name')
    return input()

def getImageTag():
    print('please input image:tag')
    return input()

def setDefaultConfig():
    global gDefaultConfg
    print('is https? (y/n)')
    isHttps = input()
    if isHttps.lower().startswith('y'):
        gDefaultConfg[PREFIX] = 'https'
    else:
        gDefaultConfg[PREFIX] = 'http'

    print('please input registry host')
    gDefaultConfg[HOST] = input()

    print('please input registry host port')
    gDefaultConfg[PORT] = int(input())

    with open(scriptPath() + '/default_config.json', 'w') as conf:
        json.dump(gDefaultConfg, conf, indent = 4)

def loadDefaultConfig():
    global gDefaultConfg
    with open(scriptPath() + '/default_config.json') as conf:
        gDefaultConfg = json.load(conf)

def startRegistry():
    mappingPath = '/opt/data/registry'
    configPath = scriptPath() + '/config.yml'

    print('please input port')
    port = int(input())

    # aws ec2 need sudo to use docker
    os.system('sudo docker run -d -p {0}:{0} -v {1}:/var/lib/registry -v {2}:/etc/docker/registry/config.yml --restart=always --name registry registry:latest'.format(port, mappingPath, configPath))

def checkCatalog():
    prefix = getPrefix()
    host = getHost()
    os.system('curl {1}://{0}/v2/_catalog'.format(host, prefix))

def checkImageTagList():
    prefix = getPrefix()
    host = getHost()
    image = getImage()
    os.system('curl {2}://{0}/v2/{1}/tags/list'.format(host, image, prefix))

def tagAndPushImage():
    host = getHost()
    imageTag = getImageTag() 
    os.system('docker tag {1} {0}/{1}'.format(host, imageTag))
    os.system('docker push {0}/{1}'.format(host, imageTag))

def initFuncDict(dict):
    dict[0] = startRegistry
    dict[1] = setDefaultConfig 
    dict[2] = checkCatalog
    dict[3] = checkImageTagList
    dict[4] = tagAndPushImage 

def main():
    loadDefaultConfig()

    print('Please input selection')
    menu = '0. start registry\n'
    menu += '1. default config\n'
    menu += '2. check catalog\n'
    menu += '3. check image tag list\n'
    menu += '4. docker tag and push image\n'
    print(menu)

    funcDict = dict()
    initFuncDict(funcDict)
    sel = int(input())

    funcDict[sel]()

if __name__ == "__main__":
    main()

