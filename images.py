import numpy as np
import cv2 as cv
from main import MainWindow
import matplotlib.pyplot as plt
import logging


class Image:
    def __init__(self):
        self.imageData = None
        self.dataType = None
        self.imageShape = None
        self.view_images = {}

    def load_image(self, path, view):
        self.imageData = cv.imread(path)
        self.imageData = cv.cvtColor(self.imageData, cv.COLOR_RGB2GRAY)
        self.dataType = self.imageData.dtype
        self.imageShape = self.imageData.shape
        # print("the image loaded shape is ", self.imageShape)
        # save copies of the image data relative to the view it was loaded in
        self.view_images[view] = self.imageData
        # print(self.imageData)
        if self.view_images is not None:
            # (print("sara"))
            min_height, min_width = min(img.shape[0] for img in self.view_images.values()), min(
                img.shape[1] for img in self.view_images.values())
            self.imageData = cv.resize(self.imageData, (min_width, min_height))

    def fourier_transform(self, img):
        img_fourier = np.fft.fft2(img)
        img_fourier_shifted = np.fft.fftshift(img_fourier)
        return img_fourier_shifted

    def inverseFourier(self, weighted_img_ft):
        img_inverse_fourier = np.real(np.fft.ifft2(weighted_img_ft))
        return img_inverse_fourier

    def realComponent(self, img_fourier):
        return np.real(img_fourier)

    def imaginaryComponent(self, img_fourier):
        return np.imag(img_fourier)

    def magnitude(self, img_fourier):
        return np.abs(img_fourier)

    def phase(self, img_fourier):
        return np.angle(img_fourier)

    def adjust_brightness_contrast(self, alpha, beta):
        return cv.convertScaleAbs(self.imageData, alpha=alpha, beta=beta)


class Modes:
    def __init__(self):
        # magnitude_phase = "magnitude_phase mode"
        # real_imaginary = "real_imaginary mode"
        # Define the groups
        self.group1 = ["Magnitude", "Phase"]
        self.group2 = ["Real", "Imaginary"]

    def choose_mode(self, component, combobox, all_comboboxes):
        # Find index of the item
        index = combobox.findText(component)
        # print("index:", index)

        # Determine which group to hide based on the current selection
        if component in self.group1:
            hide_group = self.group2
        elif component == "Select A Component...":
            pass
        else:
            hide_group = self.group1

        for combobox in all_comboboxes:
            # Loop through all items in the combobox
            for i in range(combobox.count()):
                # If the item was found
                if component != "Select A Component...":
                    # If the item is in the hide group, disable it
                    # print("sure")
                    if combobox.itemText(i) in hide_group:
                        combobox.model().item(i).setEnabled(False)
                    else:
                        combobox.model().item(i).setEnabled(True)
                else:
                    # enable all components
                    combobox.model().item(i).setEnabled(True)
                    combobox.setCurrentText("Select A Component...")
        print("yarab")


class Mixer4images:
    def __init__(self):
        # self.main = None
        self.chosen_mode = None
        self.weighted_magnitude = []
        self.weighted_phase = []
        self.weighted_real = []
        self.weighted_imaginary = []
        self.image = Image()
        self.active_region = False
        # self.main_window = main.MainWindow()
        # self.main= main
        self.main_window = MainWindow

    def mix(self, weights_dict, current_component, image_ft, weight_value, combobox, mask=None, flag=None):
        # Apply weight to the chosen component for the selected image
        weighted_component = self.apply_weights(weight_value, current_component, image_ft, mask, flag)
        # Reset all values for the combobox to 0
        weights_dict[combobox] = {'Real': 0, 'Imaginary': 0, 'Magnitude': 0, 'Phase': 0}
        # Update the weight in the dictionary
        weights_dict[combobox][current_component] = weighted_component
        # print("chosen mode1111:", self.chosen_mode)
        if self.chosen_mode == "magnitude_phase mode":
            self.weighted_magnitude = [info['Magnitude'] for info in weights_dict.values()]
            self.weighted_phase = [info['Phase'] for info in weights_dict.values()]
            tot_weighted = self.mix_magnitude_phase(self.weighted_magnitude, self.weighted_phase)
            tot_weighted = np.fft.ifftshift(tot_weighted)  # what we just add to creect what wrong
        elif self.chosen_mode == "real_imaginary mode":
            self.weighted_real = [info['Real'] for info in weights_dict.values()]
            self.weighted_imaginary = [info['Imaginary'] for info in weights_dict.values()]
            tot_weighted = self.mix_real_imaginary(self.weighted_real, self.weighted_imaginary)
            tot_weighted = np.fft.ifftshift(tot_weighted)  # what we just add to creect what wrong
        else:
            return
        image_after_inverse = self.image.inverseFourier(tot_weighted)
        # print("Type of image_after_inverse:", type(image_after_inverse))

        # Check the shape of the NumPy array if it's a 2D array (grayscale image)
        # print("Shape of image_after_inverse:", image_after_inverse.shape)
        cv.imwrite('test2.jpg', np.real(image_after_inverse))
        image = cv.imread('test2.jpg', cv.IMREAD_GRAYSCALE)

        return image

    def apply_weights(self, weight_value, current_component, image_ft, mask=None, flag=None):
        component_methods = {
            'Real': self.image.realComponent,
            'Imaginary': self.image.imaginaryComponent,
            'Magnitude': self.image.magnitude,
            'Phase': self.image.phase
        }
        if current_component in component_methods:
            fourier_component = component_methods[current_component](image_ft)
            if mask is not None:
                if flag:
                    fourier_component *= mask
                else:
                    fourier_component *= ~mask
            weighted_component = (weight_value * fourier_component) / 100
        else:
            weighted_component = None

        return weighted_component

    def mix_magnitude_phase(self, weighted_magnitude, weighted_phase):
        magnitude = sum(weighted_magnitude)
        phase = sum(weighted_phase)
        return magnitude * np.exp(1j * phase)

    def mix_real_imaginary(self, weighted_real, weighted_imaginary):
        real = sum(weighted_real)
        imaginary = sum(weighted_imaginary)
        return real + 1j * imaginary

    def check_region(self, flag):
        self.active_region = flag