import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import threading
import time
import numpy as np

# FLIR Spinnaker SDK (PySpin) 로드 시도
try:
    import PySpin
    PYSPIN_AVAILABLE = True
except ImportError:
    PYSPIN_AVAILABLE = False

class CameraGUI:
    def __init__(self, container, print_message_func):
        self.container = container
        self.print_message = print_message_func
        self.container.title("Dual Camera Monitoring")
        self.container.configure(bg='#222222')
        
        # 전체화면 설정
        self.container.attributes("-fullscreen", True)
        self.container.bind("<Escape>", self.close_window)

        # 메인 레이아웃 구성
        self.main_frame = tk.Frame(self.container, bg='#222222')
        self.main_frame.pack(fill='both', expand=True)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # 닫기 버튼
        close_btn = tk.Button(self.container, text="X Close", command=self.close_window, 
                              bg='red', fg='white', font=('Times New Roman', 14, 'bold'))
        close_btn.place(relx=0.98, rely=0.01, anchor='ne')

        # [왼쪽] Basler 카메라 (OpenCV 기반, 기본 Index=1로 설정하여 노트북 웹캠 회피)
        self.cam_left = OpenCVCameraModule(self.main_frame, "Basler (Top View)", cam_index=1)
        self.cam_left.frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)

        # [오른쪽] FLIR 카메라 (PySpin 설치 여부에 따라 전용 모듈 또는 OpenCV 폴백)
        if PYSPIN_AVAILABLE:
            self.print_message("FLIR Spinnaker SDK (PySpin) Detected. Using Native API.")
            self.cam_right = FLIRCameraModule(self.main_frame, "FLIR (Nozzle View)")
        else:
            self.print_message("PySpin Not Found. Fallback to OpenCV for right camera.")
            self.cam_right = OpenCVCameraModule(self.main_frame, "FLIR (Nozzle View)", cam_index=2)
            
        self.cam_right.frame.grid(row=0, column=1, sticky='nsew', padx=10, pady=10)
        self.print_message("Camera Monitoring Started.")

    def close_window(self, event=None):
        self.cam_left.stop()
        self.cam_right.stop()
        self.container.destroy()
        self.print_message("Camera Monitoring Closed.")


class OpenCVCameraModule:
    """OpenCV를 사용하는 범용 카메라 모듈 (Basler 및 웹캠용)"""
    def __init__(self, parent, title, cam_index):
        self.frame = tk.Frame(parent, bg='#333333', bd=2, relief='groove')
        self.title = title
        self.cam_index = cam_index
        
        self.flip_h = tk.BooleanVar(value=False)
        self.flip_v = tk.BooleanVar(value=False)
        self.rotation_angle = 0
        self.grid_on = tk.BooleanVar(value=False)
        self.exposure_val = tk.DoubleVar(value=-5.0)
        self.gain_val = tk.DoubleVar(value=0.0)

        self.is_running = True
        self.cap = cv2.VideoCapture(self.cam_index, cv2.CAP_DSHOW)

        self.create_ui()
        self.start_video_thread()

    def create_ui(self):
        lbl_title = tk.Label(self.frame, text=self.title, bg='#333333', fg='white', font=('Times New Roman', 20, 'bold'))
        lbl_title.pack(side='top', pady=5)

        self.video_label = tk.Label(self.frame, bg='black')
        self.video_label.pack(side='top', fill='both', expand=True, padx=10, pady=5)

        control_panel = tk.Frame(self.frame, bg='#444444')
        control_panel.pack(side='bottom', fill='x', padx=10, pady=10)

        # 1행: 카메라 인덱스(번호) 선택 및 화면 제어
        row1 = tk.Frame(control_panel, bg='#444444')
        row1.pack(fill='x', pady=5)
        
        # [핵심] 카메라 번호를 UI에서 바꿀 수 있는 콤보박스
        lbl_idx = tk.Label(row1, text="Cam Port:", bg='#444444', fg='yellow', font=('Times New Roman', 12, 'bold'))
        lbl_idx.pack(side='left', padx=5)
        
        self.combo_idx = ttk.Combobox(row1, values=[0, 1, 2, 3, 4], width=3, state='readonly')
        self.combo_idx.set(self.cam_index)
        self.combo_idx.pack(side='left', padx=5)
        self.combo_idx.bind("<<ComboboxSelected>>", self.change_camera)

        chk_flip_h = tk.Checkbutton(row1, text="Flip H", variable=self.flip_h, bg='#444444', fg='white', selectcolor='#555555', font=('Times New Roman', 12))
        chk_flip_h.pack(side='left', padx=10)
        
        chk_flip_v = tk.Checkbutton(row1, text="Flip V", variable=self.flip_v, bg='#444444', fg='white', selectcolor='#555555', font=('Times New Roman', 12))
        chk_flip_v.pack(side='left', padx=10)
        
        btn_rot = tk.Button(row1, text="Rotate 90°", command=self.rotate_90, bg='#555555', fg='white', font=('Times New Roman', 12))
        btn_rot.pack(side='left', padx=10)

        chk_grid = tk.Checkbutton(row1, text="Grid On/Off", variable=self.grid_on, bg='#444444', fg='white', selectcolor='#555555', font=('Times New Roman', 12))
        chk_grid.pack(side='left', padx=10)

        # 2행: 노출 및 게인
        row2 = tk.Frame(control_panel, bg='#444444')
        row2.pack(fill='x', pady=5)

        tk.Label(row2, text="Exposure:", bg='#444444', fg='white', font=('Times New Roman', 12)).pack(side='left', padx=5)
        scale_exp = tk.Scale(row2, variable=self.exposure_val, from_=-10.0, to=0.0, resolution=0.1, orient='horizontal', bg='#444444', fg='white', command=self.update_camera_settings)
        scale_exp.pack(side='left', fill='x', expand=True, padx=5)

        tk.Label(row2, text="Gain:", bg='#444444', fg='white', font=('Times New Roman', 12)).pack(side='left', padx=5)
        scale_gain = tk.Scale(row2, variable=self.gain_val, from_=0, to=255, orient='horizontal', bg='#444444', fg='white', command=self.update_camera_settings)
        scale_gain.pack(side='left', fill='x', expand=True, padx=5)

    def change_camera(self, event=None):
        new_idx = int(self.combo_idx.get())
        if self.cap.isOpened():
            self.cap.release()
        self.cam_index = new_idx
        self.cap.open(self.cam_index, cv2.CAP_DSHOW)
        self.update_camera_settings()

    def rotate_90(self):
        self.rotation_angle = (self.rotation_angle + 90) % 360

    def update_camera_settings(self, event=None):
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_EXPOSURE, self.exposure_val.get())
            self.cap.set(cv2.CAP_PROP_GAIN, self.gain_val.get())

    def start_video_thread(self):
        self.thread = threading.Thread(target=self.update_frame)
        self.thread.daemon = True
        self.thread.start()

    def update_frame(self):
        while self.is_running:
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    if self.flip_h.get(): frame = cv2.flip(frame, 1)
                    if self.flip_v.get(): frame = cv2.flip(frame, 0)
                    if self.rotation_angle == 90: frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                    elif self.rotation_angle == 180: frame = cv2.rotate(frame, cv2.ROTATE_180)
                    elif self.rotation_angle == 270: frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    if self.grid_on.get():
                        h, w, _ = frame_rgb.shape
                        color = (0, 255, 0)
                        cv2.line(frame_rgb, (w//3, 0), (w//3, h), color, 1)
                        cv2.line(frame_rgb, (2*w//3, 0), (2*w//3, h), color, 1)
                        cv2.line(frame_rgb, (0, h//3), (w, h//3), color, 1)
                        cv2.line(frame_rgb, (0, 2*h//3), (w, 2*h//3), color, 1)

                    img = Image.fromarray(frame_rgb)
                    label_w, label_h = self.video_label.winfo_width(), self.video_label.winfo_height()
                    if label_w > 10 and label_h > 10:
                        img.thumbnail((label_w, label_h), Image.Resampling.LANCZOS)
                    
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.video_label.imgtk = imgtk
                    self.video_label.configure(image=imgtk)
            time.sleep(0.03)

    def stop(self):
        self.is_running = False
        if self.cap.isOpened():
            self.cap.release()

class FLIRCameraModule:
    """Spinnaker SDK (PySpin)를 사용하는 FLIR 전용 카메라 모듈"""
    def __init__(self, parent, title):
        self.frame = tk.Frame(parent, bg='#1a1a3a', bd=2, relief='groove') # 약간 푸른빛 배경으로 구별
        self.title = title
        
        self.flip_h = tk.BooleanVar(value=False)
        self.flip_v = tk.BooleanVar(value=False)
        self.rotation_angle = 0
        self.grid_on = tk.BooleanVar(value=False)

        self.is_running = True
        self.system = None
        self.cam_list = None
        self.cam = None

        self.create_ui()
        self.init_flir()
        self.start_video_thread()

    def create_ui(self):
        lbl_title = tk.Label(self.frame, text=self.title + " [PySpin Native]", bg='#1a1a3a', fg='#00ffff', font=('Times New Roman', 20, 'bold'))
        lbl_title.pack(side='top', pady=5)

        self.video_label = tk.Label(self.frame, bg='black')
        self.video_label.pack(side='top', fill='both', expand=True, padx=10, pady=5)

        control_panel = tk.Frame(self.frame, bg='#333355')
        control_panel.pack(side='bottom', fill='x', padx=10, pady=10)

        row1 = tk.Frame(control_panel, bg='#333355')
        row1.pack(fill='x', pady=5)
        
        chk_flip_h = tk.Checkbutton(row1, text="Flip H", variable=self.flip_h, bg='#333355', fg='white', selectcolor='#444466', font=('Times New Roman', 12))
        chk_flip_h.pack(side='left', padx=10)
        
        chk_flip_v = tk.Checkbutton(row1, text="Flip V", variable=self.flip_v, bg='#333355', fg='white', selectcolor='#444466', font=('Times New Roman', 12))
        chk_flip_v.pack(side='left', padx=10)
        
        btn_rot = tk.Button(row1, text="Rotate 90°", command=self.rotate_90, bg='#555577', fg='white', font=('Times New Roman', 12))
        btn_rot.pack(side='left', padx=10)

        chk_grid = tk.Checkbutton(row1, text="Grid On/Off", variable=self.grid_on, bg='#333355', fg='white', selectcolor='#444466', font=('Times New Roman', 12))
        chk_grid.pack(side='left', padx=10)
        
        # FLIR의 노출/게인 제어는 SDK 특성상 매우 복잡하여 우선 Auto 모드로 구동시킵니다.
        tk.Label(control_panel, text="* Exposure and Gain are automatically optimized by FLIR Auto Algorithm.", 
                 bg='#333355', fg='gray', font=('Times New Roman', 10)).pack(side='bottom', pady=2)

    def rotate_90(self):
        self.rotation_angle = (self.rotation_angle + 90) % 360

    def init_flir(self):
        try:
            self.system = PySpin.System.GetInstance()
            self.cam_list = self.system.GetCameras()
            if self.cam_list.GetSize() > 0:
                self.cam = self.cam_list.GetByIndex(0)
                self.cam.Init()
                # 연속 촬영 모드 설정
                if self.cam.AcquisitionMode.GetAccessMode() == PySpin.RW:
                    self.cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
                self.cam.BeginAcquisition()
            else:
                print("FLIR 카메라를 찾을 수 없습니다.")
        except Exception as e:
            print(f"FLIR 초기화 오류: {e}")

    def start_video_thread(self):
        self.thread = threading.Thread(target=self.update_frame)
        self.thread.daemon = True
        self.thread.start()

    def update_frame(self):
        while self.is_running:
            if self.cam is not None:
                try:
                    image_result = self.cam.GetNextImage(1000)
                    if not image_result.IsIncomplete():
                        # PySpin을 이용해 원본 이미지를 고품질 RGB 배열로 즉시 변환
                        image_converted = image_result.Convert(PySpin.PixelFormat_RGB8, PySpin.HQ_LINEAR)
                        frame_rgb = image_converted.GetNDArray()
                        image_result.Release()

                        # 이미지 변환 적용
                        if self.flip_h.get(): frame_rgb = cv2.flip(frame_rgb, 1)
                        if self.flip_v.get(): frame_rgb = cv2.flip(frame_rgb, 0)
                        if self.rotation_angle == 90: frame_rgb = cv2.rotate(frame_rgb, cv2.ROTATE_90_CLOCKWISE)
                        elif self.rotation_angle == 180: frame_rgb = cv2.rotate(frame_rgb, cv2.ROTATE_180)
                        elif self.rotation_angle == 270: frame_rgb = cv2.rotate(frame_rgb, cv2.ROTATE_90_COUNTERCLOCKWISE)

                        if self.grid_on.get():
                            h, w, _ = frame_rgb.shape
                            color = (0, 255, 0)
                            cv2.line(frame_rgb, (w//3, 0), (w//3, h), color, 1)
                            cv2.line(frame_rgb, (2*w//3, 0), (2*w//3, h), color, 1)
                            cv2.line(frame_rgb, (0, h//3), (w, h//3), color, 1)
                            cv2.line(frame_rgb, (0, 2*h//3), (w, 2*h//3), color, 1)

                        img = Image.fromarray(frame_rgb)
                        label_w, label_h = self.video_label.winfo_width(), self.video_label.winfo_height()
                        if label_w > 10 and label_h > 10:
                            img.thumbnail((label_w, label_h), Image.Resampling.LANCZOS)
                        
                        imgtk = ImageTk.PhotoImage(image=img)
                        self.video_label.imgtk = imgtk
                        self.video_label.configure(image=imgtk)
                except PySpin.SpinnakerException:
                    pass
            time.sleep(0.01) # FLIR 고프레임 대응

    def stop(self):
        self.is_running = False
        time.sleep(0.1)
        if self.cam is not None:
            try:
                self.cam.EndAcquisition()
                self.cam.DeInit()
            except: pass
            del self.cam
        if self.cam_list is not None:
            self.cam_list.Clear()
        if self.system is not None:
            self.system.ReleaseInstance()