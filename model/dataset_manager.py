import os
import pandas as pd
import nltk
import pickle
from tqdm import tqdm
import sys
from keras.preprocessing.sequence import pad_sequences
import ntpath

this_path = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.abspath(os.path.join(this_path, os.pardir))

sys.path.append(root_path)

from model.batch_iterator import BatchIterator,BatchGenerator
from embedding.load_glove_embeddings import load_glove_embeddings
from utility.text import *
from utility.model import *
from utility.monitor import *


this_path = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.abspath(os.path.join(this_path, os.pardir))
dataset_path = os.path.join(root_path, 'dataset/')
tokenized_path = os.path.join(root_path, 'tokenized/')
embedding_path = os.path.join(root_path, 'embedding/')

embedding_prefix = 'EMB_'
tokenized_prefix = 'A'

files = ['articles1.csv', 'articles2.csv', 'articles3.csv']


class DatasetManager:
    """
    This class takes care of providing the training data in batches.
    It even computes the proper embedding matrix for all the words present in the corpus
    """

    def __init__(self,
                 min_headline_len,
                 min_article_len,
                 max_headline_len,
                 max_article_len,
                 verbose=False
                 ):

        self.min_headline_len = min_headline_len
        self.min_article_len = min_article_len
        self.max_article_len = max_article_len
        self.max_headline_len = max_headline_len
        self.verbose = verbose

        self.dataset = [
            os.path.join(dataset_path, file) for file in files
        ]

    def tokenize(self, size=10000):

        if self.verbose:
            print('Tokenization started. Size set to', size)

        for idx, path in enumerate(self.dataset):

            if self.verbose:
                print('-' * len(path) + '\nWorking on', path)

            # Load frame and drop everything but what we need
            frame = pd.read_csv(path, encoding='utf8').filter(['title', 'content'])

            o_len = frame.shape[0]

            # Fill nan values with nothing but replace NaN which is a float and make the script crash
            frame = frame.fillna('')

            if self.verbose:
                print('Removing recurrent headlines..')

            # Preprocessing: remove recurrent headlines (e.g: "- the new york times")
            frame['title'] = frame['title'].str.replace(' - The New York Times', '')

            if self.verbose:
                print('Removing non-ASCII chars..')

            # Remove all non ASCII chars
            frame['title'] = frame['title'].replace({r'[^\x00-\x7F]+': ''}, regex=True)
            frame['content'] = frame['content'].replace({r'[^\x00-\x7F]+': ''}, regex=True)

            if self.verbose:
                print('Filtering out small news..')

            # Remove short articles or headlines
            frame = frame[frame['title'].str.split().apply(len) >= self.min_headline_len]
            frame = frame[frame['content'].str.split().apply(len) >= self.min_article_len]

            n_len = frame.shape[0]

            if self.verbose:
                print(str(o_len - n_len), 'news were removed before processing chunks'
                                          ' because were too short (either headline or article)')

            # Truncate headlines and articles
            frame['title'] = frame['title'].apply(
                lambda x: ' '.join(x.split()[:self.max_headline_len])
            )
            frame['content'] = frame['content'].apply(
                lambda x: ' '.join(x.split()[:self.max_article_len])
            )

            if self.verbose:
                print('News were truncated to desired size')

            n_chunks = round(frame.shape[0] / size)

            if self.verbose:
                print('Frame will be divided in', str(n_chunks), 'chunks')

            for chunk in range(n_chunks):

                if self.verbose:
                    print('Working on chunk', chunk + 1)

                sub_frame = frame.iloc[chunk * size: chunk * size + size].copy()

                if self.verbose:
                    print('Number of elements:', sub_frame.shape[0])

                # lower all strings
                sub_frame['title'] = sub_frame['title'].str.lower()
                sub_frame['content'] = sub_frame['content'].str.lower()

                # Tokenize
                sub_frame['title'] = sub_frame['title'].apply(lambda row: nltk.word_tokenize(row))
                sub_frame['content'] = sub_frame['content'].apply(lambda row: nltk.word_tokenize(row))

                tkn_head = sub_frame['title'].tolist()
                tkn_desc = sub_frame['content'].tolist()

                # Truncate the articles to the first dot
                tkn_head = truncate_sentences(tkn_head, self.max_headline_len, stop_words=['.', '!', '?'])
                tkn_desc = truncate_sentences(tkn_desc, self.max_article_len, stop_words=['.', '!', '?'])

                thrown = 0

                for h, d in zip(tkn_head[:], tkn_desc[:]):
                    if len(h) < self.min_headline_len or len(d) < self.min_article_len:
                        tkn_head.remove(h)
                        tkn_desc.remove(d)
                        thrown += 1

                if self.verbose:
                    print('=> After tokenization and paragraph truncate', thrown, 'more news have been thrown')
                    print('Headline length (words): avg = %s, min = %s, max = %s' % get_text_stats(tkn_head))
                    print('Article length (words): avg = %s, min = %s, max = %s' % get_text_stats(tkn_desc))

                out = []
                for t, d in zip(tkn_head, tkn_desc):
                    out.append([t, d])

                f_name = tokenized_prefix + str(idx) + '_C' + str(chunk + 1) + '.pkl'
                save_path = os.path.join(root_path, 'tokenized/', f_name)
                # Save to pickle
                with open(save_path, 'wb') as handle:
                    pickle.dump(out, handle)

                n_len -= thrown

            print('All chunks have been processed')
            print('We dropped a total of ' + str(o_len - n_len) + ' news - %.2f%%' % ((1 - n_len/o_len) * 100))
            print('-' * len(path))

    @staticmethod
    def load_embeddings(f_name='embeddings.pkl'):

        with open(os.path.join(embedding_path, f_name), 'rb') as handle:
            return pickle.load(handle)

    @staticmethod
    def load_word2index(f_name='word2index.pkl'):

        with open(os.path.join(embedding_path, f_name), 'rb') as handle:
            return pickle.load(handle)

    def load_test(self, num_decoder_tokens, f_name):
        with open(os.path.join(embedding_path, f_name), 'rb') as handle:
            data = np.array(pickle.load(handle))
            headlines = list(data[:, 0])
            articles = list(data[:, 1])

            try:
                return get_inputs_outputs(
                    x=articles,
                    y=headlines,
                    max_decoder_seq_len=self.max_headline_len,
                    num_decoder_tokens=num_decoder_tokens
                )

            except MemoryError as me:
                print('[<->] Memory alloc failed while loading test set. Size might be too large, '
                      'try rebuilding test set with less elements')
                raise me

    def generate_embeddings(
            self,
            glove_embedding_len,
            tokenized_dir='tokenized/',
            embedding_dir='embedding/',
    ):
        print('-' * 100)
        print('Computing embedding matrix. This process might require some time')
        print('For each tokenized file, we will update our matrix')

        print('Loading in memory glove embeddings..')

        # We need to load now our embeddings in order to proceed with further processing
        word2index, embeddings = load_glove_embeddings(
            fp=os.path.join(
                root_path,
                embedding_dir,
                'glove.6B.' + str(glove_embedding_len) + 'd.txt'
            ),
            embedding_dim=glove_embedding_len
        )

        tokenized = [
            os.path.join(
                root_path,
                tokenized_dir,
                f
            ) for f in os.listdir(os.path.join(root_path, tokenized_dir))
        ]
        vocabulary = []

        for file in (tokenized if self.verbose else tqdm(tokenized)):
            print('Working on', file)
            # Read tokenized news and titles
            with open(file, 'rb') as handle:

                data = np.array(pickle.load(handle))
                headlines, articles = data[:, 0], data[:, 1]

                if self.verbose:
                    # Print how many articles are present in the pickle
                    # Print even some statistics
                    print('Loaded %s articles' % len(articles))
                    print('Headline length (words): avg = %s, min = %s, max = %s' % get_text_stats(headlines))
                    print('Article length (words): avg = %s, min = %s, max = %s' % get_text_stats(articles))

                # Compute the vocabulary now, after truncating the lists
                # IMPORTANT : The total number of words will still depend on the number of available embedding!
                vocabulary_sorted, vocabulary_counter = get_vocabulary(headlines + articles)

                if self.verbose:
                    print('Computing for embeddable words..')

                # Find all the words in the truncated sentences for which we have an embedding
                embeddable = get_embeddable(vocabulary_sorted, word2index)

                added = 0

                if self.verbose:
                    print('Looking for new words..')

                # Adding all the embeddable words to our vocabulary
                # This process is slow
                for word in (tqdm(embeddable) if self.verbose else embeddable):
                    if word not in vocabulary:
                        added += 1
                        vocabulary.append(word)

        if self.verbose:
            print('Vocabulary fully computed, in total there are', len(vocabulary), 'different words')
            print('Now we are ready to generate padded and embedded files')

        word2index, embeddings, start_token, stop_token, padding_token = get_reduced_embedding_matrix(
            vocabulary,
            embeddings,
            word2index,
            glove_embedding_len,
            truncate_embedding_matrix_to = 2000,
        )

        if self.verbose:
            print('Saving embeddings')

        f_word2index = 'word2index.pkl'
        f_embeddings = 'embeddings.pkl'

        objects = {
            os.path.join(root_path, 'embedding/', f_word2index): word2index,
            os.path.join(root_path, 'embedding/', f_embeddings): embeddings
        }

        for path, data in objects.items():
            # Save to pickle
            with open(path, 'wb') as handle:
                pickle.dump(data, handle)

    def generate_emebedded_documents(self, tokenized_dir='tokenized/', ):
        word2index = DatasetManager.load_word2index()

        start_token = word2index['start_token']
        stop_token = word2index['stop_token']
        padding_token = word2index['padding_token']


        tokenized = [os.path.join(root_path, tokenized_dir, f) for f in
            os.listdir(os.path.join(root_path, tokenized_dir))]

        # Generating padded and embedded files
        for file in (tokenized if self.verbose else tqdm(tokenized)):
            print('Working on', file)
            # Read tokenized news and titles
            with open(file, 'rb') as handle:
                data = np.array(pickle.load(handle))
                headlines, articles = data[:, 0], data[:, 1]
            if self.verbose:
                print('Mapping current file to glove embeddings..')
            # We now need to map each word to its corresponding glove embedding index
            # IMPORTANT: If a word is not found in glove, IT WILL BE REMOVED! (for the moment..)
            headlines = map_to_glove_index(headlines, word2index)
            articles = map_to_glove_index(articles, word2index)

            if self.verbose:
                print('Adding start and stop tokens..')
            # VERY IMPORTANT
            # We want to add first start and stop tokens, and then perform padding!!!
            # This is a key part, we the order differs, we will not have what we want
            add_start_stop_tokens(headlines, start_token, stop_token, self.max_headline_len)
            add_start_stop_tokens(articles, start_token, stop_token, self.max_headline_len)

            if self.verbose:
                print('Padding sequences..')
            # Now we want to pad the headlines and articles to a fixed length
            headlines = pad_sequences(headlines, maxlen=self.max_headline_len, padding='post', value=padding_token)
            articles = pad_sequences(articles, maxlen=self.max_article_len, padding='post', value=padding_token)

            out = []
            for h, a in zip(headlines, articles):
                out.append([h, a])

            filename = ntpath.basename(file)
            filename = embedding_prefix + filename
            save_path = os.path.join(root_path, 'tokenized/', filename)

            # Save to pickle
            with open(save_path, 'wb') as handle:
                pickle.dump(out, handle)

    @staticmethod
    def generate_test_set(from_file, size=500):
        """
        IMPORTANT: This method will load and create a new test file REMOVING elements from the provided file
        :param size: the size of the test set
        :param from_file: the file to get test instances from
        """

        # Read tokenized news and titles
        with open(from_file, 'rb') as handle:
            data = np.array(pickle.load(handle))
            headlines, articles = data[:, 0], data[:, 1]

        out = []

        print('Saving TEST embedded test file')
        for h, a in zip(headlines[:size], articles[:size]):
            out.append([h, a])

        filename = embedding_prefix + 'TEST.pkl'
        save_path = os.path.join(root_path, 'tokenized/', filename)

        # Save to pickle
        with open(save_path, 'wb') as handle:
            pickle.dump(out, handle)

        out = []

        print('Overriding original file removing test instances..')
        for h, a in zip(headlines[size:], articles[size:]):
            out.append([h, a])

        filename = ntpath.basename(from_file)
        filename = embedding_prefix + filename
        save_path = os.path.join(root_path, 'tokenized/', filename)

        # Save to pickle
        with open(save_path, 'wb') as handle:
            pickle.dump(out, handle)

    def get_train_test(self, block_size=500):

        testing_set_path = os.path.join(tokenized_path, embedding_prefix + 'TEST.pkl')
        training_set_paths = []
        for f in os.listdir(tokenized_path):
            if ntpath.basename(f).startswith(embedding_prefix + tokenized_prefix):
                training_set_paths.append(os.path.join(tokenized_path, f))

        print('Training set made up by:')
        for p in training_set_paths:
            print(p)
        print('Testing set made up by:')
        print(testing_set_path)

        print('Getting number of total tokens..')
        w2i = DatasetManager.load_word2index()
        num_decoder_tokens = len(w2i)
        del w2i

        print('Generating iterator and testing set.. Using', num_decoder_tokens, 'tokens')

        """
        training_it = BatchIterator(
            max_headline_len=self.max_headline_len,
            num_decoder_tokens=num_decoder_tokens,
            tokenized_paths=training_set_paths,
            output_size=block_size,
            verbose=self.verbose
        )
        """
        training_gen = BatchGenerator(
            max_headline_len=self.max_headline_len,
            num_decoder_tokens=num_decoder_tokens,
            tokenized_paths=training_set_paths,
            output_size=block_size,
            verbose=self.verbose
        )



        print('Batch iterator successfully created')

        # ei = encoder input.. and so on
        ei_ts, di_ts, dt_ts = self.load_test(num_decoder_tokens, testing_set_path)
        return training_gen,ei_ts, di_ts, dt_ts
        #return training_it, ei_ts, di_ts, dt_ts
