while True:
    try:
        number = int(input('Please input decimal number: '))
        print('{:x}'.format(number))
    except:
        break;

