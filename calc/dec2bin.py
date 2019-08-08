while True:
    try:
        number = int(input('Please input decimal number: '))
        print('{:b}'.format(number))
    except:
        break;

