import os 
import tempfile
import csv
import json
import uuid
import random
import warnings
import logging

import torch
import torchaudio
from torch.utils.data import Dataset, DataLoader

import yt_dlp
import soundfile as sf
import librosa

"""
This is a helper file for working with the Acapella Dataset hosted
at [1] and published in [2]. It is a list of youtube videos comprising 
46 hours of solo, non-professional, acapella singing. Each entry 
is a youtube id with some information about the singer and the 
program material (languange, for example).

Download audio dataset using `download_acapellas`.

[1] https://ipcv.github.io/Acappella/acappella/
[2] Montesinos, Juan F., Venkatesh S. Kadandale, and Gloria Haro. 
    “A Cappella: Audio-Visual Singing Voice Separation.” arXiv, 
    October 18, 2021. http://arxiv.org/abs/2104.09946.

"""


# logger setup
logging.basicConfig(filename=os.path.join("log.txt"), 
                    level=10,
                    filemode='w', 
                    format='%(name)s - %(levelname)s - %(message)s')

def get_num_lines(file):
    return sum(1 for _ in open(file))

def parse_time_str(time_str):
    if '.' in time_str:
        minutes, seconds = time_str.split('.')
    else:
        minutes = '0'
        seconds = time_str
    if len(seconds) < 2:
        seconds = seconds + '0'
    
    minutes = int(minutes)
    seconds = int(seconds)
    seconds += 60 * minutes
    return seconds

def download_acapellas(num_entries, destination_dir='.'):
    """Acapellas"""
    data_register = "acapella_info.csv"
    total_num_entries = get_num_lines(data_register)
    entry_row_idxs = random.sample(range(0, total_num_entries), num_entries)

    # read rows
    with open(data_register, 'r') as f:
        reader = csv.DictReader(f)
        rows = [row | {'Idx': idx} for idx, row in enumerate(reader) if idx in entry_row_idxs]

    # download audio
    for row in rows:

        # get identifying fields
        idx = row['Idx']
        url = row['Link']
        id = row['ID']
        
        # get times in seconds
        start_time = parse_time_str(row['Init'])
        end_time = parse_time_str(row['Fin'])

        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': '%(id)s.%(ext)s',
                'paths': {
                    'home': f'{temp_dir}'
                },
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except:
                logging.warning(f'Row {idx} with url {url} could not be downloaded.')
                continue


            # get audio and slice it down to singing
            filepath = os.path.join(temp_dir, f"{id}.mp3")
            audio, sample_rate = sf.read(filepath)
            # force to mono
            if len(audio.shape) > 1:
                audio = audio[:, 0]
            # get time in samples
            start = int(start_time * sample_rate)
            end = int(end_time * sample_rate)
            # slice audio
            audio = audio[start:end]

            # save 
            outfilename = f"{idx}_{id}.mp3"
            outfilepath = os.path.join(destination_dir, outfilename)
            sf.write(outfilepath, audio, sample_rate)

            logging.info(f"Successfully downloaded Row {idx}.")