import logging
import os
import tempfile
import traceback
from datetime import datetime
from typing import List

import flet as ft
from flet import (
    Column,
    ElevatedButton,
    FilePicker,
    FilePickerResultEvent,
    IconButton,
    ListView,
    Page,
    Row,
    Text,
    TextField,
    colors,
    icons,
    Container,
)

import rclone_decrypt.decrypt as decrypt

# Configure logging
# We will use a custom handler, so basicConfig here might be redundant if we
# want to capture everything but we'll keep it for file logging.
log_path = os.path.join(tempfile.gettempdir(), "rclone-decrypt-warning.log")
logging.basicConfig(filename=log_path, level=logging.DEBUG)


class GuiLogHandler(logging.Handler):
    def __init__(self, log_widget):
        super().__init__()
        self.log_widget = log_widget

    def emit(self, record):
        log_entry = self.format(record)
        # Append to the TextField value
        if self.log_widget.value:
            self.log_widget.value += "\n" + log_entry
        else:
            self.log_widget.value = log_entry

        # Only update if the widget is attached to a page
        if self.log_widget.page:
            self.log_widget.update()


def start_gui(debug: bool = False):
    def main(page: Page):
        page.title = "rclone-decrypt"
        page.window_width = 800
        page.window_height = 575
        page.window_min_width = 800
        page.window_max_width = 800
        page.window_min_height = 575
        page.window_max_height = 575
        page.window_maximizable = False
        page.padding = 20
        page.theme_mode = ft.ThemeMode.LIGHT

        # --- Logs Dialog ---
        log_field = TextField(
            read_only=True,
            multiline=True,
            text_style=ft.TextStyle(font_family="monospace"),
            expand=True,
            border=colors.TRANSPARENT,
        )
        log_dialog = ft.AlertDialog(
            title=Text("Logs"),
            content=Container(
                content=log_field,
                width=600,
                height=400,
                border=ft.border.all(1, colors.OUTLINE),
                border_radius=5,
                padding=5,
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda e: page.close_dialog())
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        def show_logs_click(e):
            page.dialog = log_dialog
            log_dialog.open = True
            page.update()

        page.appbar = ft.AppBar(
            title=Text("rclone-decrypt"),
            center_title=False,
            bgcolor=colors.SURFACE_VARIANT,
            actions=[
                IconButton(
                    icons.TERMINAL,
                    tooltip="Show Logs",
                    on_click=show_logs_click,
                ),
            ],
        )

        # State
        files_to_decrypt: List[str] = []
        config_file_path = decrypt.default_rclone_conf_dir
        output_dir_path = decrypt.default_output_dir

        # --- Event Handlers & Pickers ---

        def update_files_list():
            files_list_view.controls.clear()
            if not files_to_decrypt:
                files_list_view.controls.append(Text("No files selected."))
            else:
                for f in files_to_decrypt:
                    files_list_view.controls.append(
                        Row(
                            controls=[
                                IconButton(
                                    icon=icons.CLOSE,
                                    icon_color=colors.GREY_700,
                                    on_click=lambda e, path=f: remove_file(
                                        path
                                    ),
                                    tooltip="Remove from list",
                                ),
                                Text(f, expand=True),
                            ]
                        )
                    )
            page.update()

        def remove_file(path_to_remove):
            if path_to_remove in files_to_decrypt:
                files_to_decrypt.remove(path_to_remove)
                update_files_list()

        # 1. Config Picker
        def pick_config_result(e: FilePickerResultEvent):
            nonlocal config_file_path
            if e.files:
                config_file_path = e.files[0].path
                config_file_field.value = config_file_path
                page.update()

        config_picker = FilePicker(on_result=pick_config_result)
        page.overlay.append(config_picker)

        # 2. Output Picker
        def pick_output_result(e: FilePickerResultEvent):
            nonlocal output_dir_path
            if e.path:
                output_dir_path = e.path
                output_dir_field.value = output_dir_path
                page.update()

        output_picker = FilePicker(on_result=pick_output_result)
        page.overlay.append(output_picker)

        # 3. Add Folder Picker
        def add_folder_result(e: FilePickerResultEvent):
            if e.path:
                # Walk the directory and add all files
                for root, dirs, files in os.walk(e.path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        if full_path not in files_to_decrypt:
                            files_to_decrypt.append(full_path)
                update_files_list()

        add_folder_picker = FilePicker(on_result=add_folder_result)
        page.overlay.append(add_folder_picker)

        # 4. Add Files Picker (Multiple)
        def add_files_result(e: FilePickerResultEvent):
            if e.files:
                for f in e.files:
                    if f.path not in files_to_decrypt:
                        files_to_decrypt.append(f.path)
                update_files_list()

        add_files_picker = FilePicker(on_result=add_files_result)
        page.overlay.append(add_files_picker)

        def add_files_click(e):
            add_files_picker.pick_files(
                allow_multiple=True,
                dialog_title="Select Files to Decrypt",
            )

        def add_folder_click(e):
            add_folder_picker.get_directory_path(
                dialog_title="Select Folder to Decrypt"
            )

        # --- UI Components ---

        # Config Row
        config_file_field = TextField(
            label="Config File",
            value=config_file_path,
            expand=True,
            read_only=True,
        )

        config_row = Row(
            controls=[
                config_file_field,
                ElevatedButton(
                    "Browse",
                    icon=icons.FOLDER_OPEN,
                    on_click=lambda _: config_picker.pick_files(
                        allow_multiple=False, allowed_extensions=["conf"]
                    ),
                ),
            ],
        )

        # Output Row
        output_dir_field = TextField(
            label="Output Directory",
            value=output_dir_path,
            expand=True,
            read_only=True,
        )

        output_row = Row(
            controls=[
                output_dir_field,
                ElevatedButton(
                    "Browse",
                    icon=icons.FOLDER_OPEN,
                    on_click=lambda _: output_picker.get_directory_path(),
                ),
            ],
        )

        # Files List Area
        files_list_view = ListView(expand=True, spacing=5, padding=5)

        # Initialize list
        update_files_list()

        files_area = Column(
            controls=[
                Row(
                    controls=[
                        Text(
                            "Files to Decrypt:",
                            style=ft.TextThemeStyle.TITLE_MEDIUM,
                            expand=True,
                        ),
                        Row(
                            controls=[
                                ElevatedButton(
                                    "Add Files",
                                    icon=icons.ADD,
                                    on_click=add_files_click,
                                ),
                                ElevatedButton(
                                    "Add Folder",
                                    icon=icons.CREATE_NEW_FOLDER,
                                    on_click=add_folder_click,
                                ),
                            ],
                            spacing=10,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                Container(
                    content=files_list_view,
                    border=ft.border.all(1, colors.OUTLINE),
                    border_radius=5,
                    height=150,
                ),
            ]
        )

        # Decrypt Action
        status_text = Text("")

        def decrypt_click(e):
            status_text.value = "Decrypting..."
            status_text.color = colors.BLUE
            page.update()

            try:
                if not files_to_decrypt:
                    status_text.value = "No files to decrypt!"
                    status_text.color = colors.RED
                    page.update()
                    return

                for f in files_to_decrypt:
                    clean_path = f.strip("\"'")
                    # Verify file exists
                    if not os.path.exists(clean_path):
                        print(f"Skipping missing file: {clean_path}")
                        continue

                    decrypt.decrypt(
                        clean_path, config_file_path, output_dir_path
                    )

                status_text.value = "Decryption Complete!"
                status_text.color = colors.GREEN
            except Exception as ex:
                err_msg = f"Error: {ex}"
                status_text.value = err_msg
                status_text.color = colors.RED

                err_logger = logging.getLogger("rclone_decrypt")
                now = datetime.now()
                trace = traceback.format_exc()
                err_logger.error(f"{now} \n {trace}")
                if debug:
                    print(trace)

            page.update()

        decrypt_button = ElevatedButton(
            "Decrypt All Files",
            icon=icons.LOCK_OPEN,
            on_click=decrypt_click,
            style=ft.ButtonStyle(
                color=colors.WHITE,
                bgcolor=colors.BLUE,
            ),
        )

        # Setup Logging
        # Only capture logs from our app and rclone wrapper
        logger = logging.getLogger("rclone_decrypt")
        # Create handler
        gui_handler = GuiLogHandler(log_field)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        gui_handler.setFormatter(formatter)
        logger.addHandler(gui_handler)
        # Set level to capture enough info
        logger.setLevel(logging.INFO)

        # Main Layout
        page.add(
            config_row,
            output_row,
            ft.Divider(),
            files_area,
            ft.Divider(),
            Row([decrypt_button], alignment=ft.MainAxisAlignment.CENTER),
            status_text,
        )
        page.update()

    ft.app(target=main, view=ft.AppView.FLET_APP)


if __name__ == "__main__":
    start_gui()
