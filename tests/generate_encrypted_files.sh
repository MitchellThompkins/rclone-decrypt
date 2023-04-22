#!/bin/bash

cd tests/ && \
rclone --config rclone_encrypt.conf sync raw_files/ crypt0:encrypted_files0/ && \
rclone --config rclone_encrypt.conf sync raw_files/ crypt1:encrypted_files1/ && \
rclone --config rclone_encrypt.conf sync raw_files/ crypt2:encrypted_files2/ && \
cd ..
