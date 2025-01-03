import click

import rclone_decrypt.decrypt as decrypt
import rclone_decrypt.gui as GUI


help_str_config = f'''config file. default config file is:
                   {decrypt.default_rclone_conf_dir}'''
help_str_output = f'''output dir in which to put files. default folder is:
                   {decrypt.default_output_dir}'''


@click.command()
@click.option(
    "--config",
    help=help_str_config,
    default=decrypt.default_rclone_conf_dir,
    required=True,
)
@click.option("--files", help="dir or file to decrypt", default=None)
@click.option(
    "--output_dir",
    help=help_str_output,
    default=decrypt.default_output_dir,
)
@click.option("--gui", help="start the GUI", is_flag=True, default=False)
@click.option("--gui_debug", help="print debug messages", is_flag=True,
              default=False)
def cli(config, files, output_dir, gui, gui_debug):
    if gui is True:
        GUI.start_gui(gui_debug)
    else:
        try:
            if files is None:
                raise ValueError("files cannot be None")
            else:
                decrypt.decrypt(files, config, output_dir)

        except ValueError as err:
            decrypt.print_error(err)


if __name__ == "__main__":
    cli()
