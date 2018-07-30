import gzip
import os

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


CSV_DATA_STORE_FILE = './heartrate_datastore.csv.gz'
NUMPY_DATA_STORE_FILE = './heartrate_datastore.h5'


def load_csv_data():
    try:
        with gzip.open(CSV_DATA_STORE_FILE, 'rt', newline='') as file:
            return pd.read_csv(
                file,
                header=None,
                names=['Datetime', 'Heartrate(BPM)'],
                index_col=0,
                skipinitialspace=True,
                dtype={'Datetime': np.uint64, 'Heartrate(BPM)': np.float64},
                # converters={'Datetime': parse_iso_datetime},
                parse_dates=True,
                infer_datetime_format=True,
            )
    except FileNotFoundError:
        return pd.DataFrame(
            names=['Datetime', 'Heartrate(BPM)'],
        )


def load_numpy_data():
    return pd.read_hdf(NUMPY_DATA_STORE_FILE, 'heartrate')


def save_numpy_data():
    global loaded_data
    loaded_data.to_hdf(
        NUMPY_DATA_STORE_FILE,
        key='heartrate',
        format='table',
        mode='w',
        complib='zlib',
        complevel=9,
    )


# save_numpy_data()

try:
    loaded_data = load_numpy_data()
except FileNotFoundError:
    loaded_data = load_csv_data()
