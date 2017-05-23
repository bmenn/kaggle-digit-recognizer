from sklearn.ensemble import RandomForestClassifier
import luigi
import luigi.s3
import pandas as pd
import pickle

class DataTask(luigi.Task):
    def output(self):
        return luigi.s3.S3Target('s3://bmenn-kaggle-digit-recognizer/train.csv')
    
class FeatureTask(luigi.Task):
    samples = luigi.IntParameter()
    
    def requires(self):
        return DataTask()
        
    def output(self):
        return luigi.s3.S3Target('s3://bmenn-kaggle-digit-recognizer/X_%d.p' % self.samples)
    
    def run(self):
        train_df = pd.read_csv('s3://bmenn-kaggle-digit-recognizer/train.csv')
        X = train_df.drop('label', axis=1).values[:self.samples]
        
        with self.output().open('w') as f:
            f.write(str(pickle.dumps(X)))
            
class LabelTask(luigi.Task):
    samples = luigi.IntParameter()
    
    def requires(self):
        return DataTask()
        
    def output(self):
        return luigi.s3.S3Target('s3://bmenn-kaggle-digit-recognizer/y_%d.p' % self.samples)
    
    def run(self):
        train_df = pd.read_csv('s3://bmenn-kaggle-digit-recognizer/train.csv')
        y = train_df['label'].values[:self.samples]
        
        with self.output().open('w') as f:
            f.write(str(pickle.dumps(y)))
            
class RandomForestClassifierTask(luigi.Task):
    n_estimators = luigi.IntParameter()
    samples = luigi.IntParameter()
    
    def requires(self):
        return [
            FeatureTask(samples=self.samples),
            LabelTask(samples=self.samples)
        ]
    
    def output(self):
        return luigi.s3.S3Target('s3://bmenn-kaggle-digit-recognizer/%d_%d_f1-score' % (self.samples, self.n_estimators))
    
    def run(self):
        clf = RandomForestClassifier(n_estimators=self.n_estimators)
        X = None
        y = None
        
        with self.input()[0].open('r') as f:
            X = pickle.load(bytes(f.read()))
            
        with self.input()[1].open('r') as f:
            y = pickle.load(bytes(f.read()))
            
        clf.fit(X, y)
        y_predict = clf.predict(X)
        
        score = f1_score(y, y_predict, average='micro')
        
        with self.output().open('w') as f:
            f.write(str(score))

class ModelSelection(luigi.Task):
    def requires(self):
        return [
            RandomForestClassifierTask(n_estimators=n_estimators, samples=samples)
            for samples in [100, 500, 1000, 5000]
            for n_estimators in [5, 10, 50, 100]
        ] 
    
if __name__ == '__main__':
    luigi.run()