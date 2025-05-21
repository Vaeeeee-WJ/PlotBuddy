import os
import sys
import cv2
import ctypes
import numpy as np
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, ttk, simpledialog

class ImageMagnifier:
    def __init__(self):
        # 初始化变量
        self.image_path          = None
        self.image               = None
        self.drawing             = False
        self.preview_mode        = False
        self.start_point         = (-1, -1)
        self.end_point           = (-1, -1)
        self.preview_window_name = "Preview"
        self.main_window_name    = "Image"
        self.preview             = None
        
        # 可自定义参数
        self.lw             = 1  # 线宽
        self.region_count   = 1  # 放大区域个数
        self.current_region = 0  # 当前区域索引
        self.border_color   = [(0, 0, 255)]  # 存储边框的颜色
        self.boxes          = []  # 保存放大区域的坐标
        self.area           = 'Down' # 默认放大区域显示在图像下方 D U L R
        self.gap            = 0 # 区域间距

    def show_settings_dialog(self):
        """显示参数设置对话框"""
        # 创建对话框窗口
        settings_window = tk.Tk()
        settings_window.title("参数设置")
        settings_window.geometry("800x800")  # 调整高度以适应可能增加的颜色设置
        settings_window.resizable(False, False)

        # 界面优化---------------------------------
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        ScaleFactor=ctypes.windll.shcore.GetScaleFactorForDevice(0)
        settings_window.tk.call('tk', 'scaling', ScaleFactor/75) 

        # 居中显示
        settings_window.update_idletasks()
        width = settings_window.winfo_width()
        height = settings_window.winfo_height()
        x = (settings_window.winfo_screenwidth() // 2) - (width // 2)
        y = (settings_window.winfo_screenheight() // 2) - (height // 2)
        settings_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # 创建主框架
        main_frame = ttk.Frame(settings_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 区域个数设置 - 使用加减按钮
        ttk.Label(main_frame, text="放大区域个数:").grid(row=0, column=0, sticky=tk.W, pady=10)
        
        region_frame = ttk.Frame(main_frame)
        region_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=10)
        
        region_count_var = tk.IntVar(value=self.region_count)
        
        def decrease_region_count():
            current = region_count_var.get()
            if current > 1:
                region_count_var.set(current - 1)
                # 强制更新显示
                region_count_entry.configure(state='normal')
                region_count_entry.delete(0, tk.END)
                region_count_entry.insert(0, region_count_var.get())
                region_count_entry.configure(state='readonly')
        
        def increase_region_count():
            current = region_count_var.get()
            if current < 4:
                region_count_var.set(current + 1)
                # 强制更新显示
                region_count_entry.configure(state='normal')
                region_count_entry.delete(0, tk.END)
                region_count_entry.insert(0, region_count_var.get())
                region_count_entry.configure(state='readonly')
        
        ttk.Button(region_frame, text="-", width=5, command=decrease_region_count).pack(side=tk.LEFT)
        region_count_entry = ttk.Entry(region_frame, textvariable=region_count_var, width=5, justify=tk.CENTER)
        region_count_entry.pack(side=tk.LEFT, padx=5)
        region_count_entry.configure(state='readonly')
        ttk.Button(region_frame, text="+", width=5, command=increase_region_count).pack(side=tk.LEFT)
        
        # 只需要放大一个区域时，不需要设置放大区域间隔
        def on_region_count_change(*args):
            if region_count_var.get() == 1:
                gap_entry.configure(state='disabled')
            else:
                gap_entry.configure(state='normal')
        region_count_var.trace_add("write", on_region_count_change)

        
        # 线宽设置 - 使用加减按钮
        ttk.Label(main_frame, text="线宽设置:").grid(row=1, column=0, sticky=tk.W, pady=10)
        
        line_width_frame = ttk.Frame(main_frame)
        line_width_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=10)
        
        line_width_var = tk.IntVar(value=self.lw)

        
        # 区域位置选择 - 使用下拉框
        ttk.Label(main_frame, text="放大区域位置:").grid(row=2, column=0, sticky=tk.W, pady=10)

        position_options = ["Down", "Up", "Left", "Right"]
        position_var = tk.StringVar(value=position_options[0])
        position_combobox = ttk.Combobox(main_frame, textvariable=position_var, values=position_options, state="readonly", width=5)
        position_combobox.grid(row=2, column=1, sticky=tk.W, pady=10)
        position_combobox.current(0)
        ## 实时获取每次下拉框中选择的值
        def get_area(event):
            self.area = position_combobox.get()
        position_combobox.bind("<<ComboboxSelected>>", get_area)
        
        # 放大区域间隔设置
        ttk.Label(main_frame, text="放大区域间隔:").grid(row=2, column=2, sticky=tk.W, padx=5)
        gap_var = tk.IntVar(value=self.region_gap if hasattr(self, 'region_gap') else 10)  # 设置初始值，可设为实例变量

        def validate_integer_input(new_value):
            if new_value == "":
                return True  # 允许清空
            try:
                value = int(new_value)
                if self.area == 'Up' or 'Down':
                    return 0 <= value <= self.image.shape[1] // 2  # 最大不要超过图像W/2
                else:
                    return 0 <= value <= self.image.shape[0] // 2  # 最大不要超过图像H/2
            except ValueError:
                return False
        ## 实时获取设置的 放大区域间隔
        def get_gap(event):
            self.gap = gap_entry.get()

        vcmd = (settings_window.register(validate_integer_input), '%P')

        gap_entry = ttk.Entry(main_frame, textvariable=gap_var, width=5, validate='key', validatecommand=vcmd)
        gap_entry.grid(row=2, column=3, sticky=tk.W)
        gap_entry.bind("<KeyRelease>", get_gap)

        
        def decrease_line_width():
            current = line_width_var.get()
            if current > 1:
                line_width_var.set(current - 1)
                # 强制更新显示
                line_width_entry.configure(state='normal')
                line_width_entry.delete(0, tk.END)
                line_width_entry.insert(0, line_width_var.get())
                line_width_entry.configure(state='readonly')
        
        def increase_line_width():
            current = line_width_var.get()
            if current < 10:
                line_width_var.set(current + 1)
                # 强制更新显示
                line_width_entry.configure(state='normal')
                line_width_entry.delete(0, tk.END)
                line_width_entry.insert(0, line_width_var.get())
                line_width_entry.configure(state='readonly')
        
        ttk.Button(line_width_frame, text="-", width=5, command=decrease_line_width).pack(side=tk.LEFT)
        line_width_entry = ttk.Entry(line_width_frame, textvariable=line_width_var, width=5, justify=tk.CENTER)
        line_width_entry.pack(side=tk.LEFT, padx=5)
        line_width_entry.configure(state='readonly')
        ttk.Button(line_width_frame, text="+", width=5, command=increase_line_width).pack(side=tk.LEFT)
        
        # 颜色设置框架 - 动态更新
        color_frame = ttk.LabelFrame(main_frame, text="边框颜色设置")
        color_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # 颜色预览和选择组件列表
        color_previews = []
        color_buttons = []
        
        # 初始化颜色设置UI
        def update_color_ui():
            # 清空现有组件
            for widget in color_frame.winfo_children():
                widget.destroy()
            
            # 获取当前区域数量
            count = region_count_var.get()
            
            # 确保颜色列表长度足够
            while len(self.border_color) < count:
                self.border_color.append((0, 0, 255))  # 默认添加蓝色
            if len(self.border_color) > count:
                self.border_color = self.border_color[:count]
            
            # 创建对应数量的颜色设置UI
            color_previews.clear()
            color_buttons.clear()
            
            for i in range(count):
                # 颜色标签
                ttk.Label(color_frame, text=f"区域 {i+1} 颜色:").grid(row=i, column=0, sticky=tk.W, pady=5)
                
                # 当前颜色预览
                preview = tk.Canvas(color_frame, width=30, height=20, bg='white')
                preview.grid(row=i, column=1, sticky=tk.W, pady=5)
                color_previews.append(preview)
                
                # BGR转RGB显示
                bgr_color = self.border_color[i]
                rgb_color = f'#{bgr_color[2]:02x}{bgr_color[1]:02x}{bgr_color[0]:02x}'
                preview.create_rectangle(2, 2, 28, 18, fill=rgb_color, outline="")
                
                # 颜色选择按钮
                def choose_color(index=i):
                    # BGR转RGB
                    bgr_color = self.border_color[index]
                    rgb_color = (bgr_color[2], bgr_color[1], bgr_color[0])
                    
                    color = colorchooser.askcolor(
                        color=f'#{rgb_color[0]:02x}{rgb_color[1]:02x}{rgb_color[2]:02x}',
                        title=f"选择区域 {index+1} 边框颜色"
                    )
                    
                    if color[0] is not None:
                        r, g, b = [int(x) for x in color[0]]
                        # RGB转BGR存储
                        self.border_color[index] = (b, g, r)
                        color_previews[index].create_rectangle(2, 2, 28, 18, fill=color[1], outline="")
                
                button = ttk.Button(color_frame, text="选择颜色", command=choose_color)
                button.grid(row=i, column=2, sticky=tk.W, pady=5)
                color_buttons.append(button)
        
        # 初始更新颜色UI
        update_color_ui()
        
        # 区域数量变化时更新颜色UI
        region_count_var.trace_add("write", lambda *args: update_color_ui())
        
        # 确定和取消按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        def on_ok():
            # 更新类成员变量
            self.region_count = region_count_var.get()
            self.lw = line_width_var.get()
            self.current_region = 0  # 重置当前区域索引
            settings_window.destroy()
            settings_window.quit()
        
        ttk.Button(button_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=settings_window.destroy).pack(side=tk.LEFT, padx=10)
        
        # 显示对话框并等待
        settings_window.mainloop()

    def show_save_dialog(self, final_img):
        """显示结果保存对话框"""
            
        def save_image():
            # 打开文件夹选择对话框
            folder_selected = filedialog.askdirectory(title="选择保存图像的文件夹")
            if folder_selected:
                save_path = os.path.join(folder_selected, "final_result.png")
                cv2.imwrite(save_path, final_img)
                messagebox.showinfo("保存成功", f"图像已保存到：{save_path}")
            else:
                messagebox.showwarning("未保存", "未选择文件夹，图像未保存。")
            window.quit()
            window.destroy()
            cv2.destroyAllWindows()
            sys.exit()


        def batch_process():
            messagebox.showinfo(
                "注意事项!!!",
                "请保证要处理的图像都在同一文件夹下，且该文件夹下所有图片大小一致，图片名称不同！"
            )
            folder_path = filedialog.askdirectory(title="选择批量处理图片所在的文件夹")
            
            # 在folder_path 同级新建一个结果文件夹
            new_folder_path = os.path.join(os.path.dirname(folder_path), 'Result')
            os.makedirs(new_folder_path, exist_ok=True)
            cv2.imwrite(os.path.join(new_folder_path, 'current_image_result.png'), final_img)
            
            if folder_path:
                image_names = os.listdir(folder_path)

                messagebox.showinfo("提示", f"共找到 {len(image_names)} 张图片，即将进行批量处理。")
                print("需要处理的图像：", image_names)

                print('正在处理......')
                for img_name in image_names:
                    img_path = os.path.join(folder_path, img_name)

                    self.preview = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                    self.image = self.preview.copy()
                    for i in range(len(self.boxes)):
                        cv2.rectangle(self.preview, self.boxes[i][0], self.boxes[i][1],
                        self.border_color[i], self.lw)
                    
                    res = self.image_stitchingh() 
                    cv2.imshow(f'{img_name}', res)
                    cv2.imwrite(os.path.join(new_folder_path, f'{img_name.split(".")[0]}-result.{img_name.split(".")[1]}'), res)
                message = tk.Tk()
                message.withdraw()
                messagebox.showinfo("提示", f"批量处理完成。结果已保存到：\n{new_folder_path}")
                message.quit()
                message.destroy()
                cv2.destroyAllWindows()
                sys.exit()

            window.destroy()

        def exit_program():
            messagebox.showinfo("退出", "程序已退出。")
            window.quit()
            window.destroy()
            cv2.destroyAllWindows()
            sys.exit()

        # 创建窗口
        window = tk.Tk()
        window.title("请选择要执行的操作")
        window.geometry("600x360")
        window.resizable(False, False)

        # 创建按钮
        btn1 = tk.Button(window, text="1. 直接保存（英文路径）", width=25, height=2, command=save_image)
        btn1.pack(pady=10)

        btn2 = tk.Button(window, text="2. 保存结果并批量处理其他图像", width=25, height=2, command=batch_process)
        btn2.pack(pady=10)

        btn3 = tk.Button(window, text="3. 不保存,直接退出", width=25, height=2, command=exit_program)
        btn3.pack(pady=10)

        # 启动事件循环
        window.mainloop()     
    def select_image(self):
        """打开文件选择对话框选择图片"""
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.image_path = file_path
            self.image = cv2.imread(self.image_path)
            if self.image is None:
                messagebox.showerror("错误", "无法加载所选图片")
                return False
            return True
        return False

    def create_magnified_image(self, start_point, end_point, region_index=0):
        """创建放大的图像（支持多区域颜色）"""
        current_color = self.border_color[region_index] if self.border_color else (0, 0, 255)  # 默认红色

        # 坐标有效性检查
        x1, y1 = max(self.lw, start_point[0]), max(self.lw, start_point[1])
        x2, y2 = min(self.image.shape[1] - self.lw, end_point[0]), min(self.image.shape[0] - self.lw, end_point[1])
        
        # 处理无效区域（防止框选区域过小或反向）
        if x1 >= x2 or y1 >= y2:
            return None
        
        # 截取选中区域
        img_magnify = self.image[y1 - self.lw:y2 + self.lw, x1 - self.lw:x2 + self.lw].copy()
        
        # 处理空图像（例如框选到边界外）
        if img_magnify.size == 0:
            return None
        
        # 计算缩放比例（保持宽高比）
        original_width, original_height = img_magnify.shape[1], img_magnify.shape[0]
        new_width = self.image.shape[1] - 2 * self.lw  # 目标宽度（扣除边框）
        ratio = new_width / original_width if original_width != 0 else 1.0
        new_height = int(original_height * ratio)
        
        # 缩放图像（使用双线性插值保持平滑）
        resized_image = cv2.resize(img_magnify, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        
        # 添加边框（使用当前区域颜色）
        resized_image = cv2.copyMakeBorder(
            resized_image,
            top=self.lw, bottom=self.lw, left=self.lw, right=self.lw,
            borderType=cv2.BORDER_CONSTANT,
            value=current_color
        )
        
        # 在原图上绘制矩形（使用当前区域颜色）
        image_with_rect = self.image.copy()
        cv2.rectangle(
            image_with_rect, (x1, y1), (x2, y2),
            color=current_color, thickness=self.lw, lineType=cv2.LINE_AA
        )
        
        return  resized_image


    def mouse_callback(self, event, x, y, flags, param):
        """鼠标事件回调函数（支持多区域绘制）"""
        # 确保颜色列表长度足够

        while len(self.border_color) < self.region_count:
            self.border_color.append((255, 0, 0))  # 默认添加蓝色
        
        if event == cv2.EVENT_LBUTTONDOWN:
            # 左键按下，开始新区域绘制
            if self.current_region >= self.region_count:
                return  # 已达到最大区域数
                
            self.drawing = True
            self.start_point = (x, y)
            self.preview_mode = False
            
        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            # 鼠标移动，实时显示当前区域框选
            temp_img = self.image.copy()

            # 绘制已完成的区域
            for i in range(len(self.boxes)):
                cv2.rectangle(temp_img, self.boxes[i][0], self.boxes[i][1], 
                            self.border_color[i], self.lw) 

            # 绘制当前正在框选的区域
            if self.current_region < len(self.border_color):
                cv2.rectangle(temp_img, self.start_point, (x, y), 
                            self.border_color[self.current_region], self.lw)

            cv2.imshow(self.main_window_name, temp_img)
            self.preview = temp_img
            
        elif event == cv2.EVENT_LBUTTONUP:
            # 左键释放，完成当前区域
            if not self.drawing:
                return
                
            self.drawing = False
            self.end_point = (x, y)
            
            # 保存当前区域坐标
            self.boxes.append([self.start_point, self.end_point])

            # 更新预览- 每框选一个区域就显示其放大的图像
            self.current_region += 1
            if self.current_region <= self.region_count:
                self.update_preview()

            # 如果还有区域需要绘制，重置状态
            if self.current_region < self.region_count:
                self.drawing = False
                self.preview_mode = False
            else:
                self.preview_mode = True

    def image_stitchingh(self):
        """拼接图像"""

        magnified_All = []   # 保存所有待放大的区域 
        
        for box in self.boxes:
            x1, y1 = box[0][0], box[0][1]
            x2, y2 = box[1][0], box[1][1]
            img  = self.image[y1 - self.lw:y2 + self.lw, x1 - self.lw:x2 + self.lw].copy()
            magnified_All.append(img)

        if self.area == 'Down' or self.area == 'Up':
            ## 若放大区域个数为1
            if len(magnified_All) == 1:
                W = self.image.shape[1] - 2 * self.lw
                H = (magnified_All[0].shape[0] * W / magnified_All[0].shape[1])
                H = int(H)
                magnified_img = cv2.resize(magnified_All[0], (W, H), interpolation=cv2.INTER_LINEAR)
                magnified_img = cv2.copyMakeBorder(
                    magnified_img,
                    top=self.lw, bottom=self.lw, left=self.lw, right=self.lw,
                    borderType=cv2.BORDER_CONSTANT,
                    value=self.border_color[0]
                )

                
            else:    
                # 统一放大区域的高度
                H  = (self.image.shape[1] - 2 * self.lw * self.region_count - int(self.gap) * (self.region_count - 1)) / (sum(img.shape[1] / img.shape[0] for img in magnified_All) )
                H   = int(H)

                # 缩放图像（使用双线性插值保持平滑）
                for i in range(len(magnified_All)):
                    new_width  = int(magnified_All[i].shape[1] * H / magnified_All[i].shape[0])
                    magnified_All[i] = cv2.resize(magnified_All[i], (new_width, H), interpolation=cv2.INTER_LINEAR)

                
                    # 添加边框（使用当前区域颜色）
                    magnified_All[i] = cv2.copyMakeBorder(
                        magnified_All[i],
                        top=self.lw, bottom=self.lw, left=self.lw, right=self.lw,
                        borderType=cv2.BORDER_CONSTANT,
                        value=self.border_color[i]
                    )
            
                num_images = len(magnified_All)
                total_img_width = sum(img.shape[1] for img in magnified_All)
                
                # 计算基础间隔宽度和多余的像素
                num_gaps = num_images - 1 if num_images > 1 else 1
                total_gap_width = self.image.shape[1] - total_img_width
                base_gap = total_gap_width // num_gaps
                extra_gap = total_gap_width % num_gaps  # 用于分配到前几个间隔中

                # 初始化输出图像
                magnified_img = np.full((H + 2 * self.lw, self.image.shape[1], 3), 255, dtype=magnified_All[0].dtype)

                x = 0
                for i in range(num_images):
                    img = magnified_All[i]
                    w = img.shape[1]
                    magnified_img[:, x:x + w, :] = img
                    x += w
                    if i < num_images - 1:
                        x += base_gap + (1 if i < extra_gap else 0)
            
            if self.area == 'Down':
                result  = np.vstack([self.preview, magnified_img])
            else:
                result  = np.vstack([magnified_img, self.preview])
            return result

        else :
            ## 若放大区域个数为1
            if len(magnified_All) == 1:
                H = self.image.shape[0] - 2 * self.lw
                W = (magnified_All[0].shape[1] * H / magnified_All[0].shape[0])
                W = int(W)
                magnified_img = cv2.resize(magnified_All[0], (W, H), interpolation=cv2.INTER_LINEAR)
                magnified_img = cv2.copyMakeBorder(
                    magnified_img,
                    top=self.lw, bottom=self.lw, left=self.lw, right=self.lw,
                    borderType=cv2.BORDER_CONSTANT,
                    value=self.border_color[0]
                )

                
            else:    
                # 统一放大区域的宽度
                W  = (self.image.shape[0] - 2 * self.lw * self.region_count - int(self.gap) * (self.region_count - 1)) / (sum(img.shape[0] / img.shape[1] for img in magnified_All))
                W   = int(W)

                # 缩放图像（使用双线性插值保持平滑）
                for i in range(len(magnified_All)):
                    new_height  = int(magnified_All[i].shape[0] * W / magnified_All[i].shape[1])
                    magnified_All[i] = cv2.resize(magnified_All[i], (W, new_height), interpolation=cv2.INTER_LINEAR)

                
                    # 添加边框（使用当前区域颜色）
                    magnified_All[i] = cv2.copyMakeBorder(
                        magnified_All[i],
                        top=self.lw, bottom=self.lw, left=self.lw, right=self.lw,
                        borderType=cv2.BORDER_CONSTANT,
                        value=self.border_color[i]
                    )
            
                num_images = len(magnified_All)
                total_img_height = sum(img.shape[0] for img in magnified_All)
                
                # 计算基础间隔宽度和多余的像素
                num_gaps = num_images - 1 if num_images > 1 else 1
                total_gap_width = self.image.shape[0] - total_img_height
                base_gap = total_gap_width // num_gaps
                extra_gap = total_gap_width % num_gaps  # 用于分配到前几个间隔中

                # 初始化输出图像
                magnified_img = np.full((self.image.shape[0], W + 2 * self.lw, 3), 255, dtype=magnified_All[0].dtype)

                x = 0
                for i in range(num_images):
                    img = magnified_All[i]
                    h = img.shape[0]
                    magnified_img[x:x + h, :, :] = img
                    x += h
                    if i < num_images - 1:
                        x += base_gap + (1 if i < extra_gap else 0)
            
            if self.area == 'Right':
                result  = np.hstack([self.preview, magnified_img])
            else:
                result  = np.hstack([magnified_img, self.preview])
            return result
        
    def update_preview(self):
        """更新预览窗口，显示所有已绘制区域的放大效果"""
            
        # 为每个区域创建放大图
        magnified = self.create_magnified_image(self.boxes[-1][0], self.boxes[-1][1], self.current_region - 1)
        cv2.imshow(self.preview_window_name + f"{self.current_region}", magnified)
        
        # 区域框选完成则显示最终拼接图像
        if self.current_region == self.region_count:
            final_img = self.image_stitchingh()
            cv2.imshow('final', final_img)

            # 结果保存设置
            self.show_save_dialog(final_img)

    def run(self):
        """主运行函数"""
        # 先选择图片，再显示参数设置对话框
        if not self.select_image():
            return
            
        # 显示参数设置对话框
        self.show_settings_dialog()

        cv2.namedWindow(self.main_window_name)
        cv2.imshow(self.main_window_name, self.image)
        cv2.setMouseCallback(self.main_window_name, self.mouse_callback)

        while True:
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):  # 按q退出
                break
            elif key == ord('c'):  # 按c取消当前选择
                if self.preview_mode:
                    cv2.destroyWindow(self.preview_window_name)
                    cv2.imshow(self.main_window_name, self.image)
                    self.preview_mode = False
                    self.start_point = (-1, -1)
                    self.end_point = (-1, -1)
                    if self.current_region > 0:
                        self.current_region -= 1
            elif key == ord('s'):  # 按s保存当前结果
                if self.preview_mode:
                    result = self.create_magnified_image(self.start_point, self.end_point)
                    save_path = self.image_path.rsplit('.', 1)[0] + '_magnified.' + self.image_path.rsplit('.', 1)[1]
                    cv2.imwrite(save_path, result)
                    messagebox.showinfo("成功", f"图片已保存至：\n{save_path}")
            elif key == ord('p'):  # 按p重新打开参数设置对话框
                self.show_settings_dialog()
            
            # 检查窗口是否被关闭
            if cv2.getWindowProperty(self.main_window_name, cv2.WND_PROP_VISIBLE) < 1:
                break

        cv2.destroyAllWindows()

if __name__ == '__main__':
    magnifier = ImageMagnifier()
    magnifier.run()    