#!/usr/bin/env python

import argparse
import obspy
import os
from typing import Union
from collections import namedtuple
from obspy import UTCDateTime


def add_zero_if_below_10(val):
    if val < 10:
        ret =  '0'+str(val)
    else:
        ret = str(val)
    return ret


parser = argparse.ArgumentParser(description='This script is made to convert Taurus miniseed structure (file per '
                                             'channel) to Centaur file structure (file per station). '
                                             'Groupping of channels is made only on the basis of filenames. '
                                             'IT DOES NOT TAKE INTO ACCOUNT STARTTIMES OF SEEDS.')
parser.add_argument('-i', '--input_dir', type=str,  required=True, help='Directory containing input miniseeds. '
                                                                       'Must exist.')
parser.add_argument('-o', '--output_dir', type=str, required=True, help='Directory where to save output miniseeds. '
                                                                        'It will be created if necessary.')
parser.add_argument('-r', '--order', type=str, default=None, help='Provide custom channel order in output stream. '
                                                                    'If none, the order will be as found.')
parser.add_argument('-s', '--dirstructure', type=bool, default=False, help='If True, seeds will be saved in dir structure '
                                                                          'as Year/Month/Day/*.mseed')                                                                    
parser.add_argument('-v', '--verbose', type=bool, default=True, help='Print all the steps in stdout?')

args = parser.parse_args()

input_dir = args.input_dir
output_dir = args.output_dir
verbose = args.verbose

SeedStruct = namedtuple('SeedStruct', 'filepath seedid station channel date hour utc')

if not os.path.exists(input_dir):
    raise BaseException("Provided input dir does not exists.")

if not os.path.exists(output_dir):
    if verbose:
        print('Output dir does not exists. Trying to create')
    os.makedirs(output_dir)

walky = list(os.walk(input_dir))

dirs = [os.path.join(input_dir, x) for x in walky[0][1]]

for di in dirs:
    seednames = [x for x in os.listdir(di) if x[-4:] == 'seed']

    seedstructs = []

    curr_output_dir = os.path.join(output_dir, os.path.split(di)[-1])
    curr_output_dir = os.path.join(output_dir, os.path.split(di)[-1])

    if not args.dirstructure:
        os.makedirs(curr_output_dir, exist_ok=True)

    for seedname in seednames:
        filepath = os.path.join(di, seedname)

        seedid, date, hour_seed = seedname.split('_')

        network, station, location, channel = seedid.split('.')

        fullhour, _ = hour_seed.split('.')

        year = int(date[:4])
        month = int(date[4:6])
        day = int(date[6:8])

        hour = int(fullhour[:2])
        minute = int(fullhour[2:4])
        second = int(fullhour[4:6])

        utc = UTCDateTime(year, month, day, hour, minute, second)

        seedstructs.append(SeedStruct(filepath, seedid, station, channel, date, fullhour, utc))

    skippy = []

    for i, seedstruct_one in enumerate(seedstructs):
        if i in skippy:
            continue
        else:
            skippy.append(i)

        if verbose:
            print('Staring to look for cochannels for seed {}'.format(seedstruct_one.filepath))
        
        merging_flag = False

        for j, seedstruct_two in enumerate(seedstructs):
            if j in skippy:
                continue

            if seedstruct_one.utc == seedstruct_two.utc and seedstruct_one.channel != seedstruct_two.channel:
                if verbose:
                    print('I just found first cochannel {}'.format(seedstruct_two.filepath))

                for k, seedstruct_three in enumerate(seedstructs):
                    if k in skippy:
                        continue

                    if seedstruct_one.utc == seedstruct_three.utc \
                            and seedstruct_one.channel != seedstruct_three.channel\
                            and seedstruct_two.channel != seedstruct_three.channel:
                        if verbose:
                            print('I just found second cochannel {}'.format(seedstruct_three.filepath))
                            print('I am starting to merge all channels.')

                        channels = {}
                        channels[seedstruct_one.channel[-1]] = seedstruct_one
                        channels[seedstruct_two.channel[-1]] = seedstruct_two
                        channels[seedstruct_three.channel[-1]] = seedstruct_three
                        

                        st_res = obspy.Stream()

                        if args.order is not None:
                            for ch in args.order:
                                st = obspy.read(channels[ch].filepath)
                                if len(st) > 1:
                                    print('There are few traces in file {}. Will be merged with obspy.Stream.merge('
                                          'method=0, fill_value="interpolate").'.format(channels[ch].filepath))
                                    st.merge(method=0, fill_value='interpolate')
                                    merging_flag = True

                                st_res.append(st[0])
                        else:
                            for ch in channels.values():
                                st = obspy.read(ch.filepath)
                                if len(st) > 1:
                                    print('There are few traces in file {}. Will be merged with obspy.Stream.merge('
                                          'method=0, fill_value="interpolate").'.format(ch.filepath))
                                    st.merge(method=0, fill_value='interpolate')
                                    merging_flag = True

                                st_res.append(st[0])
                        
                        if merging_flag:
                            output_filename = '_'.join([seedstruct_one.seedid[:-4],
                                                        seedstruct_one.date,
                                                        seedstruct_one.hour])
                        else:
                            output_filename = '_'.join([seedstruct_one.seedid[:-4],
                                                        seedstruct_one.date,
                                                        seedstruct_one.hour,
                                                        'merged_traces'])
                        output_filename += '.miniseed'

                        if args.dirstructure:
                            result_dir = os.path.join(output_dir, 
                                                      str(seedstruct_one.utc.year),
                                                      add_zero_if_below_10(seedstruct_one.utc.month),
                                                      add_zero_if_below_10(seedstruct_one.utc.day))
                            os.makedirs(result_dir, exist_ok=True)
                            result_filepath = os.path.join(result_dir, output_filename)
                        else:
                            result_filepath = os.path.join(curr_output_dir, output_filename)

                        if verbose:
                            print('Writting output file {}'.format(result_filepath))

                        st_res.write(result_filepath, format='MSEED')

                        skippy.append(j)
                        skippy.append(k)

if verbose:
    print('Done')
