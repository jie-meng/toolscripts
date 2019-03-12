import os

if __name__  == '__main__':
    print('How many commits to patch?')
    count = int(input())

    os.system('rm patches.zip')
    os.system('git format-patch -{0}'.format(count))
    os.system('zip -r patches.zip *.patch')
    os.system('rm *.patch')
