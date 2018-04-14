
import yaml
import sys
import getopt


from .raw_accounting_parser import Parser, User, City



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

if __name__ == '__main__':
    main(sys.argv[0:])
