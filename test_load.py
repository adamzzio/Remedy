import pickle as pkl

filename_model_pretest = 'static/model/model_rf_pretest_remedy.sav'
filename_tfidf_pretest = 'static/model/tfidf_pretest_remedy.pickle'
filename_model_posttest = 'static/model/model_rf_posttest_remedy.sav'
filename_tfidf_posttest = 'static/model/tfidf_posttest_remedy.pickle'

def load_model():
    model_pretest = pkl.load(open(filename_model_pretest, 'rb'))
    tfidf_pretest = pkl.load(open(filename_tfidf_pretest, 'rb'))
    model_posttest = pkl.load(open(filename_model_posttest, 'rb'))
    tfidf_posttest = pkl.load(open(filename_tfidf_posttest, 'rb'))
    return model_pretest, tfidf_pretest, model_posttest, tfidf_posttest

model_pretest, tfidf_pretest, model_posttest, tfidf_posttest = load_model()
# import sklearn
# print(sklearn.__version__)