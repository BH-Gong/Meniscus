response = "C\tIDN\tCRUX-D\t1000"

parts = response.rstrip('\r\n').split('\t')
id_code = parts[0]
command_code = parts[1][:3]
a = parts[1][-1:]
params = parts[2:]

if a is int:
    params.insert(0, a)

if command_code == 'IDN':
    model_name = params[0]
    version = int(params[1]) / 1000

print(params)