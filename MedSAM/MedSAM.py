# -*- coding: utf-8 -*-
import logging
import os
import requests
import json

import vtk

import ctk
import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import SimpleITK as sitk
import numpy as np


try:
    from numpysocket import NumpySocket
except ModuleNotFoundError as e:
    slicer.util.pip_install("numpysocket")
    from numpysocket import NumpySocket

#
# MedSAM
#


class MedSAM(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "MedSAM"
        self.parent.categories = [
            "Examples"
        ]  # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.dependencies = (
            []
        )  # TODO: add here list of module names that this module requires
        self.parent.contributors = [
            "Jun Ma (UoT), Lin Han (NYU Tandon School of Engineering)"
        ]
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#MedSAM">module documentation</a>.
"""
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""

        # Additional initialization step after application startup is complete

    #     slicer.app.connect("startupCompleted()", self.initializeAfterStartup)

    # def initializeAfterStartup(self):
    #     print("initializeAfterStartup", slicer.app.commandOptions().noMainWindow)
    #     if not slicer.app.commandOptions().noMainWindow:
    #         print("in")
    #         # print("here")
    #         # self.settingsPanel = MONAILabelSettingsPanel()
    #         # slicer.app.settingsDialog().addPanel("MONAI Label", self.settingsPanel)


#
# Register sample data sets in Sample Data module
#


# def registerSampleData():
#     """
#     Add data sets to Sample Data module.
#     """
#     # It is always recommended to provide sample data for users to make it easy to try the module,
#     # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

#     import SampleData

#     iconsPath = os.path.join(os.path.dirname(__file__), "Resources/Icons")

#     # To ensure that the source code repository remains small (can be downloaded and installed quickly)
#     # it is recommended to store data sets that are larger than a few MB in a Github release.

#     # MedSAM1
#     SampleData.SampleDataLogic.registerCustomSampleDataSource(
#         # Category and sample name displayed in Sample Data module
#         category="MedSAM",
#         sampleName="MedSAM1",
#         # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
#         # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
#         thumbnailFileName=os.path.join(iconsPath, "MedSAM1.png"),
#         # Download URL and target file name
#         uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
#         fileNames="MedSAM1.nrrd",
#         # Checksum to ensure file integrity. Can be computed by this command:
#         #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
#         checksums="SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
#         # This node name will be used when the data set is loaded
#         nodeNames="MedSAM1",
#     )

#     # MedSAM2
#     SampleData.SampleDataLogic.registerCustomSampleDataSource(
#         # Category and sample name displayed in Sample Data module
#         category="MedSAM",
#         sampleName="MedSAM2",
#         thumbnailFileName=os.path.join(iconsPath, "MedSAM2.png"),
#         # Download URL and target file name
#         uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
#         fileNames="MedSAM2.nrrd",
#         checksums="SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
#         # This node name will be used when the data set is loaded
#         nodeNames="MedSAM2",
#     )


#
# MedSAMWidget
#


class MedSAMWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation

        self.logic = None
        self._parameterNode = None
        self._volumeNode = None
        self._segmentNode = None

        self._updatingGUIFromParameterNode = False

        self.dgPositivePointListNode = None
        self.dgPositivePointListNodeObservers = []
        self.ignorePointListNodeAddEvent = False

    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/MedSAM.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = MedSAMLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose
        )
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose
        )
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.NodeAddedEvent, self.onSceneEndImport
        )

        # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
        # (in the selected parameter node).
        # self.ui.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
        # self.ui.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
        # self.ui.imageThresholdSliderWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
        # self.ui.invertOutputCheckBox.connect("toggled(bool)", self.updateParameterNodeFromGUI)
        # self.ui.invertedOutputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)

        # Buttons
        # self.ui.applyButton.connect("clicked(bool)", self.onApplyButton)
        self.ui.calculateEmbeddingButton.connect(
            "clicked(bool)", self.calculateEmbeddingClicked
        )

        # Points
        self.ui.dgPositiveControlPointPlacementWidget.setMRMLScene(slicer.mrmlScene)
        self.ui.dgPositiveControlPointPlacementWidget.placeButton().toolTip = (
            "Select +ve points"
        )
        self.ui.dgPositiveControlPointPlacementWidget.buttonsVisible = False
        self.ui.dgPositiveControlPointPlacementWidget.placeButton().show()
        self.ui.dgPositiveControlPointPlacementWidget.deleteButton().show()
        self.ui.dgPositiveControlPointPlacementWidget.setPlaceModeEnabled(False)
        self.ui.dgPositiveControlPointPlacementWidget.setPlaceMultipleMarkups(
            self.ui.dgPositiveControlPointPlacementWidget.ForcePlaceMultipleMarkups
        )
        # print(type(self.ui.dgPositiveControlPointPlacementWidget))

        self.ui.embeddedSegmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        self.ui.embeddedSegmentEditorWidget.setMRMLSegmentEditorNode(
            self.logic.get_segment_editor_node()
        )

        # fall back segmentation node
        segmentationNode = slicer.mrmlScene.GetNodeByID("MedSAMSegmentation")
        if segmentationNode is None:
            self.segmentationNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLSegmentationNode"
            )
        else:
            self.segmentationNode = segmentationNode
            self.segmentationNode.SetName("MedSAMSegmentation")

        self.initializeParameterNode()

    def calculateEmbeddingClicked(self):
        self.volumeNode = slicer.mrmlScene.GetFirstNodeByClass(
            "vtkMRMLScalarVolumeNode"
        )

        self.segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(
            self.volumeNode
        )
        self.ui.embeddedSegmentEditorWidget.setSegmentationNode(self.segmentationNode)
        self.ui.embeddedSegmentEditorWidget.setSourceVolumeNode(self.volumeNode)

        scan = slicer.util.arrayFromVolume(self.volumeNode).astype("float32")
        # print(type(self.volumeNode.GetDisplayNode()))
        dn = self.volumeNode.GetDisplayNode()
        # print(dn.GetWindow(), dn.GetWindowLevelMax(), dn.GetWindowLevelMin())
        # print(dir(dn))

        requests.post(
            "http://localhost:5555/setImage",
            json={
                "wmin": str(dn.GetWindowLevelMin()),
                "wmax": str(dn.GetWindowLevelMax()),
            },
        )
        # TODO: support rgb image here
        self.H, self.W = scan.shape[1:]  # [n slice / None, H, W, C]

        with NumpySocket() as s:
            s.connect(("localhost", 5556))
            s.sendall(scan)

        # self.ui.dgPositiveControlPointPlacementWidget.setPlaceModeEnabled(True)

    def onDeepGrowPointListNodeModified(self, observer, eventid):
        # TODO: prompt error when embedding calc isnt finished
        # logging.debug("Deepgrow Point Event!!")
        points = self.getControlPointsXYZ(self.dgPositivePointListNode, "foreground")
        # print(points)
        if len(points) == 4:
            for idx in range(1, 4):
                if points[idx][2] != points[0][2]:
                    slicer.util.errorDisplay(
                        "The four extreme points need to be in the same slice"
                    )
                    self.dgPositivePointListNode.RemoveAllControlPoints()
                    return

            points = np.array(points)
            slice_idx = points[0][2]
            xmin = max(min(points[:, 1]) - 3, 0)
            xmax = min(max(points[:, 1]) + 3, self.W)
            ymin = max(min(points[:, 0]) - 3, 0)
            ymax = min(max(points[:, 0]) + 3, self.H)
            # print(xmin, ymin, xmax, ymax)
            try:
                resp = requests.post(
                    "http://localhost:5555/infer",
                    json={
                        "slice_idx": str(slice_idx),
                        "bbox": list(map(str, (xmin, ymin, xmax, ymax))),
                    },
                )

                mask = np.asarray(json.loads(resp.json()))
                mask = np.transpose(mask, (1, 0))
                segmentId = self.ui.embeddedSegmentEditorWidget.currentSegmentID()
                curr_mask = slicer.util.arrayFromSegmentBinaryLabelmap(
                    self.segmentationNode, segmentId, self.volumeNode
                )
                curr_mask[slice_idx] |= mask

                # print(type(curr_mask), curr_mask.shape)

                # TODO: leave a state here on undo stack
                slicer.util.updateSegmentBinaryLabelmapFromArray(
                    curr_mask, self.segmentationNode, segmentId, self.volumeNode
                )
            except Exception as e:
                print(str(e))

            self.dgPositivePointListNode.RemoveAllControlPoints()

    def onSceneEndImport(self, caller, event):
        if not self._volumeNode:
            self.updateGUIFromParameterNode()

    def cleanup(self):
        """
        Called when the application closes and the module widget is destroyed.
        """
        print("cleanup")
        self.removeObservers()

    def enter(self):
        """
        Called each time the user opens this module.
        """
        print("enter")
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self):
        """
        Called each time the user opens a different module.
        """
        # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
        self.removeObserver(
            self._parameterNode,
            vtk.vtkCommand.ModifiedEvent,
            self.updateGUIFromParameterNode,
        )

    def onSceneStartClose(self, caller, event):
        """
        Called just before the scene is closed.
        """
        print("onSceneStartClose")
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)
        self.resetPointList(
            self.ui.dgPositiveControlPointPlacementWidget,
            self.dgPositivePointListNode,
            self.dgPositivePointListNodeObservers,
        )
        self.dgPositivePointListNode = None

    def resetPointList(self, markupsPlaceWidget, pointListNode, pointListNodeObservers):
        if markupsPlaceWidget.placeModeEnabled:
            markupsPlaceWidget.setPlaceModeEnabled(False)

        if pointListNode:
            slicer.mrmlScene.RemoveNode(pointListNode)
            self.removePointListNodeObservers(pointListNode, pointListNodeObservers)

    def removePointListNodeObservers(self, pointListNode, pointListNodeObservers):
        if pointListNode and pointListNodeObservers:
            for observer in pointListNodeObservers:
                pointListNode.RemoveObserver(observer)

    def onSceneEndClose(self, caller, event):
        """
        Called just after the scene is closed.
        """
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self):
        """
        Ensure parameter node exists and observed.
        """
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.
        print("initializeParameterNode")
        self.setParameterNode(self.logic.getParameterNode())
        if not self._parameterNode.GetNodeReference("InputVolume"):
            firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass(
                "vtkMRMLScalarVolumeNode"
            )
            if firstVolumeNode:
                self._parameterNode.SetNodeReferenceID(
                    "InputVolume", firstVolumeNode.GetID()
                )

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        # if not self._parameterNode.GetNodeReference("InputVolume"):
        #     firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        #     if firstVolumeNode:
        #         self._parameterNode.SetNodeReferenceID("InputVolume", firstVolumeNode.GetID())
        pass

    def setParameterNode(self, inputParameterNode):
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        # if inputParameterNode:
        #     self.logic.setDefaultParameters(inputParameterNode)

        # Unobserve previously selected parameter node and add an observer to the newly selected.
        # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
        # those are reflected immediately in the GUI.
        if self._parameterNode is not None:
            self.removeObserver(
                self._parameterNode,
                vtk.vtkCommand.ModifiedEvent,
                self.updateGUIFromParameterNode,
            )
        self._parameterNode = inputParameterNode
        if self._parameterNode is not None:
            self.addObserver(
                self._parameterNode,
                vtk.vtkCommand.ModifiedEvent,
                self.updateGUIFromParameterNode,
            )

        # Initial GUI update
        self.updateGUIFromParameterNode()

    def updateGUIFromParameterNode(self, caller=None, event=None):
        """
        This method is called whenever parameter node is changed.
        The module GUI is updated to show the current state of the parameter node.
        """

        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
        self._updatingGUIFromParameterNode = True
        if not self.dgPositivePointListNode:
            (
                self.dgPositivePointListNode,
                self.dgPositivePointListNodeObservers,
            ) = self.createPointListNode(
                "P", self.onDeepGrowPointListNodeModified, [0.5, 1, 0.5]
            )

            self.ui.dgPositiveControlPointPlacementWidget.setCurrentNode(
                self.dgPositivePointListNode
            )
            self.ui.dgPositiveControlPointPlacementWidget.setPlaceModeEnabled(False)

        # self.ui.dgPositiveControlPointPlacementWidget.setEnabled(self.ui.deepgrowModelSelector.currentText)
        self.ui.dgPositiveControlPointPlacementWidget.setEnabled("deepedit")

        # All the GUI updates are done
        self._updatingGUIFromParameterNode = False

    def createPointListNode(self, name, onMarkupNodeModified, color):
        displayNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsDisplayNode")
        # displayNode.SetTextScale(0)
        displayNode.SetSelectedColor(color)

        pointListNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        pointListNode.SetName(name)
        pointListNode.SetAndObserveDisplayNodeID(displayNode.GetID())

        pointListNodeObservers = []
        self.addPointListNodeObserver(pointListNode, onMarkupNodeModified)
        return pointListNode, pointListNodeObservers

    def removePointListNodeObservers(self, pointListNode, pointListNodeObservers):
        if pointListNode and pointListNodeObservers:
            for observer in pointListNodeObservers:
                pointListNode.RemoveObserver(observer)

    def addPointListNodeObserver(self, pointListNode, onMarkupNodeModified):
        pointListNodeObservers = []
        if pointListNode:
            eventIds = [slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent]
            for eventId in eventIds:
                pointListNodeObservers.append(
                    pointListNode.AddObserver(eventId, onMarkupNodeModified)
                )
        return pointListNodeObservers

    def updateParameterNodeFromGUI(self, caller=None, event=None):
        """
        This method is called when the user makes any change in the GUI.
        The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
        """

        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        wasModified = (
            self._parameterNode.StartModify()
        )  # Modify all properties in a single batch

        # self._parameterNode.SetNodeReferenceID("InputVolume", self.ui.inputSelector.currentNodeID)
        # self._parameterNode.SetNodeReferenceID("OutputVolume", self.ui.outputSelector.currentNodeID)
        # self._parameterNode.SetParameter("Threshold", str(self.ui.imageThresholdSliderWidget.value))
        # self._parameterNode.SetParameter("Invert", "true" if self.ui.invertOutputCheckBox.checked else "false")
        # self._parameterNode.SetNodeReferenceID("OutputVolumeInverse", self.ui.invertedOutputSelector.currentNodeID)

        self._parameterNode.EndModify(wasModified)

    def onApplyButton(self):
        """
        Run processing when user clicks "Apply" button.
        """
        pass

    def getControlPointXYZ(self, pointListNode, index):
        v = self._volumeNode
        RasToIjkMatrix = vtk.vtkMatrix4x4()
        v.GetRASToIJKMatrix(RasToIjkMatrix)

        coord = pointListNode.GetNthControlPointPosition(index)

        world = [0, 0, 0]
        pointListNode.GetNthControlPointPositionWorld(index, world)

        p_Ras = [coord[0], coord[1], coord[2], 1.0]
        p_Ijk = RasToIjkMatrix.MultiplyDoublePoint(p_Ras)
        p_Ijk = [round(i) for i in p_Ijk]

        logging.debug(f"RAS: {coord}; WORLD: {world}; IJK: {p_Ijk}")
        return p_Ijk[0:3]

    def onClickDeepgrow(self, current_point, skip_infer=False):
        print("onClickDeepgrow")
        # model = self.ui.deepgrowModelSelector.currentText
        # if not model:
        #     slicer.util.warningDisplay("Please select a deepgrow model")
        #     return

        # _, segment = self.currentSegment()
        # if not segment:
        #     slicer.util.warningDisplay("Please add the required label to run deepgrow")
        #     return

        # foreground_all = self.getControlPointsXYZ(self.dgPositivePointListNode, "foreground")
        # background_all = self.getControlPointsXYZ(self.dgNegativePointListNode, "background")

        # segment.SetTag("MONAILabel.ForegroundPoints", json.dumps(foreground_all))
        # segment.SetTag("MONAILabel.BackgroundPoints", json.dumps(background_all))
        # if skip_infer:
        #     return

        # # use model info "deepgrow" to determine
        # deepgrow_3d = False if self.models[model].get("dimension", 3) == 2 else True
        # start = time.time()

        # label = segment.GetName()
        # operationDescription = f"Run Deepgrow for segment: {label}; model: {model}; 3d {deepgrow_3d}"
        # logging.debug(operationDescription)

        # if not current_point:
        #     if not foreground_all and not deepgrow_3d:
        #         slicer.util.warningDisplay(operationDescription + " - points not added")
        #         return
        #     current_point = foreground_all[-1] if foreground_all else background_all[-1] if background_all else None

        # try:
        #     qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)

        #     sliceIndex = None
        #     if self.deepedit_multi_label:
        #         params = {}
        #         segmentation = self._segmentNode.GetSegmentation()
        #         for name in self.info.get("labels", []):
        #             points = []
        #             segmentId = segmentation.GetSegmentIdBySegmentName(name)
        #             segment = segmentation.GetSegment(segmentId) if segmentId else None
        #             if segment:
        #                 fPosStr = vtk.mutable("")
        #                 segment.GetTag("MONAILabel.ForegroundPoints", fPosStr)
        #                 pointset = str(fPosStr)
        #                 print(f"{segmentId} => {name} Control points are: {pointset}")
        #                 if fPosStr is not None and len(pointset) > 0:
        #                     points = json.loads(pointset)

        #             params[name] = points
        #         params["label"] = label
        #         labels = None
        #     else:
        #         sliceIndex = current_point[2] if current_point else None
        #         logging.debug(f"Slice Index: {sliceIndex}")

        #         if deepgrow_3d or not sliceIndex:
        #             foreground = foreground_all
        #             background = background_all
        #         else:
        #             foreground = [x for x in foreground_all if x[2] == sliceIndex]
        #             background = [x for x in background_all if x[2] == sliceIndex]

        #         logging.debug(f"Foreground: {foreground}")
        #         logging.debug(f"Background: {background}")
        #         logging.debug(f"Current point: {current_point}")

        #         params = {
        #             "label": label,
        #             "foreground": foreground,
        #             "background": background,
        #         }
        #         labels = [label]

        #     params["label"] = label
        #     params.update(self.getParamsFromConfig("infer", model))
        #     print(f"Request Params for Deepgrow/Deepedit: {params}")

        #     image_file = self.current_sample["id"]
        #     result_file, params = self.logic.infer(model, image_file, params, session_id=self.getSessionId())
        #     print(f"Result Params for Deepgrow/Deepedit: {params}")
        #     if labels is None:
        #         labels = (
        #             params.get("label_names")
        #             if params and params.get("label_names")
        #             else self.models[model].get("labels")
        #         )
        #         if labels and isinstance(labels, dict):
        #             labels = [k for k, _ in sorted(labels.items(), key=lambda item: item[1])]

        #     freeze = label if self.ui.freezeUpdateCheckBox.checked else None
        #     self.updateSegmentationMask(result_file, labels, None if deepgrow_3d else sliceIndex, freeze=freeze)
        # except:
        #     logging.exception("Unknown Exception")
        #     slicer.util.errorDisplay(operationDescription + " - unexpected error.", detailedText=traceback.format_exc())
        # finally:
        #     qt.QApplication.restoreOverrideCursor()

        # self.updateGUIFromParameterNode()
        # logging.info(f"Time consumed by Deepgrow: {time.time() - start:3.1f}")

    def onEditControlPoints(self, pointListNode, tagName):
        if pointListNode is None:
            return

        pointListNode.RemoveAllControlPoints()
        segmentId, segment = self.currentSegment()
        if segment and segmentId:
            v = self._volumeNode
            IjkToRasMatrix = vtk.vtkMatrix4x4()
            v.GetIJKToRASMatrix(IjkToRasMatrix)

            fPosStr = vtk.mutable("")
            segment.GetTag(tagName, fPosStr)
            pointset = str(fPosStr)
            logging.debug(
                f"{segmentId} => {segment.GetName()} Control points are: {pointset}"
            )

            if fPosStr is not None and len(pointset) > 0:
                points = json.loads(pointset)
                for p in points:
                    p_Ijk = [p[0], p[1], p[2], 1.0]
                    p_Ras = IjkToRasMatrix.MultiplyDoublePoint(p_Ijk)
                    logging.debug(f"Add Control Point: {p_Ijk} => {p_Ras}")
                    pointListNode.AddControlPoint(p_Ras[0:3])

    def onSelectLabel(self, caller=None, event=None):
        self.updateParameterNodeFromGUI(caller, event)

        self.ignorePointListNodeAddEvent = True
        self.onEditControlPoints(
            self.dgPositivePointListNode, "MONAILabel.ForegroundPoints"
        )
        self.ignorePointListNodeAddEvent = False

    def getControlPointsXYZ(self, pointListNode, name):
        v = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        # v = self._volumeNode
        RasToIjkMatrix = vtk.vtkMatrix4x4()
        v.GetRASToIJKMatrix(RasToIjkMatrix)

        point_set = []
        n = pointListNode.GetNumberOfControlPoints()
        for i in range(n):
            coord = pointListNode.GetNthControlPointPosition(i)

            world = [0, 0, 0]
            pointListNode.GetNthControlPointPositionWorld(i, world)

            p_Ras = [coord[0], coord[1], coord[2], 1.0]
            p_Ijk = RasToIjkMatrix.MultiplyDoublePoint(p_Ras)
            p_Ijk = [round(i) for i in p_Ijk]

            logging.debug(f"RAS: {coord}; WORLD: {world}; IJK: {p_Ijk}")
            point_set.append(p_Ijk[0:3])

        logging.info(f"{name} => Current control points: {point_set}")
        return point_set


#
# MedSAMLogic
#


class MedSAMLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self):
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)

    def setDefaultParameters(self, parameterNode):
        """
        Initialize parameter node with default settings.
        """
        if not parameterNode.GetParameter("Threshold"):
            parameterNode.SetParameter("Threshold", "100.0")
        if not parameterNode.GetParameter("Invert"):
            parameterNode.SetParameter("Invert", "false")

    def process(
        self, inputVolume, outputVolume, imageThreshold, invert=False, showResult=True
    ):
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        :param inputVolume: volume to be thresholded
        :param outputVolume: thresholding result
        :param imageThreshold: values above/below this threshold will be set to 0
        :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
        :param showResult: show output volume in slice viewers
        """

        if not inputVolume or not outputVolume:
            raise ValueError("Input or output volume is invalid")

        import time

        startTime = time.time()
        logging.info("Processing started")

        # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
        cliParams = {
            "InputVolume": inputVolume.GetID(),
            "OutputVolume": outputVolume.GetID(),
            "ThresholdValue": imageThreshold,
            "ThresholdType": "Above" if invert else "Below",
        }
        cliNode = slicer.cli.run(
            slicer.modules.thresholdscalarvolume,
            None,
            cliParams,
            wait_for_completion=True,
            update_display=showResult,
        )
        # We don't need the CLI module node anymore, remove it to not clutter the scene with it
        slicer.mrmlScene.RemoveNode(cliNode)

        stopTime = time.time()
        logging.info(f"Processing completed in {stopTime-startTime:.2f} seconds")

    def get_segment_editor_node(self):
        # Use the Segment Editor module's parameter node for the embedded segment editor widget.
        # This ensures that if the user switches to the Segment Editor then the selected
        # segmentation node, volume node, etc. are the same.
        segmentEditorSingletonTag = "SegmentEditor"
        segmentEditorNode = slicer.mrmlScene.GetSingletonNode(
            segmentEditorSingletonTag, "vtkMRMLSegmentEditorNode"
        )
        if segmentEditorNode is None:
            segmentEditorNode = slicer.mrmlScene.CreateNodeByClass(
                "vtkMRMLSegmentEditorNode"
            )
            segmentEditorNode.UnRegister(None)
            segmentEditorNode.SetSingletonTag(segmentEditorSingletonTag)
            segmentEditorNode = slicer.mrmlScene.AddNode(segmentEditorNode)
        return segmentEditorNode


#
# MedSAMTest
#


class MedSAMTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """Do whatever is needed to reset the state - typically a scene clear will be enough."""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here."""
        self.setUp()
        self.test_MedSAM1()

    def test_MedSAM1(self):
        """Ideally you should have several levels of tests.  At the lowest level
        tests should exercise the functionality of the logic with different inputs
        (both valid and invalid).  At higher levels your tests should emulate the
        way the user would interact with your code and confirm that it still works
        the way you intended.
        One of the most important features of the tests is that it should alert other
        developers when their changes will have an impact on the behavior of your
        module.  For example, if a developer removes a feature that you depend on,
        your test should break so they know that the feature is needed.
        """

        self.delayDisplay("Starting the test")

        # Get/create input data

        import SampleData

        registerSampleData()
        inputVolume = SampleData.downloadSample("MedSAM1")
        self.delayDisplay("Loaded test data set")

        inputScalarRange = inputVolume.GetImageData().GetScalarRange()
        self.assertEqual(inputScalarRange[0], 0)
        self.assertEqual(inputScalarRange[1], 695)

        outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
        threshold = 100

        # Test the module logic

        logic = MedSAMLogic()

        # Test algorithm with non-inverted threshold
        logic.process(inputVolume, outputVolume, threshold, True)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], threshold)

        # Test algorithm with inverted threshold
        logic.process(inputVolume, outputVolume, threshold, False)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], inputScalarRange[1])

        self.delayDisplay("Test passed")
