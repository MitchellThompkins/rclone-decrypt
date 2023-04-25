![example workflow](https://github.com/mitchellthompkins/rclone-decrypt/actions/workflows/main.yml/badge.svg)

# rclone-decrypt
`rclone-decrypt` is a utility which will decrypt files that were encrypted with
[rclone](https://rclone.org/). The anticipated use-case is that a user has
independently downloaded an **encrypted** file or directory directly from a
remote cloud storage (Backblaze B2/Amazon Drive/Dropbox/etc...) and now wants to
decrypt it.

Given a rclone.conf file, this tool is simply a wrapper around `rclone` which
sets up a "local remote" to host the downloaded encrypted files and then calls
`rclone copy` in order to decrypt the files into a desired output folder.

Ostensibly I did this because my family backs-up our local NAS to a remote host
but the rest of my family prefers to download files one-off from the cloud host
and are not comfortable using the rclone CLI. This offers a CLI in addition to
an easy-to-use GUI to make life simple.

**Use at your own risk! Be sure you have copies of anything you're trying to
decrypt, just in case something goes wrong!**

## Requirements

* `rclone` must be installed and in `$PATH`
* Python >= 3.7 (may work with lower versions but this is untested)

## CLI usage
```
> rclone-decrypt --config /path/to/rclone.conf --files /path/to/file/or/dir/
```

Example usages:
```
> rclone-decrypt --config rclone.conf --files /home/my_encrypted_dir
> rclone-decrypt --config rclone.conf --files /0f12hh28evsof1kgflv67ldcn/9g6h49o4ht35u7o5e4iv5a1h28
> rclone-decrypt --config rclone.conf --files /home/my_encrypted_file.bin
```

## GUI usage
TBD

## Development
```
source .venv/bin/activate
python3 -m pytest
deactivate
```

