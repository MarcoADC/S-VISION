import threading
import numpy as np

class DataContainer:
    def __init__(self, num_sensores):
        
        self.data_list = []
        self.colum_num = num_sensores +2 #+2 por numero de muestra y tiempo de muestra
        self.lock = threading.Lock()

    def update_data(self, new_data):
        with self.lock:
            self.data_list = new_data.tolist()

    def add_data_row(self, new_row):
        with self.lock:
            
            if len(new_row) < self.colum_num:

                new_row_padded = new_row + [0] * (self.colum_num - len(new_row))
                self.data_list.append(new_row_padded)
            elif len(new_row) < self.colum_num:
                print('implementar , len(new_row) < self.colum_num')            
            else:
                self.data_list.append(new_row)

    def get_data(self):
        with self.lock:
            return np.array(self.data_list)

    def get_columns_number(self):
        return self.colum_num
    
    def get_rows_numer(self):
        return len(self.data_list)