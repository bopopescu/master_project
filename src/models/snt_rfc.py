import multiprocessing
import numpy as np
import utils.temperature_segmentation_and_calculation as temp_feature_util
# from collections import Counter
from sklearn.ensemble import RandomForestClassifier as RFC
from sklearn.metrics import accuracy_score, confusion_matrix




class HARRandomForrest():
    def __init__(self):
        self.RFC_classifier = None
        self.predictions = None
        self.test_ground_truth_labels = None
        self.accuracy = None
        self.confusion_matrix = None

    def train(self,
              back_training_feat,
              thigh_training_feat,
              labels,
              samples_pr_window,
              train_overlap,
              number_of_trees=100
              ):

            print("RFC TRAIN BTF: ", back_training_feat)

            back_training_feat = temp_feature_util.segment_acceleration_and_calculate_features(back_training_feat,
                                                                                  samples_pr_window=samples_pr_window,
                                                                                  overlap=train_overlap)

            thigh_training_feat = temp_feature_util.segment_acceleration_and_calculate_features(thigh_training_feat,
                                                                                    samples_pr_window=samples_pr_window,
                                                                                    overlap=train_overlap)

            labels = temp_feature_util.segment_labels(labels, samples_pr_window=samples_pr_window, overlap=train_overlap)
           
            both_features = np.hstack((back_training_feat, thigh_training_feat))

            print("Hopefully this RFC will create and fit")
            self.RFC_classifier = RFC(n_estimators=number_of_trees,
                                 class_weight="balanced",
                                 random_state=0,
                                 n_jobs=-1
                                 ).fit(both_features, labels)
            print("I kinda diiiid! ")

    def test(self, back_test_feat, thigh_test_feat, labels, samples_pr_window, train_overlap):

        print("RFC TEST BTF: ", back_test_feat)

        back_test_feat = temp_feature_util.segment_acceleration_and_calculate_features(back_test_feat,
                                                                          samples_pr_window=samples_pr_window,
                                                                          overlap=train_overlap)

        thigh_test_feat = temp_feature_util.segment_acceleration_and_calculate_features(thigh_test_feat,
                                                                           samples_pr_window=samples_pr_window,
                                                                           overlap=train_overlap)

        self.test_ground_truth_labels = temp_feature_util.segment_labels(labels, samples_pr_window=samples_pr_window, overlap=train_overlap)

        both_features = np.hstack((back_test_feat, thigh_test_feat))

        print("Hopefully this RFC test and predict")
        self.predictions = self.RFC_classifier.predict(both_features)
        print("I kinda diiiid! ")
        print("PREDICTIONS: \n{}".format(self.predictions))

    def classify(self, back_test_feat, thigh_test_feat, samples_pr_window, train_overlap):
        back_test_feat = temp_feature_util.segment_acceleration_and_calculate_features(back_test_feat,
                                                                          samples_pr_window=samples_pr_window,
                                                                          overlap=train_overlap)

        thigh_test_feat = temp_feature_util.segment_acceleration_and_calculate_features(thigh_test_feat,
                                                                           samples_pr_window=samples_pr_window,
                                                                           overlap=train_overlap)
        both_features = np.hstack((back_test_feat, thigh_test_feat))
        self.predictions = self.RFC_classifier.predict(both_features)
        return self.predictions


    def calculate_accuracy(self):
        # TODO check that object attributes are not None, raise exception
        gt = self.test_ground_truth_labels
        preds = self.predictions

        self.accuracy = accuracy_score(gt, preds)
        return self.accuracy

    def calculate_confusion_matrix(self):
        # TODO check that object attributes are not None, raise exception
        gt = self.test_ground_truth_labels
        preds = self.predictions

        self.confusion_matrix = confusion_matrix(gt, preds)
        return self.confusion_matrix

    def window_classification(self, window):
        res = self.RFC_classifier.predict([window])
        return res

