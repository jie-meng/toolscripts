while True:
    try:
        number = input('Please input hex number: ')
        decimal = int(number, 16)
        print('{:b}'.format(decimal))
    except:
        break;

