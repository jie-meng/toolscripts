import os
import sys
import subprocess

def retrieve_images_from_phone():
    result = subprocess.getoutput('adb shell ls /sdcard/DCIM/Camera')
    items = result.split('\n')
    items.sort(reverse = True)
    items = list(filter(lambda x: x.endswith('jpg') and x.startswith('IMG'), items))

    count = int(input('How many images to retrieve (latest)?\n'))
    images = items[:count]

    for index, image in enumerate(images):
        os.system('adb pull /sdcard/DCIM/Camera/{0} ./{0}'.format(image))

if __name__ == "__main__":
    retrieve_images_from_phone()

