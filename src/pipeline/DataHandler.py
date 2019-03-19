
import os
import re
import axivity
import pandas as pd
import numpy as np
import time
from utils import zip_utils
from utils import csv_loader




class DataHandler():
    # TODO: change all places pd.read_csv is called to self.load_dataframe_from_csv(...)

    def __init__(self):
        self.name = None
        self.data_unzipped_path = None
        self.data_synched_csv_path = None
        self.data_cleanup_path = None
        self.data_input_folder = os.getcwd() + '../../data/input'
        self.data_output_folder = os.getcwd() + '../../data/output'
        self.data_temp_folder = os.getcwd() + '/../../data/temp'
        self.dataframe_iterator = None

    def unzip_synch_cwa(self, filepath='filepath', temp_dir='working_dir', unzip_cleanup=False):
        self.data_unzipped_path = self.unzip_7z_archive(
            filepath=os.path.join(os.getcwd(), filepath),
            unzip_to_path=self.data_temp_folder,
            cleanup=unzip_cleanup
        )
        self.data_unzipped_path = os.path.relpath(self.data_unzipped_path)

        with axivity.timesynched_csv(self.data_unzipped_path, clean_up=False) as synch_csv:
            print("Saved timesynched csv")

        synched_csv = list(filter(lambda x: 'timesync' in x, os.listdir(self.data_unzipped_path)))
        self.data_synched_csv_path = (self.data_unzipped_path + '/' + synched_csv[0])

        # try:
        #
        #     # Unzip contents of zipfile
        #     # self.name = filepath.split('/')[-1].split('.')[0]
        #     # unzip_to_path = os.path.join(temp_dir, os.path.basename(filepath))
        #     # self.data_cleanup_path = unzip_to_path # store the path to the unzipped folder for easy cleanup
        #
        #
        #
        #
        #
        # except Exception as e:
        #     print("could not unzipp 7z arhcive and synch it", e)


    def unzip_7z_archive(self, filepath, unzip_to_path='../../data/temp', return_inner_dir=True, cleanup=True):
        self._check_paths(filepath, unzip_to_path)
        unzip_to_path = os.path.join(unzip_to_path, os.path.basename(filepath))
        print("UNZIP to PATH inside y7a: ", unzip_to_path)

        unzipped_dir_path = zip_utils.unzip_subject_data(
            subject_zip_path=filepath,
            unzip_to_path=unzip_to_path,
            return_inner_dir=return_inner_dir
        )

        self.data_cleanup_path = unzip_to_path  # store the path to the unzipped folder for easy cleanup
        if cleanup:
            self.cleanup_temp_folder()
        else:
            # TODO: change this to elif and pass in a parameter with default strict or something...
            try:
                os.system("chmod 755 -R {}".format(unzip_to_path))
            except Exception as e:
                print("Could not give easy access rights")

        return unzipped_dir_path



    # TODO: mekk 1 funksjon for å save csv!!!!
    # TODO: bytt ut alle plasser det stpr read csv til load_csv ett eller annet drit i DH
    def merge_multiple_csvs(self, master_csv_path, slave_csv_path, slave2_csv_path, out_path=None,
                            master_columns=['time', 'bx', 'by', 'bz', 'tx', 'ty', 'tz'],
                            slave_columns=['time', 'bx1', 'by1', 'bz1', 'btemp'],
                            slave2_columns=['time', 'tx1', 'ty1', 'tz1', 'ttemp'],
                            rearrange_columns_to=None,
                            merge_how='inner'):

        print("READING MASTER CSV")
        master_df = pd.read_csv(master_csv_path, header=None)
        master_df.columns = master_columns

        print("READING SLAVE CSV")
        slave_df = pd.read_csv(slave_csv_path, header=None)
        slave_df.columns = slave_columns

        print("READING SLAVE2 CSV")
        slave2_df = pd.read_csv(slave2_csv_path, header=None)
        slave2_df.columns = slave2_columns

        # Merge the csvs
        print("MERGING MASTER AND SLAVE CSV")
        merged_df = master_df.merge(slave_df, on='time', how=merge_how).merge(slave2_df, on='time', how=merge_how)

        ## Rearrange the columns
        if not rearrange_columns_to is None:
            print("REARRANGING CSV COLUMNS")
            merged_df = merged_df[rearrange_columns_to]

        if out_path is None:
            master_file_dir, master_filename_w_format = os.path.split(master_csv_path)
            out_path = os.path.join(master_file_dir,
                                    master_filename_w_format.split('.')[0] + '_TEMP_SYNCHED_BT.csv')

        else:
            out_path_dir, out_path_filename = os.path.split(out_path)
            if out_path_filename == '':
                out_path_filename = os.path.basename(master_csv_path).split('.')[0] + '_TEMP_SYNCHED_BT.csv'

            if not os.path.exists(out_path_dir):
                print('Creating output directory... ', out_path_dir)
                os.makedirs(out_path_dir)

            out_path = os.path.join(out_path_dir, out_path_filename)

        # print("SAVING MERGED CSV")
        # print("DONE, here is a sneak peak:\n", merged_df.head(5))
        # print("Saving")
        # merged_df.to_csv(out_path, index=False, float_format='%.6f')
        # print("Saved synched and merged as csv to : ", os.path.abspath(out_path))

        self.dataframe_iterator = merged_df

        # self.data_cleanup_path = os.path.abspath(out_path[:out_path.find('.7z/') + 4])
        # self.data_synched_csv_path = os.path.abspath(out_path)
        # self.name = os.path.basename(out_path)
        # self.data_temp_folder = os.path.abspath(os.path.split(out_path)[0])

    def write_temp_to_txt(self, dataframe=None, dataframe_path=None):

        df = None

        if not dataframe is None:
            df = dataframe
        # 01
        elif dataframe is None and not dataframe_path is None:
            try:
                df = pd.read_csv(dataframe_path)
            except Exception as e:
                print("Did not give a valid csv_path")
                raise e
        # 00
        elif dataframe is None and dataframe_path is None:
            print("Need to pass either dataframe or csv_path")
            raise Exception("Need to pass either dataframe or csv_path")
        # 11 save memory and performance
        elif dataframe and dataframe_path:
            df = dataframe

        print("STARTING weiting temp to file")
        # TODO: change to datafram_iterator??
        # self.dataframe_iterator = df.apply(self.find_temp, axis=0, raw=True)

        for i in ['btemp', 'ttemp']:
            start_time = time.time()
            print('Creating %s txt file' % i)
            nanIndex = list(df[i].index[df[i].apply(np.isnan)])
            valildIndex = list(df[i].index[df[i].notnull()])
            firstLastIndex = [nanIndex[0], nanIndex[-1]]
            print('Validindex len:', len(valildIndex))
            print('nanindex len:', len(nanIndex))
            print('SUM:', int(len(nanIndex) + len(valildIndex)))

            file = open('../../data/temp/4000181.7z/4000181/' + i + '.txt', 'w')
            if firstLastIndex[0] < valildIndex[0]:
                file.write(str(str((float(df.loc[valildIndex[0], i]) * 300 / 1024) - 50) + '\n') * (valildIndex[0] - firstLastIndex[0]))

            for j in range(len(valildIndex) - 1):
                if j % 1000 == 0:
                    print(j)
                if valildIndex[j] + 1 == valildIndex[j + 1]:
                    file.write(str((float(df.loc[valildIndex[j], i]) * 300 / 1024) - 50) + '\n')
                else:
                    file.write(str((float(df.loc[valildIndex[j], i]) * 300 / 1024) - 50) + '\n')
                    file.write(str(str((float(df.loc[valildIndex[j+1], i]) * 300 / 1024) - 50) + '\n') * ((valildIndex[j + 1]) - (valildIndex[j] + 1)))
            if firstLastIndex[1] > valildIndex[-1]:
                file.write(str(str((float(df.loc[valildIndex[-1], i]) * 300 / 1024) - 50) + '\n') * ((firstLastIndex[-1]+1) - valildIndex[-1]))
            else:
                file.write(str((float(df.loc[valildIndex[-1], i]) * 300 / 1024) - 50) + '\n')


            file.close()
            print("---- %s seconds ---" % (time.time() - start_time))

        return self.get_dataframe_iterator()

    def concat_timesynch_and_temp(self, master_csv_path, btemp_txt_path, ttemp_txt_path):

        print("READING MASTER CSV")
        master_df = pd.read_csv(master_csv_path, header=None)
        master_df.columns = ['time', 'bx', 'by', 'bz', 'tx', 'ty', 'tz']

        print("READING SLAVE CSV")
        btemp_df = pd.read_csv(btemp_txt_path, header=None)
        btemp_df.columns = ['btemp']

        print("READING SLAVE2 CSV")
        ttemp_df = pd.read_csv(ttemp_txt_path, header=None)
        ttemp_df.columns = ['ttemp']

        # Merge the csvs
        print("MERGING MASTER AND SLAVE CSV")
        merged_df = pd.concat([master_df, btemp_df, ttemp_df], axis=1,)


        master_file_dir, master_filename_w_format = os.path.split(master_csv_path)
        out_path = os.path.join(master_file_dir, master_filename_w_format.split('.')[0] + '_TEMP_BT.csv')

        self.dataframe_iterator = merged_df

        print("SAVING MERGED CSV")
        print("DONE, here is a sneak peak:\n", merged_df.head(5))
        print("Saving")
        merged_df.to_csv(out_path, index=False, float_format='%.6f')
        print("Saved synched and merged as csv to : ", os.path.abspath(out_path))


    ##########

    def _check_paths(self, filepath, temp_dir):
        # Make sure zipfile exists
        if not os.path.exists(filepath):
            # print(">>>>>>>>: ", 3.1)
            raise RuntimeError('Provided zip file "%s" does not exist' % filepath)
            # Make sure that a working directory for unzipping and time synching also exists
        if not temp_dir:
            # print(">>>>>>>>: ", 3.2)
            raise RuntimeError('A working directory ("-w <directoy name.") must be specified when using --zip-file')
        if not os.path.exists(temp_dir):
            # print(">>>>>>>>: ", 3.3)
            raise RuntimeError('Provided working directory "%s" does not exist' % temp_dir)

    def create_output_dir(self, output_dir_path, name):
        # Create output directory if it does not exist
        self.data_output_folder = os.path.join(output_dir_path, name)
        if not os.path.exists(self.data_output_folder):
            os.makedirs(self.data_output_folder)



    def _get_csv_file(self, filepath):
        '''
        Returns a context for getting csv file, either by a directly specified one
        or through unzipping a provided zip file and synching it with axivity's software
        '''

        # TODO : Rewrite this to support the DataHandler class, and not the old style as below
        # # If a precomputed, timesynched file is available -> use it
        try:
            if not os.path.exists(filepath):
                raise RuntimeError('Provided presynched file "%s" does not exist' % filepath)
            self.name = os.path.splitext(os.path.basename(filepath))[0]
            self.data_synched_csv_path = filepath

        except Exception:
            print("Could not get the csv_file. Check the INPUT DIRECTORY PATH and FILENAME")

    def load_dataframe_from_csv(self, input_directory_path,
                                filename,
                                header=None,
                                columns=['timestamp', 'x', 'y', 'z'],
                                whole_days=False,
                                chunk_size=20000,
                                max_days=6):


        filepath = os.path.join(input_directory_path, filename)
        self._get_csv_file(filepath)

        print("NAME:", self.name)
        print("DSCP: ", self.data_synched_csv_path)

        # Create output directory if it does not exist
        self.create_output_dir(self.data_output_folder, self.name)

        # self.dataframe_iterator = pd.read_csv(self.data_synched_csv_path, header=header, names=columns)

        # # Read csv files in chunks
        if whole_days:
            # Use custom loader that scans to first midnight if --whole-days is enabled
            '''
            if columns is None, the column names must be the first row in the csv!
            else if columns is specifiec, the pd.read_csv will set header param to None, meaning use the first row as data row
            '''
            self.dataframe_iterator = csv_loader.csv_chunker(self.data_synched_csv_path, chunk_size, ts_index=0,
                                                             columns=None, n_days=max_days)

        else:
            # TODO : read up on what the chunksize and parse_dates parameter does
            # Otherwise, just load with pandas
            # self.dataframe_iterator = pd.read_csv(self.data_synched_csv_path, header=None, chunksize=chunk_size,
            #                                       names=columns, parse_dates=[0])
            self.dataframe_iterator = pd.read_csv(self.data_synched_csv_path, header=header, names=columns)


    def load_dataframe_from_7z(self, input_arhcive_path, whole_days=False, chunk_size=20000, max_days=6):

        # Unzipp and synch
        self._get_cwa_files(filepath=input_arhcive_path, temp_dir=self.data_temp_folder)

        # Create output directory if it does not exist
        self.create_output_dir(self.data_output_folder, self.name)

        # Return if no csv file was found
        if self.data_synched_csv_path is None:
            raise Exception("Synched_csv is none")

        print('Got synched csv file:', self.data_synched_csv_path)

        # Read csv files in chunks
        columns = ['timestamp', 'back_x', 'back_y', 'back_z', 'thigh_x', 'thigh_y', 'thigh_z']
        if whole_days:
            # Use custom loader that scans to first midnight if --whole-days is enabled
            self.dataframe_iterator = csv_loader.csv_chunker(self.data_synched_csv_path, chunk_size, ts_index=0,
                                                        columns=columns, n_days=max_days)
        else:
            # Otherwise, just load with pandas
            self.dataframe_iterator = pd.read_csv(self.data_synched_csv_path, header=None, chunksize=chunk_size,
                                             names=columns, parse_dates=[0])

    def get_dataframe_iterator(self):
        return self.dataframe_iterator

    def get_unzipped_path(self):
        return self.data_unzipped_path

    def get_synched_csv_path(self):
        return self.data_synched_csv_path

    def cleanup_temp_folder(self):
        print("Cleaning {}".format(self.data_cleanup_path))
        try:
            zip_utils.clean_up_working_dir(self.data_cleanup_path)
            print("Cleanup SUCCESS")
        except:
            print("Cleanup FAILED")

    def merge_csvs_on_first_time_overlap(self,
                                         master_csv_path,
                                         slave_csv_path,
                                         out_path=None,
                                         merge_column="time",
                                         master_columns=['time', 'bx', 'by', 'bz', 'btemp'],
                                         slave_columns=['time', 'tx', 'ty', 'tz', 'ttemp'],
                                         rearrange_columns_to=None,
                                         save=True,
                                         **kwargs
                                         ):
        '''
        Master_csv is the csv that the first recording is used as starting point

        :param master_csv_path:
        :param slave_csv_path:
        :param out_path:
        :param merge_column: the column name or default Time || can be None
        :param master_columns: the name to give each column in master csv
        :param slave_columns: the name to give each column in master csv
        :param rearrange_columns_to:
        :param save: default True
        :param **kwargs: additional keyword=value arguments, that can be used with the pandas.merge() function
        :return: None
        '''

        # TODO: PASS IN MASTER AND SLAVE COLUMN NAMES
        # TODO change all the pd.read_csv s to use datahandlers own load_from_csv function

        print("READING MASTER CSV")
        master_df = pd.read_csv(master_csv_path)
        master_df.columns = master_columns

        print("READING SLAVE CSV")
        slave_df = pd.read_csv(slave_csv_path)
        slave_df.columns = slave_columns

        # Merge the csvs
        print("MERGING MASTER AND SLAVE CSV")
        merged_df = master_df.merge(slave_df, on=merge_column, **kwargs)

        # print("MASTER SHAPE: {} \n SLAVE SHAPE: {} \n MERGED SHAPE: {}".format(master_df.shape, slave_df.shape, merged_df.shape))

        ## Rearrange the columns
        if not rearrange_columns_to is None:
            print("REARRANGING CSV COLUMNS")
            merged_df = merged_df[rearrange_columns_to]

        if out_path is None:
            master_file_dir, master_filename_w_format = os.path.split(master_csv_path)
            out_path = os.path.join(master_file_dir, master_filename_w_format.split('.')[0] + '_TEMP_SYNCHED_BT.csv')

        else:
            out_path_dir, out_path_filename= os.path.split(out_path)
            if out_path_filename == '':
                out_path_filename = os.path.basename(master_csv_path).split('.')[0] + '_TEMP_SYNCHED_BT.csv'

            if not os.path.exists(out_path_dir):
                print('Creating output directory... ', out_path_dir)
                os.makedirs(out_path_dir)

            out_path = os.path.join(out_path_dir, out_path_filename)

        if save:
            print("SAVING MERGED CSV")
            merged_df.to_csv(out_path, index=False)
            # merged_df.to_csv(out_path, index=False, float_format='%.6f')
            print("Saved synched and merged as csv to : ", os.path.abspath(out_path))


        self.dataframe_iterator = merged_df

        self.data_cleanup_path = os.path.abspath(out_path[:out_path.find('.7z/') + 4])
        self.data_synched_csv_path = os.path.abspath(out_path)
        self.name = os.path.basename(out_path)
        self.data_temp_folder = os.path.abspath(os.path.split(out_path)[0])
        return self.get_dataframe_iterator()



    def convert_column_from_str_to_datetime_test(self, dataframe=None, column_name="time"):
        # TODO if dataframe is actually dataframe object, self.dataframe_iterator = dataframe
        if isinstance(dataframe, str):
            self.dataframe_iterator = pd.read_csv(dataframe)
            print(self.dataframe_iterator.head(5))
            print()
            self.dataframe_iterator.columns = ['time', 'bx', 'by', 'bz', 'tx', 'ty', 'tz', 'btemp', 'ttemp']
        else:
            print("USING THE Datahandlers own dataframe-Instance")

        self.dataframe_iterator[column_name] = pd.to_datetime(self.dataframe_iterator[column_name])
        print(self.dataframe_iterator.dtypes)

    def convert_column_from_str_to_datetime(self, column_name="time"):
        self.dataframe_iterator[column_name] = pd.to_datetime(self.dataframe_iterator[column_name])
        print(self.dataframe_iterator.dtypes)

    def convert_column_from_str_to_numeric(self, column_name="ttemp"):
        self.dataframe_iterator[column_name] = pd.to_numeric(self.dataframe_iterator[column_name])
        print(self.dataframe_iterator.dtypes)

    def set_column_as_index(self, column_name):
        self.dataframe_iterator.set_index(column_name, inplace=True)
        print("The dataframe index is now: ", self.dataframe_iterator.index.name)

    def add_new_column(self, name='label', default_value=np.nan):
        self.dataframe_iterator.insert(len(self.dataframe_iterator.columns), name, value=default_value)
        print(self.dataframe_iterator.describe())

    def add_columns_based_on_csv(self, path, columns_name=['label'], join_type='outer', **kwargs_read_csv):
        df_label = pd.read_csv(path, **kwargs_read_csv)
        df_label.columns = columns_name

        self.dataframe_iterator = pd.concat(objs=[self.dataframe_iterator, df_label], join=join_type, axis=1, sort=False)




    def add_labels_file_based_on_intervals(self, intervals={}, label_mapping={}):
        '''
        intervals = {
            'Label' : [
                        date:YYYY-MM-DD
                        start: HH:MM:SS
                        stop: HH:MM:SS
                    ]
        }

        :param dataframe:
        :param intervals:
        :return:
        '''

        if not intervals:
            print("Faak off, datahandler add_labels_file_based_on_intervals")

        for label in intervals:
            print("label", label)
            for interval in intervals[label]:
                print("INTERVAL", interval)
                date = interval[0]
                start = interval[1]
                end = interval[2]

                start_string = '{} {}'.format(date, start)
                end_string = '{} {}'.format(date, end)
                # get indexes to add label to
                self.dataframe_iterator.loc[start_string:end_string, 'label'] = label

        print(self.dataframe_iterator)

    def read_and_return_multiple_csv_iterators(self, dir_path,
                                               filenames=['back', 'thigh', "labels"],
                                               format='csv',
                                               header=None,
                                               asNumpyArray=True):
        if not filenames:
            raise Exception('Filenames for csv to read cannot be empty')

        csvs = []
        error = []
        regex_base = "[A-Za-z_\-.]*{}[A-Za-z_\-.]*.{}"

        for name in filenames:
            print("Trying to read file: ", name, " @ ", dir_path)
            try:
                filename = [f for f in os.listdir(dir_path) if re.match(regex_base.format(name, format), f, re.IGNORECASE)][0]
                if filename:
                    if asNumpyArray:
                        csvs.append(pd.read_csv(os.path.join(dir_path, filename), header=header).to_numpy)
                    else:
                        csvs.append(pd.read_csv(os.path.join(dir_path, filename), header=header))
            except Exception as e:
                error.append( (name, e) )
            finally:
                for e, err in error:
                    print("Could not find or read file: {} --> {}".format(e, err))
                raise Exception("Something went wrong when reading csvs ")
        print("DONE reading csv's!")
        return csvs

    def get_rows_and_columns(self, dataframe=None, rows=None, columns=None):
        '''
        
        :param dataframe: 
        :param rows: 
        :param columns: 
        :return: 
        '''

        if dataframe is None:
            print("Faak off, datahandler get_rows_and_columns")
            # TODO fix exception

        if rows is None and columns is None:
            return dataframe
        elif rows is None:
            return dataframe.iloc[:, columns]
        elif columns is None:
            return dataframe.iloc[rows, :]
        else:
            return dataframe.iloc[rows, columns]



    def set_active_dataframe(self, dataframe):
        self.dataframe_iterator = dataframe

    def save_dataframe_to_path(self, path, dataframe=None):
        if dataframe is None:
            dataframe = self.get_dataframe_iterator()

        dataframe.to_csv(path)

    def remove_rows_where_columns_have_NaN(self, dataframe=None, columns=[]):
        df = dataframe or self.get_dataframe_iterator()
        if df is None:
            raise Exception("No dataframe detected")

        df.dropna(subset=columns, inplace=True)
        self.set_active_dataframe(df)


    def show_dataframe(self):
        print(self.dataframe_iterator)

    def head_dataframe(self, n=5):
        print(self.dataframe_iterator.head(n))

    def tail_dataframe(self, n=5):
        print(self.dataframe_iterator.tail(n))


    ### FOR REMOVAL! ASK SIGVER FIRST
    #
    #
    #
    #
    ###################################

    def _adc_to_c(self, row, normalize=False):
        if not np.isnan(row['btemp']):
            row['btemp'] = (row['btemp'] * 300 / 1024) - 50
        if not np.isnan(row['ttemp']):
            row['ttemp'] = (row['ttemp'] * 300 / 1024) - 50

        if normalize:
            print("NORAMLIZATION NOT IMPLEMENTED YET")
            # TODO IMPLEMENT NORMALIZATION

            # temperature_celsius_b = (row['btemp'] * 300 / 1024) - 50
            # temperature_celsius_t = (row['ttemp'] * 300 / 1024) - 50

        return row

    def convert_ADC_temp_to_C(self, dataframe=None, dataframe_path=None, normalize=False, save=False):
        '''
        IF passed in dataframe, sets dh objects dataframe to the converted, not inplace change on the parameter
        The check of path and dataframe should be upgradet, but works for now.
        Perhaps make the apply function be inplace

        :param dataframe:
        :param dataframe_path:
        :param normalize:
        :param save:
        :return:
        '''

        df = None

        # 10
        if not dataframe is None:
            df = dataframe
        # 01
        elif dataframe is None and not dataframe_path is None:
            try:
                df = pd.read_csv(dataframe_path)
            except Exception as e:
                print("Did not give a valid csv_path")
                raise e
        # 00
        elif dataframe_path is None and dataframe_path is None:
            print("Need to pass either dataframe or csv_path")
            raise Exception("Need to pass either dataframe or csv_path")
        # 11 save memory and performance
        elif dataframe and dataframe_path:
            # Todo this will never happen, i think because of if
            df = dataframe

        print("STARTING converting adc to celcius...")
        self.dataframe_iterator = df.apply(self._adc_to_c, axis=1, raw=False, normalize=normalize)

        print(self.dataframe_iterator.describe(), "\n")
        print ()
        print(self.dataframe_iterator.dtypes)
        print()
        print("DONE, here is a sneak peak:\n", self.dataframe_iterator.head(5))

        if (dataframe_path or self.data_synched_csv_path) and save:
            path = dataframe_path or self.data_synched_csv_path
            self.dataframe_iterator.to_csv(path, index=False, float_format='%.6f')

        return self.get_dataframe_iterator()



    def vertical_stack_dataframes(self, df1, df2, set_as_current_df=True):
        # TODO : CHECK IF THER IS MORE PATHS THAT NEEDS TO BE SET, THERE ARE!
        union = pd.merge(df1, df2, how='outer')
        if set_as_current_df:
            self.set_active_dataframe(union)

        return union

    def vertical_stack_csvs(self, csv_path_one,
                            csv_path_two,
                            column_names_df1=[],
                            column_names_df2=[],
                            rearranged_columns_after_merge=[],
                            index_column_name=None):
        # TODO : CHECK IF THER IS MORE PATHS THAT NEEDS TO BE SET, THERE ARE!

        df1 = pd.read_csv(csv_path_one)
        df2 = pd.read_csv(csv_path_two)

        if column_names_df1:
            df1.columns = column_names_df1
        if column_names_df2:
            df2.columns = column_names_df2

        self.vertical_stack_dataframes(df1, df2)

        if rearranged_columns_after_merge:
            self.rearrange_columns(rearranged_columns_after_merge)


        if index_column_name:
            self.set_column_as_index(column_name=index_column_name)

        return self.get_dataframe_iterator()


    def rearrange_columns(self, rearranged_columns):
        self.dataframe_iterator = self.dataframe_iterator[rearranged_columns]


if __name__ == '__main__':
    pass


