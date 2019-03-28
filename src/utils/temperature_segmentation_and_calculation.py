import numpy as np
from collections import Counter

def max(array):
    '''
    Finds and returns the highest value in the array
    :param array:
    :return:
    '''
    return np.max(array)


def min(array):
    '''
    Finds and returns the lowest value in the array
    :param array:
    :return:
    '''
    return np.min(array)


def first_last_delta(array):
    temperature_first_sample_in_window = array.item(0)
    temperature_last_sample_in_window = array.item(-1)
    return temperature_last_sample_in_window - temperature_first_sample_in_window


def max_min_delta(array):
    '''
    # The variation in temperature from the warmest to the coldest
    :param array:
    :return:
    '''
    # max_temp = max(array)
    # min_temp = min(array)

    max_temp = np.amax(array)
    min_temp = np.amin(array)
    return max_temp - min_temp



def segment_acceleration_and_calculate_features_old(sensor_data,
                                                samples_pr_window=50,
                                                overlap=0.0,
                                                remove_sign_after_calculation=True):
    '''

    :param sensor_data: [ [1x, 1y, 1z, 1t], [2x, 2y, 2z, 2t], ... [Nx, Ny, Nz, Nt] ]
    :param samples_pr_window:
    :param overlap:
    :param remove_sign_after_calculation:
    :return:
    '''

    # print("len sensor data: ", sensor_data.shape)
    functions = [
        max,
        min,
        max_min_delta,
        first_last_delta,
    ]

    # window_samples = int(sampling_rate * window_length)
    window_samples = samples_pr_window

    # print("Windows samples ", window_samples)
    step_size = int(round(window_samples * (1.0 - overlap)))

    all_features = []

    for window_start in np.arange(0, sensor_data.shape[0], step_size):
        # print("Window start: ", window_start, "Sensor_data.shape[0]: ", sensor_data.shape[0], step_size)
        window_start = int(round(window_start))
        window_end = window_start + int(round(window_samples))
        if window_end > sensor_data.shape[0]:
            break

        window = sensor_data[window_start:window_end]

        # print("Window", window)
        extracted_features = []
        # print("Windows start: ")


        # do the temperature features stuff
        for func in functions:
            value = func(window)
            extracted_features.append(value)


        all_features.append(np.hstack(extracted_features))

    one_large_array = np.vstack(all_features)

    if remove_sign_after_calculation:
        np.absolute(one_large_array, one_large_array)

    return one_large_array



def segment_acceleration_and_calculate_features(sensor_data,
                                                temp,
                                                samples_pr_window=50,
                                                overlap=0.0,
                                                remove_sign_after_calculation=True):
    '''

    :param sensor_data: [ [1x, 1y, 1z], [2x, 2y, 2z], ... [Nx, Ny, Nz] ]
    :param btemp: [ [t1], [t2], ... [tn] ]
    :param ttemp: [ [t1], [t2], ... [tn] ]
    :param samples_pr_window:
    :param overlap:
    :param remove_sign_after_calculation:
    :return:
    '''

    # print("len sensor data: ", sensor_data.shape)
    temp_functions = [
        max,
        min,
        max_min_delta,
        first_last_delta,
    ]

    acceleration_functions = [
        max,
        min,
        max_min_delta,
        first_last_delta,
    ]

    # window_samples = int(sampling_rate * window_length)
    window_samples = samples_pr_window

    # print("Windows samples ", window_samples)
    step_size = int(round(window_samples * (1.0 - overlap)))

    all_features = []

    # temp_data = np.concatenate((btemp, ttemp), axis=1)
    temp_data = temp

    for window_start in np.arange(0, sensor_data.shape[0], step_size):
        # print("Window start: ", window_start, "Sensor_data.shape[0]: ", sensor_data.shape[0], step_size)
        window_start = int(round(window_start))
        window_end = window_start + int(round(window_samples))
        if window_end > sensor_data.shape[0]:
            break

        window = sensor_data[window_start:window_end]

        temp_window = temp_data[window_start:window_end]

        # print("Window", window)
        extracted_features = []
        # print("Windows start: ")


        # do the temperature features stuff
        for func in temp_functions:
            value = func(temp_window)
            # print("VALUE", value, type(value))
            # input("...")
            extracted_features.append(value)
            # print("EF: ", extracted_features)
            # input("...")

        for func in acceleration_functions:
            # iterate trough x, y and z
            for feature in range(window.shape[1]):
                # get all the values in that "column"
                features = np.take(window, feature, axis=1)
                value = func(features)
                extracted_features.append(value)


        all_features.append(np.hstack(extracted_features))

    one_large_array = np.vstack(all_features)

    if remove_sign_after_calculation:
        np.absolute(one_large_array, one_large_array)

    return one_large_array



def segment_labels(label_data, overlap=0.0, samples_pr_window=50):
    # window_samples = int(sampling_rate * window_length)
    window_samples = samples_pr_window
    step_size = int(round(window_samples * (1.0 - overlap)))

    labels = []

    for window_start in np.arange(0, label_data.shape[0], step_size):
        window_start = int(round(window_start))
        window_end = window_start + int(round(window_samples))
        if window_end > label_data.shape[0]:
            break
        window = label_data[window_start:window_end]
        # print(window)
        top = find_majority_activity(window)
        labels.append(top)

    return np.array(labels)


def find_majority_activity(window):
    sensor_labels_list = window.tolist()
    labels_without_list = []
    for sensor_label in sensor_labels_list:
        labels_without_list.append(sensor_label[0])
    counts = Counter(labels_without_list)
    top = counts.most_common(1)[0][0]
    return top