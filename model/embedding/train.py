import sys
import os
import time

this_path = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.abspath(os.path.join(this_path, os.pardir, os.pardir))
sys.path.append(root_path)

print(root_path)

from model.embedding.generator import DataGenerator
from keras.callbacks import EarlyStopping, TensorBoard
from dataset.dataset_manager import DatasetManager
from model import encoderdecoder
from model import config
from model.embedding import output_generator

config = config.embedding_cfg

# Model save name
model_name = 'n2t_full_embedding_' + str(config.glove_embedding_len) + '_latent_' + str(
    config.latent_dim) + '_cosine_patience_5.h5'

# Overfitting avoidance
early_stopping = EarlyStopping(monitor='val_loss', patience=5, min_delta=0)

# Model checkpoint
# checkpoint = ModelCheckpoint(filepath=model_name+'_earlystopped_.h5', monitor='val_loss', save_best_only=True)

# Tensorboard
# histogram_freq=1, write_graph=True
tensorboard = TensorBoard(log_dir=config.tensorboard_log_dir, write_graph=True)

# Callbacks
callbacks = [tensorboard, early_stopping]

print(config.preprocess_data)

if config.preprocess_data:
    # -------------------------------------------------------------------------------------
    # --------------------------------- DATA PROCESSING -----------------------------------
    # -------------------------------------------------------------------------------------

    mgr = DatasetManager(max_headline_len=config.max_headline_len, max_article_len=config.max_article_len,
                         min_headline_len=config.min_headline_len, min_article_len=config.min_article_len, verbose=False,
                         get_in_out=output_generator.get_inputs_outputs)
    mgr.tokenize(size=50, only_tfidf=False, folder=config.preprocess_folder)
    mgr.generate_embeddings(glove_embedding_len=config.glove_embedding_len, tokenized_dir=config.preprocess_folder,
                            embedding_dir=config.embedding_matrix_location)
    mgr.generate_emebedded_documents(tokenized_dir=config.preprocess_folder, embedding_dir=config.embedding_matrix_location)

embeddings = DatasetManager.load_embeddings(embedding_dir=config.embedding_matrix_location)
word2index = DatasetManager.load_word2index(embedding_dir=config.embedding_matrix_location)

# ----------------------------------------------------------------------------------------
# ----------------------------------------- TRAIN ----------------------------------------
# ----------------------------------------------------------------------------------------

print('\nBuilding model')

model = encoderdecoder.encoder_decoder(latent_dim=config.latent_dim, max_encoder_seq_len=config.max_article_len,
                                       max_decoder_seq_len=config.max_headline_len,
                                       num_encoder_tokens=embeddings.shape[0],
                                       num_decoder_tokens=embeddings.shape[0],
                                       glove_embedding_len=config.glove_embedding_len,
                                       output_dimension=config.glove_embedding_len,
                                       embeddings=embeddings, optimizer=config.optimizer,
                                       dense_activation=config.dense_activation, loss=config.loss)

model.summary()

print('-' * 100)
print('We will train for a total of', config.tot_epochs, 'epochs')
print('-' * 100)

data_generator = DataGenerator(max_decoder_seq_len=config.max_headline_len, decoder_tokens=embeddings.shape[0],
                               test_size=config.test_ratio, embeddings=embeddings,
                               glove_embedding_len=config.glove_embedding_len, )

model.fit_generator(generator=data_generator.generate_train(), validation_data=data_generator.generate_test(),
                    validation_steps=data_generator.get_steps_validation(), epochs=config.tot_epochs, max_queue_size=2,
                    use_multiprocessing=False, verbose=2, steps_per_epoch=data_generator.get_steps_per_epoch(),
                    callbacks=callbacks)

# Save model
print('Saving model...')
model.save(model_name)
