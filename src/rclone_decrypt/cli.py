import click
import rclone_decrypt.decrypt as decrypt

@click.command()
@click.option('--config',
        help='config file',
        required=True)
@click.option('--files',
        help='dir to de-crypt',
        default=None)
@click.option('--download',
        help='file or dir to download and de-crypt',
        default=None)
@click.option('--output_dir',
        help='output dir in which to put files',
        default=decrypt.default_output_folder)
def cli(config, files, download, output_dir):
    try:
        if files is None and download is None:
            raise ValueError("files and download cannot be None")
        else:
            instance = decrypt.get_rclone_instance(config)
            decrypt.decrypt(instance, files, output_dir)

    except ValueError as err:
        decrypt.print_error(err)

if __name__ == '__main__':
    cli()
