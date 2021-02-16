import os

def findIncludeDirRecursively(path, ls = None):
    if ls == None:
        ls = []

    for p in os.listdir(path):
        p = os.path.join(path, p)
        if os.path.isdir(p):
            if p.endswith('include'):
                ls.append(p)
            else:
                findIncludeDirRecursively(p, ls)

    return ls

ls = findIncludeDirRecursively(os.getcwd())
for f in ls:
    print(f)
