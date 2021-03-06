from sklearn.metrics import mean_squared_error
from math import sqrt
import lightgbm as lgb
from sklearn.cross_validation import KFold
import numpy as np

def get_oof(clf, x_train, y, x_test):
    NFOLDS=5
    SEED=71
    kf = KFold(len(x_train), n_folds=NFOLDS, shuffle=True, random_state=SEED)
    oof_train = np.zeros((len(x_train),))
    oof_test = np.zeros((len(x_test),))
    oof_test_skf = np.empty((NFOLDS, len(x_test)))
    lgbm_params =  {
        'task': 'train',
        'boosting_type': 'gbdt',
        'objective': 'binary',
        'metric': ['auc', 'binary_logloss'],
        # 'max_depth': 15,
        'num_leaves': 20,
        'min_deal_in_leaf':1500,
        'feature_fraction': 0.7,
        'bagging_fraction': 0.7,
        'lambda_l1':1.0,
        'lambda_l2':1.0,
        'bagging_freq': 4,
        'learning_rate': 0.01,
        'max_bin':255,
        'verbose': 0
    }
    for i, (train_index, test_index) in enumerate(kf):
        print('\nFold {}'.format(i))
        x_tr = x_train[train_index]
        y_tr = y[train_index]
        y_te = y[test_index]
        x_te = x_train[test_index]
        lgtrain = lgb.Dataset(x_tr, y_tr)
        lgvalid = lgb.Dataset(x_te, y_te)
        lgb_clf = lgb.train(
            lgbm_params,
            lgtrain,
            num_boost_round=20000,
            valid_sets=[lgtrain, lgvalid],
            valid_names=['train','valid'],
            early_stopping_rounds=700,
            verbose_eval=50
        )
        oof_train[test_index] = lgb_clf.predict(x_te)
        oof_test_skf[i, :]    = lgb_clf.predict(x_test)
        del (lgvalid, lgtrain)
        gc.collect()
    oof_test[:] = oof_test_skf.mean(axis=0)
    return oof_train, oof_test

def train_all(tdf, ydf, Tdf):
  lgbm_params =  {
      'task': 'train',
      'boosting_type': 'gbdt',
      'objective': 'binary',
      'metric': ['auc', 'binary_logloss'],
      'num_leaves': 31,
      'min_deal_in_leaf':1500,
      'feature_fraction': 0.7,
      'bagging_fraction': 0.7,
      'lambda_l1':1.0,
      'lambda_l2':1.0,
      'bagging_freq': 1,
      'learning_rate': 0.05,
      'max_bin':255,
      'verbose': 0
  }
  lgtrain = lgb.Dataset(tdf, ydf)
  cvr = lgb_clf = lgb.cv(
      lgbm_params,
      lgtrain,
      num_boost_round=1400,
      #valid_sets=[lgtrain, lgvalid],
      #valid_names=['train','valid'],
      nfold=5,
      #early_stopping_rounds=40,
      verbose_eval=5
  )
  print(cvr.keys())
  preds = lgb_clf.predict(Tdf)
  return preds

import glob, gc
import pandas as pd
import sys
if '--join' in sys.argv:
  train = pd.read_csv('../input/train.csv')
  test  = pd.read_csv('../input/test.csv')
  def ll(x):
    print(x)
    return np.load(x)
  adf   = np.vstack( [ll(fn) for fn in sorted(glob.glob('dumps/*.npy')) ] )
  train_height = len(train)
  tdf   = adf[0:train_height]
  Tdf   = adf[train_height:len(adf)]
  y     = train['target']
  print('orig train shape', train.shape)
  print('maked train shape', tdf.shape)
  print('orig test shape',  test.shape)
  print('maked test shape', Tdf.shape)
  tdf_  = np.hstack([train.drop(['target'], axis=1).values, tdf])
  Tdf_  = np.hstack([test.values, Tdf])
  print('train shape', tdf_.shape)
  print('test shape', Tdf_.shape)
  np.savez('join.npz', y=y, tdf=tdf_, Tdf=Tdf_)

if '--kfold' in sys.argv:
  npz = np.load('join.npz')
  print(npz.files)
  y, tdf, Tdf = map(lambda x:npz[x], npz)
  oof_train, oof_test = get_oof(None, tdf,  y, Tdf)
  from sklearn.metrics import roc_auc_score
  from sklearn.metrics import log_loss
  train_auc     = roc_auc_score(y, oof_train)
  train_logloss = log_loss(y, oof_train)
  print('train auc', train_auc)
  print('train logloss', train_logloss)
  print("Modeling Stage")
  preds = np.concatenate([oof_test])
  sub   = pd.read_csv('../input/sample_submission.csv')
  sub['target'] = preds
  sub.to_csv('sub_hgb.csv', index=False)

if '--all' in sys.argv:
  train_all(tdf, y, Tdf)
