import logging
import os
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
)

import rclone_decrypt.decrypt as decrypt

# Configure logging (similar to original)
logging.basicConfig(
    filename="/tmp/rclone-decrypt-warning.log", level=logging.DEBUG
)


def start_gui(debug: bool = False):
    def main(page: Page):
        page.title = "rclone-decrypt"
        page.window_width = 800
        page.window_height = 600
        page.padding = 20
        page.theme_mode = ft.ThemeMode.LIGHT

        # State
        files_to_decrypt: List[str] = []
        config_file_path = decrypt.default_rclone_conf_dir
        output_dir_path = decrypt.default_output_dir
        
        # UI Elements
        
        # Config File Selection
        config_file_field = TextField(
            label="Config File",
            value=config_file_path,
            expand=True,
            read_only=True,
        )

        def pick_config_result(e: FilePickerResultEvent):
            nonlocal config_file_path
            if e.files:
                config_file_path = e.files[0].path
                config_file_field.value = config_file_path
                page.update()

        config_picker = FilePicker(on_result=pick_config_result)
        page.overlay.append(config_picker)

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

        # Output Directory Selection
        output_dir_field = TextField(
            label="Output Directory",
            value=output_dir_path,
            expand=True,
            read_only=True,
        )

        def pick_output_result(e: FilePickerResultEvent):
            nonlocal output_dir_path
            if e.path:
                output_dir_path = e.path
                output_dir_field.value = output_dir_path
                page.update()

        output_picker = FilePicker(on_result=pick_output_result)
        page.overlay.append(output_picker)

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

        # Files List
        files_list_view = ListView(expand=True, spacing=10, padding=10)

        def remove_file(path_to_remove):
            if path_to_remove in files_to_decrypt:
                files_to_decrypt.remove(path_to_remove)
                update_files_list()

        def update_files_list():
            files_list_view.controls.clear()
            for f in files_to_decrypt:
                files_list_view.controls.append(
                    Row(
                        controls=[
                            Text(f, expand=True),
                            IconButton(
                                icon=icons.DELETE,
                                icon_color=colors.RED,
                                on_click=lambda e, path=f: remove_file(path),
                            ),
                        ]
                    )
                )
            page.update()

        # Drag and Drop Handler
        def file_picker_result(e: FilePickerResultEvent):
            if e.files:
                for f in e.files:
                    if f.path not in files_to_decrypt:
                        files_to_decrypt.append(f.path)
                update_files_list()
        
        # Native OS Drag and Drop (if supported by Flet on the platform)
        # Note: Flet's `on_file_drop` handles this.

        # Decrypt Action
        status_text = Text("")

        def decrypt_click(e):
            status_text.value = "Decrypting..."
            page.update()
            
            try:
                for f in files_to_decrypt:
                    # Strip potential extra quotes if dragged/dropped might add them
                    # though Flet usually handles paths cleanly.
                    clean_path = f.strip('"\'') 
                    decrypt.decrypt(clean_path, config_file_path, output_dir_path)
                
                status_text.value = "Decryption Complete!"
                status_text.color = colors.GREEN
            except Exception as ex:
                err_msg = f"Error: {ex}"
                status_text.value = err_msg
                status_text.color = colors.RED
                
                # Log error
                err_logger = logging.getLogger(__name__)
                now = datetime.now()
                trace = traceback.format_exc()
                err_logger.error(f"{now} \n {trace}")
                if debug:
                    print(trace)

            page.update()


        decrypt_button = ElevatedButton(
            "Decrypt Files",
            icon=icons.LOCK_OPEN,
            on_click=decrypt_click,
            style=ft.ButtonStyle(
                color=colors.WHITE,
                bgcolor=colors.BLUE,
            )
        )

        # Layout
        page.add(
            Text("Rclone Decrypt", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            config_row,
            output_row,
            Text("Files to Decrypt (Drag and drop files here):"),
            ft.Container(
                content=files_list_view,
                border=ft.border.all(1, colors.OUTLINE),
                border_radius=5,
                height=200, # Fixed height for the list area
            ),
            Row([decrypt_button], alignment=ft.MainAxisAlignment.CENTER),
            status_text,
        )

        # Handle file drop
        def on_drop(e: ft.FilePickerResultEvent):
             # Flet on_file_drop event returns a FilePickerResultEvent-like object 
             # but strictly speaking it's a specific event type, however we might need to parse it.
             # Actually, page.on_file_drop passes a FileDropEvent
             pass

        # Since Flet 0.21.0, page.on_file_drop is the way for drag and drop
        def page_on_drop(e: ft.FileDropEvent):
            # e.files is a list of FileDropEventFile
            for f in e.files:
                path = f.path
                if path not in files_to_decrypt:
                    files_to_decrypt.append(path)
            update_files_list()

        page.on_file_drop = page_on_drop


    ft.app(target=main)

if __name__ == "__main__":
    start_gui()