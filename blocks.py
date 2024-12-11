
from PyQt5.QtWidgets import QGraphicsItem
from PyQt5.QtCore import QRectF

class Block(QGraphicsItem):
    def __init__(self, name, x, y, width, height, color, parameters=None):
        super().__init__()
        self.rect = QRectF(x, y, width, height)  # Bounding rect centered at (0, 0)
        self.color = color
        self.name = name
        self.parameters = parameters or {}

        

    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget):
        painter.setPen(self.color)
        painter.setBrush(self.color)
        painter.drawRect(self.rect)
        print(f'{self.rect.x()},{self.rect.y()}')

    def contains(self, point):
        local_point = self.mapFromScene(point)
        
        print(f'Click position {local_point.x()}, {local_point.y()}')

        # Verificar si el punto local (con el delta) está dentro del rectángulo
        return self.rect.contains(local_point)
    
    def update_parameters(self, new_parameters):
        self.parameters = new_parameters

    def get_param_values(self):
        return list(self.parameters.values())

    def get_name(self):
        return self.name