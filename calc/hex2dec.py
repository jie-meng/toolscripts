while True:
    try:
        number = input('Please input hex number: ')
        print(int(number, 16))
    except:
        break;

