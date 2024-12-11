from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableView, QDialogButtonBox, QHBoxLayout, QPushButton
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import numpy as np

class TableViewDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Visualización de CSV')
        self.setGeometry(100, 100, 800, 600)
        
        # Variable to hold the CSV data
        self.csv_data = None
        
        # Configure the table view
        self.table_view = QTableView()
        
        # Configure the layout and add the table view
        layout = QVBoxLayout()
        layout.addWidget(self.table_view)
        
        # Create a button box for confirm and cancel
        button_layout = QHBoxLayout()
        self.confirm_button = QPushButton("Confirm Import")
        self.cancel_button = QPushButton("Cancel")
        
        # Connect the buttons to their actions
        self.confirm_button.clicked.connect(self.confirm_import)
        self.cancel_button.clicked.connect(self.reject)  # Close dialog on cancel
        
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.cancel_button)
        
        # Add the button layout to the main layout
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Load the CSV file and populate the table
        self.load_csv(file_path)

    def load_csv(self, file_path):
        # Read the CSV file using numpy
        try:
            data = np.genfromtxt(file_path, delimiter=',', dtype=str)
        
            # Create the table model and add the data
            model = QStandardItemModel()
            
            # Add headers if available
            if data.size > 0:
                model.setHorizontalHeaderLabels(data[0])  # Set headers as the first row
                data = data[1:]  # Exclude the header row from the actual data
            
            # Populate the table with the CSV data
            for row in data:
                items = [QStandardItem(cell) for cell in row]
                model.appendRow(items)
            
            # Set the model to the table view
            self.table_view.setModel(model)
            
            # Store the data to be used when confirming the import
            self.csv_data = data
        except Exception as e:
            print(e)
    


    def confirm_import(self):
        # Accept the dialog and close it, signaling the data is confirmed
        self.accept()
        
    def get_data(self):
        # Get the model from the table view
        model = self.table_view.model()
        
        # Initialize a list to hold the exported data
        data = []
        
        # Iterate over the rows and columns of the model
        for row in range(model.rowCount()):
            row_data = []
            for column in range(model.columnCount()):
                # Get the item at the current row and column
                item = model.item(row, column)
                
                # Convert the item text to a float and add it to the row data
                try:
                    value = float(item.text())  # Convert the text to a float
                    row_data.append(value)
                except ValueError:
                    # Handle the case where conversion fails
                    print(f"Warning: could not convert '{item.text()}' to a float.")
                    row_data.append(0)  # Append a default value if conversion fails
                    
            # Append the row data to the main data list
            data.append(row_data)
        
        # Convert the list to a numpy array (optional, for easier manipulation)
        return np.array(data)