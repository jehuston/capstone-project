import pandas as pd
import numpy as np
import sys
import string
from pymongo import MongoClient
from gensim import corpora, models, similarities
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

## need to create a shared stopwords set, dictionary, index, model --> maybe instance variables of the class?
class MyRecommender():
    '''
    A class that will build take in text documents, build a dictionary and index, and
    return recommendations from that index upon new input.
    '''
    def __init__(self, model):
        self.model = model
        self.stopset = set(stopwords.words('english'))
        self.stopset.update(['description', 'available']) ## add some words that appear a lot in menu data
        self.dictionary = None
        self.dictionary_len = 0
        self.index = None
        self.corpus = None
        self.df = None ## Need df to get recipe ids back?

    def _prepare_documents(self, db):
        '''
        INPUT: database connection
        OUTPUT: array of strings

        Given database connection, collect all recipe documents, join ingredients lists
        into strings, and return as array.
        '''
        cursor = db.recipes.find({}, {'rec_id': 1, 'title' : 1, 'ingredients': 1, '_id' : 0})
        self.df = pd.DataFrame(list(cursor))
        self.df['ingredients'] = self.df['ingredients'].apply(lambda x: " ".join(x))
        documents = self.df['ingredients'].values
        return documents

    def _clean_text(self, documents):
        '''
        INPUT: array of strings
        OUTPUT: array of lists (ok?)

        Given array of strings (recipes or restaurant menus), tokenize and return as array.
        '''
        stopset = set(stopwords.words('english'))
        stopset.update(['description', 'available']) ## add some words that appear a lot in menu data
        wnl = WordNetLemmatizer()
        texts = []

        for doc in documents:
            words = doc.lower().split()
            tokens = []
            for word in words:
                if word not in stopset and not any(c.isdigit() for c in word): #filter stopwords and numbers
                    token = wnl.lemmatize(word.strip(string.punctuation))
                    tokens.append(token)
            texts.append(tokens)

        text_array = np.array(texts)
        return text_array

    def _create_dictionary(self, db):
        '''
        INPUT: text documents (array of strings)
        OUTPUT: gensim dictionary object, corpus

        Create a dictionary mapping of words in corpus.
        '''
        ## Vectorize and store recipe text
        documents = self._prepare_documents(db)
        texts = self._clean_text(documents)
        self.dictionary = corpora.Dictionary(texts)
        self.corpus = [self.dictionary.doc2bow(text) for text in texts] ## convert to BOW

        for i in self.dictionary.iterkeys():
            self.dictionary_len +=1

    def _create_model(self):
        '''
        INPUT: Model class, corpus (ARRAY)
        OUTPUT: trained model, index (for similarity scoring)

        Create a model using the collection of documents (corpus). Create an index
        to query against to find similar documents.
        '''
        ## Apply model
        self.model = self.model(self.corpus)
        ## prepare for similarity queries - unlikely to be memory constrained (< 100K docs) so won't write to disk
        self.index = similarities.SparseMatrixSimilarity(self.model[self.corpus], num_features = self.dictionary_len) # num_features is len of dictionary
        #return model, index

    def _vectorize_restaurant_menu(self, name, db):
        '''
        INPUT: restaurant name (STRING), database connection
        OUTPUT: menu vector (ARRAY)

        Given restaurant name that exists in database, return menu and vectorize to
        prepare for similarity query.
        '''
        ## Get 1 restaurant menu
        cursor = db.restaurants.find_one({'name' : name})
        menu = cursor['menu']

        ## Vectorize and prep menu text
        ## Broken if menu field is empty! Only 16 of these though.
        menu_list = [" ".join(i) for i in zip(menu['items'], menu['descriptions'])]
        menu_string = " ".join(menu_list)

        menu_tokens = self._clean_text([menu_string])[0]
        menu_vector = self.dictionary.doc2bow(menu_tokens)
        return menu_vector

    def fit(self, db):
        '''
        INPUT: connection to database with recipes, restaurants data
        OUTPUT: fit model, index

        Creates a dictionary and model for recommender system. Given database connection,
        find all recipe ingredient lists, vectorize, build corpus and dictionary,
        fit model and create index.
        '''
        self._create_dictionary(db)
        self._create_model()


    def get_recommendations(self, name, db, num):
        '''
        INPUT: index (), menu vector (ARRAY), number (INT) of recommendations requested
        OUTPUT: dataframe/series(?) of recommended recipes

        Returns top n recommended recipes based on cosine similiarity to restaurant menu.
        '''
        menu_vector = self._vectorize_restaurant_menu(name, db)
        sims = self.index[self.model[menu_vector]] ## convert BOW to Tfidf
        rec_indices = np.argsort(sims)[:-(num+1):-1] # gets top n
        return self.df.loc[rec_indices, 'title'], sims[rec_indices]

## THIS WORKS!!!!!!!!!!!!!!!!1!!1!!!

if __name__ == '__main__':

    restaurant_name = sys.argv[1]
    ## Connect to database
    conn = MongoClient()
    db = conn.project

    model = models.TfidfModel
    recommender = MyRecommender(model)
    recommender.fit(db)
    ## Need to do the above just once - when all recipes collected, can write to disk ##
    ## (see gensim docs)

    recs, scores = recommender.get_recommendations(restaurant_name, db, 5)
    print [result for result in zip(recs, scores)]
    #print recs
