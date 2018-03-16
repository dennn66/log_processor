import yaml

import sys
import getopt

import numpy as np
import pandas as pd

import datetime as dt
import dateutil as du
import pytz

import os

import paramiko

import time
from collections import OrderedDict

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
    radius_log_path: str
    tmp_path: str
    log_path: str
    city: City
    from_date: dt.datetime
    to_date: dt.datetime
    username : str
    raw_df : pd.DataFrame
    ssh_user : User

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

        if self.username == '':
            print("\nAll usernames")
        else:
            username_tag = self.tags.get('User-Name')
            self.raw_df = self.raw_df[self.raw_df[username_tag] == self.username]
            print("\nUsername:" + self.username)
        # df = df.drop('username', 1)
        return self.raw_df

    def parselogs(self):
        start = time.time()

        sources = self.city.bras_sources  #config.get('collectors').get(city).get('bras_sources')
        remote_logpath =  self.city.logpath #config.get('collectors').get(city).get('logpath')
        radius_log_path = self.radius_log_path #config.get('radius_log_path')
        collector_hosts = self.city.collector_hosts #config.get('collectors').get(city).get('collector_hosts')

        privatekeyfile = self.ssh_user.key #config.get('ssh_user').get('privatekeyfile')
        username = self.ssh_user.username #config.get('ssh_user').get('username')

        period = self.to_date - self.from_date + dt.timedelta(days=1)
        df2 = pd.DataFrame()

        for host in collector_hosts:
            mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
            try:
                transport = paramiko.Transport((host.ip, 22))
                transport.connect(username=username, pkey=mykey)
                sftp = paramiko.SFTPClient.from_transport(transport)

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

                        remote_filename = remote_logpath + "%04d" % logdate.year + "%02d" % logdate.month + "-" + source + "/" + \
                                          "%04d" % logdate.year + "%02d" % logdate.month + "%02d" % logdate.day + ".acct"

                        try:
                            rsize = sftp.stat(remote_filename).st_size
                            # print('remote file exists')
                            try:
                                if rsize != os.stat(local_filename).st_size:
                                    # print("wrong size")
                                    raise FileNotFoundError
                                # print('local file exist')

                            except:
                                print('loading remote file ...')
                                sftp.get(remote_filename, local_filename)

                            df = self.parsefile(local_filename)
                            if df.size > 0:
                                df2 = pd.concat([df2, df], verify_integrity=False)
                        except IOError:
                            pass
                sftp.close()
                transport.close()
            except paramiko.SSHException:
                print('Host: ' + str(host) + " connection Error")
                for day in range(0, period.days):
                    logdate = self.from_date + dt.timedelta(days=day)
                    for source in sources:

                        local_filename = radius_log_path + '/' + self.city.name + "/" + host.ip + '/' + "%04d" % logdate.year + "%02d" % logdate.month + "-" + source + "/" + \
                                         "%04d" % logdate.year + "%02d" % logdate.month + "%02d" % logdate.day + ".acct"
                        try:
                            os.stat(local_filename)
                            df = self.parsefile(local_filename)
                            if df.size > 0:
                                df2 = pd.concat([df2, df], verify_integrity=False)

                        except:
                            pass
        if len(df2) > 0:
            df2.Timestamp = pd.to_numeric(df2.Timestamp, errors='ignore', downcast='integer')
            df2['tsutc'] = pd.to_datetime(df2['Timestamp'], unit='s')
            df2['tsutc'] = df2['tsutc'].apply(lambda x: pytz.timezone("UTC").localize(x))
            df2['tsutc'] = df2['tsutc'].apply(
                lambda x: x.astimezone(pytz.timezone(self.city.timezone)))
            df2 = df2.set_index(self.index)
        print('Parsing time: {:.2f} seconds'.format(time.time() - start))
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
        return df2

    def parsefile(self, filename):
        print("l:" + filename)
        ids = []
        id = "unknown"
        skip = False

        # Create dataframe
        df2 = pd.DataFrame()
        try:
            raw_data = open(filename, 'rt')
        except:
            return df2

        for x in raw_data:
            x = x.strip()
            if x[0:2] == "id":
                if x[0:5] == "id=2;":
                    print(x)
                if 'df' in locals():
                    df2 = df2.append(df, ignore_index=True)
                    # print('append ' + str(df))
                    del df
                [id, date, timestamp] = x.split(";")
                [tag, id] = id.split("=")
                if False:
                    # if id in ids:
                    skip = True
                else:
                    skip = False
                    ids = ids + [id]
                    df = self.createdataframe()

            elif not skip:
                if len(x) > 0:
                    [tag, value] = x.split(" = ")
                    tag = self.tags.get(tag.strip())
                    if tag != None:
                        if tag in self.counters:
                            statmode = int(value[:6], 16)
                            value = int(value[7:], 16)
                            if self.traffic_types.get(statmode) != None:
                                df[(self.traffic_types.get(statmode), tag)] += value
                        elif tag in self.index:
                            df[tag] = value
                        else:
                            if self.dims != None:
                                if tag in self.dims:
                                    df[tag] = value
        raw_data.close

        if 'df' in locals():
            # print('append ' + str(df))
            df2 = df2.append(df, ignore_index=True)
            del df
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

            t = time.time().is_integer()
            writer = pd.ExcelWriter(self.tmp_path + '/output_' + str(time.time()) + '.xlsx')
            summary.to_excel(writer, 'summary')  # , engine='xlwt')
            resampled.to_excel(writer, 'traffic_hourly')  # , engine='xlwt')
            traffic.to_excel(writer, 'traffic_by_updates')  # , engine='xlwt')
            counters = self.raw_df.copy()
            counters = counters[(counters.tsutc > self.from_date) & (counters.tsutc < self.to_date)]
            counters.to_excel(writer, 'counters')  # , engine='xlwt')

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

            if self.dims != None:
                dim_groups = traffic.groupby(self.dims)
                # print( dims)
                for name, dim_group in dim_groups:
                    dim_group = dim_group.drop(self.dims, 1)
                    print("----------------------------------------")
                    print(name)
                    print("==============================")
                    dim_group = dim_group.resample('60Min').sum().fillna(0).sort_index()
                    if len(self.dims) > 1:
                        for dim_number in range(0, len(self.dims)):
                            dim_group[('dims', self.dims[dim_number])] = name[dim_number]
                    else:
                        dim_group[('dims', self.dims[0])] = name
                    resampled = resampled.append(dim_group)
            else:
                resampled = traffic.resample('60Min').sum().fillna(0).sort_index()

            resampled.fillna(0, inplace=True)
            resampled.sort_index()
            # resampled = trafic[from_date:to_date]


            traffic_summary_index = []

            for counter in self.counters:
                resampled[('traffic_summary', counter)] = 0
                traffic_summary_index += [('traffic_summary', counter)]
                for traffic_type in self.traffic_types:
                    if self.traffic_types[traffic_type] in self.traffic_summary:
                        resampled[('traffic_summary', counter)] += resampled[(self.traffic_types[traffic_type], counter)]

            idx = self.createindex()
            traffic_summary_index = idx + traffic_summary_index

            resampled.to_excel(writer, 'traffic_hourly')  # , engine='xlwt')

            summary = pd.DataFrame(resampled.loc[:, traffic_summary_index].sum())
            summary.reset_index(inplace=True)

            summary = summary.pivot(index='level_0', columns='level_1', values=0)

            summary.to_excel(writer, 'summary')  # , engine='xlwt')

            writer.save()

        else:
            print("no data found")


def main(argv):
    info = argv[0]+' -p <from_date>-<to_date> -u <username> \n'+\
        'Example: \n'+\
        argv[0]+' -p 01.09.2017-01.10.2017 -u 10.0.0.1\n'+\
        argv[0]+' -p 01.09.2017/01:00:00-01.10.2017/23:59:59 -u 10.0.0.1'



    username = ''
    #username = '46.52.244.220'
    from_date_s = "29.01.2018 10:40:00+05:00"
    to_date_s = "29.01.2018 12:00:00+05:00"
    city_name = 'tula'
    settings = '../../conf/logparser.yaml'
    radius_log_path = '../../radius-logs'
    tmp_path = '../../tmp'
    log_path = '../../log'

    try:
        opts, args = getopt.getopt(argv[1:], "hp:u:c:s:", ["period=", "username=", "city=", "settings="])
    except getopt.GetoptError:
        print( info)
        sys.exit(2)

    for opt, arg in opts:
        if opt == "-h":
            print( info)
            sys.exit()
        elif opt in ("-p", "--period"):
            from_date_s, to_date_s = arg.split("-")
        elif opt in ("-u", "--username"):
            username = arg
        elif opt in ("-c", "--city"):
            city_name = arg
        elif opt in ("-s", "--settings"):
            settings = arg

    with open(settings, 'r') as stream:
        try:
            config = yaml.load(stream)
        except yaml.YAMLError as exc:
            print("Error in config file " + settings)
            print(exc)
            sys.exit(2)



    parser = Parser( radius_log_path, tmp_path, log_path, config.get('parser_config'))
    parser.ssh_user = User(config.get('ssh_user').get('username'), config.get('ssh_user').get('privatekeyfile'))
    parser.city = City(city_name, config.get('collectors').get(city_name).get('timezone'), config.get('collectors').get(city_name).get('logpath'))
    parser.city.load(config)
    parser.set_filter(from_date_s, to_date_s, username)
    parser.read_data()
    parser.save()


    print(parser)



    '''
    for city_conf in config.get('collectors'):
        if city_conf == city_name :
            city = City(city_conf, config.get('collectors').get(city_conf).get('timezone'))
            for collector_ip in config.get('collectors').get(city_conf).get('collector_hosts'):
                print(collector_ip)
                print(config.get('collectors').get(city_conf).get('logpath'))

'''


if __name__ == '__main__':
    main(sys.argv[0:])
