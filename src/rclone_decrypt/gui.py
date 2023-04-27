import logging
import os

from tkinter import *
from tkinter import filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD

class DecryptWindow:
    def __init__(self, title:str, geometry:str, debug:bool):
        self.title = title
        self.geometry = geometry
        self.window = TkinterDnD.Tk()
        self.selected_entry = None

        self.debug = debug

        self.browse_button = Button(self.window, text="Browse", command=self.get_directory)
        self.remove_button = Button(self.window, text="Remove", command=self.remove_entry)
        self.decrypt_button = Button(self.window, text="Decrypt", command=self.decrypt)
        self.lb = Listbox(self.window, width=50, height=20)
        self.files = []

    def decrypt(self):
        pass

    def select(self, evt):
        self.selected_entry = self.lb.get(self.lb.curselection())

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

        #self.lb.insert(1, "drag files to here")

        # Listbox
        self.lb.drop_target_register(DND_FILES)
        self.lb.dnd_bind('<<Drop>>', lambda e: self.add_to_list(e.data))
        self.lb.bind('<<ListboxSelect>>',self.select)
        self.lb.pack(pady=20)

        # Button
        self.browse_button.pack(pady=20)
        self.remove_button.pack(pady=20)
        self.decrypt_button.pack(pady=20)

        self.remove_button.pack(pady=20)

        self.window.mainloop()


def start_gui(debug:bool=False):
    title = 'rclone-decrypt'
    geometry = "1000x1000+100+200"

    w = DecryptWindow(title, geometry, debug)
    w.render()


if __name__ == '__main__':
    start_gui()
