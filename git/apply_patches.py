import os.path

def findFiles(path, pred = None, ls = None):
    if ls == None:
        ls = []

    for p in os.listdir(path):
        p = os.path.join(path, p)
        if os.path.isfile(p):
            if not pred or pred(p):
                ls.append(p)

    return ls

if __name__  == '__main__':
    os.system('unzip patches.zip')

    ls = findFiles(os.getcwd(), lambda x: x.endswith('.patch'))
    ls.sort()
    for f in ls:
        os.system('git am < ' + f)

    os.system('rm *.patch')
    os.system('rm patches.zip')

