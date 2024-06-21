import copy
import tkinter as tk
from tkinter import filedialog, colorchooser, simpledialog, ttk, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os


def load_fonts_from_parent_directory():
    # 폰트 경로 리스트 생성 및 반환
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    font_dir = os.path.join(parent_dir, "fonts")
    font_files = {}
    if os.path.exists(font_dir) and os.path.isdir(font_dir):
        for file in os.listdir(font_dir):
            if file.lower().endswith(".ttf"):
                font_name = os.path.basename(file)[:-4]
                font_files[font_name] = os.path.join(font_dir, file)
    return font_files


def hex_to_rgb(color):
    # 16진수 색상 코드를 R, G, B 값으로 변환하는 함수
    color = color.lstrip('#')
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def select_text_on_focus(event):
    event.widget.select_range(0, tk.END)
    event.widget.icursor(tk.END)


def is_dark_color(color):
    # 색상이 어두운 색상인지 판단하는 함수 (R, G, B 값의 평균이 128보다 작으면 어두운 색으로 판단)
    r, g, b = hex_to_rgb(color)
    return (r + g + b) / 3 < 128


def validate_size(value):
    if value.isdigit() or value == "":
        if len(value) <= 3:
            return True
    return False


def pick_color_from_popup(button):
    color = colorchooser.askcolor()[1]
    if color:
        button.config(bg=color)
        if is_dark_color(color):
            button.config(fg="#FFFFFF")
        else:
            button.config(fg="#000000")


def get_actual_text_size(text, font, font_name):
    temp_image = Image.new('L', (1, 1))
    temp_draw = ImageDraw.Draw(temp_image)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]

    # 폰트별 높이 조정 배율
    height_scales = {
        "Dovemayo_gothic": 1.5,
        "GamjaFlower-Regular": 1.6,
        "KCC-Chassam": 1.6,
        "오뮤_다예쁨체": 1.4,
        "휴먼범석체": 1.1
    }

    adjusted_height = int(height * height_scales.get(font_name, 1.0))

    return width, adjusted_height


class ImageEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("ImageEditor")

        # Canvas 생성 및 이벤트 바인딩
        self.canvas = tk.Canvas(root, bg='white')
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", self.on_right_click)

        # 이미지 및 문자 정보 초기화
        self.image_path = None
        self.image = None
        self.image_tk = None
        self.text_images = {}
        self.text_info = {}
        self.current_text = None
        self.last_position = (0, 0)

        self.original_image_size = None  # 원본 이미지의 크기
        self.scale_factor = (1, 1)

        self.original_text_info = copy.deepcopy(self.text_info)

        # 기본 폰트 및 문자 색상 설정
        self.font_files = load_fonts_from_parent_directory()
        self.font = (list(self.font_files.keys())[0], 30)
        self.text_color = "#000000"

        # 메뉴 바 생성 및 메뉴 아이템 추가
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)
        file_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="사진 가져오기", accelerator="Ctrl+O", command=self.open_image)
        self.root.bind_all("<Control-o>", lambda event: self.open_image())
        file_menu.add_command(label="사진 저장", accelerator="Ctrl+S", command=self.save_image)
        self.root.bind_all("<Control-s>", lambda event: self.save_image())
        menu.add_command(label="문자 추가", command=self.add_text)
        self.root.bind_all("<Control-n>", lambda event: self.add_text())

    def clear_canvas(self):
        self.canvas.delete("all")
        self.image = None
        self.image_tk = None
        self.text_images = {}
        self.text_info = {}
        self.current_text = None

    def open_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")])
        if not file_path:
            return
        self.image_path = file_path
        self.clear_canvas()

        self.image = Image.open(file_path)

        # 원래의 이미지 크기 저장
        self.original_image_size = self.image.size

        # 이미지 크기 조절
        max_width = self.root.winfo_screenwidth() * 0.8  # 최대 80% 크기로 제한
        max_height = self.root.winfo_screenheight() * 0.8
        self.image.thumbnail((max_width, max_height), Image.LANCZOS)

        self.image_tk = ImageTk.PhotoImage(self.image)

        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image_tk)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        self.canvas.config(width=self.image.size[0], height=self.image.size[1])

    def save_image(self):
        if not self.image:
            messagebox.showerror("알림", "이미지가 없습니다.")
            return

        # 원본 이미지 크기로 확장
        self.scale_factor = (self.original_image_size[0] / self.image.size[0], self.original_image_size[1] / self.image.size[1])

        edited_image = self.image.resize(self.original_image_size, Image.LANCZOS)
        draw = ImageDraw.Draw(edited_image)

        for item, info in self.text_info.items():
            text = info['text']
            font_name = info['font'][0]
            original_font_size = info['font'][1]
            scaled_font_size = int(original_font_size * sum(self.scale_factor)/2)  # 스케일링 팩터 적용

            font_path = self.font_files[font_name]
            font_obj = ImageFont.truetype(font_path, scaled_font_size)
            x, y = info['position']

            scaled_x = int(x * self.scale_factor[0])
            scaled_y = int(y * self.scale_factor[1])

            if info['direction'] == 'horizontal':
                draw.text((scaled_x, scaled_y), text, font=font_obj, fill=info['color'])
            else:
                char_width, char_height = get_actual_text_size(text, font_obj, font_name)
                for i, char in enumerate(text):
                    draw.text((scaled_x, scaled_y + i * char_height), char, font=font_obj, fill=info['color'])

        save_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("All Files", "*.*")])
        if save_path:
            edited_image.save(save_path)
            self.original_text_info = copy.deepcopy(self.text_info)

    def add_text(self):
        if not self.image:
            messagebox.showerror("알림", "이미지가 없습니다.")
            return
        # 문자를 이미지로 추가
        text = simpledialog.askstring("문자 추가", "\t문자를 입력하세요.\t\t")
        if text:
            text = text.encode('utf-8').decode('utf-8')
            x, y = self.last_position

            font_path = self.font_files[self.font[0]]
            font_obj = ImageFont.truetype(font_path, self.font[1])

            text_width, text_height = get_actual_text_size(text, font_obj, self.font[0])

            text_img = Image.new('RGBA', (text_width, text_height), (255, 255, 255, 0))
            text_draw = ImageDraw.Draw(text_img)
            text_draw.text((0, 0), text, font=font_obj, fill=self.text_color)

            text_img_tk = ImageTk.PhotoImage(text_img)
            image_item = self.canvas.create_image(x, y, anchor=tk.NW, image=text_img_tk)

            self.text_images[image_item] = text_img_tk
            self.text_info[image_item] = {'text': text, 'font': self.font, 'color': self.text_color, 'position': (x, y),
                                          'direction': 'horizontal'}

            self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
            self.last_position = (x + text_width, y + text_height)

    def on_canvas_click(self, event):
        self.last_position = (event.x, event.y)
        try:
            closest_items = self.canvas.find_closest(event.x, event.y)
            if closest_items and closest_items[0] in self.text_info:
                self.current_text = closest_items[0]
            else:
                self.current_text = None
        except Exception as e:
            pass

    def on_drag(self, event):
        if self.current_text:
            prev_x, prev_y = self.last_position
            delta_x = event.x - prev_x
            delta_y = event.y - prev_y

            x, y = self.text_info[self.current_text]['position']
            self.canvas.move(self.current_text, delta_x, delta_y)

            self.last_position = (event.x, event.y)
            self.text_info[self.current_text]['position'] = (x + delta_x, y + delta_y)

    def on_right_click(self, event):
        selected_item = self.canvas.find_withtag(tk.CURRENT)

        if selected_item and selected_item[0] in self.text_info:
            self.current_text = selected_item[0]
            self.show_popup(selected_item[0])

    def show_popup(self, item):
        popup = tk.Toplevel(self.root)
        popup.title("문자 수정")
        popup.grab_set()

        for i in range(4):
            popup.grid_columnconfigure(i, weight=1)
        for i in range(6):
            popup.grid_rowconfigure(i, weight=1)

        tk.Label(popup, text="문자:", anchor='e').grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        text_entry = tk.Entry(popup)
        text_entry.grid(row=0, column=1, columnspan=2, sticky='ew', padx=5, pady=5)
        text_entry.insert(0, self.text_info[item]['text'])
        text_entry.bind("<FocusIn>", select_text_on_focus)

        tk.Label(popup, text="글꼴:", anchor='e').grid(row=1, column=0, sticky='ew', padx=5, pady=5)

        font_names = list(self.font_files.keys())
        selected_font_name = os.path.basename(self.text_info[item]['font'][0])
        font_combobox = ttk.Combobox(popup, values=font_names, state="readonly")
        font_combobox.set(selected_font_name)
        font_combobox.grid(row=1, column=1, columnspan=2, sticky='ew', padx=5, pady=5)

        tk.Label(popup, text="문자 크기:", anchor='e').grid(row=2, column=0, sticky='ew', padx=5, pady=5)
        validate_size_entry = root.register(validate_size)
        size_entry = tk.Entry(popup, width=10, validate="key", validatecommand=(validate_size_entry, "%P"))
        size_entry.grid(row=2, column=1, columnspan=2, sticky='ew', padx=5, pady=5)
        size_entry.insert(0, str(self.text_info[item]['font'][1]))
        size_entry.bind("<FocusIn>", select_text_on_focus)

        tk.Label(popup, text="색상:", anchor='e').grid(row=3, column=0, sticky='ew', padx=5, pady=5)
        color_button = tk.Button(popup, text="색상을 선택하세요.", command=lambda: pick_color_from_popup(color_button),
                                 bg=self.text_info[item]['color'])
        if is_dark_color(self.text_info[item]['color']):
            color_button.config(fg="#FFFFFF")
        color_button.grid(row=3, column=1, columnspan=2, sticky='ew', padx=5, pady=5)

        tk.Label(popup, text="방향:", anchor='e').grid(row=4, column=0, sticky='ew', padx=5, pady=5)
        direction_var = tk.StringVar(value=self.text_info[item]['direction'])
        direction_horizontal = tk.Radiobutton(popup, text="가로", variable=direction_var, value="horizontal")
        direction_vertical = tk.Radiobutton(popup, text="세로", variable=direction_var, value="vertical")
        direction_horizontal.grid(row=4, column=1, padx=5, pady=5)
        direction_vertical.grid(row=4, column=2, padx=5, pady=5)

        save_button = tk.Button(popup, text="저장",
                                command=lambda: self.save_changes(popup, item, text_entry, font_combobox.get(),
                                                                  size_entry, color_button, direction_var.get()))
        save_button.grid(row=5, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        popup.bind('<Return>', lambda event: save_button.invoke())

        delete_button = tk.Button(popup, text="삭제", command=lambda: self.delete_text(popup, item))
        delete_button.grid(row=5, column=2, columnspan=2, sticky='ew', padx=5, pady=5)

        text_entry.focus()

    def save_changes(self, popup, item, text_entry, font_var, size_entry, color_button, direction):
        if not text_entry.get():
            messagebox.showerror("알림", "문자가 없습니다.")
            return
        if size_entry:
            new_text = text_entry.get()
            selected_font_path = self.font_files[font_var]
            selected_font_size = int(size_entry.get())
            selected_font_full = (font_var, selected_font_size)
            new_color = color_button.cget("bg")
            font_obj = ImageFont.truetype(selected_font_path, selected_font_size)

            if direction == "vertical":
                char_height = get_actual_text_size(new_text, font_obj, font_var)[1]
                adjusted_height = char_height * len(new_text)
                text_width, text_height = char_height, adjusted_height
            else:
                text_width, text_height = get_actual_text_size(new_text, font_obj, font_var)
                adjusted_height = int(text_height * 1.2)

            text_img = Image.new('RGBA', (text_width, adjusted_height), (255, 255, 255, 0))
            text_draw = ImageDraw.Draw(text_img)
            if direction == "horizontal":
                text_draw.text((0, (adjusted_height - text_height) // 2), new_text, font=font_obj, fill=new_color)
            else:
                for i, char in enumerate(new_text):
                    char_img = Image.new('RGBA', (text_width, char_height), (255, 255, 255, 0))
                    char_draw = ImageDraw.Draw(char_img)
                    char_draw.text((0, 0), char, font=font_obj, fill=new_color)
                    text_img.paste(char_img, (0, i * char_height))

            text_img_tk = ImageTk.PhotoImage(text_img)

            self.canvas.itemconfig(item, image=text_img_tk)
            self.text_images[item] = text_img_tk

            self.text_info[item]['text'] = new_text
            self.text_info[item]['font'] = selected_font_full
            self.text_info[item]['color'] = new_color
            self.text_info[item]['direction'] = direction
        else:
            messagebox.showerror("알림", "문자 크기가 없습니다.")
            return
        popup.destroy()

    def delete_text(self, popup, item):
        self.canvas.delete(item)
        del self.text_info[item]
        popup.destroy()

    def close_window(self):
        if self.text_info and self.text_info != self.original_text_info:
            result = messagebox.askyesnocancel("경고", "저장되지 않은 텍스트가 있습니다. 저장하시겠습니까?")
            if result:
                self.save_image()
            elif result is None:
                return
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)
        self.root.mainloop()


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageEditor(root)

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # 창의 크기를 설정
    window_width = screen_width // 5 * 4
    window_height = screen_height // 5 * 4
    root.geometry(f"{window_width}x{window_height}")

    # 화면 중앙 배치
    x_position = (screen_width - window_width) // 2
    y_position = (screen_height - window_height) // 5
    root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
    root.resizable(False, False)
    app.run()
