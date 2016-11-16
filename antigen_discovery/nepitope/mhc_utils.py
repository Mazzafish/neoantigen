import pandas
import os
import glob
from nepitope import pep_utils


class FileConsolidation(object):
    """
    Class to ease up the analysis of multiple files/proteins. It will take as inputs a file containing the results
    from netMHCcons and will provide methods to output the data in nicely formatted pandas dataframes that contain
    a variety of accessory information regarding the proteins in question.
    """
    stable_cols = ['Pos', 'Peptide', 'ID']  #Columns that are always present

    def __init__(self, filepath, fasta_file, from_alignmet=False):
        """
        When netMHC or any other prediction method is run locally, then it might be the case that you'll have multiple
        files, each containing prediction for different alleles/n-mers. This method takes care of loading them all
        and consolidating them for later processing.
        :param filepath: path to files
        :param file_names: name of files
        :return:
        """
        self.fasta = fasta_file
        self.filepath = filepath
        self.files = glob.glob(self.filepath + '*.xls')
        self.allele_list = self._get_allele_list_from_file_names()
        self.protein_list = self._get_prot_list(self.files)

    def return_df_list(self):    #USE
        """
        Returning a list of dataframes from class.files attribute
        :return: list of dataframes if multiple files are provided, one per each file.
        """
        list_dfs = []

        for idx, files in enumerate(self.files):

            df = pandas.read_csv(files, sep='\t', skiprows=1)
            df = df[['Pos', 'Peptide', 'nM', 'Rank', 'ID']]
            df["Allele"] = self.allele_list[idx]
            df = self.aggregate_info(df)
            list_dfs.append(df)

        return list_dfs

    def optimized_list_df_by_prot(self, list_df):     #USE

        concatd = pandas.concat(list_df)
        prot_list = list(concatd.ID.unique())
        concatd = self.aggregate_info(concatd)  ##affinity and len data

        df_list_by_protein = []                 #slice by protein
        for i in prot_list:
            df_list_by_protein.append(concatd[concatd['ID'] == i])

        orig_name_prot_list = []   #rename protein names accoridng to original fasta file
        for i in df_list_by_protein:
            orig_name_prot_list.append(self.replace_names_in_df(i))

        return orig_name_prot_list

    @staticmethod
    def replace_X_with_underscore(df):
        """
        Necessary for proper netMHC processing.
        :param df: df
        :return: df
        """
        df['Peptide'] = df['Peptide'].str.replace('X', '-')
        return df

    @staticmethod
    def label_affinity(row):      #USE
        """
        Function ot be applied to a dataframe to introduce a column with a label for the binding affinity
        :param row: row of df
        :return: binding affinity level
        """
        if row['nM'] < 50.0:
            return 'High'
        if 50.0 < row['nM'] < 500.0:
            return 'Intermediate'
        if 500.0 < row['nM'] < 5000.0:
            return 'Low'
        if row['nM'] > 5000.0:
            return 'No'

    def aggregate_info(self, df1):      #USE
        """
        Add extra data to dataframe: affinity level label, and n-mer
        :param df1: df
        :return: df with extra data
        """

        df1['Affinity Level'] = df1.apply(lambda row: self.label_affinity(row), axis=1)
        df1['n-mer'] = df1['Peptide'].str.len()

        return df1

    @staticmethod
    def get_allele_list(files):
        """
        Retrieve alleles from netMHC file
        :param files: netMHC predictions
        :return: list of alleles
        """
        unique_alleles = []

        for i in files:

            df1 = pandas.read_csv(i, sep='\t')
            cols = list(df1.columns)

            for item in cols:
                if item.startswith('H'):
                    unique_alleles.append(item)

        return unique_alleles

    @staticmethod
    def rename_cols(df):

        col_names = list(df.columns)

        for i in col_names:
            if '.' in i:
                df = df.rename(columns={i: i.split('.')[0]})

        return df

    @staticmethod
    def add_allele_name(list_dfs, allele_list):
        """
        Add allele as a column to dataframes in a list of dataframes
        :param list_dfs: list of dfs
        :param allele_list: allele list retrieved from netMHC predictions
        :return: list of dataframes
        """

        for i in range(0, len(list_dfs[:-1])):
            list_dfs[i]['Allele'] = allele_list[i]

        return list_dfs

    def get_name_mapping(self):   #USE

        orig_names = pep_utils.create_separate_lists(self.fasta)[0]
        orig_names = [orig_name.replace('.', '_').strip('>') for orig_name in orig_names]
        abbr_names = self.protein_list
        name_mapping = {}

        for abbr_name in abbr_names:
            for orig_name in orig_names:
                if orig_name.startswith(abbr_name):
                    name_mapping[abbr_name] = orig_name

        return name_mapping

    def replace_names_in_df(self, df):  #USE

        name_mapping = self.get_name_mapping()

        for key in name_mapping.keys():
            if df.ID.unique()[0] == key:
                df.ID = df.ID.str.replace(key, name_mapping[key])
        return df

    def _get_file_names(self):  #USE
        files = []
        for i in self.file_names:
            files.append(self.filepath + i)
        return files

    def _get_allele_list_from_file_names(self):  #USE

        alleles = []
        for file in self.files:
            file_info = os.path.splitext(file)[0].split('_')

            for inf in file_info:
                if inf.startswith('HLA'):
                    alleles.append(inf)
        return alleles

    @staticmethod
    def _get_prot_list(files):  #USE
        """
        Retrieve list of proteins from netMHC file
        :param files: netMHC predictions
        :return: list of proteins
        """

        df1 = pandas.read_csv(files[0], sep='\t', skiprows=1)
        prot_ids = list(df1['ID'].unique())

        return prot_ids