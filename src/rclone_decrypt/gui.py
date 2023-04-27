import logging
import os

from tkinter import *
from tkinter import filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD

import rclone_decrypt.decrypt as decrypt

class DecryptWindow:
    def __init__(self, title:str, geometry:str, debug:bool):
        self.title = title
        self.geometry = geometry
        self.window = TkinterDnD.Tk()
        self.selected_entry = None

        self.debug = debug
        self.files = []
        self.config_file = decrypt.default_rclone_conf_dir
        self.output_dir = decrypt.default_output_dir

        self.browse_config_button = Button(self.window, text="Browse", command=self.get_config)
        self.remove_button = Button(self.window, text="Remove Selected", command=self.remove_entry)
        self.decrypt_button = Button(self.window, text="Decrypt", command=self.decrypt)
        self.lb = Listbox(self.window, width=50, height=10)

        self.config_entry = Text(self.window, height = 1, width = 50)
        self.config_entry.insert(END, self.config_file)
        self.config_entry.config(state=DISABLED)

    def decrypt(self):
        #for f in self.files:
        #    decrypt.decrypt(f, config, output_dir)
        pass

    def select(self, evt):
        self.selected_entry = self.lb.get(self.lb.curselection())

    def get_config(self):
        file = filedialog.askopenfile(mode ='r', filetypes =[('rclone config', '*.conf')])
        if file:
            self.config_file = os.path.abspath(file.name)

    def get_directory(self):
        file = filedialog.askopenfile(mode='r')
        if file:
            self.add_to_list(os.path.abspath(file.name))

    def add_to_list(self, path):
        if path not in self.files:
            self.files.append(path)
            self.lb.insert(END, path)
        else:
            if self.debug:
                logging.warning(f'{path} already in list.')

    def remove_entry(self):
        if self.selected_entry is not None:
            self.files.remove(self.selected_entry)

            entry = self.lb.get(0, END).index(self.selected_entry)
            self.lb.delete(entry)
            self.selected_entry = None

    def render(self):
        self.window.title(self.title)
        self.window.geometry(self.geometry)

        config_label = Label(self.window, text="Select a config file:" )
        config_label.pack(pady=5)

        self.config_entry.pack(pady=5)

        instruction_label = Label(self.window, text="Drag files below or find with Browse" )
        instruction_label.pack(pady=5)

        # File control buttons
        self.browse_config_button.pack(pady=20, side=LEFT)
        self.remove_button.pack(pady=20, side=RIGHT)

        # Listbox
        self.lb.drop_target_register(DND_FILES)
        self.lb.dnd_bind('<<Drop>>', lambda e: self.add_to_list(e.data))
        self.lb.bind('<<ListboxSelect>>',self.select)
        self.lb.pack(pady=20)

        # Button
        self.decrypt_button.pack(pady=20)

        self.window.mainloop()


def start_gui(debug:bool=False):
    title = 'rclone-decrypt'
    geometry = "1000x1000+100+200"

    w = DecryptWindow(title, geometry, debug)
    w.render()


if __name__ == '__main__':
    start_gui()
