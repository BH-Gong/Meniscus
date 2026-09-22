def convert_gcode_to_motor(self, line):
    queue=self.command_queue
    line = line.strip() 
    if not line: return 

    parts = line.split()
    g_command = parts[0]
    
    if g_command == 'G90':
        self.absolute_flag = True
        return
    elif g_command == 'G91':
        self.absolute_flag = False
        return

    case_no,axis_list,port_list=self.port_option()

    if g_command in ['G0', 'G1']:
        params=self.model.parse_gcode_line(line)
        x_par,y_par,z_par, feedrate=self.calculate_parameter(params)

        if feedrate is not None:
            self.command_queue.put(lambda vel=feedrate: self.model.WTB(axis_list[0], port_list[0], 0, vel))
            self.command_queue.put(lambda vel=feedrate: self.model.WTB(axis_list[1], port_list[1], 0, vel))
            self.command_queue.put(lambda vel=feedrate: self.model.WTB(axis_list[2], port_list[2], 0, vel))

        if x_par!=0 and y_par!=0 and z_par!=0:
            if case_no in (1,2,3): ports=[self.ports[0], self.ports[1]] 
            else: ports=[self.ports[1], self.ports[0]] 
            self.model.shift_xyz(axis_list,case_no,x_par,y_par,z_par,ports,0, queue, feedrate, self.absolute_flag)
        
        elif x_par!=0 and y_par!=0 and z_par==0: 
            if case_no in (1,6):
                port = self.ports[0] if case_no==1 else self.ports[1]
                self.command_queue.put(lambda ax=axis_list[0], ay=axis_list[1], p=port, x=x_par, y=y_par, f=feedrate, abs=self.absolute_flag: 
                                        self.model.MPS(ax, ay, p, 0, x, y, f, abs))
            else:
                if case_no in (2,4): ports=[self.ports[0], self.ports[1]]
                else: ports=[self.ports[1], self.ports[0]]
                self.model.shift_xy(axis_list,x_par,y_par,ports,queue, feedrate, self.absolute_flag)

        elif x_par!=0 and y_par==0 and z_par!=0:
            if case_no in (2,5):
                port = self.ports[0] if case_no==2 else self.ports[1]
                self.command_queue.put(lambda ax=axis_list[0], az=axis_list[2], p=port, x=x_par, z=z_par, f=feedrate, abs=self.absolute_flag: 
                                        self.model.MPS(ax, az, p, 0, x, z, f, abs))
            else:
                if case_no in (1,4): ports=[self.ports[0], self.ports[1]]
                else: ports=[self.ports[1], self.ports[0]]
                self.model.shift_xz(axis_list,x_par,z_par,ports,queue, feedrate, self.absolute_flag)

        elif x_par==0 and y_par!=0 and z_par!=0:
            if case_no in (3,4):
                port = self.ports[0] if case_no==3 else self.ports[1]
                self.command_queue.put(lambda ay=axis_list[1], az=axis_list[2], p=port, y=y_par, z=z_par, f=feedrate, abs=self.absolute_flag: 
                                        self.model.MPS(ay, az, p, 0, y, z, f, abs))
            else:
                if case_no in (1,5): ports=[self.ports[0], self.ports[1]]
                else: ports=[self.ports[1], self.ports[0]]
                self.model.shift_yz(axis_list,y_par,z_par,ports,queue, feedrate, self.absolute_flag)

        elif x_par!=0:
            if self.absolute_flag: self.command_queue.put(lambda ax=axis_list[0], p=port_list[0], x=x_par: self.model.APS(ax,0,p,x))
            else: self.command_queue.put(lambda ax=axis_list[0], p=port_list[0], x=x_par: self.model.RPS(ax,0,p,x))
        elif y_par!=0:
            if self.absolute_flag: self.command_queue.put(lambda ay=axis_list[1], p=port_list[1], y=y_par: self.model.APS(ay,0,p,y))
            else: self.command_queue.put(lambda ay=axis_list[1], p=port_list[1], y=y_par: self.model.RPS(ay,0,p,y))
        elif z_par!=0:
            if self.absolute_flag: self.command_queue.put(lambda az=axis_list[2], p=port_list[2], z=z_par: self.model.APS(az,0,p,z))
            else: self.command_queue.put(lambda az=axis_list[2], p=port_list[2], z=z_par: self.model.RPS(az,0,p,z))
    
    elif g_command == 'G04':
        wait_time = 0.0
        for part in parts:
            if part.startswith('P'):
                try: wait_time = float(part[1:]) / 1000.0
                except ValueError: pass
            elif part.startswith('S') or part.startswith('X'):
                try: wait_time = float(part[1:])
                except ValueError: pass

        if wait_time > 0:
            self.command_queue.put(lambda: self.model.wait_all_idle())
            self.command_queue.put(lambda t=wait_time: Logger.log(f"--- Dwell Start: {t}s ---"))
            self.command_queue.put(lambda t=wait_time: time.sleep(t))
            self.command_queue.put(lambda: Logger.log("--- Dwell End ---"))

    elif g_command=='G28':
        self.command_queue.put(lambda axis=axis_list[0], port=port_list[0]: self.model.ORG(axis,0,port))
        self.command_queue.put(lambda axis=axis_list[1], port=port_list[1]: self.model.ORG(axis,0,port))
        self.command_queue.put(lambda axis=axis_list[2], port=port_list[2]: self.model.ORG(axis,0,port))
        self.pos={'X':0, 'Y':0, 'Z':0}
    
    elif g_command=='G98':
        self.command_queue.put(lambda axis=axis_list[3], port=port_list[3]: self.model.RPS(axis,3,port, 80))
    elif g_command=='G99':
        self.command_queue.put(lambda axis=axis_list[3], port=port_list[3]: self.model.RPS(axis,9,port, 200))
