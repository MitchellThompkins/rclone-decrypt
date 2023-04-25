import click
import rclone_decrypt.decrypt as decrypt

@click.command()
@click.option('--config',
        help='config file',
        required=True)
@click.option('--files',
        help='dir or file to decrypt',
        default=None)
@click.option('--output_dir',
        help='output dir in which to put files',
        default=decrypt.default_output_folder)
def cli(config, files, output_dir):
    try:
        if files is None:
            raise ValueError("files cannot be None")
        else:
            decrypt.decrypt(config, files, output_dir)

    except ValueError as err:
        decrypt.print_error(err)

if __name__ == '__main__':
    cli()
