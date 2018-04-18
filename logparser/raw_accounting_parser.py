
import sys

import numpy as np
import pandas as pd

import datetime as dt
import dateutil as du
import pytz

import os
import paramiko


import time
#from collections import OrderedDict

class City:
    name = ''
    timezone = ''
    logpath = '/opt/fr.krus/acct/'

    def __init__(self,  city_name : str, city_timezone : str, logpath: str):
        self.name = city_name
        self.timezone = city_timezone
        self.collector_hosts = []
        self.bras_sources = []
        self.logpath = logpath

    def add_bras_source(self, source_ip : str):
        self.bras_sources += [source_ip]

    def add_collector(self, collector_ip : str, collector_log_path : str):
        self.collector_hosts += [Collector(collector_ip, collector_log_path)]

    def load(self, config):
        for city_conf in config.get('collectors'):
            if city_conf == self.name:
                for collector_ip in config.get('collectors').get(city_conf).get('collector_hosts'):
                    self.add_collector(collector_ip, config.get('collectors').get(city_conf).get('logpath'))
                for bras_source in config.get('collectors').get(city_conf).get('bras_sources'):
                    self.add_bras_source(bras_source)

    def __str__(self):
        return self.name

class Collector:
    ip = ''
    def __init__(self,  collector_ip : str, collector_log_path : str):
        self.ip = collector_ip
        self.logpath = collector_log_path

    def __str__(self):
        return self.ip

class User:
    username = ''
    key = ''
    def __init__(self, usr : str, key_file: str ):
        self.username = usr
        self.key = key_file

    def __str__(self):
        return self.username


class Parser:
    def __init__(self, radius_log_path : str,  tmp_path : str, log_path : str, parser_config):
        self.radius_log_path = radius_log_path
        self.tmp_path = tmp_path
        self.log_path = log_path
        self.city = None
        self.tags = parser_config.get('tags')
        self.dims = parser_config.get('dims')
        self.counters = parser_config.get('counters')
        self.index = parser_config.get('index')
        self.traffic_types = parser_config.get('traffic_types')
        self.traffic_summary = parser_config.get('traffic_summary')

    def __init__(self, config,  request):
        print(str(config))
        print(str(request))
        self.radius_log_path = config.get('radius_log_path')
        self.tmp_path = config.get('tmp_path')
        self.log_path = config.get('log_path')
        self.tags = config.get('parser_config')['tags']
        self.dims = config.get('parser_config')['dims']
        self.counters = config.get('parser_config')['counters']
        self.index = config.get('parser_config')['index']
        self.traffic_types = config.get('parser_config')['traffic_types']
        self.traffic_summary = config.get('parser_config')['traffic_summary']

        self.ssh_user = User(config.get('ssh_user').get('username'), config.get('ssh_user').get('privatekeyfile'))
        self.city = City(request.get('city'),
                         config.get('collectors').get(request.get('city')).get('timezone'),
                           config.get('collectors').get(request.get('city')).get('logpath'))
        self.city.load(config)

        self.from_date = self.set_date_tz(request.get('from_date'), self.city.timezone)
        self.to_date = self.set_date_tz(request.get('to_date'), self.city.timezone)
        self.username = request.get('username').strip(' "\'\n\t')

        print("Parsing logs from", self.from_date, "to", self.to_date)
        print('Filtred by username: ' + self.username)
        self.filename = ''
        self.mkdir_if_not_exist(self.radius_log_path)
        self.mkdir_if_not_exist(self.tmp_path)
        self.mkdir_if_not_exist(self.log_path)

    def __str__(self):
        return str(self.city)

    def set_date_tz(self, date_s, tz: str):
        try:
            date_dt = du.parser.parse(date_s, dayfirst=True)
            if date_dt.tzinfo == None:
                localtz = pytz.timezone(tz)
                date_dt = localtz.localize(date_dt)
            return date_dt
        except:
            print("Date ", date_s, " parsing error")
            sys.exit(2)

    def set_filter(self, from_date_s : str, to_date_s: str, username : str):
        self.from_date = self.set_date_tz(from_date_s, self.city.timezone)
        self.to_date = self.set_date_tz(to_date_s, self.city.timezone)
        self.username = username
        print("Parsing logs from", self.from_date, "to", self.to_date)
        print('Filtred by username: ' + username)

    def read_data(self):
        self.raw_df = self.parselogs()
        return self.raw_df

    def compare_and_download(self, sftp, remote_filename, local_filename):
        try:
            rsize = sftp.stat(remote_filename).st_size
            # print('remote file exists')
            try:
                if rsize != os.stat(local_filename).st_size:
                    # print("wrong size")
                    raise FileNotFoundError
                # print('local file exist')
            except:
                print('loading remote file ' + remote_filename)
                sftp.get(remote_filename, local_filename)
        except IOError:
            pass

    def collect_log_files(self):
        radius_logs = set()
        sources = self.city.bras_sources  #config.get('collectors').get(city).get('bras_sources')
        remote_logpath =  self.city.logpath #config.get('collectors').get(city).get('logpath')
        radius_log_path = self.radius_log_path #config.get('radius_log_path')
        collector_hosts = self.city.collector_hosts #config.get('collectors').get(city).get('collector_hosts')

        privatekeyfile = self.ssh_user.key #config.get('ssh_user').get('privatekeyfile')
        username = self.ssh_user.username #config.get('ssh_user').get('username')

        period = self.to_date - self.from_date + dt.timedelta(days=1)

        for host in collector_hosts:
            mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
            try:
                #raise paramiko.SSHException
                transport = paramiko.Transport((host.ip, 22))
                transport.connect(username=username, pkey=mykey)
                sftp = paramiko.SFTPClient.from_transport(transport)
            except paramiko.SSHException:
                print('Host: ' + str(host) + " connection Error")
                sftp = None

            for day in range(0, period.days):
                logdate = self.from_date + dt.timedelta(days=day)
                for source in sources:
                    self.mkdir_if_not_exist(radius_log_path)
                    self.mkdir_if_not_exist(radius_log_path + '/' + self.city.name)
                    self.mkdir_if_not_exist(radius_log_path + '/' + self.city.name + "/" + host.ip)
                    self.mkdir_if_not_exist(
                        radius_log_path + '/' + self.city.name + "/" + host.ip + '/' + "%04d" % logdate.year + "%02d" % logdate.month + "-" + source)

                    local_filename = radius_log_path + '/' + self.city.name + "/" + host.ip + '/' + "%04d" % logdate.year + "%02d" % logdate.month + "-" + source + "/" + \
                                     "%04d" % logdate.year + "%02d" % logdate.month + "%02d" % logdate.day + ".acct"

                    if(sftp != None):
                        remote_filename = remote_logpath + "%04d" % logdate.year + "%02d" % logdate.month + "-" + source + "/" + \
                                          "%04d" % logdate.year + "%02d" % logdate.month + "%02d" % logdate.day + ".acct"
                        self.compare_and_download(sftp, remote_filename, local_filename)

                    try:
                        os.stat(local_filename)
                        radius_logs.add(local_filename)
                    except:
                        pass
        return radius_logs

    def parselogs(self):
        start = time.time()
        radius_logs = self.collect_log_files()
        df2 = pd.DataFrame()

        for local_filename in radius_logs:
            df = self.parsefile(local_filename)
            if df.size > 0:
                df2 = pd.concat([df2, df], verify_integrity=False)

        if len(df2) > 0:
            df2.Timestamp = pd.to_numeric(df2.Timestamp, errors='ignore', downcast='integer')
            df2['tsutc'] = pd.to_datetime(df2['Timestamp'], unit='s')
            df2['tsutc'] = df2['tsutc'].apply(lambda x: pytz.timezone("UTC").localize(x))
            df2['tsutc'] = df2['tsutc'].apply(
                lambda x: x.astimezone(pytz.timezone(self.city.timezone)))
            df2 = df2.set_index(self.index)
        print('Parsing time: {:.2f} seconds'.format(time.time() - start))
        return df2

    def get_timestamp(self, file, position, blocksize, backward=False):
        coursor = position
        if not backward:
            while True:
                file.seek(coursor)
                block = file.read(blocksize)
                lines = block.split('\n')
                size = lines.__len__()
                for line in lines[0:size-1]:
                    if line[0:2] == "id":
                        [id, date, timestamp] = line.split(";")
                        [tag, timestamp] = timestamp.split("=")
                        return (coursor, float(timestamp))
                    line_len = line.__len__()+1
                    file.seek(coursor)
                    tst = file.read(line_len)
                    coursor += line_len
        else:
            while True:
                file.seek(coursor - blocksize)
                block = file.read(blocksize)
                lines = block.split('\n')
                size = lines.__len__()
                for i in range(size-1, 1, -1):
                    line = lines[i]
                    if line[0:2] == "id":
                        [id, date, timestamp] = line.split(";")
                        [tag, timestamp] = timestamp.split("=")
                        line_len = line.__len__() + 1
                        coursor = coursor - line_len + 1
                        file.seek(coursor)
                        tst = file.read(line_len)
                        return (coursor, float(timestamp))
                    line_len = line.__len__()+1
                    file.seek(coursor - line_len + 1)
                    tst = file.read(line_len)
                    coursor -= line_len
        return (-1, 0.0)

    def get_file_position(self, filename, timestamp):

        fsize = os.stat(filename).st_size
        file = open(filename, 'r')
        start_cursor = 0
        end_cursor = fsize

        (position, pos_timestamp) = self.get_timestamp(file, start_cursor, 1024)
        if(position >= 0):
            start_timestamp = (pos_timestamp)
            start_cursor = position


        (position, pos_timestamp) = self.get_timestamp(file, end_cursor, 1024, backward=True)
        if(position >= 0):
            end_timestamp = (pos_timestamp)
            end_cursor = position

        if(timestamp <= start_timestamp):
            return (0,0)

        if(timestamp >= end_timestamp):
            return (fsize, fsize)


        middle = start_cursor
        while True:
            last = middle
            middle = int((end_cursor + start_cursor) / 2)
            (position, pos_timestamp) = self.get_timestamp(file, middle, 1024)
            if(position >= 0):
                if(pos_timestamp > timestamp):
                    end_timestamp = (pos_timestamp)
                    end_cursor = position

                else:
                    start_timestamp = (pos_timestamp)
                    start_cursor = position
            file.seek(int(start_cursor))
            tst = file.read(int(end_cursor - start_cursor + 100))
            if middle == last:
                break

        file.close()
        return (start_cursor, end_cursor)

    def read_in_chunks(self, file_object, chunk_size=1024, start=0, end=0):
        """Lazy function (generator) to read a file piece by piece.
        Default chunk size: 1k."""
        coursor = start
        block_size = chunk_size
        file_object.seek(start)
        while True:
            if (end > 0) and (end - coursor < chunk_size):
                block_size = end - coursor
            if(block_size > 0):
                block = file_object.read(block_size)
                if not block:
                    break
                lines = block.split('\n')
                size = lines.__len__()
                for line in lines[0:size - 1]:
                    line_len = line.__len__() + 1
                    file_object.seek(coursor)
                    yield (line, coursor, line_len)
                    tst = file_object.read(line_len)
                    coursor += line_len

            else:
                break


    def get_value(self, tag, raw_value):
        if tag in self.counters:
            statmode = int(raw_value[:6], 16)
            value = int(raw_value[7:], 16)
            if self.traffic_types.get(statmode) != None:
                return (self.traffic_types.get(statmode), value)
        elif tag in self.index:
            return(tag, raw_value.strip(' "\'\n\t'))
        else:
            if self.dims != None:
                if tag in self.dims:
                    return (tag, raw_value.strip(' "\'\n\t'))
        return (None, None)

    def read_messages(self, file_object, chunk_size=1024, start=0, end=0):
        block_begin = start
        block_end = end
        for (x, coursor, line_len) in self.read_in_chunks(file_object, chunk_size, start, end):
            #oldpos = file_object.tell()
            #file_object.seek(oldpos)
            #block = file_object.read(line_len)
            #file_object.seek(oldpos)
            x = x.strip()
            if x[0:2] == "id":
                if x[0:5] == "id=2;":
                    print(x)
                if 'df' in locals():
                    block_end = coursor-1
                    yield (df, block_begin, block_end)
                    # print('append ' + str(df))
                    del df
                block_begin = coursor
                [id, date, timestamp] = x.split(";")
                [tag, id] = id.split("=")
                df = self.createdataframe()
            else:
                if len(x) > 0:
                    [tag, value] = x.split(" = ")
                    tag = self.tags.get(tag.strip())
                    #tag = self.tags.get(tag.strip())
                    if tag != None:
                        (tag, value) = self.get_value(tag, value)
                        if tag !=  None:
                            df[tag] = value
        if 'df' in locals():
            block_end = coursor - 1
            yield (df, block_begin, block_end)


    def parsefile(self, filename):
        (start, end) = self.get_file_position(filename, self.from_date.timestamp())
        start_pos = start
        (start, end) = self.get_file_position(filename, self.to_date.timestamp())
        end_pos = end
        df2 = pd.DataFrame()
        print("l:" + filename + "; start:" + str(start_pos)+ "; end:" + str(end_pos))

        try:
            f = open(filename, 'r')
        except:
            return df2
        for (df, block_begin, block_end) in self.read_messages(f, 1024, start_pos, end_pos):
            #oldpos = f.tell()
            #f.seek(oldpos)
            #block = f.read(block_end - block_begin)
            #f.seek(oldpos)

            if(self.username != ''):
                df = df[df[self.tags.get('User-Name')] == self.username]
            if df.size > 0:
                df['filename'] = filename
                df['block_begin'] = block_begin
                df['block_end'] = block_end
                df2 = pd.concat([df2, df], verify_integrity=False)

        f.close
        return df2


    def createindex(self):
        col1 = []
        col2 = []
        ttdic = self.traffic_types.values()
        tt = set()
        for val in ttdic:
            tt.add(val)
        for tr_type in tt:
            for ctr in self.counters:
                col1 = col1 + [tr_type]
                col2 = col2 + [ctr]
        return list(zip(col1, col2))

    def createdataframe(self):
        # Column Multi-Index for counters
        col_idx_arr = self.createindex()
        col_idx = pd.MultiIndex.from_tuples(col_idx_arr)

        # Fill counters with 0
        df2 = pd.DataFrame(np.zeros(len(col_idx_arr)).reshape(1, len(col_idx_arr)), columns=col_idx, dtype='int64')

        # Columns  for index and dimentions
        if self.dims != None:
            for dim in self.dims:
                df2[dim] = np.nan
        for ind in self.index:
            df2[ind] = np.nan

        # Columns  for position in logs
        df2['filename'] = np.nan
        df2['block_begin'] = np.nan
        df2['block_end'] = np.nan
        return df2


    def mkdir_if_not_exist(self, path: str):
        try:
            os.mkdir(path)
        except:
            pass

    def save(self):
        if self.raw_df.shape[0] > 0:
            resampled = pd.DataFrame()
            traffic = pd.DataFrame()
            summary = pd.DataFrame()

            self.filename = self.tmp_path + '/output_' + str(time.time()) + '.xlsx'

            writer = pd.ExcelWriter(self.filename)
            summary.to_excel(writer, 'summary')  # , engine='xlwt')
            resampled.to_excel(writer, 'traffic_hourly')  # , engine='xlwt')
            traffic.to_excel(writer, 'traffic_by_updates')  # , engine='xlwt')

            print('writing counters...')
            counters = self.raw_df.copy()
            counters = counters[(counters.tsutc > self.from_date) & (counters.tsutc < self.to_date)]
            counters = counters.sort_values(['username', 'tsutc'], ascending=[True, True])
            counters.to_excel(writer, 'counters')  # , engine='xlwt')

            print('writing trafic by updates...')
            session_key = [self.tags.get('Acct-Session-Id'),
                           self.tags.get('NAS-Identifier')]
            sessions = self.raw_df.groupby(level=session_key)
            for name, session in sessions:
                session.set_index('tsutc', inplace=True)
                session = session.sort_index()
                session.fillna(0, inplace=True)
                col_idx_arr = self.createindex()
                for idx in col_idx_arr:
                    session[idx] = session[idx].diff().shift(0)
                    session.loc[session[idx] < 0, idx] = 0
                session.fillna(0, inplace=True)
                traffic = pd.concat([traffic, session], verify_integrity=False)
            traffic = traffic.loc[(traffic.index > self.from_date) & (traffic.index < self.to_date)]
            traffic_rep = traffic.copy()
            for counter in self.counters:
                traffic_rep[('traffic_summary', counter)] = 0
                for traffic_type in self.traffic_types:
                    if self.traffic_types[traffic_type] in self.traffic_summary:
                        traffic_rep[('traffic_summary', counter)] += traffic_rep[(self.traffic_types[traffic_type], counter)]
            traffic_rep.to_excel(writer, 'traffic_by_updates')  # , engine='xlwt')

            traffic.drop('filename', axis=1, inplace=True)
            traffic.drop('block_begin', axis=1, inplace=True)
            traffic.drop('block_end', axis=1, inplace=True)

            print('writing trafic hourly...')
            if self.dims != None:
                dim_groups = traffic.groupby(self.dims)
                # print( dims)
                for name, dim_group in dim_groups:
                    dim_group = dim_group.drop(self.dims, 1)
                    dim_group = dim_group.resample('60Min').sum().fillna(0).sort_index()
                    if len(self.dims) > 1:
                        for dim_number in range(0, len(self.dims)):
                            dim_group[('dims', self.dims[dim_number])] = name[dim_number]
                    else:
                        dim_group[('dims', self.dims[0])] = name
                    resampled = pd.concat([resampled, dim_group], verify_integrity=False)
            else:
                resampled = traffic.resample('60Min').sum().fillna(0).sort_index()
            resampled.fillna(0, inplace=True)
            resampled.sort_index()
            traffic_summary_index = []
            for counter in self.counters:
                resampled[('traffic_summary', counter)] = 0
                traffic_summary_index += [('traffic_summary', counter)]
                for traffic_type in self.traffic_types:
                    if self.traffic_types[traffic_type] in self.traffic_summary:
                        resampled[('traffic_summary', counter)] += resampled[(self.traffic_types[traffic_type], counter)]
            resampled.to_excel(writer, 'traffic_hourly')  # , engine='xlwt')

            print('writing summary...')
            idx = self.createindex()
            traffic_summary_index = idx + traffic_summary_index
            summary = pd.DataFrame(resampled.loc[:, traffic_summary_index].sum())
            summary.reset_index(inplace=True)
            summary = summary.pivot(index='level_0', columns='level_1', values=0)
            summary.to_excel(writer, 'summary')  # , engine='xlwt')

            print('done ' + self.filename)
            writer.save()

        else:
            print("no data found")
        return self.filename


