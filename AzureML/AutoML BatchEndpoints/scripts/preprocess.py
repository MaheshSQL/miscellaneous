import argparse
import datetime
from pathlib import Path
import yaml
from mltable import load
from sklearn.model_selection import train_test_split  


def parse_args():
    # setup arg parser
    parser = argparse.ArgumentParser()

    # add arguments
    parser.add_argument("--train_data", type=str)
    # parser.add_argument("--validation_data", type=str)
    # parser.add_argument("--test_data", type=str)
    parser.add_argument("--preprocessed_train_data", type=str)
    parser.add_argument("--preprocessed_validation_data", type=str)
    parser.add_argument("--preprocessed_test_data", type=str)
    # parse args
    args = parser.parse_args()
    print("args received ", args)
    # return args
    return args


def get_preprocessed_data(dataframe):
    """
    Do your preprocessing as needed here..
    Currently we are just passing pandas dataframe as it is...
    """
    return dataframe


def main(args):
    
    print(f'args.preprocessed_train_data:{args.preprocessed_train_data}')
    print(f'args.preprocessed_validation_data:{args.preprocessed_validation_data}')
    print(f'args.preprocessed_test_data:{args.preprocessed_test_data}')
    
    # Define split percentages  
    train_size = 0.8  
    validation_size = 0.1
    test_size = 0.1
    random_state=42
    
    # Ensure the splits sum to 1  
    assert train_size + validation_size + test_size == 1, "Split percentages must sum to 1"  

    """
    Preprocessing of training/validation/test data
    """
    train_data_table = load(args.train_data)
    train_dataframe = train_data_table.to_pandas_dataframe()
    
    #---------------------------------#
    # train, validation, test split

    # Split dataframe into train and temp (validation + test)  
    train_df, temp_df = train_test_split(train_dataframe, test_size=(1 - train_size), random_state=random_state)  

    # Split temp dataframe into validation and test  
    val_df, test_df = train_test_split(temp_df, test_size=test_size, random_state=random_state)  
    #---------------------------------#
    
    
    preprocessed_train_dataframe = get_preprocessed_data(train_df)
    print(f'preprocessed_train_dataframe.shape: {preprocessed_train_dataframe.shape}')

    # write preprocessed train data in output path
    preprocessed_train_dataframe.to_csv(
        args.preprocessed_train_data + "/Australian Vehicle Prices_train.csv",
        index=False,
        header=True,
    )
    

    # Commented below as we are splitting train_df into val_df and test_df, below only required when these all 3 datasets will be provided explicitly.
    # validation_data_table = load(args.validation_data)
    # validation_dataframe = validation_data_table.to_pandas_dataframe()
    preprocessed_validation_dataframe = get_preprocessed_data(val_df)
    print(f'preprocessed_validation_dataframe.shape: {preprocessed_validation_dataframe.shape}')

    # write preprocessed validation data in output path
    preprocessed_validation_dataframe.to_csv(
        args.preprocessed_validation_data + "/Australian Vehicle Prices_validation.csv",
        index=False,
        header=True,
    )

    # Commented below as we are splitting train_df into val_df and test_df, below only required when these all 3 datasets will be provided explicitly.
    # test_data_table = load(args.test_data)
    # test_dataframe = test_data_table.to_pandas_dataframe()
    preprocessed_test_dataframe = get_preprocessed_data(test_df)
    print(f'preprocessed_test_dataframe.shape: {preprocessed_test_dataframe.shape}')

    # write preprocessed validation data in output path
    preprocessed_test_dataframe.to_csv(
        args.preprocessed_test_data + "/Australian Vehicle Prices_test.csv",
        index=False,
        header=True,
    )

    # Write MLTable yaml file as well in output folder
    # Since in this example we are not doing any preprocessing, we are just copying same yaml file from input,change it if needed

    # read and write MLModel yaml file for train data
    with open(args.train_data + "/MLTable", "r") as file:
        yaml_file = yaml.safe_load(file)
        yaml_file['paths'][0]['file'] = './Australian Vehicle Prices_train.csv'
    with open(args.preprocessed_train_data + "/MLTable", "w") as file:
        yaml.dump(yaml_file, file)

    # read and write MLModel yaml file for validation data
    # with open(args.validation_data + "/MLTable", "r") as file: # <-- Commented as we shall only supply MLTable for train, same used as reference for val and test
    with open(args.train_data + "/MLTable", "r") as file:        
        yaml_file = yaml.safe_load(file)
        yaml_file['paths'][0]['file'] = './Australian Vehicle Prices_validation.csv'
    with open(args.preprocessed_validation_data + "/MLTable", "w") as file:
        yaml.dump(yaml_file, file)

    # read and write MLModel yaml file for validation data
    # with open(args.test_data + "/MLTable", "r") as file: # <-- Commented as we shall only supply MLTable for train, same used as reference for val and test
    with open(args.train_data + "/MLTable", "r") as file:
        yaml_file = yaml.safe_load(file)
        yaml_file['paths'][0]['file'] = './Australian Vehicle Prices_test.csv'
    with open(args.preprocessed_test_data + "/MLTable", "w") as file:
        yaml.dump(yaml_file, file)


# run script
if __name__ == "__main__":
    # parse args
    args = parse_args()

    # run main function
    main(args)
