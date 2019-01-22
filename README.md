
# News2Headline [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![CodeFactor](https://www.codefactor.io/repository/github/ab3llini/news2headline/badge)](https://www.codefactor.io/repository/github/ab3llini/news2headline)

Recurrent neural networks for headline generation.

> We have written a paper about this work. You can find it in the project root.


## Abstract
The aim of this work is to build a Deep Learning algorithm that is able to predict articles headline starting from their content. 

We first introduce the reasons and related work that inspired us, illustrate the dataset we used, present some of the foundamental preprocessing steps performed on the dataset and then we dive into the details about the model we used.

We are proposing two different models, both made up by an Encoder-Decoder neural network architecture that exploits pre-trained GloVe embeddings. 

In the last section we present results of our models against the state-of-the-art techniques using three different evaluation metrics: BLEU, Semantic Similarity and Syntactic Correctness.

The interesting result we can derive from this work is that we were able to replicate state-of-the-art results in limited time and starting from scratch. 

This work has been developed as a class project for UIC CS 521: Statistical Natural Language Processing.
