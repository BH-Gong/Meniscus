all_error_code={'0':'Emergency stop status is detected (not dependent on the driv e conditions)',
        '1':'No STX on the head of the command.',
        '4':'Characters other than specified characters and numbers are included.',
        '5':'No applicable command.',
        '100':'Total number of parameters is incorrect.',
        '101':'Parameter value on 1st parameter is out of range.',
        '102':'Parameter value on 2nd parameter is out of range.',
        '103':'Parameter value on 3rd parameter is out of range.',
        '104':'Parameter value on 4th parameter is out of range.',
        '105':'Parameter value on 5th parameter is out of range.',
        '106':'Parameter value on 6th parameter is out of range.',
        '121':'There is no applicable system No.',
        '130':'Due to system settings being made, commands cannot be executed.',
        '300':'Tried to turn excitation of the axis being driven OFF.',
        '302':'Tried to operate while axes are driving.',
        '303':'Tried to write the present value of the axis during driving',
        '304':('Stopped at CW limit during driving. ','Tried to drive in the CW direction in the CW limit detection state.'),
        
        '305':('Stopped at CCW limit during driving. ','Tried to drive in the CCW direction in the CCW limit detection state.'),
        '306':('Some MPS driving in the limit detection state direction','Tried to conduct MPS driving in the limit detection state direction.'),
        '307':'Both CW and CCW limiters are included.',
        '308':'Tried to move an axis with its excitation OFF.',
        '310':'Coordinates of the movement destination are outside of the manageable range.',
        '313':'Tried to write the system settings of the axis being driven.',
        '314':'The axis being driven was stopped due to emergency stop detection.',
        '325':'The axis being driven was stopped by INCOM due to a command.',
        '500':'Tried to drive iin MPS with the MPI command not issued.',
        '505':'Coordinates of the first axis movement destination are outside of the manageable range.',
        '506':'Coordinates of the second axis movement destination are outside of the manageable range.',
        '511':'The first axis and second axis are the same axis.',
        '605':'Tried to set the start speed in excess of 80% of the maximum speed',
        '700':'Tried to change an incompatible system setting No.',
        '800':'Tried to execute a drive command during emergency stop.',
        '804':'Tried to execute an RST command during drive.'}

class CRUX:
    def __init__(self):
        self.error_codes=all_error_code

    def commun(self,code,connection):
        encode=b'\x02' + code.encode('ascii') + b'\r\n'
        connection.write(encode)
        encoded_response = connection.read_until(b'\n')
        response = encoded_response.decode('ascii')

        response_code=response[1:4]
        self.lookup_error(response_code)

    def get_error_message(self, error_code):
        return self.error_codes.get(error_code, 'Unknown Error')

    def lookup_error(self, error_code):
        error_message=self.get_error_message(error_code)
        length=len(error_code)
        if length==1:
            print('This error is a kind of system error')
            print(error_message)
        elif length!=1 and error_code.startswith('1'):
            print('This error is a kind of parameter error')
            print(error_message)
        elif error_code.startswith('3'):
            print('This error is a kind of drive system error')
            if error_code in ('304', '305', '306'):
                #response_method=self.select_parameter('response_method')
                print(error_message[0])
            else:
                print(error_message)
        elif length!=1 and error_code.startswith('5'):
            print('This error is a kind of MPS command error')
            print(error_message)
        elif error_code.startswith('6'):
            print('This error is a kind of WTB command calculation error')
            print(error_message)
        elif error_code.startswith('7'):
            print('This error is a kind of system setting errors(WSY command errors)')
            print(error_message)
        else:
            print('This is error is other error')
            print(error_message)