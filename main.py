import cv2
import numpy as np
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QFileDialog, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
import sys
import matplotlib.pyplot as plt
import logging
import images
from crop import CropItem, CustomGraphicsView

logging.basicConfig(filename="logging_file.log",
                    filemode="w",
                    format="(%(asctime)s) | %(name)s | %(levelname)s => '%(message)s'",
                    datefmt="%d - %B - %Y, %H:%M:%S")

my_logger = logging.getLogger("name")    #i can change the name as i want

my_logger.warning("This Is Warning Message") #this line i will write each time i want to make logging


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.combobox_mapping = {}
        self.img = images.Image()
        self.mode = images.Modes()
        self.mixer = images.Mixer4images()

        # Load the UI Page
        self.original_signal_output = None
        uic.loadUi(r'Mixer.ui', self)
        self.setWindowTitle('Mixer')

        # Create QGraphicsScene for each graphics view
        self.scenes = [QGraphicsScene() for _ in range(4)]

        # Create QGraphicsScene for Fourier labels
        self.ft_scenes = [QGraphicsScene() for _ in range(4)]

        # Set image and fourier label scenes & handle mouse clicks via graphics view
        self.views = []
        self.ft_labels = []
        self.views = self.setup_views(self.views, self.scenes, 'label_img')
        self.ft_labels = self.setup_views(self.ft_labels, self.ft_scenes, 'FT_label')

        # draw rectangle regions button
        self.rectangle_region_button.clicked.connect(self.on_button_click)
         
        # reset rectangle regions button
        self.reset_region_button.clicked.connect(self.reset_regions)

        # toggle rectangle regions' shading button
        self.toggle_shading_button.clicked.connect(self.toggleShading)
        
        self.crop_items = []
        self.FT_components = {}
        self.FT_regions = {}
        self.FT_cropItems = {}
        self.active_region = False
         
        self.comboboxes = [getattr(self, f'FT_img{i + 1}') for i in range(4)]
        # the above line is equal to: comboboxes = [self.FT_img1, self.FT_img2, self.FT_img3, self.FT_img4]
        
        # Create sliders for each image
        self.sliders = {combobox: getattr(self, f'ft_img_slider{i + 1}') for i, combobox in enumerate(self.comboboxes)}

        # Create line edits for each image
        self.line_edits = {combobox: getattr(self, f'Image_weight{i + 1}') for i, combobox in enumerate(self.comboboxes)}

        # Dictionary to store weights for each image based on its view's combobox
        self.weights_dict = {combobox: {'Real': 0, 'Imaginary': 0, 'Magnitude': 0, 'Phase': 0} for combobox in self.sliders}

        # Initialize a dictionary to store the selected modes for each image
        self.selected_modes_dict = {}

        # Connect comboboxes to update function
        for i in range(4):
            self.comboboxes[i].currentIndexChanged.connect(self.updateFourierComponent)

        # Connect sliders to update function
        for combobox, slider in self.sliders.items():
            slider.valueChanged.connect(lambda value, cmb=combobox: self.image_mixer(value, cmb))
            combobox.currentTextChanged.connect(lambda text, cmb=combobox: self.select_mode(text, cmb))

        # Set the scene for self.graphicsView_10 and self.graphicsView_9
        self.scenes = [QGraphicsScene() for _ in range(2)]
        # self.scene_graphicsView_10 = QGraphicsScene()
        # self.scene_graphicsView_9 = QGraphicsScene()
        for i in range(2):
            view_name = f'graphicsView_{i + 9}'
            view = getattr(self, view_name)
            scene = self.scenes[i]
            view.setScene(scene)

    def setup_views(self, labels, scenes, attr_name):
        if attr_name == 'FT_label':
            for i in range(4):
                label = getattr(self, f'{attr_name}_{i + 1}')
                graphics_view = self.findChild(QGraphicsView, label.objectName())
                custom_graphics_view = CustomGraphicsView(scenes[i], self)
                custom_graphics_view.setGeometry(graphics_view.geometry())
                layout = graphics_view.parent().layout()
                layout.replaceWidget(graphics_view, custom_graphics_view)
                graphics_view.deleteLater()

                labels.append(custom_graphics_view)
                
        elif attr_name == 'label_img':
            for i in range(4):
                label = getattr(self, f'{attr_name}_{i + 1}')
                labels.append(label)
                label.setScene(scenes[i])
                # mouse slide to change brightness/contrast
                label.mouseMoveEvent = lambda event, v=label: self.handleMouseMoveEvent(event, v)
                # double click to: import images (left) or reset image (right)
                label.mouseDoubleClickEvent = lambda event, v=label: self.handleViewDoubleClick(event, v)
        return labels

    # Selection region rectangle
    def on_button_click(self):
        self.active_region = True
        self.mixer.active_region = self.active_region
        # Loop over all FT views
        for ft_label in self.ft_labels:
            # Get the image item from the scene
            image_item = next((item for item in ft_label.scene().items() if isinstance(item, QGraphicsPixmapItem)), None)
            
            # If there's no image item in the scene, skip this iteration
            if image_item is None:
                # print(f"No image item found in {ft_label.objectName()}'s scene.")
                continue

            combobox, value = self.get_slider_value(ft_label)
            # Check if a CropItem already exists on the scene
            if any(isinstance(item, CropItem) for item in ft_label.scene().items()):
                # print(f"A CropItem already exists in {ft_label.objectName()}'s scene.")
                self.image_mixer(value, combobox)
                continue

            # Create a CropItem and add it to the scene of the current view
            crop_item = CropItem(image_item)
            self.crop_items.append(crop_item)
            # print(f"ft_label: {isinstance(ft_label, CustomGraphicsView)}")

            # Connect the signal from each handle to the slot
            for handle in crop_item.sizeGripItem._handleItems:
                handle.emitter.positionChanged.connect(lambda newPos, handle: ft_label.updateOtherCropItems(newPos, handle))
            
            ft_label.fitInView(ft_label.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)  # Fit the image within the view
            ft_label.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            ft_label.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            ft_label.setFixedSize(ft_label.size())
            
            self.FT_regions[ft_label] = crop_item # save the CropItem instance relative to its FT view
            self.FT_cropItems = {crop_Items: label for label, crop_Items in self.FT_regions.items()}     

            self.image_mixer(value, combobox)

    def reset_regions(self):
        self.active_region = False
        for ft_label in list(self.FT_regions.keys()): # Create a copy of the keys
            # Get the first element of the tuple
            crop_item = self.FT_regions[ft_label]
            ft_label.scene().removeItem(crop_item)
            self.FT_regions.pop(ft_label)
            combobox, value = self.get_slider_value(ft_label)
            self.image_mixer(value, combobox)
        
    def toggleShading(self):
        # Loop over all FT views
        for ft_label in self.ft_labels:
            if any(isinstance(item, CropItem) for item in ft_label.scene().items()):
                crop_item = self.FT_regions[ft_label]  # Get the CropItem for the given ft_label
                combobox, value = self.get_slider_value(ft_label)
                # Toggle the shade_inside attribute
                crop_item.shade_inside = not crop_item.shade_inside
                crop_item.create_path()  # Update the path
                self.image_mixer(value, combobox)

    def handleViewDoubleClick(self, event, view):
        try:
            if event.button() == Qt.LeftButton:
                file_dialog = QFileDialog()
                file_dialog.setFileMode(QFileDialog.ExistingFile)
                file_path, _ = file_dialog.getOpenFileName(self, "Open Image File", "", "Images (*.png *.jpg *.bmp *.jpeg)")
                if file_path:
                    self.img.load_image(file_path, view)
                    self.displayImage(view, self.img.imageData)

                    view_name = view.objectName()
                    # view_name = view
                    for i in range(4):
                        if str(i+1) in view_name:
                            self.combobox_mapping[self.comboboxes[i]] = {'image': self.img.view_images[view], 
                                                                         'view': view,
                                                                         'ft_label': self.ft_labels[i]}
                    # print(f"combobox_mapping: {self.combobox_mapping}")
            
            # reset image with right double-click
            elif event.button() == Qt.RightButton:
                # print("detected double right-click")
                # Get the corresponding original image
                original_image = self.img.view_images.get(view)
                if original_image is not None:
                    # Reset the image to its original state
                    self.img.imageData = original_image
                    # update image data relative to view in self.combobox_mapping
                    self.update_image_data(view, self.img.imageData)
                    # Display the original image
                    self.displayImage(view,self.img.imageData)
        
        except Exception as e:
            print("Exception:", e)

    def handleMouseMoveEvent(self, event, view):
        # Get the size of the scene
        scene_rect = view.sceneRect()
        scene_width = scene_rect.width()
        scene_height = scene_rect.height()

        # Calculate the mouse position relative to the scene
        mouse_x = event.x()
        mouse_y = event.y()

        # Calculate the midpoints
        midpoint_x = scene_width / 2
        midpoint_y = scene_height / 2

        # Check if the mouse is within the scene
        if 0 <= mouse_x <= scene_width and 0 <= mouse_y <= scene_height:
            if event.buttons() & Qt.LeftButton:
                # print("detected slide")
                # Calculate contrast and brightness factors based on mouse position relative to midpoints
                contrast_factor = 1 + 2 * ((mouse_x - midpoint_x) / midpoint_x)  # range -1.0 - 3.0
                brightness_factor = 100 * (1 - (mouse_y - midpoint_y) / midpoint_y)  # range -100 - 100
                # Get the corresponding image
                img_info = self.img.view_images.get(view)
                if img_info is not None:
                    self.img.imageData = img_info
                    # Adjust brightness/contrast
                    self.img.imageData = self.img.adjust_brightness_contrast(contrast_factor, brightness_factor)
                    # print(f"image info: {self.img.imageData}")
                    # update image data relative to view in self.combobox_mapping
                    self.update_image_data(view, self.img.imageData)
                    
                    # Display the updated image
                    self.displayImage(view, self.img.imageData)
        
    def update_image_data(self, view, new_image_data):
        # Iterate over the dictionary
        for combobox, info in self.combobox_mapping.items():
            # Check if the view matches
            if info['view'] == view:
                # Update the image data
                info['image'] = new_image_data
                break
            
    def get_slider_value(self, ft_label):
        # Iterate over the dictionary
        for combobox, info in self.combobox_mapping.items():
            # Check if the view matches
            if info['ft_label'] == ft_label:
                combobox = combobox
                slider = self.sliders[combobox]
                value = slider.value()
                return combobox, value
    
    def displayImage(self, view, image):
        if len(image.shape) == 2:
            # Grayscale image
            height, width = image.shape
            bytes_per_line = width
            q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(q_image)
            view.scene().clear()
            view.scene().addPixmap(pixmap)
            # print(f"check scene: {view.scene().items()}")
            view.fitInView(view.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
    
    def updateFourierComponent(self):
        self.sender_combobox = self.sender()
        selected_component = self.sender_combobox.currentText()
        # print("selected_component:", selected_component)

        if selected_component == "Select A Component...":
            return

        if self.img.view_images is None:
            print("No images loaded yet.")
            return

        corresponding_info = self.combobox_mapping.get(self.sender_combobox)
        # print("corresponding_info_:",corresponding_info)

        if corresponding_info:
            corresponding_image = corresponding_info['image']
            corresponding_ft_label = corresponding_info['ft_label']

            x = self.img.fourier_transform(corresponding_image)

            # map methods in the image class without calling them
            method_mapping = {
                r'Real': self.img.realComponent,
                r'Imaginary': self.img.imaginaryComponent,
                r'Magnitude': self.img.magnitude,
                r'Phase': self.img.phase,
            }

            if selected_component in method_mapping:
                # function object selected based on selected component
                component_method = method_mapping[selected_component]
                # call the method represented by component_method with tge fourier transform of the image as input (x)
                component_data = component_method(x)  # function call

                if corresponding_ft_label:
                    self.FT_components[corresponding_ft_label] = component_data
                    self.displayFourierComponent(corresponding_ft_label, component_data, selected_component)
                else:
                    print("Error: Corresponding Fourier label not found for the current combobox.")
        else:
            print("Error: Corresponding info not found for the current combobox.")

    def displayFourierComponent(self, view, component, title):
        if title == 'Magnitude':
            my_logger.info(
                "Applying log normalization to the magnitude component to reduce the dynamic range and improve visibility.")
            plt.imshow(np.log(component), cmap='gray')
        elif title == 'Real' or title == 'Imaginary':
            my_logger.info("Before transformation:")
            my_logger.info("Min: {}".format(np.min(component)))
            my_logger.info("Max: {}".format(np.max(component)))
            my_logger.info("Average: {}".format(np.mean(component)))

            my_logger.info(
                "Applying histogram equalization to the real/imaginary component to enhance contrast and improve visibility.")
            equalized_component = cv2.equalizeHist(component.astype(np.uint8))

            my_logger.info("After transformation:")
            my_logger.info("Min: {}".format(np.min(equalized_component)))
            my_logger.info("Max: {}".format(np.max(equalized_component)))
            my_logger.info("Average: {}".format(np.mean(equalized_component)))

            plt.imshow(equalized_component, cmap='gray')
        else:
            plt.imshow(component, cmap='gray')

        # view_name = view.objectName()

        plt.gcf().set_size_inches(component.shape[1] / 79, component.shape[0] / 79)  # resize image
        plt.axis('off')  # Turn off axis labels
        # plt.savefig(f'temp_{view_name}.png', bbox_inches='tight', pad_inches=0)  # Save with tight bounding box
        plt.savefig('temp.png', bbox_inches='tight', pad_inches=0)  # Save with tight bounding box
        plt.close()

        # q_image = QImage(f'temp_{view_name}.png')
        q_image = QImage('temp.png')
        pixmap = QPixmap.fromImage(q_image)
        view.scene().clear()
        view.scene().addPixmap(pixmap)
        view.fitInView(view.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)  # Fit the image within the view
        
    def select_mode(self, component, combobox):
        if component == "Magnitude" or component == "Phase":
            self.mixer.chosen_mode = "magnitude_phase mode"
        elif component == "Real" or component == "Imaginary":
            self.mixer.chosen_mode = "real_imaginary mode"
        # print("chosen_mode:", self.mixer.chosen_mode)
        # print("enough")
        self.mode.choose_mode(component, combobox, self.comboboxes)

    def save_cropped_region(self, ft_label):
        # Get the coordinates of the cropping rectangle
        crop_item = self.FT_regions[ft_label]
        extern_rect = crop_item.getExternRect()
        rect = crop_item.rect()
        x = int(rect.x())
        y = int(rect.y())
        width = int(rect.width())
        height = int(rect.height())

        # Get the Fourier component corresponding to the ft_label
        fourier_component = self.FT_components[ft_label]
        if fourier_component is not None:
            # Calculate the scaling factor
            scale_x = fourier_component.shape[1] / extern_rect.width()
            scale_y = fourier_component.shape[0] / extern_rect.height()
            
            # Map the coordinates of the cropping rectangle on the view back to the indices of the Fourier component data array
            x = int(x * scale_x)
            y = int(y * scale_y)
            width = int(width * scale_x)
            height = int(height * scale_y)
            
            # Create a mask of zeros with the same shape as the Fourier component
            mask = np.zeros(fourier_component.shape).astype(bool)
            # Set the values in the mask to True for the pixels inside the rectangle
            mask[y:y+height, x:x+width] = 1

            return mask, crop_item.shade_inside
        
        else: return None

    def image_mixer(self, weight_value, combobox):
        # Get the corresponding image for the current combobox
        corresponding_info = self.combobox_mapping.get(combobox)
        if corresponding_info:
            corresponding_image = corresponding_info['image']

            corresponding_label = corresponding_info['ft_label']
            
            # Update the line edit with the current weight
            line_edit = self.line_edits.get(combobox)
            # print('line_edit.text()',line_edit.text())
            if line_edit:
                line_edit.setText(f"{weight_value}%")

            # get current mode
            current_component = combobox.currentText()
            # print("current_component:", current_component)

            # calculate fourier transform for the image
            image_ft = self.img.fourier_transform(corresponding_image)
            
            if self.active_region and any(isinstance(item, CropItem) for item in corresponding_label.scene().items()):
                # Get the cropped region of the Fourier component
                mask, flag = self.save_cropped_region(corresponding_label)
            else:
                mask = None  # a default value
                flag = None

            image = self.mixer.mix(self.weights_dict, current_component, image_ft, weight_value, combobox, mask, flag)

            selected_output = self.choose_output.currentText()

            if selected_output == "Output 2":
                selected_graphics_view = self.graphicsView_9
            else:
                # Handle other cases or provide a default view
                selected_graphics_view = self.graphicsView_10

            # Call the display function with the selected graphics view
            self.displayImage(selected_graphics_view, image)


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()