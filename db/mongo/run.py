import sys
import json
import datetime as datetime
import os
import os.path

gConfig = {}

def scriptPath():
    return os.path.dirname(os.path.abspath(__file__))

def loadConfig():
    global gConfig
    with open(scriptPath() + '/config.json') as conf:
        gConfig = json.load(conf)

def quit():
    pass

def dump():
    global gConfig

    os.system('rm -rf {0}/dump/{1}'.format(scriptPath(), gConfig.get('dbname')))
    os.system('cd {0} && mongodump --forceTableScan --host {1}:{2} --authenticationDatabase {3} -u {4} -p {5} -d {3}'\
              .format(scriptPath(), gConfig.get('host'), gConfig.get('port'), gConfig.get('dbname'), gConfig.get('username'), gConfig.get('password')))
    os.system('cd {0}/dump && zip -r {1}.zip {1}'.format(scriptPath(), gConfig.get('dbname')))
    os.system('rm -rf {0}/dump/{1}'.format(scriptPath(), gConfig.get('dbname')))

    timeStr = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    os.system('cd {0}/dump && mv {1}.zip {1}_{2}.zip'.format(scriptPath(), gConfig.get('dbname'), timeStr))

    files = os.listdir('{0}/dump'.format(scriptPath()))
    arr = list(map(lambda x: '{0}/dump/{1}'.format(scriptPath(), x), files))
    arr = list(filter(lambda x: os.path.isfile(x) and x.endswith('zip'), arr))
    arr.sort()

    if len(arr) > 0 and len(arr) > gConfig.get('recordsCount'):
        os.system('rm ' + arr[0])

def restore():
    global gConfig

    os.system('rm -rf {0}/dump/{1}'.format(scriptPath(), gConfig.get('dbname')))

    print('Restore from which record?')
    files = os.listdir('{0}/dump'.format(scriptPath()))
    arr = list(map(lambda x: '{0}/dump/{1}'.format(scriptPath(), x), files))
    arr = list(filter(lambda x: os.path.isfile(x) and x.endswith('zip'), arr))
    arr.sort(reverse = True)
    idx = 1
    for r in arr:
        print('{0}. {1}'.format(idx, arr[idx - 1]))
        idx += 1
    sel = int(input())
    record = os.path.basename(arr[sel - 1])
    print(record)
    os.system('cd {0}/dump && unzip {1}'.format(scriptPath(), record))

    print('Please input class name:')
    className = input()
    os.system('cd {0} && mongorestore --drop --host {1}:{2} -u {3} -p {4} -d {5} -c {6} dump/{5}/{6}.bson'\
              .format(scriptPath(), gConfig.get('host'), gConfig.get('port'), gConfig.get('username'), gConfig.get('password'), gConfig.get('dbname'), className))

    os.system('rm -rf {0}/dump/{1}'.format(scriptPath(), gConfig.get('dbname')))

def restoreAll():
    global gConfig

    print('Restore from which record?')
    files = os.listdir('{0}/dump'.format(scriptPath()))
    arr = list(map(lambda x: '{0}/dump/{1}'.format(scriptPath(), x), files))
    arr = list(filter(lambda x: os.path.isfile(x) and x.endswith('zip'), arr))
    arr.sort(reverse = True)
    idx = 1
    for r in arr:
        print('{0}. {1}'.format(idx, arr[idx - 1]))
        idx += 1
    sel = int(input())
    record = os.path.basename(arr[sel - 1])
    print(record)
    os.system('cd {0}/dump && unzip {1}'.format(scriptPath(), record))
    os.system('cd {0} && mongorestore --drop --host {1}:{2} -u {3} -p {4} -d {5} dump/{5}'.format(scriptPath(), gConfig.get('host'), gConfig.get('port'), gConfig.get('username'), gConfig.get('password'), gConfig.get('dbname')))
    os.system('rm -rf {0}/dump/{1}'.format(scriptPath(), gConfig.get('dbname')))

def initFuncDict(dict):
    dict[0] = ('quit', quit)
    dict[1] = ('dump db', dump)
    dict[2] = ('restore class', restore)
    dict[2] = ('restore whole db', restoreAll)

def pickSelectFromMenu(funcDict):
    print('Please input selection:')
    selections = list(funcDict.items())
    selections.sort()

    for item in selections:
        print('{0}. {1}'.format(item[0], item[1][0]))

    return input()

def main():
    loadConfig()

    funcDict = dict()
    initFuncDict(funcDict)

    sel = int(sys.argv[1]) if len(sys.argv) > 1 else int(pickSelectFromMenu(funcDict))

    print('-----------------------------------------------')
    print('{0}. {1} selected ...'.format(sel, funcDict[sel][0]))
    funcDict[sel][1]()

    print('done.')

if __name__ == "__main__":
    main()
