import sys, os
# try: sys.path.append( os.path.abspath( os.path.join( os.path.dirname( __file__), '..')))
# except: print("SAdsadsadhsa;hkldasjkd")
import re, math, random, time
import numpy as np
import cwa_converter
import pickle
from multiprocessing import Process, Queue, current_process, freeze_support, Manager
from pipeline.DataHandler import DataHandler
from keras.models import load_model
from layers.normalize import Normalize
import utils.temperature_segmentation_and_calculation as temp_feature_util
from src.config import Config
from src import models
from keras.models import load_model



class Pipeline:
    def __init__(self):
        print("HELLO FROM PIPELINE")
        # Create a data handling object for importing and manipulating dataset ## PREPROCESSING
        print('CREATING datahandler')
        self.dh = DataHandler()
        print('CREATED datahandler')
        self.dataframe = None

    def printProgressBar(self, current, totalOperations, sizeProgressBarInChars, explenation=""):
        # try:
        #     import sys, time
        # except Exception as e:
        #     print("Could not import sys and time")

        fraction_completed = current / totalOperations
        filled_bar = round(fraction_completed * sizeProgressBarInChars)

        # \r means start from the beginning of the line
        fillerChars = "#" * filled_bar
        remains = "-" * (sizeProgressBarInChars - filled_bar)

        sys.stdout.write('\r{} {} {} [{:>7.2%}]'.format(
            explenation,
            fillerChars,
            remains,
            fraction_completed
        ))

        sys.stdout.flush()


    def unzip_extractNconvert_temp_merge_dataset(self, rel_filepath, label_interval, label_mapping, unzip_path='../data/temp', unzip_cleanup=False, cwa_paralell_convert=True):
        # unzip cwas from 7z arhcive
        unzipped_path = self.dh.unzip_7z_archive(
            filepath=os.path.join(os.getcwd(), rel_filepath),
            unzip_to_path=unzip_path,
            cleanup=unzip_cleanup
        )

        print('UNZIPPED PATH RETURNED', unzipped_path)

        ##########################
        #
        #
        ##########################

        # convert the cwas to independent csv containing timestamp xyz and temp
        back_csv, thigh_csv = cwa_converter.convert_cwas_to_csv_with_temp(
            subject_dir=unzipped_path,
            out_dir=unzipped_path,
            paralell=cwa_paralell_convert
        )

        ##########################
        #
        #
        ##########################


        # Timesynch and concate csvs
        self.dh.merge_csvs_on_first_time_overlap(
            master_csv_path=back_csv,
            slave_csv_path=thigh_csv,
            rearrange_columns_to=[
                'time',
                'bx',
                'by',
                'bz',
                'tx',
                'ty',
                'tz',
                'btemp',
                'ttemp'
            ]
        )

        df = self.dh.get_dataframe_iterator()
        print(df.head(5))
        # input("looks ok ? \n")


        ##########################
        #
        #
        ##########################

        self.dh.convert_ADC_temp_to_C(
            dataframe=df,
            dataframe_path=None,
            normalize=False,
            save=True
        )

        df = self.dh.get_dataframe_iterator()
        print(df.head(5))
        # input("looks ok ? \n")

        ##########################
        #
        #
        ##########################


        print('SET INDEX TO TIMESTAMP')
        #test that this works with a dataframe and not only path to csv
        # thus pre-loaded and makes it run a little faster
        self.dh.convert_column_from_str_to_datetime_test(
                dataframe=df,
        )

        self.dh.set_column_as_index("time")
        print('DONE')

        ##########################
        #
        #
        ##########################


        print('MAKE NUMERIC')
        self.dh.convert_column_from_str_to_numeric(column_name="btemp")

        self.dh.convert_column_from_str_to_numeric(column_name="ttemp")
        print('DONE')

        ##########################
        #
        #
        ##########################


        print('ADDING LABELS')
        self.dh.add_new_column()
        print('DONE')

        self.dh.add_labels_file_based_on_intervals(
            intervals=label_interval,
            label_mapping=label_mapping
        )


        # ##########################
        # #
        # #
        # ##########################

        # dh.show_dataframe()
        df = self.dh.get_dataframe_iterator()

        return df, self.dh

    # TODO create method for unzip_extractNconvert_temp_stack_dataset() or adopt the above def..

    def get_features_and_labels(self, df, dh=None, columns_back=[0,1,2,6], columns_thigh=[3,4,5,7], column_label=[8]):
        if dh is None:
            dh = DataHandler()

        back_feat, thigh_feat, labels = None, None, None

        print(columns_back, columns_thigh, column_label)

        if columns_back:
            back_feat = dh.get_rows_and_columns(dataframe=df, columns=columns_back).values
        if columns_thigh:
            thigh_feat = dh.get_rows_and_columns(dataframe=df, columns=columns_thigh).values
        if column_label:
            labels = dh.get_rows_and_columns(dataframe=df, columns=column_label).values

        return back_feat, thigh_feat, labels


    ####################################################################################################################
    #                                   vPARALLELL PIPELINE EXECUTE WINDOW BY WINDOW CODEv                             #
    ####################################################################################################################

    # MODEL Klassifisering
    def model_classification_worker(self, input_q, output, model):
        for idx, window in iter(input_q.get, 'STOP'):
            # print("model_classification_worker executing")
            # print("MODLE CLASSIFICATION: \n", "IDX: ", idx, "\n","WINDOW: \n", window, "\n", "SHAPE: ", window.shape, "\n", "DIMS: ", window.ndim)

            # Vil ha in ett ferdig window, aka windows maa lages utenfor her og addes til queue
            # TODO: enten velge ut x antall av window, predikere de og ta avg result som LSTM (den med flest forekomster)
            # TODO: eller bare ett random row in window og predikerer den og bruker res som LSTM
            res = model.window_classification(window[0])[0]
            # print("RESSS: >>>>>> :: ", res, type(res))

            # output_queue.put((idx, window, res))
            # TODO remove window from output tuple, we do not need the temperature window anymore
            output.append((idx, window, res))




    def parallel_pipeline_classification_run(self, dataframe, rfc_model_path, lstm_models_paths, samples_pr_window, train_overlap=0.8, num_proc_mod=1, seq_lenght=None):
        '''

        :param dataframe: Pandas DataFrame
        :param rfc_model_path: str with path to saved RFC
        :param lstm_models_paths: dictionary containing lstm_mapping and path {rfc_result_number : model_path}
        :param samples_pr_window:
        :param train_overlap:
        :param num_proc_mod:
        :param num_proc_clas:
        :param seq_lenght:
        :return:
        '''

        # TODO: burde passe inn back, thigh og label columns til methoden også videre inn i get_features_and_labels

        self.dataframe = dataframe
        NUMBER_OF_PROCESSES_models = num_proc_mod

        # Create queues
        model_queue = Queue()
        # output_classification_queue = Queue()
        manager = Manager()
        output_classification_windows = manager.list()


        # Submit tasks for model klassifisering
        back_feat, thigh_feat, label = self.get_features_and_labels(self.dataframe) # returns numpy arrays
        back_feat = temp_feature_util.segment_acceleration_and_calculate_features(back_feat,
                                                                    samples_pr_window=samples_pr_window,
                                                                    overlap=train_overlap)

        thigh_feat = temp_feature_util.segment_acceleration_and_calculate_features(thigh_feat,
                                                                    samples_pr_window=samples_pr_window,
                                                                    overlap=train_overlap)

        # concatinates example : [[1,2,3],[4,5,6]] og [[a,b,c], [d,e,f]] --> [[1,2,3,a,b,c], [4,5,6,d,e,f]]
        # akas rebuild the dataframe shape
        both_features = np.hstack((back_feat, thigh_feat))


        # print("BOTH FEATURES SHAPE : ", both_features.shape)
        # TODO: EXTRACT THE CONVERTION INTO WINDOWS INTO OWN FUNC
        num_rows_in_window = 1
        if seq_lenght:
            num_rows = both_features.shape[0]
            num_rows_in_window = int( num_rows / seq_lenght)


        feature_windows = []
        last_index = 0

        for _ in range(num_rows_in_window):
            feature_windows.append(both_features[last_index:last_index + seq_lenght])
            last_index = last_index + seq_lenght

        both_features = np.array(feature_windows)
        # print(both_features.shape)

        number_of_tasks = both_features.shape[0]

        for idx, window in enumerate(both_features):
            model_queue.put((idx, window))


        # Lists to maintain processes
        processes_model = []

        # CREATE a worker processes on model klassifisering
        for _ in range(NUMBER_OF_PROCESSES_models):
            RFC = pickle.load(open(rfc_model_path, 'rb'))
            processes_model.append(Process(target=self.model_classification_worker,
                                           args=(model_queue,
                                                 output_classification_windows,
                                                 RFC)
                                           ))

        # START the worker processes
        for process in processes_model:
            process.start()

        # waith for tasks_queue to become empty before sending stop signal to workers
        while not model_queue.empty():
            # print("CURRENT: {}\nQUEUE SIZE: {}".format(number_of_tasks - model_queue.qsize(), model_queue.qsize()))
            self.printProgressBar(
                current=int(number_of_tasks - model_queue.qsize()),
                totalOperations=number_of_tasks,
                sizeProgressBarInChars=30,
                explenation="Model classification :: ")


        self.printProgressBar(
            current=int(number_of_tasks - model_queue.qsize()),
            totalOperations=number_of_tasks,
            sizeProgressBarInChars=30,
            explenation="Model classification :: ")
        print("DONE")

        # Tell child processes to stop waiting for more jobs
        for _ in range(NUMBER_OF_PROCESSES_models):
            model_queue.put('STOP')

        # print(">>>>>>>>>>>>>>>>> EUREKA <<<<<<<<<<<<<<<<<")

        # LET ALL PROCESSES ACTUALLY TERMINATE AKA FINISH THE JOB THEIR DOING
        while any([p.is_alive() for p in processes_model]):
            pass

        # print(">>>>>>>>>>>>>>>>> POT OF GOLD <<<<<<<<<<<<<<<<<")

        # join the processes aka block the threads, do not let them take on any more jobs
        for process in processes_model:
            process.join()

        # print("\nALL PROCESSES STATUS BEFORE TERMINATING:\n{}".format(processes_model))

        # Kill all the processes to release memory or process space or something. its 1.15am right now
        for process in processes_model:
            process.terminate()

        print(">>>>>>>>>>>>>>>>> ||||||||| <<<<<<<<<<<<<<<<<")

        # continue the pipeline work
        # ...
        # ...
        # ...


        # See results
        print("OUTPUT/Activities windows to classify : ", len(output_classification_windows))

        both_sensors_windows_queue = filter(lambda x: x[2] == '1', output_classification_windows)
        thigh_sensors_windows_queue = filter(lambda x: x[2] == '2', output_classification_windows)
        back_sensors_windows_queue = filter(lambda x: x[2] == '3', output_classification_windows)

        back_colums = ['back_x', 'back_y', 'back_z']
        thigh_colums = ['thigh_x', 'thigh_y', 'thigh_z']

        # x1 = model.get_features([dataframe], ['back_x', 'back_y', 'back_z'], batch_size=1, sequence_length=seq_lenght)
        xBack = np.concatenate([dataframe[back_colums].values[ : (len(dataframe) - len(dataframe) % seq_lenght) ] for dataframe in [dataframe]])
        xThigh = np.concatenate([dataframe[thigh_colums].values[: (len(dataframe) - len(dataframe) % seq_lenght)] for dataframe in [dataframe]])

        xBack = xBack.reshape(-1, seq_lenght, len(back_colums))
        xThigh = xThigh.reshape(-1, seq_lenght, len(thigh_colums))

        print("XBACK: ", xBack.shape)

        # BOTH
        model = None
        config = Config.from_yaml(lstm_models_paths["1"]['config'], override_variables={})
        model_name = config.MODEL['name']
        model_args = dict(config.MODEL['args'].items(), **config.INFERENCE.get('extra_model_args', {}))
        model_args['batch_size'] = 1

        model = models.get(model_name, model_args)
        model.compile()
        model.model.load_weights(lstm_models_paths["1"]['weights'])
        model.compile()
        for meta in both_sensors_windows_queue:
            wndo_idx, _, mod = meta[0], meta[1][0], meta[2]
            x1 = xBack[wndo_idx].reshape(1, seq_lenght, xBack.shape[2])
            x2 = xThigh[wndo_idx].reshape(1, seq_lenght, xThigh.shape[2])

            target, prob = model.predict_on_one_window(window=[x1, x2])
            print("<<<<>>>>><<<>>>: \n", ":: 1 ::", target, prob)
        del model  # remove the model


        ## THIGH
        model = None
        config = Config.from_yaml(lstm_models_paths['2']['config'], override_variables={})
        model_name = config.MODEL['name']
        model_args = dict(config.MODEL['args'].items(), **config.INFERENCE.get('extra_model_args', {}))
        model_args['batch_size'] = 1

        model = models.get(model_name, model_args)
        model.compile()
        model.model.load_weights(lstm_models_paths["2"]['weights'])
        model.compile()

        for meta in thigh_sensors_windows_queue:
            wndo_idx, _, mod = meta[0], meta[1][0], meta[2]
            x1 = xThigh[wndo_idx].reshape(1, seq_lenght, xThigh.shape[2])

            target, prob = model.predict_on_one_window(window=x1)
            print("<<<<>>>>><<<>>>: \n", " :: 2 :: ", target, prob)
        del model  # remove the model

        ## BACK
        model = None
        config = Config.from_yaml(lstm_models_paths['3']['config'], override_variables={})
        model_name = config.MODEL['name']
        model_args = dict(config.MODEL['args'].items(), **config.INFERENCE.get('extra_model_args', {}))
        model_args['batch_size'] = 1

        model = models.get(model_name, model_args)
        model.compile()
        model.model.load_weights(lstm_models_paths['3']['weights'])
        model.compile()
        for meta in back_sensors_windows_queue:
            wndo_idx, _, mod = meta[0], meta[1][0], meta[2]
            x1 = xThigh[wndo_idx].reshape(1, seq_lenght, xBack.shape[2])

            target, prob = model.predict_on_one_window(window=x1)
            print("<<<<>>>>><<<>>>: \n"," ::3 :: ", target, prob)
        del model  # remove the model








        # classifiers = {}
        # for key in lstm_models_paths.keys():
        #     config = Config.from_yaml(lstm_models_paths[key]['config'], override_variables={})
        #     model_name = config.MODEL['name']
        #     model_args = dict(config.MODEL['args'].items(), **config.INFERENCE.get('extra_model_args', {}))
        #     model_args['batch_size'] = 1
        #
        #     model = models.get(model_name, model_args)
        #     # model.compile()
        #     model.model.load_weights(lstm_models_paths[key]['weights'])
        #     # model.compile()
        #
        #     classifiers[key] = {"model": model, "weights": lstm_models_paths[key]["weights"]}
        #
        #
        # start = 0
        # end = len(output_classification_windows) // 5
        # while start < end:
        #     meta = output_classification_windows.pop()
        #     wndo_idx, _, mod_clas = meta[0], meta[1][0], meta[2]
        #     model = classifiers[mod_clas]['model']
        #     # model.compile() # with this as the only compile it started to run agian...
        #     # weights_path = classifiers[mod_clas]['weights']
        #
        #     # get the correct features from the dataframe, and not the temperature feature
        #     x1 = model.get_features([dataframe], ['back_x', 'back_y', 'back_z'], batch_size=1, sequence_length=seq_lenght)
        #     x2 = model.get_features([dataframe], ['thigh_x', 'thigh_y', 'thigh_z'], batch_size=1, sequence_length=seq_lenght)
        #     x1 = x1[wndo_idx].reshape(1, seq_lenght, x1.shape[2])
        #     x2 = x2[wndo_idx].reshape(1, seq_lenght, x2.shape[2])
        #     if mod_clas == "1":  # both sensors
        #         target, prob = model.predict_on_one_window(window=[x1, x2])
        #     elif mod_clas == '2':  # just thigh sensor
        #         target, prob = model.predict_on_one_window(window=x2)
        #     elif mod_clas == '3':  # just back sensor
        #         target, prob = model.predict_on_one_window(window=x1)
        #     print(target, prob)
        #     # print(res)
        #     self.printProgressBar(start, end, 20, explenation="Activity classification prog. :: ")
        #     start += 1
        #
        # self.printProgressBar(start, end, 20, explenation="Activity classification prog. :: ")




    ####################################################################################################################
    #                                   ^PARALLELL PIPELINE EXECUTE WINDOW BY WINDOW CODE^                             #
    ####################################################################################################################

    def create_large_dafatframe_from_multiple_input_directories(self,
                                                                list_with_subjects,
                                                                back_keywords=['Back'],
                                                                thigh_keywords = ['Thigh'],
                                                                label_keywords = ['GoPro', "Labels"],
                                                                out_path=None,
                                                                merge_column = None,
                                                                master_columns = ['bx', 'by', 'bz'],
                                                                slave_columns = ['tx', 'ty', 'tz'],
                                                                rearrange_columns_to = None,
                                                                save=False,
                                                                added_columns_name=["new_col"]
                                                                ):



        subjects = {}
        for subject in list_with_subjects:
            if not os.path.exists(subject):
                print("Could not find Subject at path: ", subject)

            files = {}
            for sub_files_and_dirs in os.listdir(subject):
                # print(sub_files_and_dirs)
                words = re.split("[_ .]", sub_files_and_dirs)
                words = list(map(lambda x: x.lower(), words))

                check_for_matching_word = lambda words, keywords: [True if keyword.lower() == word.lower() else False
                                                                   for word in words for keyword in keywords]

                if any(check_for_matching_word(words, back_keywords)):
                    files["backCSV"] = sub_files_and_dirs

                elif any(check_for_matching_word(words, thigh_keywords)):
                    files["thighCSV"] = sub_files_and_dirs

                elif any(check_for_matching_word(words, label_keywords)):
                    files["labelCSV"] = sub_files_and_dirs

            subjects[subject] = files

        # print(subjects)

        merged_df = None
        dh = DataHandler()
        dh_stacker = DataHandler()
        for idx, root_dir in enumerate(subjects):
            subject = subjects[root_dir]
            # print("SUBJECT: \n", subject)

            master = os.path.join(root_dir, subject['backCSV'])
            slave = os.path.join(root_dir, subject['thighCSV'])
            label = os.path.join(root_dir, subject['labelCSV'])

            # dh = DataHandler()
            dh.merge_csvs_on_first_time_overlap(
                master,
                slave,
                out_path=out_path,
                merge_column=merge_column,
                master_columns=master_columns,
                slave_columns=slave_columns,
                rearrange_columns_to=rearrange_columns_to,
                save=save,
                left_index=True,
                right_index=True
            )

            dh.add_columns_based_on_csv(label, columns_name=added_columns_name, join_type="inner")

            if idx == 0:
                merged_df = dh.get_dataframe_iterator()
                continue

            merged_old_shape = merged_df.shape
            # vertically stack the dataframes aka add the rows from dataframe2 as rows to the dataframe1
            merged_df = dh_stacker.vertical_stack_dataframes(merged_df, dh.get_dataframe_iterator(),
                                                             set_as_current_df=False)

        #     print(
        #     "shape merged df: ", merged_df.shape, "should be ", dh.get_dataframe_iterator().shape, "  more than old  ",
        #     merged_old_shape)
        #
        # print("Final merge form: ", merged_df.shape)
        return merged_df


    @staticmethod
    def load_model_weights(model, weights_path):
        model.load_weights(weights_path)


if __name__ == '__main__':
    p = Pipeline()