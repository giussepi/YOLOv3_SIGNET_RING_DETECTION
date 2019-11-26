# -*- coding: utf-8 -*-
""" utils/classes/cutpatch """

from copy import deepcopy
import json
import os
import shutil

import cv2 as cv
import kfbReader
import xmltodict

import settings


class MiniPatch:
    """
    Reads ROI json files and their respective kfb images and creates
    minipatches using ROI json with their respective xml annotations

    Usage:
        MiniPatch()()
        MiniPatch(cut_size=608)()
    """

    def __init__(self, *args, **kwargs):
        """
        * Initializes the object
        * Clean the content of anno_location folder
        """
        self.path_image = kwargs.get('path_image', settings.INPUT_FOLDER)
        self.path_anno = kwargs.get('path_anno', settings.INPUT_FOLDER)
        self.roi_list = list(filter(lambda x: x.endswith('.json'), os.listdir(self.path_image)))
        self.anno_list = list(filter(lambda x: x.endswith('.xml'), os.listdir(self.path_anno)))
        self.anno_location = self.image_location = settings.OUTPUT_FOLDER
        self.holdback = kwargs.get('holdback', settings.HOLDBACK)
        self.smalllim = kwargs.get('smallim', settings.SMALLLIM)
        self.cut_size = kwargs.get('cut_size', settings.CUT_SIZE)
        self.overlap_coefficient = kwargs.get('overlap_coefficient', settings.OVERLAP_COEFFICIENT)
        self.overlap = int(self.overlap_coefficient * self.cut_size)

        self.__clean_create_folders()

    def __call__(self):
        """ Functor call """
        return self.__process_files()

    def __clean_create_folders(self):
        """ Removes the output folder and recreate it for the new outputs """
        if os.path.isdir(self.anno_location):
            shutil.rmtree(self.anno_location)
        os.mkdir(self.anno_location)

    def __create_roi_json_file(self, filename, source_filename, x, y, xmax, ymax):
        """
        Creates a roi json file at self.image_location using the provided
        arguments
        """
        with open(os.path.join(self.image_location, filename), 'w') as _file:
            data = dict(
                source=source_filename,
                roi={'x': x, 'y': y, 'w': xmax - x, 'h': ymax - y}
            )
            json.dump(data, _file)

    def __cutpatchXML(self, x, y, x2, y2, genfilename, documents):
        """
        Creates the xml file for the current patch (based on the arguments)
        containing the bboxes it has inside
        Args:
            x, y, x2, y2: xmin, ymin, xmax, ymax
            genfilename:  the name of the json annotation file
            documents:    dictionary obtained by xmltodict.parse
        """
        if(documents == 'none'):
            return 0
        else:
            mm = 0
            genfilename = genfilename.replace(" ", "_")

            # Not all the ROIs has bounding boxes #############################
            try:
                if isinstance(documents['annotation']['object'], dict):
                    documents['annotation']['object'] = [documents['annotation']['object']]
            except KeyError:
                return False

            obj = len(documents['annotation']['object'])-1
            doc1 = deepcopy(documents)
            doc1['annotation']['filename'] = genfilename
            doc1['annotation']['size']['width'] = str(self.cut_size)
            doc1['annotation']['size']['height'] = str(self.cut_size)

            while(obj != -1):
                bx1 = int(doc1['annotation']['object'][obj]['bndbox']['xmin'])
                by1 = int(doc1['annotation']['object'][obj]['bndbox']['ymin'])
                bx2 = int(doc1['annotation']['object'][obj]['bndbox']['xmax'])
                by2 = int(doc1['annotation']['object'][obj]['bndbox']['ymax'])

                if(((x <= bx1 <= x2) or (x <= bx2 <= x2))
                   and ((y <= by1 <= y2) or (y <= by2 <= y2))
                   and ((min(x2, bx2) - max(x, bx1))*(min(y2, by2) - max(y, by1))) >= ((bx2 - bx1) * (by2 - by1) * self.smalllim)):
                    doc1['annotation']['object'][obj]['bndbox']['xmin'] = str(int(max(x, bx1)-x))
                    doc1['annotation']['object'][obj]['bndbox']['ymin'] = str(int(max(y, by1)-y))
                    doc1['annotation']['object'][obj]['bndbox']['xmax'] = str(int(min(x2, bx2)-x))
                    doc1['annotation']['object'][obj]['bndbox']['ymax'] = str(int(min(y2, by2)-y))
                    # # NOTE:  using real/original coordinates
                    # doc1['annotation']['object'][obj]['bndbox']['xmin'] = str(int(max(x, bx1)))
                    # doc1['annotation']['object'][obj]['bndbox']['ymin'] = str(int(max(y, by1)))
                    # doc1['annotation']['object'][obj]['bndbox']['xmax'] = str(int(min(x2, bx2)))
                    # doc1['annotation']['object'][obj]['bndbox']['ymax'] = str(int(min(y2, by2)))

                    mm += 1
                else:
                    doc1['annotation']['object'].remove(doc1['annotation']['object'][obj])

                obj -= 1

            print('mm = ' + str(mm))

            if(len(doc1['annotation']['object']) > 0):
                genAnnoname = genfilename.replace(".json", ".xml")
                genAnnoname = genAnnoname.replace(" ", "_")
                out = xmltodict.unparse(doc1)

                with open(os.path.join(self.anno_location, genAnnoname), 'wb+') as _file:
                    _file.write(out.encode('utf8'))
                    _file.close()

                print(genfilename)
                return True
            else:
                # os.remove(self.image_location + fileXml)
                return False

    def __process_files(self):
        """
        Reads the roi files from self.roi_list and creates the
        roi json and roi xml files
        """
        read = kfbReader.reader()
        read.setReadScale(settings.KFBREADER_SCALE)
        # img_pattern = re.compile(r'(?P<filename>[\w]+)-roi\w*.json', re.IGNORECASE)

        for roifile in self.roi_list:
            print(roifile)
            ###################################################################
            #                         using kfbreader                         #
            ###################################################################
            roi_json_file = open(os.path.join(self.path_image, roifile))
            roi_json_obj = json.load(roi_json_file)
            roi_json_file.close()

            read.ReadInfo(
                os.path.join(self.path_image, roi_json_obj['source']),
                settings.KFBREADER_SCALE,
                False
            )

            roi = read.ReadRoi(
                roi_json_obj['roi']['x'],
                roi_json_obj['roi']['y'],
                roi_json_obj['roi']['w'],
                roi_json_obj['roi']['h'],
                scale=settings.KFBREADER_SCALE
            )

            h, w = roi.shape[:2]
            # comment #########################################################

            y = 0
            annofilename = roifile.replace(".json", ".xml")

            try:
                with open(os.path.join(self.path_anno, annofilename)) as fd:
                    doc = xmltodict.parse(fd.read(), dict_constructor=dict)
            except:
                doc = 'none'

            while(y <= (h-self.cut_size)):
                x = 0
                while(x <= (w-self.cut_size)):
                    real_x = roi_json_obj['roi']['x'] + x
                    real_y = roi_json_obj['roi']['y'] + y

                    genfilename = roifile.replace(".json", "_{}_{}.json".format(real_x, real_y))
                    genfilename = genfilename.replace(" ", "_")

                    if (self.__cutpatchXML(real_x,
                                           real_y,
                                           real_x+self.cut_size,
                                           real_y+self.cut_size,
                                           genfilename, doc) is True):
                        # fimg.crop((x, y, x+self.cut_size, y+self.cut_size)).save(self.image_location +
                        #                                                genfilename)  # (left, upper, right, lower)
                        self.__create_roi_json_file(
                            genfilename,
                            roi_json_obj['source'],
                            real_x,
                            real_y,
                            real_x+self.cut_size,
                            real_y+self.cut_size
                        )
                    else:
                        print("none1!")

                    x = x + self.overlap

                if ((x-self.cut_size) <= (self.holdback*self.cut_size)):
                    x = w - self.cut_size
                    real_x = roi_json_obj['roi']['x'] + x
                    real_y = roi_json_obj['roi']['y'] + y
                    genfilename = roifile.replace(".json", "_{}_{}.json".format(real_x, real_y))
                    genfilename = genfilename.replace(" ", "_")

                    if (self.__cutpatchXML(real_x,
                                           real_y,
                                           roi_json_obj['roi']['x']+w,
                                           real_y+self.cut_size,
                                           genfilename, doc) is True):
                        # fimg.crop((x, y, w, y+self.cut_size)).save(self.image_location +
                        #                                            genfilename)  # (left, upper, right, lower)
                        self.__create_roi_json_file(
                            genfilename,
                            roi_json_obj['source'],
                            real_x,
                            real_y,
                            roi_json_obj['roi']['x']+w,
                            real_y+self.cut_size
                        )
                    else:
                        print("none2!")

                y = y + self.overlap

            if(((h/self.cut_size) - (h//self.cut_size)) >= self.holdback):
                x = 0
                y = h - self.cut_size
                while(x <= (w-self.cut_size)):
                    real_x = roi_json_obj['roi']['x'] + x
                    real_y = roi_json_obj['roi']['y'] + y
                    genfilename = roifile.replace(".json", "_{}_{}.json".format(real_x, real_y))
                    genfilename = genfilename.replace(" ", "_")
                    if (self.__cutpatchXML(real_x,
                                           real_y,
                                           real_x+self.cut_size,
                                           real_y+self.cut_size,
                                           genfilename, doc) is True):
                        # fimg.crop((x, y, x+self.cut_size, y+self.cut_size)).save(self.image_location + genfilename)
                        self.__create_roi_json_file(
                            genfilename,
                            roi_json_obj['source'],
                            real_x,
                            real_y,
                            real_x+self.cut_size,
                            real_y+self.cut_size
                        )
                    else:
                        print("none3!")

                    x = x + self.overlap

                genfilename = roifile.replace(".json", "_{}_{}.json".format(
                    roi_json_obj['roi']['x']+w-self.cut_size,
                    roi_json_obj['roi']['y']+h-self.cut_size
                ))
                genfilename = genfilename.replace(" ", "_")

                if (self.__cutpatchXML(roi_json_obj['roi']['x']+w-self.cut_size,
                                       roi_json_obj['roi']['y']+h-self.cut_size,
                                       roi_json_obj['roi']['x']+w,
                                       roi_json_obj['roi']['y']+h,
                                       genfilename, doc) is True):
                    # fimg.crop((w-self.cut_size, h-self.cut_size, w, h)).save(self.image_location +
                    #                                                          genfilename)  # (left, upper, right, lower)
                    self.__create_roi_json_file(
                        genfilename, roi_json_obj['source'],
                        roi_json_obj['roi']['x']+w-self.cut_size,
                        roi_json_obj['roi']['y']+h-self.cut_size,
                        roi_json_obj['roi']['x']+w,
                        roi_json_obj['roi']['y']+h
                    )
                else:
                    print("none4!")


class TestMiniPatch:
    """ Reads testing kfb files and create their jpeg minipatches """

    def __init__(self, *args, **kwargs):
        """
        * Initializes the object
        """
        self.path_images = kwargs.get('path_images', settings.TEST_INPUT_FOLDER)
        self.kfb_list = os.listdir(self.path_images)
        self.holdback = kwargs.get('holdback', settings.HOLDBACK)
        self.smalllim = kwargs.get('smallim', settings.SMALLLIM)
        self.cut_size = kwargs.get('cut_size', settings.CUT_SIZE)
        self.overlap_coefficient = kwargs.get('overlap_coefficient', settings.OVERLAP_COEFFICIENT)
        self.overlap = int(self.overlap_coefficient * self.cut_size)

        self.__clean_create_folders()

    def __call__(self):
        """ Functor call """
        return self.__process_files()

    def __clean_create_folders(self):
        """ Removes the output and tmp folders and recreate them for the new outputs """
        assert os.path.isdir(self.path_images)

        if os.path.isdir(settings.TEST_OUPUT_FOLDER):
            shutil.rmtree(settings.TEST_OUPUT_FOLDER)
        os.makedirs(settings.TEST_OUPUT_FOLDER)

        if os.path.isdir(settings.TEST_TMP_DATA):
            shutil.rmtree(settings.TEST_TMP_DATA)
        os.makedirs(settings.TEST_TMP_DATA)

    def __create_jpeg_image(self, filename, xmin, ymin, xmax, ymax):
        """
        Creates a jpeg from the roi specified by the arguments and saves it at
        settings.TEST_TMP_DATA
        """
        roi = self.read.ReadRoi(xmin, ymin, xmax-xmin, ymax-ymin, scale=settings.KFBREADER_SCALE)
        cv.imwrite(
            os.path.join(settings.TEST_TMP_DATA, filename),
            roi
        )

    def __process_files(self):
        """
        Reads the kfb files from self.kfb_list and creates the
        jpeg minipatches
        """
        self.read = kfbReader.reader()
        self.read.setReadScale(settings.KFBREADER_SCALE)

        for kfbfile in self.kfb_list:
            print(kfbfile)
            self.read.ReadInfo(
                os.path.join(self.path_images, kfbfile),
                settings.KFBREADER_SCALE,
                False
            )

            h, w = self.read.getHeight(), self.read.getWidth()
            y = 0

            while(y <= (h-self.cut_size)):
                x = 0
                while(x <= (w-self.cut_size)):
                    genfilename = kfbfile.replace(".kfb", "_{}_{}.jpeg".format(x, y))
                    genfilename = genfilename.replace(" ", "_")
                    self.__create_jpeg_image(genfilename, x, y, x+self.cut_size, y+self.cut_size)
                    x = x + self.overlap

                if ((x-self.cut_size) <= (self.holdback*self.cut_size)):
                    x = w - self.cut_size
                    genfilename = kfbfile.replace(".kfb", "_{}_{}.jpeg".format(x, y))
                    genfilename = genfilename.replace(" ", "_")
                    self.__create_jpeg_image(genfilename, x, y, w, y+self.cut_size)

                y = y + self.overlap

            if(((h/self.cut_size) - (h//self.cut_size)) >= self.holdback):
                x = 0
                y = h - self.cut_size
                while(x <= (w-self.cut_size)):
                    genfilename = kfbfile.replace(".kfb", "_{}_{}.jpeg".format(x, y))
                    genfilename = genfilename.replace(" ", "_")
                    self.__create_jpeg_image(genfilename, x, y, x+self.cut_size, y+self.cut_size)
                    x = x + self.overlap

                genfilename = kfbfile.replace(".kfb", "_{}_{}.jpeg".format(
                    w-self.cut_size, h-self.cut_size))
                genfilename = genfilename.replace(" ", "_")
                self.__create_jpeg_image(genfilename, w-self.cut_size, h-self.cut_size, w, h)
