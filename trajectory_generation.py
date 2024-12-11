import sys
import numpy as np
from PyQt5.QtWidgets import  QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QPointF,pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor,QFont

class DrawWindow(QMainWindow):

    # Define a signal to emit the vectors scaled in cm
    vectors_ready = pyqtSignal(list)

    def __init__(self, N=5, max_vector_length_cm=100):
        super().__init__()
        self.setWindowTitle("Draw and Vectorize Trajectory")
        self.setGeometry(100, 100, 800, 600)
        
        self.N = N  # Number of vectors
        self.drawing = False
        self.points = []  # List to store the drawn points
        self.vectors = []  # List to store the vectors
        self.max_vector_length_cm = max_vector_length_cm  # Max vector length in cm
        
        # Main Widget and Layout
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        # Button to Vectorize the Trajectory (at the bottom)
        self.vectorize_button = QPushButton("Vectorizar Trayectoria", self)
        self.vectorize_button.clicked.connect(self.on_vectorize_button_clicked)
        self.layout.addWidget(self.vectorize_button)  # Add button at the top
        self.clear_button = QPushButton("Limpiar", self)
        self.clear_button.clicked.connect(self.clear_window)
        self.layout.addWidget(self.clear_button)  # Add button at the top
        self.layout.addStretch()  # Add stretch at the bottom to push content upwards

        
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.points.append(event.pos())  # Start capturing points
    
    def mouseMoveEvent(self, event):
        if self.drawing:
            self.points.append(event.pos())  # Continue capturing points
            self.update()  # Redraw the canvas with the new point
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Draw original trajectory (freehand)
        if self.points:
            painter.setPen(QPen(QColor(0, 0, 0), 2, Qt.SolidLine))  # Black for original path
            for i in range(1, len(self.points)):
                painter.drawLine(self.points[i - 1], self.points[i])
        
        # Draw vectorized trajectory (N vectors)
        if self.vectors:
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.SolidLine))  # Red for vectors
            for i in range(1, len(self.vectors)):
                p1 = QPointF(self.vectors[i - 1][0], self.vectors[i - 1][1])
                p2 = QPointF(self.vectors[i][0], self.vectors[i][1])
                painter.drawLine(p1, p2)

        # Draw scale in cm at the bottom
        self.draw_scale(painter)
    
    def vectorize_trajectory(self):
        if len(self.points) < self.N:
            print(f"Not enough points to create {self.N} vectors.")
            return
        
        # Convert points into numpy arrays
        points_np = np.array([(p.x(), p.y()) for p in self.points])
        
        # Calculate the cumulative distances between consecutive points
        dist = np.sqrt(np.sum(np.diff(points_np, axis=0)**2, axis=1))
        cum_dist = np.concatenate(([0], np.cumsum(dist)))
        
        # Generate equally spaced indices along the cumulative distance
        vector_indices = np.linspace(0, cum_dist[-1], self.N+1)
        
        # Interpolate to get the vector points
        vectors = [np.interp(vector_indices, cum_dist, points_np[:, dim]) for dim in range(2)]
        
        # Store the vectors for visualization
        self.vectors = list(zip(vectors[0], vectors[1]))
        
        # Trigger repaint to visualize vectors
        self.update()

        # Optionally print the vectorized points
        print("Vectorized Points (X, Y):")
        for i in range(self.N):
            print(f"Vector {i+1}: ({self.vectors[i][0]}, {self.vectors[i][1]}) -> ({self.vectors[i+1][0]}, {self.vectors[i+1][1]})")


    def draw_scale(self, painter):
        """
        Draw a grid in centimeters with labels on both axes.
        """
        window_width = self.size().width()
        window_height = self.size().height()

        # Calculate the pixels per cm using the window diagonal as 20 cm
        max_window_length_pixels = np.sqrt(window_width**2 + window_height**2)
        pixels_per_cm = max_window_length_pixels / self.max_vector_length_cm

        painter.setPen(QPen(QColor(0, 0, 0), 1, Qt.SolidLine))
        painter.setFont(QFont("Arial", 8))

        # Draw vertical grid lines and label them with centimeters
        for i in range(0, int(window_width // pixels_per_cm) + 1):
            x = int(i * pixels_per_cm)
            painter.drawLine(x, 0, x, window_height)  # Draw vertical grid line
            if i%5==0:
                painter.drawText(x + 2, 12, f"{i} cm")   # Label the grid line

        # Draw horizontal grid lines and label them with centimeters
        for i in range(0, int(window_height // pixels_per_cm) + 1):
            y = int(i * pixels_per_cm)
            painter.drawLine(0, y, window_width, y)  # Draw horizontal grid line
            if i%5==0:
                painter.drawText(2, y - 2, f"{i} cm")    # Label the grid line

    def scale_vectors_to_cm(self, vectors):
        """
        Scales the vectors so that the maximum vector length is in centimeters
        without converting them back to pixels.
        """
        # Get the maximum size of the window
        window_width = self.size().width()
        window_height = self.size().height()

        # Calculate the maximum length of the window diagonal in pixels
        max_window_length_pixels = np.sqrt(window_width**2 + window_height**2)

        # Calculate the scale: 20 cm corresponds to max_window_length_pixels pixels
        pixels_per_cm = max_window_length_pixels / self.max_vector_length_cm

        # Convert vectors from pixels to centimeters
        vector_points_np = np.array(vectors)
        
        # Apply the scale to convert from pixels to centimeters
        scaled_vectors_cm = vector_points_np / pixels_per_cm

        return list(map(tuple, scaled_vectors_cm))
    
    def on_vectorize_button_clicked(self):
        # Call the function to scale vectors
        self.vectorize_trajectory()
        print(self.vectors)
        scaled_vectors = self.scale_vectors_to_cm(self.vectors)
        
        # Emit the scaled vectors using the signal
        self.vectors_ready.emit(scaled_vectors)

    def clear_window(self):
        """
        Clears the entire drawing area, resetting the trajectory and repainting the canvas.
        """
        # Clear the list of points (assuming you store the drawn points in self.points)
        self.points = []
        self.vectors = []

        # Trigger a repaint to redraw the blank canvas
        self.update()  # This will call the paintEvent method to redraw the window
#def main():
    #app = QApplication(sys.argv)
    #window = DrawWindow(N=5)  # Set N here for number of vectors
    #window.show()
    #sys.exit(app.exec_())

#if __name__ == "__main__":
    #main()
