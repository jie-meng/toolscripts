import os

scriptPath = os.path.dirname(os.path.abspath(__file__))

def readCache():
    try:
        with open('{0}/cache/logcat-tag'.format(scriptPath)) as cache:
            return cache.read().strip()
    except Exception as e:
        return '' 

def writeCache(data):
    with open('{0}/cache/logcat-tag'.format(scriptPath), 'w') as cache:
        cache.write(data)

def main():
    if not os.path.isdir(scriptPath + '/cache'):
        os.mkdir(scriptPath + '/cache')

    args = readCache() 

    if args == '':
        print('please input args:')
        args = input().strip()
    else:
        print('use last args ({0})? y/n'.format(args))
        select = input().lower()
        if not select.startswith('y'):
            print('please input args:')
            args = input().strip()

    writeCache(args)
    os.system('adb logcat -c && adb logcat ' + args)

if __name__ == "__main__":
    main()
