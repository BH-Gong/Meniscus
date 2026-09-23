# Variations
active_flag = True
absolute_flag = True
show_hidden_logs = False

connections = []
ports = []
model = None

worker_thread = None
stop_event = None
command_queue = None

pos = {'pos_x':0, 'pos_y':0, 'pos_z':0, 'pos_tx':0, 'pos_ty':0}
nz_pos = {'pos_x':0, 'pos_y':0, 'pos_z':0, 'pos_r':0}

port_axis_mapping = {}
#############################
# port_axis_mapping = {
#     com(int): {'name': str, 'axis': str, 'combo_value': str}, {name:str(ex.com35), 'axis': int, 'combo_value': str}}
#     ...
#     }
#############################

info_dict = {}
#############################
# info_dict = {
#     'axis_BDX'(str): axis_bdx(int), 
#     ...
#     'port_BDX'(str): port_bdx(str),
#     ...
#     }
#############################

port_group = {}
#############################
# port_group = {
#     'COM3'(str): ['BDX'(STR)],
#     ...
#     }
#############################

port_lock = {}

SENTINEL = object()