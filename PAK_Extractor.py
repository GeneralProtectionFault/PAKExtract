import PyQt6
from PyQt6.QtWidgets import QApplication, QWidget, QMessageBox, QTextEdit, QComboBox, QLineEdit, QScrollBar, QFileDialog, QListWidget, QStyleFactory
from PyQt6 import uic

import qdarktheme

import sys
import os
from pathlib import Path
import io
import shutil
from glob import glob
import json
import struct
from dataclasses import dataclass, fields


# pak_file_name = ""
pak_file_dictionary = dict()


@dataclass
class quake2_pak_file_header:
    id: str                     # First 4 characters should be "PACK"
    file_table_offset: int
    file_table_size: int


def load_file_bytes(file_path):
    with open(file_path, "rb") as file:
        bytes = file.read()
    
    return bytes


def load_pak_header(self, file_bytes):
    header_bytes = struct.unpack("<ccccii", file_bytes[:12])
    # print(header_bytes[0].decode())

    # Separate the first 4 characters as 1 value (the "PACK" string found in the header)
    header_id = ''.join(header_bytes[i].decode() for i in range(4))
    

    if header_id != "PACK":
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Not idTech 2 PAK")
        msg_box.setText("ERROR: File is not an idTech 2 PAK file")
        msg_box.show()
        return -1

    header_values_parsed = (header_id,) + header_bytes[4:12]
    header = quake2_pak_file_header(*header_values_parsed)

    header.num_files = header.file_table_size / 64

    return header


def populate_file_list(ui_object, pak_file_bytes, pak_file_header, number_of_files):
    global pak_file_dictionary
    pak_file_dictionary.clear()
    ui_object.ui.lst_files.clear()

    for i in range(number_of_files):
        start_pos = pak_file_header.file_table_offset + (i*64)
        # For whatever reason, there's trash in with the 56 bytes for the filename, so we need to stop at the first null byte
        end_pos = pak_file_bytes.find(b'\x00', start_pos)

        file_name = pak_file_bytes[start_pos : end_pos].decode("ascii","ignore").rstrip('\x00')
        file_contents_offset = struct.unpack("<i", pak_file_bytes[start_pos+56:start_pos+60])[0]
        file_contents_size = struct.unpack("<i", pak_file_bytes[start_pos+60:start_pos+64])[0]

        print(file_name)
        print(file_contents_offset)
        print(file_contents_size)
        
        file_data = pak_file_bytes[file_contents_offset : file_contents_offset + file_contents_size]        

        # Add to dictionary
        pak_file_dictionary[file_name] = file_data

        # Add to UI list
        ui_object.ui.lst_files.addItem(file_name)


def write_file(pak_file_bytes, output_folder, file_name):
    # print(f"Writing (Uncompressed): {file_name}, start position: {getattr(pak_file, 'start_position')}, length: {getattr(pak_file, 'length')}, compressed size: {getattr(pak_file, 'compressed_length')}, checksum: {getattr(pak_file, 'checksum')}")
                
    global pak_file_dictionary
    this_file_bytes = pak_file_dictionary[file_name]

    # global pak_file_name
    # This will add the name of the dat file itself as a subdirectory.
    # Judging from the models w/ a .atd file, and the paths they point to, I'm guessing this is convention, and it will allow parsing the .atd w/o extra work
    print(f"output folder: {output_folder}")
    output_path = os.path.join(output_folder, file_name)
    output_path = ''.join(x for x in output_path if x.isprintable())
    
    output_directory = os.path.dirname(output_path)
    
    if not os.path.exists(output_directory):
        print(f"Making directory: {output_directory}")
        print(output_directory)
        os.makedirs(output_directory)

    output_file = open(output_path, 'wb')
    output_file.write(this_file_bytes)
    output_file.close()


def extract_all_files(output_folder, ui_object):
    try:
        # Get the actual files
        global pak_file_dictionary
        for file in pak_file_dictionary.keys():
            write_file(pak_file_dictionary[file], output_folder, file)


        msg_box = QMessageBox(ui_object)
        msg_box.setWindowTitle("Complete")
        msg_box.setText("Extraction Complete!")
        msg_box.show()


    except Exception as argument:
        msg_box = QMessageBox(ui_object)
        msg_box.setWindowTitle("ERROR")
        msg_box.setText(f"Error extracting .DAT file:\n{argument}")
        msg_box.show()
        return




class QuakeIIPAKApp(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi(os.path.join(os.getcwd(), 'PAK_Extractor.ui'), self)
        self.show()

        ### BUTTON EVENTS ###
        self.ui.btn_select_pak_file.clicked.connect(self.select_file)
        self.ui.btn_select_output_folder.clicked.connect(self.select_output_folder)
        self.ui.btn_extract_all.clicked.connect(self.extract_all)
        self.ui.btn_extract_selected.clicked.connect(self.extract_selected)


    def select_file(self):
        output_folder = self.ui.txt_output_folder.text()

        if not os.path.exists(output_folder):
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Output Folder Error")
            msg_box.setText("ERROR: Selected Output folder does not exist")
            msg_box.show()
            return

        file_name = QFileDialog.getOpenFileName(caption = "Select .pak file", filter = "*.pak")[0]
        print(f"File Name: {file_name}")
        
        if file_name != '' and file_name is not None:
            pak_file_bytes = load_file_bytes(file_name)
            pak_file_header = load_pak_header(self, pak_file_bytes)
            
            if pak_file_header == -1:
                print("Invalid PAK, aborting...")
                return

            global pak_file_name
            pak_file_name = Path(file_name).stem.lower()
            print(f"PAK FILENAME: {pak_file_name}")

            # Populate UI w/ file name
            self.ui.txt_pak_file.setText(file_name)

            number_of_files = int(pak_file_header.num_files)
            print (f"{number_of_files} files in PAK")

            populate_file_list(self, pak_file_bytes, pak_file_header, number_of_files)

            print("--------------- HEADER VALUES -------------------")
            for field in fields(pak_file_header):
                print(f"{field.name} - ", getattr(pak_file_header, field.name))

            print("--------------------------------------------------")


    def select_output_folder(self):
        try:
            # folder_name = QFileDialog.getOpenFileName(caption = "Select .dat file", filter = "*.dat")[0]
            folder = QFileDialog.getExistingDirectory(self, "Select Folder")
            self.ui.txt_output_folder.setText(folder)
        except Exception as argument:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Output Folder Error")
            msg_box.setText("Error selecting output folder:\n{argument}")
            msg_box.show()
            return


    def extract_all(self):
        output_folder = self.ui.txt_output_folder.text()
        if not os.path.exists(output_folder) or not os.path.isfile(self.ui.txt_pak_file.text()):
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Extract Error")
            msg_box.setText("ERROR: Output folder does not exist.")
            msg_box.show()
            return
        
        file = load_file_bytes(self.ui.txt_pak_file.text())
        header = load_pak_header(self, file)

        extract_all_files(output_folder, self)



    def extract_selected(self):
        if self.ui.lst_files.currentItem() is None:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText("Please select a file first.")
            msg_box.show()
            return
        

        selected_file = self.ui.lst_files.currentItem().text()

        global pak_file_dictionary
        pak_file_bytes = pak_file_dictionary[selected_file]
        # if getattr(dat_file, "compressed_length") > 0:
        #     write_compressed_file(pak_file_bytes, dat_file, self.ui.txt_output_folder.text(), getattr(dat_file, "file_name"))
        # else:
        write_file(pak_file_bytes, self.ui.txt_output_folder.text(), selected_file)

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Complete")
        msg_box.setText("File Extracted!")
        msg_box.show()




if __name__ == '__main__':
    # Prints out the themes available
    # print(QStyleFactory.keys())

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(qdarktheme.load_stylesheet())

    print(app.style().objectName())
    QuakeIIPAKUI = QuakeIIPAKApp()
    
    sys.exit(app.exec())
    