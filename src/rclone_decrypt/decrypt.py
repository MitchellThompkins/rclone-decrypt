import os
import rclone
import re
import tempfile

from statemachine import StateMachine, State

default_output_dir = "out"

# TODO(mitchellthompkins): This won't work on windows, check the rclone
# documentation for the windows default location
default_rclone_conf_dir = os.path.join(
    os.environ["HOME"], ".config", "rclone", "rclone.conf"
)


class ConfigFileError(Exception):
    def __init__(self, *args, **kwargs):
        default_message = """There is a problem with the rclone
        configuration file"""

        if not args:
            args = (default_message,)

        # Call super constructor
        super().__init__(*args, **kwargs)


def print_error(msg: str) -> None:
    """
    Print generic error.
    """
    print(f"ERROR: {msg}")


class ConfigWriterControl(StateMachine):
    searching_for_start = State(initial=True)
    type_check = State()
    writing = State()
    completed = State(final=True)

    search = searching_for_start.to(searching_for_start)
    validate = searching_for_start.to(type_check)
    is_valid = type_check.to(writing)
    is_invalid = type_check.to(searching_for_start)
    write = type_check.to(writing) | writing.to(writing)
    write_complete = writing.to(searching_for_start)
    complete = searching_for_start.to(completed) | writing.to(completed)

    def __init__(self, cfg_file: str) -> None:
        self.cfg_file = cfg_file
        self.cached_entry_start = None

        super(ConfigWriterControl, self).__init__()

    def before_validate(self, line: str) -> None:
        self.cached_entry_start = line

    def before_write(self, line: str) -> None:
        self.cfg_file.write(line)

    def before_is_valid(self, line: str) -> None:
        self.cfg_file.write(self.cached_entry_start)
        self.cfg_file.write(line)


def get_rclone_instance(config: str, files: str,
                        remote_folder_name: str) -> rclone.RClone:
    """
    Opens a config file and strips out all of the non-crypt type entries,
    modifies the remote to be local directory.

    Returns an rclone instance.
    """
    rclone_instance = None

    try:
        with open(config, "r") as f:
            config_file = f.readlines()

            with tempfile.NamedTemporaryFile(mode="wt", delete=True)\
                    as tmp_config_file:

                with open(tmp_config_file.name, "w") as config:
                    config_state = ConfigWriterControl(config)

                    for line in config_file:
                        if config_state.current_state.id ==\
                                "searching_for_start":
                            start_of_entry = re.search("\\[.*?\\]", line)

                            if start_of_entry is not None:
                                config_state.validate(line)
                            else:
                                config_state.search()

                        elif config_state.current_state.id == "type_check":
                            entry_type = re.search(
                                    "type\\s*=\\s*([\\S\\s]+)", line)
                            if entry_type is not None:
                                entry_type = entry_type.group(1).strip()
                                if entry_type == "crypt":
                                    config_state.is_valid(
                                            f"type = {entry_type}\n")
                                else:
                                    config_state.is_invalid()

                        elif config_state.current_state.id == "writing":
                            remote = re.search(
                                    "remote\\s*=\\s*([\\S\\s]+)", line)
                            if remote is not None:
                                config_state.write(
                                    f"remote =\
                                        {remote_folder_name}/\n"
                                )

                            elif line == "\n":
                                config_state.write(line)
                                config_state.write_complete()

                            else:
                                config_state.write(line)

                    config_state.complete()

                # Open the modified temporary file and create our instance
                with open(tmp_config_file.name, "r") as t:
                    o = t.read()
                    rclone_instance = rclone.with_config(o)

        # I think that given a file, any file, rclone.with_config() will always
        # return _something_ as it doesn't validate the config file
        if rclone_instance is None:
            raise ConfigFileError("The rclone instance was not created.")

    except FileNotFoundError as err:
        print_error(err)

    return rclone_instance


def rclone_copy(rclone_instance: rclone.RClone, output_dir: str) -> None:
    """
    Calls the rclone copy function via a shell instance and places the
    decrypted files into the output_dir
    """
    # convert list of remotes in str format into a list
    remotes = rclone_instance.listremotes()["out"].decode().splitlines()

    for r in remotes:
        rclone_instance.copy(f"{r}", f"{output_dir}")
        # TODO(@mitchellthompkins): rclone.copy still returns 0 for an
        # unsuccessful decryption. As long as the call itself doesn't fail, it
        # will return 0.  Need to come up with someway to detect success
        # if success['code'] == 0:
        #    break


def decrypt(
    files: str,
    config: str = default_rclone_conf_dir,
    output_dir: str = default_output_dir
        ) -> None:
    """
    Sets up the files or directories to be decrypted by moving them to the
    correct relative path. The appropriate temporary config file is generated
    and the appropriate rclone_copy function is then called to perform the
    decryption.

    Explicitly, this creates a temporary directory at the same root as where
    this is called from, moves the files (or file) to be decrypted to that
    directory, modifies a temporary config file in order to point rclone to a
    folder in _this_ directory, calls `rclone --config config file copy
    remote:local_tmp_dir out` and then moves the files back to their original
    location.
    """
    try:
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir_name:
            rclone_instance = get_rclone_instance(config, files, temp_dir_name)

            if rclone_instance is None:
                raise ConfigFileError("rclone_instance cannot be None")

            if output_dir is default_output_dir:
                # If no output_dir is provided, put the de-crypted file into a
                # folder called 'out' that lives at the same base dir as that
                # of the input file
                base_file_dir = os.path.basename(
                        os.path.dirname(files))

                file_input_dir = os.path.dirname(
                        os.path.abspath(base_file_dir))

                output_dir = os.path.join(file_input_dir, output_dir)

            # if the output folder doesn't exist, make it
            if not os.path.isdir(output_dir):
                os.mkdir(output_dir)

            # When folder names are encrypted, I don't think that the config
            # file can look wherever it wants in a sub directory, so the folder
            # we're looking for must live in the same root directory as where
            # rclone is called from
            actual_path = os.path.abspath(files)
            dir_or_file_name = os.path.basename(actual_path)
            temp_file_path = os.path.join(temp_dir_name, dir_or_file_name)

            # Move the folder
            os.rename(actual_path, temp_file_path)

            try:
                # Do the copy, we wrap this in a try in case the user
                # interrupts the process, otherwise the file won't be
                # moved back
                rclone_copy(rclone_instance, output_dir)
            except KeyboardInterrupt:
                print("\n\tterminated rclone copy!")

            # Move it back
            os.rename(temp_file_path, actual_path)

    except ConfigFileError as err:
        print_error(err)
