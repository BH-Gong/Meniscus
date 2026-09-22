import math
import threading
import time

from core import utils
from core import shared_data

class CodeGenerator():
    def __init__(self, logger, crux):
        super().__init__()
        self.pos = {}
        self.logger = logger
        self.crux = crux
        self.lock = threading.Lock()

    def convert_gcode_to_motor(self, line):
        with self.lock:
            return self._convert_gcode_to_motor(line)

    def _convert_gcode_to_motor(self, line):
        self.pos = shared_data.pos

        if not line or line.startswith(';') or line.startswith('('): 
            return

        line = line.strip() 
        if not line: return 

        parts = line.split()
        g_command = parts[0].upper()
        
        if g_command == 'G90':
            shared_data.absolute_flag = True

        elif g_command == 'G91':
            shared_data.absolute_flag = False

        elif g_command in ['G0', 'G1']:
            params = shared_data.model.parse_gcode_line(line)
            x_par, y_par, z_par, feedrate = utils.calculate_parameter(params)
            print(
                f"[PARAM] line={line} | "
                f"X={x_par}, Y={y_par}, Z={z_par}, F={feedrate}, "
                f"ABS={shared_data.absolute_flag}"
            )
            self.xyz_movement(x_par, y_par, z_par, feedrate, shared_data.absolute_flag, shared_data.command_queue)
            
        elif g_command == 'G04':
            # Dwell time
            # Yet to ready.
            pass

        elif g_command=='G28':
            # Auto Home
            # Yet to ready.
            pass

        else:
            # self.logger.error(f"Unknown : \'{line}\'")
            self.logger.error(f"Unknown command : {repr(line)} (Parsed command: {repr(g_command)})")

    ## 3D motion code ###############################################################################
    def xyz_movement(self, pos_x, pos_y, pos_z, feedrate, abs_flag, queue):
        if shared_data.info_dict == {}:
            self.logger.error('There is no port-axis information.')
            return

        print(
            f"xyz_movement: X={pos_x}, Y={pos_y}, Z={pos_z}, "
            f"F={feedrate}, ABS={abs_flag}"
        )
        
        pos_X, pos_Y, pos_Z = pos_x, pos_y, pos_z
        vel_X, vel_Y, vel_Z = utils.cal_vel(shared_data.pos, pos_x, pos_y, pos_z, feedrate, abs_flag)

        print(
            f"[VEL] X={vel_X}, Y={vel_Y}, Z={vel_Z}"
        )


        if abs_flag:
            abs_num = 0
        else:
            abs_num = 1

        # 1
        code_vx, port_vx = [(self.WTB_cg(shared_data.info_dict['axis_BDX'], 0, vel_X))], [shared_data.info_dict['port_BDX']]
        # 2
        code_vy, port_vy = [(self.WTB_cg(shared_data.info_dict['axis_BDY'], 0, vel_Y))], [shared_data.info_dict['port_BDY']]
        # 3
        code_vz, port_vz = [(self.WTB_cg(shared_data.info_dict['axis_BDZ'], 0, vel_Z))], [shared_data.info_dict['port_BDZ']]

        print(
            f"[WTB] "
            f"X={code_vx}, "
            f"Y={code_vy}, "
            f"Z={code_vz}"
        )

        if utils.is_grouped('port_BDX', 'port_BDY'):
            grouped_ax1, grouped_port1 = shared_data.info_dict['axis_BDX'], shared_data.info_dict['port_BDX']
            grouped_ax2, grouped_port2 = shared_data.info_dict['axis_BDY'], shared_data.info_dict['port_BDY']
            single, single_port = shared_data.info_dict['axis_BDZ'], shared_data.info_dict['port_BDZ']
            group_pos1, group_pos2, single_pos = pos_X, pos_Y, pos_Z
            
        elif utils.is_grouped('port_BDX', 'port_BDZ'):
            grouped_ax1, grouped_port1 = shared_data.info_dict['axis_BDX'], shared_data.info_dict['port_BDX']
            grouped_ax2, grouped_port2 = shared_data.info_dict['axis_BDZ'], shared_data.info_dict['port_BDZ']
            single, single_port = shared_data.info_dict['axis_BDY'], shared_data.info_dict['port_BDY']
            group_pos1, group_pos2, single_pos = pos_X, pos_Z, pos_Y

        elif utils.is_grouped('port_BDY', 'port_BDZ'):
            grouped_ax1, grouped_port1 = shared_data.info_dict['axis_BDY'], shared_data.info_dict['port_BDY']
            grouped_ax2, grouped_port2 = shared_data.info_dict['axis_BDZ'], shared_data.info_dict['port_BDZ']
            single, single_port = shared_data.info_dict['axis_BDX'], shared_data.info_dict['port_BDX']
            group_pos1, group_pos2, single_pos = pos_Y, pos_Z, pos_X

        else:
            grouped_ax1 = grouped_ax2 = None

        # 4
        if grouped_ax1 == None or grouped_ax2 == None:
            # 4-1
            code_pre1, port_pre1, code_pre2, port_pre2 = None, None, None, None

            # 4-2
            if abs_flag:
                code_pack = [self.APS_cg(shared_data.info_dict['axis_BDX'], 0, pos_X), 
                             self.APS_cg(shared_data.info_dict['axis_BDY'], 0, pos_Y), 
                             self.APS_cg(shared_data.info_dict['axis_BDZ'], 0, pos_Z)]
                port_pack = [shared_data.info_dict['port_BDX'],
                             shared_data.info_dict['port_BDY'],
                             shared_data.info_dict['port_BDZ']]
            else:
                code_pack = [self.RPS_cg(shared_data.info_dict['axis_BDX'], 0, pos_X), 
                             self.RPS_cg(shared_data.info_dict['axis_BDY'], 0, pos_Y), 
                             self.RPS_cg(shared_data.info_dict['axis_BDZ'], 0, pos_Z)]
                port_pack = [shared_data.info_dict['port_BDX'],
                             shared_data.info_dict['port_BDY'],
                             shared_data.info_dict['port_BDZ']]
                
            # 5
            rdp_pack = [self.RDP_cg(shared_data.info_dict['axis_BDY']), 
                        self.RDP_cg(shared_data.info_dict['axis_BDX']),
                        self.RDP_cg(shared_data.info_dict['axis_BDZ'])]
            rdp_port_pack = [shared_data.info_dict['port_BDX'],
                             shared_data.info_dict['port_BDY'],
                             shared_data.info_dict['port_BDZ']]

            print(
                f"[PACK] "
                f"code_pack={code_pack}, port_pack={port_pack} | "
                f"rdp_pack={rdp_pack}, rdp_port_pack={rdp_port_pack}"
            )
            
        else:
            if grouped_port1 != grouped_port2:
                self.logger.error('Grouped ports are not same.')
                return
            
            # 4-1
            code_pre1, port_pre1 = [self.MPI_cg(grouped_ax1, abs_num, 0)], [grouped_port1]
            code_pre2, port_pre2 = [self.MPI_cg(grouped_ax2, abs_num, 0)], [grouped_port2]

            # 4-2
            if abs_flag:
                code_pack = [self.MPS_cg(grouped_ax1, group_pos1, grouped_ax2, group_pos2),
                             self.APS_cg(single, 0, single_pos)]
                port_pack = [grouped_port1, single_port]
            else:
                code_pack = [self.MPS_cg(grouped_ax1, group_pos1, grouped_ax2, group_pos2),
                             self.RPS_cg(single, 0, single_pos)]
                port_pack = [grouped_port1, single_port]

            # 5
            rdp_pack = [self.RDP_cg(grouped_ax1), self.RDP_cg(single)]
            rdp_port_pack = [grouped_port1, single_port]
            rdp_code = [self.RDP_cg(grouped_ax2)]
            rdp_port = [grouped_port2]

            print(
                f"[PACK2] "
                f"rdp_code={rdp_code}, rdp_port={rdp_port}"
            )

        # 1
        print(f"[QUEUE-X] codes={code_vx}, ports={port_vx}")
        queue.put(lambda codes=code_vx, ports=port_vx: self.crux.send_signals(codes, ports))
        # 2
        print(f"[QUEUE-Y] codes={code_vy}, ports={port_vy}")
        queue.put(lambda codes=code_vy, ports=port_vy: self.crux.send_signals(codes, ports))
        # 3
        print(f"[QUEUE-Z] codes={code_vz}, ports={port_vz}")
        queue.put(lambda codes=code_vz, ports=port_vz: self.crux.send_signals(codes, ports))
        # 4-1
        if code_pre1 is not None:
            print(f"[QUEUE-PRE1] codes={code_pre1}, ports={port_pre1}")
            queue.put(lambda codes=code_pre1, ports=port_pre1: self.crux.send_signals(codes, ports))
            print(f"[QUEUE-PRE2] codes={code_pre2}, ports={port_pre2}")
            queue.put(lambda codes=code_pre2, ports=port_pre2: self.crux.send_signals(codes, ports))
        # 4-2
        print(f"[QUEUE-PACK] codes={code_pack}, ports={port_pack}")
        queue.put(lambda codes=code_pack, ports=port_pack: self.crux.send_signals(codes, ports))
        # 5
        print(f"[QUEUE-RDP1] codes={rdp_pack}, ports={rdp_port_pack}")
        queue.put(lambda codes=rdp_pack, ports=rdp_port_pack: self.crux.send_signals(codes, ports))
        print(f"[QUEUE-RDP2] codes={rdp_code}, ports={rdp_port}")
        queue.put(lambda codes=rdp_code, ports=rdp_port: self.crux.send_signals(codes, ports))
        
        if abs_flag:
            self.pos={'pos_x':pos_x, 'pos_y':pos_y, 'pos_z':pos_z}
        else:
            self.pos={'pos_x':self.pos['pos_x'] + pos_x,
                      'pos_y':self.pos['pos_y'] + pos_y,
                      'pos_z':self.pos['pos_z'] + pos_z}
            
        shared_data.pos = self.pos
        print(f"[XYZ END] shared_data.pos={shared_data.pos}")


    ## code generator ####################################################################################
    def APS_cg(self, axis, speedtable, pos_pulse):
        code = 'APS%d/%d/%d/%d' %(axis, speedtable, pos_pulse, 0)

        return code
    
    def RPS_cg(self, axis, speedtable, pos_pulse):
        code = 'RPS%d/%d/%d/%d' %(axis, speedtable, pos_pulse, 0)

        return code
    
    def MPI_cg(self, axis, drive_type, speedtable):
        code = 'MPI%d/%d/%d' %(axis, drive_type, speedtable)

        return code

    def MPS_cg(self, axis1, pos1, axis2, pos2):
        code = 'MPS%d/%d/%d/%d/%d' %(axis1, pos1, axis2, pos2, 0)

        return code

    def RDP_cg(self, axis):
        code = 'RDP%d' %axis

        return code

    def WTB_cg(self, axis, speedtable_No, vel):
        code='WTB%d/%d/%d/%d/%d/%d' %(axis, speedtable_No, vel, vel, 1, 1)

        return code
    
    def ORG_cg(self, axis, speedtable):
        code = 'ORG%d/%d/%d' %(axis, speedtable, 0)

        return code

    def STP_cg(self, axis):
        code = 'STP%d/%d' %(axis, 0)

        return code