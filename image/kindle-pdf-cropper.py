#!/usr/bin/env python3

# Install dependencies on MacOS
#
# brew install imagemagick
# brew install ghostscript
# pip3 install Pillow

import sys
import os
import os.path
from shutil import rmtree
from PIL import Image

def splitPdf2Jpg(imagePath, baseFilename, srcPdf):
    print('Please input density (such as 200, more density more clear text, but cost more time to convert)')
    density = input()

    rmtree(imagePath, True)
    os.mkdir(imagePath)

    os.system('convert -quality 100 -density {3} {0} {1}/{2}-%06d.jpg'.format(srcPdf, imagePath, baseFilename, density))

def mergeJpg2Pdf(imagePath, baseFilename, srcPath):
    os.system('convert {0}/{1}* {2}/{1}-kindle.pdf'.format(imagePath, baseFilename, srcPath))

def testImageWidth(imagePath, baseFilename, srcPath):
    print('Input the offset you want to crop? (Please input 4 numbers, separate with comma: top,right,bottom,left)')
    offsets = input()
    crops = list(map(lambda x: int(x.strip()), offsets.split(',')))
    if len(crops) < 4:
        print('Incorrect input')
        sys.exit(-1)

    print('Which image do you want to test? (input format: 000012, which means the 12th jpg)')
    imageNumber = int(input())
    formatImageNumber = '{0:06d}'.format(imageNumber)

    im = Image.open('{0}/{1}-000000.jpg'.format(imagePath, baseFilename))
    width, height = im.size

    # convert -crop 640x1161+48+0 learn-english-0007.jpg dest.jpg
    os.system('convert -crop {0}x{1}+{2}+{3} {4}/{5}-{6}.jpg {7}/test.jpg'.format(width - crops[3] - crops[1], height - crops[0] - crops[2], crops[3], crops[0], imagePath, baseFilename, formatImageNumber, srcPath))

def resizeAllImagesWidth(imagePath, baseFilename):
    print('Input the offset you want to crop? (Please input 4 numbers, separate with comma: top,right,bottom,left)')
    offsets = input()
    crops = list(map(lambda x: int(x.strip()), offsets.split(',')))
    if len(crops) < 4:
        print('Incorrect input')
        sys.exit(-1)

    im = Image.open('{0}/{1}-000000.jpg'.format(imagePath, baseFilename))
    width, height = im.size

    allFiles = os.listdir(imagePath)
    for file in allFiles:
        os.system('convert -crop {0}x{1}+{2}+{3} {4}/{5} {4}/{5}'.format(width - crops[3] - crops[1], height - crops[0] - crops[2], crops[3], crops[0], imagePath, file))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('please input pdf file as argument')
        sys.exit(-1)

    srcPdf = os.path.realpath(sys.argv[1])
    srcPath = os.path.dirname(srcPdf)
    baseFilename = os.path.splitext(os.path.basename(srcPdf))[0]
    imagePath = '{0}/{1}'.format(os.path.dirname(srcPdf), baseFilename)

    print('Please selection:')
    print('1. splitPdf2Jpg')
    print('2. testImageWidth')
    print('3. resizeAllImagesWidth')
    print('4. mergeJpg2Pdf')

    selection = int(input())
    if selection == 1:
        splitPdf2Jpg(imagePath, baseFilename, srcPdf)
    elif selection == 2:
        testImageWidth(imagePath, baseFilename, srcPath)
    elif selection == 3:
        resizeAllImagesWidth(imagePath, baseFilename)
    elif selection == 4:
        mergeJpg2Pdf(imagePath, baseFilename, srcPath)
    else:
        print('unkown selection')
        sys.exit(-1)

    print('done')
