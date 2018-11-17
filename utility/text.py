from collections import Counter
import numpy as np

def get_vocabulary(list_):

    """
    Computes the vocabulary for the provided list of sentences
    :param list_: a list of sentences (strings)
    :return: a dictionary with key, val = word, count and a sorted list, by count, of all the words
    """

    all_the_words = []

    for text in list_:
        for word in text:
            all_the_words.append(word)

    vocabulary_counter = Counter(all_the_words)
    vocabulary_sorted = list(map(lambda x: x[0], sorted(vocabulary_counter.items(), key=lambda x: -x[1])))
    return vocabulary_sorted, vocabulary_counter


def get_avg_text_len(list_):
    return sum([len(x) for x in list_]) / len(list_)


def get_max_text_len(list_):
    return max([len(x) for x in list_])


def get_min_text_len(list_):
    return min([len(x) for x in list_])


def get_text_stats(list_):
    """
    Returns statistics about the list of sentences in a more efficient way
    w.r.t. calling the three methods above separately
    """

    lens = [len(x) for x in list_]
    l_ = len(list_)

    return sum(lens) / l_, min(lens), max(lens)


def map_sentence_to_glove_index(list_, word2index):
    """
    Will map all the words in the list with their corresponding index in the glove words dict
    :param list_: the list of words
    :param word2index: the dict which contains the mapping between words and glove indices
    :return: the mapped list
    """
    mapped = []

    for word in list_:
        if word in word2index:
            mapped.append(word2index[word])

    return mapped


def map_to_glove_index(sentences, word2index):
    """
    Wrapper around map_sentence_to_glove_index to process multiple headlines/articles
    """
    indexed = []
    for sentence in sentences:
        indexed.append(map_sentence_to_glove_index(sentence, word2index))

    return indexed


def truncate_sentences(sentences, maxlen):
    truncated = []
    for sentence in sentences:
        truncated.append(sentence[:maxlen])

    return truncated


def get_embeddable(words, word2index):
    embeddable = []
    for word in words:
        if word in word2index:
            embeddable.append(word)
    return embeddable


def print_first_n_pairs(a, b, n):
    for (i, (a, b)) in enumerate(zip(a[:n], b[:n])):
        print(str(i) + ')\n' + str(a) + '\n' + str(b))


def get_reduced_embedding_matrix(vocab, glove_embeddings, word2index, glove_size):

    new_word2index = {}
    new_embedding = np.zeros((len(vocab), glove_size))

    for index, word in enumerate(vocab):
        new_word2index[word] = index
        new_embedding[index] = glove_embeddings[word2index[word]]

    return new_word2index, new_embedding

