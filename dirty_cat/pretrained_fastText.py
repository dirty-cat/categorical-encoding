import os
import numpy as np
import fasttext
import fasttext.util
from pathlib import Path
from sklearn.base import BaseEstimator, TransformerMixin


class PretrainedFastText(BaseEstimator, TransformerMixin):
    
    """
    Category embedding using a fastText pretrained model.
    In a nutshell, fastText learns embeddings for character n-grams based on
    their context. Sequences of words are then embedded by averaging the
    n-gram representations it is made of. fastText embeddings thus capture
    both semantic and morphological information.
    
    The code is largely based on the fasttext package, for which this class
    provides a simple interface.
    
    Parameters
    ----------
    
    n_components : int, default=300
        The size of the fastText embeddings (300 for the original model).
        If n_components < 300, the fastText model is automatically
        reduced to output vectors of the desired size.
        If n_components > 300, it is automatically set to 300.
        
    language : str, default='en'
        The language of the fastText model to load.
        For instance, language='en' corresponds to fastText trained on an
        English corpora. Pretrained models are available here
        <https://fasttext.cc/docs/en/crawl-vectors.html>.
    
    bin_dir : str, default='./fastText_bins'
        The path to the folder containing the fastText models to load.
        Models downloaded or saved with the 'download_model' or 'save_model'
        methods also end up in bin_dir.
    
    file_name : str or None, default=None
        If given, indicates the file to load instead of
        "cc.{language}.{n_components}.bin". This allows to load other fastText
        models than the ones available with 'download_model'.
        If given, n_components must be set appropriately to the embedding size
        of the model.
        
    References
    ----------
    For a detailed description of the method, see
    `Enriching Word Vectors with Subword Information
    <https://arxiv.org/abs/1607.04606>`_ by Bojanowski et al. (2017).
    
    Additional information about pretrained models and the fasttext package
    can be found here <https://fasttext.cc>.
    """

    def __init__(self, n_components=300, language='en',
                 bin_dir='./fastText_bins', file_name=None):
        
        self.n_components = n_components if n_components < 300 else 300
        self.language = language
        self.bin_dir = bin_dir
        # Load the model from binary file
        if file_name == None:
            file_name = f"cc.{language}.{n_components}.bin"
        self.file_path = os.path.join(bin_dir, file_name)
        self.load_model()
        return
    
    def download_model(self):
        
        """
        Download pre-trained common-crawl vectors from fastText's website
        <https://fasttext.cc/docs/en/crawl-vectors.html>.
        Downloaded models are stored in self.bin_dir.
        """
    
        cwd = os.getcwd()
        os.chdir(self.bin_dir)
        # Download fastText model in bin_dir
        fasttext.util.download_model(self.language, if_exists='ignore')
        os.chdir(cwd)
        return
    
    def load_model(self):
        
        """
        Load a pretrained fastText model from the corresponding binary file
        in self.bin_dir. If n_components is smaller than the dimensionality of
        the loaded model, the latter is automatically reduced to output vectors
        of the desired size.
        """
        
        file_path_300 = os.path.join(
            self.bin_dir, f"cc.{self.language}.300.bin")
        # Load model with dim = n_components
        if os.path.isfile(self.file_path):
            self.ft_model = fasttext.load_model(self.file_path)
        # Otherwise, load the raw model with dim = 300 and reduce it
        elif os.path.isfile(file_path_300):
            self.ft_model = fasttext.load_model(file_path_300)
            fasttext.util.reduce_model(self.ft_model, self.n_components)
        else: # Else, raise an error
            raise FileNotFoundError(
                f"The file {file_path_300} doesn't exist.\
                Download it with self.download_model(), or from\
                https://fasttext.cc/docs/en/crawl-vectors.html.\
                Then load it manually with self.load_model().")
        return
    
    def save_model(self, file_name=None):
        
        """
        Save the current fastText model in self.bin_dir.
        This is particularly useful to save reduced models, which
        require less memory to be stored/loaded.
        
        Parameters
        ----------
        
        file_name : str or None, default=None
            If given, indicates the filename under which the model
            must be saved. Otherwise, the default file_name is
            "cc.{self.language}.{self.n_components}.bin".
        """
        
        cwd = os.getcwd()
        os.chdir(self.bin_dir)
        # Save fastText model in bin_dir
        if file_name == None:
            file_name = f"cc.{self.language}.{self.n_components}.bin"
        self.ft_model.save_model(file_name)
        os.chdir(cwd)
        return
    
    def reduce_model(self, n_components):
        
        """
        Reduce the current model to obtain embeddings of the desired size.
        
        Parameters
        ----------
        
        n_components : int
            The new size of the fastText embeddings.
            Must be smaller than the previous embedding size.
        """
        
        assert n_components < self.n_components, f"Cannot expand embedding\
            size from {self.n_components} to {n_components}."
        self.n_components = n_components
        fasttext.util.reduce_model(self.ft_model, self.n_components)
        return
                    
    def fit(self, X=None, y=None):
        
        """
        Since the model is already trained, simply checks that is has been
        loaded properly.
        """

        assert hasattr(self, 'ft_model'), f"The fastText model hasn't been\
            automatically loaded. Load it manually with self.load_model()."
        return self

    def transform(self, X):
        
        """
        Return fastText embeddings of input strings in X.
        
        Parameters
        ----------
        X : array-like, shape (n_samples, ) or (n_samples, 1)
            The string data to encode.

        Returns
        -------
        X_out : 2-d array, shape (n_samples, n_components)
            Transformed input.
        """
        
        # Check input data shape
        X = np.asarray(X)
        assert X.ndim == 1 or (X.ndim == 2 and X.shape[1] == 1), f"ERROR:\
        shape {X.shape} of input array is not supported."
        if X.ndim == 2:
            X = X[:, 0]
        # Check if first item has str or np.str_ type
        assert isinstance(X[0], str), "ERROR: Input data is not string."
        # Get unique categories and store the associated embeddings in a dict
        unq_X, lookup = np.unique(X, return_inverse=True)
        unq_X_out = np.empty((len(unq_X), self.n_components))
        for idx, x in enumerate(unq_X):
            unq_X_out[idx] = self.ft_model.get_sentence_vector(x)
        X_out = unq_X_out[lookup]
        return X_out