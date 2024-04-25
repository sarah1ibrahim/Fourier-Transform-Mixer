from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject
from PyQt5.QtGui import QBrush, QColor, QPen, QPainterPath, QPainter
from PyQt5.QtWidgets import QGraphicsView, QGraphicsRectItem, QGraphicsItem, QGraphicsPathItem


# This class represents a single handle that the user can drag to resize a rectangle in a QGraphicsView.
'''The parentItem of a HandleItem is a SizeGripItem. 
Each handle is a child of the size grip, so when the size grip moves, all the handles move with it.'''
class HandleItem(QGraphicsRectItem):
    class SignalEmitter(QObject):
        positionChanged = pyqtSignal(QPointF, object)
        
    def __init__(self, position_flags, parent):
        QGraphicsRectItem.__init__(self, -5, -5, 10, 10, parent)
        self._positionFlags = position_flags
        self.setBrush(QBrush(QColor(81, 168, 220, 200)))
        self.setPen(QPen(QColor(0, 0, 0, 255), 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        self.setFlag(self.ItemIsMovable)
        self.setFlag(self.ItemSendsGeometryChanges)
        
        self.emitter = self.SignalEmitter()

    def positionflags(self):
        return self._positionFlags

    def itemChange(self, change, value):
        retVal = value # position value of handle
        #  handle’s position is about to change.
        if change == self.ItemPositionChange:
            retVal = self.restrictPosition(value)  # ensure handle stays within rectangle's boundaries
        # handle's position has just changed.
        elif change == self.ItemPositionHasChanged:
            # adjust size of rectangle based on handle's new position
            pos = value
            if self.positionflags() == SizeGripItem.TopLeft:
                self.parentItem().setTopLeft(pos)
            elif self.positionflags() == SizeGripItem.Top:
                self.parentItem().setTop(pos.y())
            elif self.positionflags() == SizeGripItem.TopRight:
                self.parentItem().setTopRight(pos)
            elif self.positionflags() == SizeGripItem.Right:
                self.parentItem().setRight(pos.x())
            elif self.positionflags() == SizeGripItem.BottomRight:
                self.parentItem().setBottomRight(pos)
            elif self.positionflags() == SizeGripItem.Bottom:
                self.parentItem().setBottom(pos.y())
            elif self.positionflags() == SizeGripItem.BottomLeft:
                self.parentItem().setBottomLeft(pos)
            elif self.positionflags() == SizeGripItem.Left:
                self.parentItem().setLeft(pos.x())
            # Emit signal with the new position and the HandleItem itself
            self.emitter.positionChanged.emit(retVal, self)
        return retVal

    def restrictPosition(self, newPos):
        retVal = self.pos()
        
        # get the external rectangle of the parent item (here, the image)
        parentRect = self.parentItem().getExternRect() 
        
        # limit new positions to the external rectangle (size of the parent item or image)
        if self.positionflags() & SizeGripItem.Top or self.positionflags() & SizeGripItem.Bottom:
            retVal.setY(max(min(newPos.y(), parentRect.bottom()), parentRect.top()))

        if self.positionflags() & SizeGripItem.Left or self.positionflags() & SizeGripItem.Right:
            retVal.setX(max(min(newPos.x(), parentRect.right()), parentRect.left()))

        # limit the positions of the handles to not surpass the bounds or edges of the internal/cropping rectangle
        if self.positionflags() & SizeGripItem.Top and retVal.y() > self.parentItem()._rect.bottom():
            retVal.setY(self.parentItem()._rect.bottom())

        elif self.positionflags() & SizeGripItem.Bottom and retVal.y() < self.parentItem()._rect.top():
            retVal.setY(self.parentItem()._rect.top())

        if self.positionflags() & SizeGripItem.Left and retVal.x() > self.parentItem()._rect.right():
            retVal.setX(self.parentItem()._rect.right())

        elif self.positionflags() & SizeGripItem.Right and retVal.x() < self.parentItem()._rect.left():
            retVal.setX(self.parentItem()._rect.left())

        return retVal


# This class represents a size grip, which is a widget that the user can drag to resize a window or a rectangle.
'''The parentItem of a SizeGripItem is a CropItem. 
The size grip is a child of the cropping rectangle, so when the cropping rectangle moves, the size grip (and therefore all the handles) move with it.'''
class SizeGripItem(QGraphicsItem):
    # The position flags based on bitwise operations; used to specify which edges of the rectangle a handle can resize.
    Top = 0x01
    Bottom = 0x1 << 1
    Left = 0x1 << 2
    Right = 0x1 << 3
    # The corner flags are created by using the bitwise OR operation (|) to combine the edge flags
    TopLeft = Top | Left
    BottomLeft = Bottom | Left
    TopRight = Top | Right
    BottomRight = Bottom | Right

    # map the position flags to appropriate cursor shapes
    handleCursors = {
        TopLeft: Qt.SizeFDiagCursor,
        Top: Qt.SizeVerCursor,
        TopRight: Qt.SizeBDiagCursor,
        Left: Qt.SizeHorCursor,
        Right: Qt.SizeHorCursor,
        BottomLeft: Qt.SizeBDiagCursor,
        Bottom: Qt.SizeVerCursor,
        BottomRight: Qt.SizeFDiagCursor,
    }

    def __init__(self, parent):
        QGraphicsItem.__init__(self, parent)
        self._handleItems = []

        self._rect = QRectF(0, 0, 0, 0)
        if self.parentItem():
            # get the size of the cropping rectangle
            self._rect = self.parentItem().rect()

        # create eight handles (one for each corner and one for each edge of the rectangle) 
        # and store them in _handleItems.
        for flag in (self.TopLeft, self.Top, self.TopRight, self.Right,
                     self.BottomRight, self.Bottom, self.BottomLeft, self.Left):
            handle = HandleItem(flag, self)
            handle.setCursor(self.handleCursors[flag])
            self._handleItems.append(handle)

        self.updateHandleItemPositions()

    def getExternRect(self):
        if self.parentItem():
            return self.parentItem().extern_rect
        else:
            return QRectF(0, 0, 0, 0)

    def boundingRect(self):
        if self.parentItem():
            return self._rect
        else:
            return QRectF(0, 0, 0, 0)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(127, 127, 127), 2.0, Qt.DashLine))
        painter.drawRect(self._rect)

    def doResize(self):
        # set the size of the cropping rectangle
        self.parentItem().setRect(self._rect)
        self.updateHandleItemPositions()

    def updateHandleItemPositions(self):
        for item in self._handleItems:
            item.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)

            if item.positionflags() == self.TopLeft:
                item.setPos(self._rect.topLeft())
            elif item.positionflags() == self.Top:
                item.setPos(self._rect.left() + self._rect.width() / 2 - 1,
                            self._rect.top())
            elif item.positionflags() == self.TopRight:
                item.setPos(self._rect.topRight())
            elif item.positionflags() == self.Right:
                item.setPos(self._rect.right(),
                            self._rect.top() + self._rect.height() / 2 - 1)
            elif item.positionflags() == self.BottomRight:
                item.setPos(self._rect.bottomRight())
            elif item.positionflags() == self.Bottom:
                item.setPos(self._rect.left() + self._rect.width() / 2 - 1,
                            self._rect.bottom())
            elif item.positionflags() == self.BottomLeft:
                item.setPos(self._rect.bottomLeft())
            elif item.positionflags() == self.Left:
                item.setPos(self._rect.left(),
                            self._rect.top() + self._rect.height() / 2 - 1)
            item.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def setTop(self, v):
        self._rect.setTop(v)
        self.doResize()

    def setRight(self, v):
        self._rect.setRight(v)
        self.doResize()

    def setBottom(self, v):
        self._rect.setBottom(v)
        self.doResize()

    def setLeft(self, v):
        self._rect.setLeft(v)
        self.doResize()

    def setTopLeft(self, v):
        self._rect.setTopLeft(v)
        self.doResize()

    def setTopRight(self, v):
        self._rect.setTopRight(v)
        self.doResize()

    def setBottomRight(self, v):
        self._rect.setBottomRight(v)
        self.doResize()

    def setBottomLeft(self, v):
        self._rect.setBottomLeft(v)
        self.doResize()


# this class represents the cropping rectangle
'''The parentItem of a CropItem is a QGraphicsPixmapItem (or any other QGraphicsItem). 
The cropping rectangle is a child of the pixmap item, so when the pixmap item moves, 
the cropping rectangle (and therefore the size grip and all the handles) move with it.'''
class CropItem(QGraphicsPathItem):
    def __init__(self, parent):
        QGraphicsPathItem.__init__(self, parent)
        # outer rectangle (the same size as the parent item or QGraphicsItem - here, it is the image as a QGraphicsPixmapItem)
        self.extern_rect = parent.boundingRect()
        # inner rectangle (the cropping rectangle)
        self.intern_rect = QRectF(0, 0, self.extern_rect.width()/2, self.extern_rect.height()/2)
        self.intern_rect.moveCenter(self.extern_rect.center())
        self.setBrush(QColor(10, 100, 100, 100))  # set brush color of the object 
        self.setPen(QPen(Qt.NoPen))  # set pen style for the object to NoPen (no outline or line will be drawn)
        self.sizeGripItem = SizeGripItem(self)  # create SizeGripItem
        self.shade_inside = True # flag to toggle region shading
        self.create_path()  # create the initial QPainterPath for the cropping rectangle

    # create a QPainterPath that represents the cropping rectangle.
    def create_path(self):
        self._path = QPainterPath()  # the path consists of two rectangles: outer and inner
        if self.shade_inside:  # Check the flag here
            # internal shading - Default
            self._path.addRect(self.intern_rect)
        else:
            # external shading - made through QPainterPath's even-odd rule for filling overlapping areas
            self._path.addRect(self.extern_rect)
            self._path.moveTo(self.intern_rect.topLeft())
            self._path.addRect(self.intern_rect)
        self.setPath(self._path)

    # get the size of the cropping rectangle
    def rect(self):
        return self.intern_rect
    
    # get the size of the image or parent/bounding rectangle
    def getExternRect(self):
        return self.extern_rect

    # set the size of the cropping rectangle
    def setRect(self, rect):
        self._intern = rect
        self.create_path() # When the size is set, the QPainterPath is updated to reflect the new size

class CustomGraphicsView(QGraphicsView):
    def __init__(self, scene, main_window):
        super().__init__(scene, main_window)
        self.main_window = main_window
        self.drag = False
        self.selected_handle = None
        
    def updateOtherCropItems(self, newPos, senderHandle):
        # Update all CropItems except the one that contains the handle that emitted the signal
        for cropItem in self.main_window.crop_items:
            if senderHandle not in cropItem.sizeGripItem._handleItems:
                # Find the corresponding handle in the other CropItem and set its position
                for handle in cropItem.sizeGripItem._handleItems:
                    if handle.positionflags() == senderHandle.positionflags():
                        handle.setPos(newPos)
                        # Call the respective function to adjust the size of the CropItem
                        if handle.positionflags() == SizeGripItem.TopLeft:
                            cropItem.sizeGripItem.setTopLeft(newPos)
                        elif handle.positionflags() == SizeGripItem.Top:
                            cropItem.sizeGripItem.setTop(newPos.y())
                        elif handle.positionflags() == SizeGripItem.TopRight:
                            cropItem.sizeGripItem.setTopRight(newPos)
                        elif handle.positionflags() == SizeGripItem.Right:
                            cropItem.sizeGripItem.setRight(newPos.x())
                        elif handle.positionflags() == SizeGripItem.BottomRight:
                            cropItem.sizeGripItem.setBottomRight(newPos)
                        elif handle.positionflags() == SizeGripItem.Bottom:
                            cropItem.sizeGripItem.setBottom(newPos.y())
                        elif handle.positionflags() == SizeGripItem.BottomLeft:
                            cropItem.sizeGripItem.setBottomLeft(newPos)
                        elif handle.positionflags() == SizeGripItem.Left:
                            cropItem.sizeGripItem.setLeft(newPos.x())
                       
            ft_label = self.main_window.FT_cropItems[cropItem]
            combobox, value = self.main_window.get_slider_value(ft_label)
            self.main_window.image_mixer(value, combobox)
                    

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)


