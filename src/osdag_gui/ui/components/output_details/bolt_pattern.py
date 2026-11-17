import sys
from PySide6.QtWidgets import (QApplication, QDialog, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QGraphicsView, QSizeGrip,
                             QGraphicsScene)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QFont, QColor
from PySide6.QtGui import QPolygonF, QBrush
from PySide6.QtCore import QPointF
from ..dialogs.custom_titlebar import CustomTitleBar
from osdag_core.Common import *

class BoltPatternGenerator(QDialog):
    def __init__(self, connection_obj, rows=3, cols=2 , main = None):
        super().__init__()
        app = QApplication.instance()
        self.theme = app.theme_manager

        self.connection = connection_obj
        self.main=main
        self.plate_height = main.plate.height
        self.plate_width = main.plate.length 
        self.hole_dia=main.bolt.bolt_diameter_provided
        self.rows=rows
        self.cols=cols
        if self.rows is None or self.rows == 0:
             self.rows = main.plate.bolts_one_line
        if self.cols is None or self.cols == 0:
             self.cols = main.plate.bolt_line
        if self.cols is None or self.cols == 0:
             self.cols = main.plate.bolt_line

        try:
            connectivity = getattr(self.main, 'connectivity', getattr(self.main, 'connectivity_loc', ''))
        except:
            connectivity = ''
        
        if self.main:
            print('DEBUG BOLT PATTERN main dir:', dir(self.main))
            if hasattr(self.main, 'uiObj'):
                print('DEBUG BOLT PATTERN uiObj dir:', dir(self.main.uiObj))

        if not connectivity and self.rows * self.cols == 4 and self.main and self.main.module_name() == 'Fin Plate Connection':
             connectivity = 'Column Web-Beam Web'
             self.rows = 2
             self.cols = 2
             
        print('DEBUG BOLT PATTERN END: connectivity =', repr(connectivity), 'rows =', self.rows, 'cols =', self.cols)

        if connectivity == 'Column Web-Beam Web' and self.rows * self.cols == 4:
            self.rows = 2
            self.cols = 2

        # Check if Strut Bolted module
        self.is_strut = False
        self.is_lap = False
        if self.main:
            try:
                module_name = self.main.module_name()
                self.is_strut = (module_name == 'Struts Bolted to End Gusset')
                self.is_lap = (module_name == 'Lap Joint Bolted Connection')
            except AttributeError:
                pass
        
        print(self.plate_height,self.plate_width)
        output=main.output_values(True)
        dict1={i[0] : i[3] for i in output}
        for i in output:
            print(i)
        self.weldsize=0
        if 'Weld.Size' in dict1:
            self.weldsize=dict1['Weld.Size']
            
        self.member_height_designation = None
        if 'section_size.designation' in dict1:
             desig = str(dict1['section_size.designation'])
             # Expected format "60 x 60 x 4" or "ISA 60 x 60 x 6"
             parts = []
             if 'x' in desig:
                 parts = desig.split('x')
             elif 'X' in desig:
                 parts = desig.split('X')
             
             if parts:
                 try:
                     # parts[0] might be "ISA 60 " or "60 "
                     tup = parts[0].strip().split()
                     # Take the last token which should be the number
                     val_str = tup[-1]
                     self.member_height_designation = float(val_str)
                 except (ValueError, IndexError):
                     pass
                     
        self.initUI()

    def setupWrapper(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setObjectName("spacing_capacity_details")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(0)
        self.title_bar = CustomTitleBar()
        self.title_bar.setTitle("Bolt Pattern")
        main_layout.addWidget(self.title_bar)
        self.content_widget = QWidget(self)
        main_layout.addWidget(self.content_widget, 1)
        size_grip = QSizeGrip(self)
        size_grip.setFixedSize(16, 16)
        overlay = QHBoxLayout()
        overlay.setContentsMargins(0, 0, 4, 4)
        overlay.addStretch(1)
        overlay.addWidget(size_grip, 0, Qt.AlignBottom | Qt.AlignRight)
        main_layout.addLayout(overlay)

    def initUI(self):
        self.setupWrapper()
        
        # Center the window on the screen with the same dimensions
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width, height = 800, 500
        x = screen_geometry.x() + (screen_geometry.width() - width) // 2
        y = screen_geometry.y() + (screen_geometry.height() - height) // 2
        self.setGeometry(x, y, width, height)
        
        # Main layout
        main_layout = QHBoxLayout()
        
        # Left panel for parameter display
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # Parameter display labels
        params = self.get_parameters()
        

        # Display the parameter values
        for key, value in params.items():
            param_layout = QHBoxLayout()
            param_label = QLabel(f'{key.title()} Distance :')
            param_label.setStyleSheet("font-size: 15px; font-weight: bold;")
            value_label = QLabel(f'{float(value):.2f}')
            value_label.setStyleSheet("font-size: 15px;")
            param_layout.addWidget(param_label)
            param_layout.addWidget(value_label)
            left_layout.addLayout(param_layout)

        param_layout = QHBoxLayout()
        param_label = QLabel("(All Dimensions are in mm)")
        param_label.setStyleSheet("font-size: 12px; font-style: italic;")
        param_layout.addWidget(param_label)
        left_layout.addLayout(param_layout)

        left_layout.addStretch()
        left_panel.setLayout(left_layout)
        
        # Right panel for the drawing using QGraphicsView
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        if self.theme.is_light():
            self.view.setBackgroundBrush(QBrush(Qt.white))
        else:
            self.view.setBackgroundBrush(QBrush(QColor("#4A4A4A")))
        # Create and add the drawing to the scene
        self.createDrawing(params)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(self.view, 3)
        
        self.content_widget.setLayout(main_layout)
        
        # Ensure the view shows all content
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
    def get_parameters(self):
        spacing_data = self.connection.spacing(status=True)  # Get actual values
        param_map = {}
        print('spacing_data length' , len(spacing_data))
        
        # Check if Strut Bolted module
        is_strut = False
        if self.main:
            try:
                # Import commonly used keys if needed or rely on string comparison since main.module_name returns string
                is_strut = (self.main.module_name() == 'Struts Bolted to End Gusset')
            except AttributeError:
                pass

        for item in spacing_data:
            key, _, _, value = item
            # print('key : ', key)
            if key == KEY_OUT_PITCH:  
                param_map['pitch'] = float(value)
            elif key == KEY_OUT_END_DIST:
                param_map['end'] = float(value)
            elif key == KEY_OUT_GAUGE1:
                param_map['gauge1'] = float(value)
            elif key == KEY_OUT_GAUGE2:
                param_map['gauge2'] = float(value)
            elif key == KEY_OUT_GAUGE:
                param_map['gauge'] = float(value)
            elif key == KEY_OUT_EDGE_DIST:
                param_map['edge'] = float(value)
            elif key == 'Member.Depth':
                param_map['Member.Depth'] = float(value)

        # For Strut Bolted module, the interpretation of parameters changes for drawing.
        # The drawing assumes:
        #   'pitch' for vertical spacing (Y-axis)
        #   'gauge' for horizontal spacing (X-axis)
        #   'end' for vertical margin (Y-axis)
        #   'edge' for horizontal margin (X-axis)
        #
        # Osdag Core for Strut (Horizontal Member):
        #   KEY_OUT_PITCH: Axial/Horizontal spacing
        #   KEY_OUT_GAUGE: Transverse/Vertical spacing
        #   KEY_OUT_END_DIST: Axial/Horizontal margin
        #   KEY_OUT_EDGE_DIST: Transverse/Vertical margin
        
        if self.is_strut:
            # Map Strut's horizontal spacing (Pitch) to drawing's horizontal spacing (gauge)
            # Map Strut's vertical spacing (Gauge) to drawing's vertical spacing (pitch)
            drawing_gauge = param_map['pitch']
            drawing_pitch = param_map['gauge']
            
            # Map Strut's horizontal margin (End Dist) to drawing's horizontal margin (edge)
            # Map Strut's vertical margin (Edge Dist) to drawing's vertical margin (end)
            drawing_edge = param_map['end']
            drawing_end = param_map['edge']

            param_map['pitch'] = drawing_pitch
            param_map['gauge'] = drawing_gauge
            param_map['end'] = drawing_end
            param_map['edge'] = drawing_edge
            
            # If gauge1/gauge2 were present, they would also need to be remapped if they represent horizontal spacing.
            # Assuming for strut, 'gauge' is the primary transverse spacing.
            if param_map.get('gauge1', 0) != 0 or param_map.get('gauge2', 0) != 0:
                # If gauge1/gauge2 are used for strut, they would represent vertical spacing.
                # In the drawing, vertical spacing is 'pitch'.
                # So, if strut uses gauge1/gauge2, they should be mapped to drawing's pitch.
                # This scenario is less common for struts, but if it happens, it needs careful handling.
                # For now, we'll assume 'gauge' is the primary transverse spacing for strut.
                pass


        # Add hardcoded hole diameter
        param_map['hole'] = self.main.bolt.bolt_diameter_provided

        try:
            connectivity = getattr(self.main, 'connectivity', getattr(self.main, 'connectivity_loc', ''))
        except:
            connectivity = ''

        if not connectivity and self.rows * self.cols == 4 and self.main and self.main.module_name() == 'Fin Plate Connection':
            connectivity = 'Column Web-Beam Web'

        if connectivity == 'Column Web-Beam Web' and self.rows * self.cols == 4:
            if param_map.get('gauge1', 0) == 0:
                param_map['gauge1'] = param_map.get('pitch', 0)
            if param_map.get('gauge2', 0) == 0:
                param_map['gauge2'] = param_map.get('pitch', 0)
            if 'gauge' in param_map and param_map.get('gauge', 0) == 0:
                param_map['gauge'] = param_map.get('pitch', 0)

        print("Extracted parameters:", param_map)

        return param_map

    def createDrawing(self, params):
        
        # Extract parameters
        pitch = params['pitch']
        end = params['end']
        if 'gauge' in params:
            gauge = params['gauge']
        else:
            gauge1 = params['gauge1']
            gauge2 = params['gauge2']
        edge = params['edge']
        hole_diameter = params['hole']
        
        # Calculate dimensions
        if 'gauge' in params:
            gauge1 = gauge
            gauge2 = gauge
        width = self.plate_width
        
        height = self.plate_height
        
        try:
            connectivity = getattr(self.main, 'connectivity', getattr(self.main, 'connectivity_loc', ''))
        except:
            connectivity = ''
        
        if self.main:
            print('DEBUG BOLT PATTERN main dir:', dir(self.main))
            if hasattr(self.main, 'uiObj'):
                print('DEBUG BOLT PATTERN uiObj dir:', dir(self.main.uiObj))

        if not connectivity and self.rows * self.cols == 4 and self.main and self.main.module_name() == 'Fin Plate Connection':
             connectivity = 'Column Web-Beam Web'
             self.rows = 2
             self.cols = 2
             
        print('DEBUG BOLT PATTERN END: connectivity =', repr(connectivity), 'rows =', self.rows, 'cols =', self.cols)

        if connectivity == "Column Web-Beam Web" and self.rows == 2 and self.cols == 2:
            if gauge1 == 0:
                gauge1 = gauge2 = pitch
                params['gauge1'] = pitch
                params['gauge2'] = pitch
                if 'gauge' in params:
                    params['gauge'] = pitch
            width = 2 * edge + (self.cols - 1) * gauge1
            height = 2 * end + (self.rows - 1) * pitch
        if self.is_strut or self.is_lap:
             if self.is_strut and self.member_height_designation is not None:
                 height = self.member_height_designation
             elif 'Member.Depth' in params:
                 height = params['Member.Depth']
        
        # Set up pens
        if self.theme.is_light():
            dimension_pen = QPen(Qt.black, 1.0)
        else:
            dimension_pen = QPen(QColor("#8A8A8A"), 1.0)
        weld_pen = QPen(Qt.red, 1)
        outline_pen = QPen(QColor("#723B17"), 2)
        red_brush = QBrush(Qt.red)

        # Dimension offsets
        h_offset = 60 # Increased to ensure left dimensions fit
        v_offset = 60
        
        # Create scene rectangle with extra space for dimensions
        # setSceneRect(x, y, w, h)
        self.scene.setSceneRect(-h_offset, -v_offset, 
                                width + 2*h_offset, height + 2*v_offset)
        
        # Draw rectangle
        background_brush = QBrush(QColor("#A7A796"))
        self.scene.addRect(0, 0, width, height, dimension_pen, background_brush)

        # Draw holes
        # Draw holes
        for row in range(self.rows):
            for col in range(self.cols):
                if self.is_strut or self.is_lap:
                    # Strut/Lap Logic (Horizontal Member)
                    # X = Left Start + End Dist (First Bolt margin) + Column Index * Pitch
                    # Y = Top Start + Edge Dist + Row Index * Gauge
                    # Note: Using 'end' as horizontal margin (End Distance) and 'pitch' as horizontal spacing
                    # Using 'edge' as vertical margin (Edge Distance) and 'gauge' as vertical spacing
                    
                    x_center = end + col * pitch
                    # Assuming symmetric placement vertically or just simple pattern from top
                    y_center = edge + row * gauge1 # Use gauge1/gauge/gauge2 logic if needed, simplify to gauge
                    
                    x = x_center - hole_diameter / 2
                    y = y_center - hole_diameter / 2
                else:
                    # Fin Plate Logic (Vertical Member/Plate)
                    # Start from right edge (for example: total layout width - edge)
                    x_center = width - edge

                    # Subtract gauges from right to left
                    for i in range(col):
                        x_center -= gauge1 if i % 2 == 0 else gauge2

                    # Y-position stays the same
                    y_center = end + row * pitch

                    # Top-left corner for drawing the circle
                    x = x_center - hole_diameter / 2
                    y = y_center - hole_diameter / 2

                # print(f"row: {row}, col: {col}, x: {x}, y: {y}")
                self.scene.addEllipse(x, y, hole_diameter, hole_diameter, outline_pen)
        
        if not self.is_strut and not self.is_lap:
            weld_size=self.weldsize
            self.scene.addRect(0, 0, weld_size, height, weld_pen,red_brush)

        print(params,dimension_pen)
        # Add dimensions
        self.addDimensions(params, dimension_pen, width, height)

    def addDimensions(self, params, pen, width, height):
        # Extract parameters
        pitch = params['pitch']
        end = params['end']
        if 'gauge' in params:
            gauge = params['gauge']
        else:
            gauge1 = params['gauge1']
            gauge2 = params['gauge2']
        edge = params['edge']

        if 'gauge' in params:
            gauge1 = gauge
            gauge2 = gauge
        
        # Offsets for dimension lines
        h_offset = 20
        v_offset = 15
        
        if self.is_strut or self.is_lap:
             # STRUT/LAP DIMENSIONS (Horizontal Layout)
             
             # Horizontal Dimensions (Top)
             # End Distance (Left Edge -> First Bolt Column)
             self.addHorizontalDimension(0, -h_offset, end, -h_offset, f"{end:g}", pen)
             
             # Pitch Spacing (Between Columns)
             for i in range(self.cols - 1):
                 x1 = end + i * pitch
                 x2 = end + (i + 1) * pitch
                 self.addHorizontalDimension(x1, -h_offset, x2, -h_offset, f"{pitch:g}", pen)
                 
             # Remaining Length (Last Bolt Column -> Right Edge)
             last_bolt_x = end + (self.cols - 1) * pitch
             rem_len = width - last_bolt_x
             self.addHorizontalDimension(last_bolt_x, -h_offset, width, -h_offset, f"{rem_len:g}", pen)
             
             # Vertical Dimensions
             # Detailed on Left, Overall on Right (Unified for Strut and Lap Joint)
             detailed_x = -v_offset
             overall_x = width + v_offset

             # Edge Distance (Top Edge -> First Bolt Row)
             self.addVerticalDimension(detailed_x, 0, detailed_x, edge, f"{edge:g}", pen)
             
             # Gauge Spacing (Between Rows)
             for i in range(self.rows - 1):
                 y1 = edge + i * gauge1
                 y2 = edge + (i + 1) * gauge1
                 self.addVerticalDimension(detailed_x, y1, detailed_x, y2, f"{gauge1:g}", pen)
                 
             # Remaining Height (Last Bolt Row -> Bottom Edge)
             last_bolt_y = edge + (self.rows - 1) * gauge1
             rem_h = height - last_bolt_y
             self.addVerticalDimension(detailed_x, last_bolt_y, detailed_x, height, f"{rem_h:g}", pen)
             
             # Overall Height
             self.addVerticalDimension(overall_x, 0, overall_x, height, f"{height:g}", pen)
             
             # Overall Width (Bottom) - Optional but good for complete member detail
             # self.addHorizontalDimension(0, height + h_offset, width, height + h_offset, f"{width:g}", pen)

        else:
            # FIN PLATE LOGIC (Vertical Layout)
            
            # Horizontal dimensions - from left edge to first bolt, then bolt to bolt, then last bolt to right edge
            x_positions = []
            # Start from left edge (weld side)
            x_positions.append(0)
            
            # Calculate all bolt x-positions (from right to left in the order they appear)
            bolt_x_positions = []
            for col in range(self.cols):
                x_center = width - edge
                for i in range(col):
                    x_center -= gauge1 if i % 2 == 0 else gauge2
                bolt_x_positions.append(x_center)
            
            # Reverse to get left to right order
            bolt_x_positions.reverse()
            x_positions.extend(bolt_x_positions)
            
            # Add the right edge position
            x_positions.append(width)
            
            # Add dimensions between consecutive positions
            for i in range(len(x_positions) - 1):
                x1 = x_positions[i]
                x2 = x_positions[i + 1]
                distance = abs(x2 - x1)
                self.addHorizontalDimension(x1, -h_offset, x2, -h_offset, f"{distance:g}", pen)
                
            # Add vertical dimensions (Pitch/End from Top)
            self.addVerticalDimension(width + v_offset, 0, width + v_offset, end, f"{end:g}", pen)
            for i in range(self.rows - 1):
                self.addVerticalDimension(width + v_offset, end + i * pitch, width + v_offset, end + (i + 1) * pitch, f"{pitch:g}", pen)
            
            # Add bottom end distance dimension
            last_bolt_y = end + (self.rows - 1) * pitch
            rem_len = height - last_bolt_y
            self.addVerticalDimension(width + v_offset, last_bolt_y, width + v_offset, height, f"{rem_len:g}", pen)
            
            # Add left side dimension
            self.addVerticalDimension(-v_offset, 0, -v_offset, height, f"{height:g}", pen)

    def addHorizontalDimension(self, x1, y1, x2, y2, text, pen):
        try:
            val = float(text)
            if val == 0:
                return
        except ValueError:
            pass
            
        self.scene.addLine(x1, y1, x2, y2, pen)
        arrow_size = 3
        ext_length = 10
        self.scene.addLine(x1, y1 - ext_length/2, x1, y1 + ext_length/2, pen)
        self.scene.addLine(x2, y2 - ext_length/2, x2, y2 + ext_length/2, pen)
        
        points_left = [
            (x1, y1),
            (x1 + arrow_size, y1 - arrow_size/2),
            (x1 + arrow_size, y1 + arrow_size/2)
        ]
        polygon_left = self.scene.addPolygon(QPolygonF([QPointF(x, y) for x, y in points_left]), pen)
        if self.theme.is_light():
            polygon_left.setBrush(QBrush(Qt.black))
        else:
            polygon_left.setBrush(QBrush(QColor("#8A8A8A")))
        
        points_right = [
            (x2, y2),
            (x2 - arrow_size, y2 - arrow_size/2),
            (x2 - arrow_size, y2 + arrow_size/2)
        ]
        polygon_right = self.scene.addPolygon(QPolygonF([QPointF(x, y) for x, y in points_right]), pen)
        if self.theme.is_light():
            polygon_right.setBrush(QBrush(Qt.black))
        else:
            polygon_right.setBrush(QBrush(QColor("#8A8A8A")))
        
        # Add text
        text_item = self.scene.addText(text)
        font = QFont()
        font.setPointSize(8)
        text_item.setFont(font)
        if self.theme.is_light():
            text_item.setDefaultTextColor(Qt.black)
        else:
            text_item.setDefaultTextColor(Qt.white)
        
        # Position text
        text_item.setPos((x1 + x2) / 2 - text_item.boundingRect().width() / 2, y1 - text_item.boundingRect().height() - 2)

    def addVerticalDimension(self, x1, y1, x2, y2, text, pen):
        try:
            val = float(text)
            if val == 0:
                return
        except ValueError:
            pass

        self.scene.addLine(x1, y1, x2, y2, pen)
        arrow_size = 3
        ext_length = 10
        self.scene.addLine(x1 - ext_length/2, y1, x1 + ext_length/2, y1, pen)
        self.scene.addLine(x2 - ext_length/2, y2, x2 + ext_length/2, y2, pen)
        
        if y2 > y1:
            points_top = [
                (x1, y1),
                (x1 - arrow_size/2, y1 + arrow_size),
                (x1 + arrow_size/2, y1 + arrow_size)
            ]
            polygon_top = self.scene.addPolygon(QPolygonF([QPointF(x, y) for x, y in points_top]), pen)
            if self.theme.is_light():
                polygon_top.setBrush(QBrush(Qt.black))
            else:
                polygon_top.setBrush(QBrush(QColor("#8A8A8A")))
            
            points_bottom = [
                (x2, y2),
                (x2 - arrow_size/2, y2 - arrow_size),
                (x2 + arrow_size/2, y2 - arrow_size)
            ]
            polygon_bottom = self.scene.addPolygon(QPolygonF([QPointF(x, y) for x, y in points_bottom]), pen)
            if self.theme.is_light():
                polygon_bottom.setBrush(QBrush(Qt.black))
            else:
                polygon_bottom.setBrush(QBrush(QColor("#8A8A8A")))
        else:
            points_top = [
                (x2, y2),
                (x2 - arrow_size/2, y2 + arrow_size),
                (x2 + arrow_size/2, y2 + arrow_size)
            ]
            polygon_top = self.scene.addPolygon(QPolygonF([QPointF(x, y) for x, y in points_top]), pen)
            if self.theme.is_light():
                polygon_top.setBrush(QBrush(Qt.black))
            else:
                polygon_top.setBrush(QBrush(QColor("#8A8A8A")))
            
            points_bottom = [
                (x1, y1),
                (x1 - arrow_size/2, y1 - arrow_size),
                (x1 + arrow_size/2, y1 - arrow_size)
            ]
            polygon_bottom = self.scene.addPolygon(QPolygonF([QPointF(x, y) for x, y in points_bottom]), pen)
            if self.theme.is_light():
                polygon_bottom.setBrush(QBrush(Qt.black))
            else:
                polygon_bottom.setBrush(QBrush(QColor("#8A8A8A")))
        
        text_item = self.scene.addText(text)
        font = QFont()
        font.setPointSize(8)
        text_item.setFont(font)
        if self.theme.is_light():
            text_item.setDefaultTextColor(Qt.black)
        else:
            text_item.setDefaultTextColor(Qt.white)

        if x1 < 0:
            text_item.setPos(x1 - text_item.boundingRect().width(), (y1 + y2) / 2 - text_item.boundingRect().height() / 2)
        else:
            text_item.setPos(x1, (y1 + y2) / 2 - text_item.boundingRect().height() / 2)


# >>> BEGIN plate_joint_spacing (added by patch_spacing_diagrams.py) >>> [eol=0]
# plate_joint_spacing.py
#
# Spacing-details dialog for the *plated* bolted joints:
#
#     * Lap Joint  - Bolted
#     * Butt Joint - Bolted
#
# The drawing is the plan view of the 3D model in its DEFAULT orientation (plate 2
# at the top, plate 1 at the bottom; bolts drawn as circles) - it is not rotated.
#
# Nothing in the drawing is hard-coded: every length, bolt position and
# proportion is computed from the design result of the module, using exactly
# the same placement rules as the CAD builders
# (``cad/SimpleConnections/BoltedLapJoint/bolted_lap_joint.py`` and
# ``cad/SimpleConnections/BoltedButtJoint/Butt_joint_bolted.py``), and the whole
# drawing is scaled to fit the window.
#
# Colours
#     Lap  : long plate #ffffff | short plate #f4f4e3 | bolt #ff3737
#     Butt : top #ffffff | middle (cover) #dbdbce | bottom #f4f4e3 | bolt #ff3737

import math

from PySide6.QtWidgets import (QApplication, QDialog, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QSizeGrip, QSizePolicy)
from PySide6.QtGui import (QPainter, QPen, QBrush, QColor, QFont,
                           QFontMetrics, QPolygonF)
from PySide6.QtCore import Qt, QPointF, QRectF, QSize

from osdag_core.Common import KEY_DISP_BUTTJOINTBOLTED

# --------------------------------------------------------------------------
# Colours requested for the drawing
# --------------------------------------------------------------------------
COLOR_WHITE = "#ffffff"
COLOR_BEIGE = "#f4f4e3"
COLOR_COVER = "#dbdbce"
COLOR_BOLT = "#ff3737"
COLOR_BOLT_EDGE = "#5a1010"

# CAD: each main plate of the butt joint is 1.25 * the cover plate length.
_BUTT_PLATE_TO_COVER = 1.25


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _num(value, default=0.0):
    """Robust float conversion (handles None, '', numpy types, NaN)."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float(default)
    if math.isnan(out) or math.isinf(out):
        return float(default)
    return out


def _count(value, default=1):
    """Robust positive integer conversion."""
    try:
        out = int(round(float(value)))
    except (TypeError, ValueError):
        return int(default)
    return max(out, 1)


def _fmt(value):
    """Dimension text: at most one decimal, no trailing '.0'."""
    text = f"{round(float(value), 1):.1f}"
    return text[:-2] if text.endswith(".0") else text


# --------------------------------------------------------------------------
# Geometry (pure python - no Qt, easy to test)
# --------------------------------------------------------------------------
class JointLayout:
    """
    Drawing model, in millimetres, in the default (un-rotated) 3D plan view.

    Origin is the top-left corner of the drawing:
        x : horizontal distance to the right   (across the plate width)
        y : vertical distance downwards        (along the plate length)
    """

    def __init__(self):
        self.kind = ""
        self.width = 0.0          # horizontal extent  (plate width)
        self.length = 0.0         # vertical extent    (whole drawing length)
        self.rects = []           # (y0, y1, colour, name)  full-width bands
        self.bolts = []           # (x, y)
        self.head_radius = 0.0    # bolt head circum-radius
        self.top_chain = []       # (x0, x1, kind)  edge | gauge ... | edge
        self.left_chain = []      # (y0, y1, kind)  end | pitch ... | end
        self.right_spans = []     # (y0, y1)        plate / cover lengths
        self.bottom_spans = []    # (x0, x1)        overall width


def _gauge_positions(width, rows, gauge, edge):
    """x (from the plate edge, as in the CAD) of every bolt line."""
    rows = max(int(rows), 1)
    if rows == 1:
        edge = edge if edge > 0 else width / 2.0
        return [edge], 0.0, edge
    if gauge <= 0:
        # Defensive: a multi-line pattern with no gauge would stack bolts.
        gauge = max((width - 2.0 * edge) / (rows - 1), 0.0)
    return [edge + r * gauge for r in range(rows)], gauge, edge


def _finish_top_chain(layout, xs):
    """Horizontal chain across the width: edge | gauge ... gauge | edge."""
    marks = [0.0] + list(xs) + [layout.width]
    kinds = ["edge"] + ["gauge"] * (len(xs) - 1) + ["edge"]
    layout.top_chain = [(marks[i], marks[i + 1], kinds[i])
                        for i in range(len(kinds)) if marks[i + 1] - marks[i] > 1e-6]


def build_lap_layout(width, rows, cols, number_bolts, pitch, gauge, edge, end,
                     overlap, bolt_dia):
    """
    Lap joint, default plan view.

    CAD (top view, y up): plate 2 (top plate) spans y in [0, 2*ov], plate 1
    spans [-ov, ov]; bolts at  x = edge + row*gauge  and  y = end + col*pitch
    (col-major fill, stopped after ``number_bolts``).  On screen y points down:
    y_screen = 2*ov - y_cad.
    """
    width = _num(width)
    rows, cols = _count(rows), _count(cols)
    pitch, end = _num(pitch), _num(end)
    xs, gauge, edge = _gauge_positions(width, rows, _num(gauge), _num(edge))

    overlap = _num(overlap)
    if overlap <= 0:
        overlap = 2.0 * end + (cols - 1) * pitch
    n_total = _count(number_bolts, rows * cols) if _num(number_bolts) > 0 else rows * cols

    lay = JointLayout()
    lay.kind = "lap"
    lay.width = width
    lay.length = 3.0 * overlap
    lay.rects = [
        (0.0, 2.0 * overlap, COLOR_WHITE, "Plate 2"),
        (2.0 * overlap, 3.0 * overlap, COLOR_BEIGE, "Plate 1"),
    ]
    lay.head_radius = 0.8 * _num(bolt_dia)          # CAD: head radius = 0.8 d

    count = 0
    done = False
    for c in range(cols):
        for r in range(rows):
            if count >= n_total:
                done = True
                break
            lay.bolts.append((xs[r], 2.0 * overlap - end - c * pitch))
            count += 1
        if done:
            break

    marks = ([overlap] + [2.0 * overlap - end - c * pitch for c in range(cols - 1, -1, -1)]
             + [2.0 * overlap])
    kinds = ["end"] + ["pitch"] * (cols - 1) + ["end"]
    lay.left_chain = [(marks[i], marks[i + 1], kinds[i]) for i in range(len(kinds))
                      if marks[i + 1] - marks[i] > 1e-6]
    _finish_top_chain(lay, xs)
    lay.right_spans = [(0.0, 2.0 * overlap), (2.0 * overlap, 3.0 * overlap)]
    lay.bottom_spans = [(0.0, width)]
    return lay


def build_butt_layout(width, rows, cols, pitch, gauge, edge, end, bolt_dia):
    """
    Butt joint, default plan view.

    CAD: cover length C = 2*(2*end + (n_y-1)*pitch); each main plate is
    1.25*C long and butts at the centre of the cover; the same bolt grid is
    mirrored on both sides of the joint line (full n_x * n_y grid per side).
    Plate 2 is at the top, plate 1 at the bottom.
    """
    width = _num(width)
    n_x, n_y = _count(rows), _count(cols)        # across width / along length
    pitch, end = _num(pitch), _num(end)
    xs, gauge, edge = _gauge_positions(width, n_x, _num(gauge), _num(edge))

    cover = 2.0 * (2.0 * end + (n_y - 1) * pitch)
    plate = _BUTT_PLATE_TO_COVER * cover
    visible = plate - cover / 2.0                # main plate visible beside cover (0.75*C)
    joint = visible + cover / 2.0                # joint line = centre of the cover

    lay = JointLayout()
    lay.kind = "butt"
    lay.width = width
    lay.length = 2.0 * visible + cover
    lay.rects = [
        (0.0, visible, COLOR_WHITE, "Plate 2"),
        (visible, visible + cover, COLOR_COVER, "Cover Plate"),
        (visible + cover, lay.length, COLOR_BEIGE, "Plate 1"),
    ]
    lay.head_radius = 0.5 * _num(bolt_dia)          # CAD: head radius = d / 2

    for j in range(n_y):
        off = end + j * pitch
        for x in xs:
            lay.bolts.append((x, joint - off))      # plate 2 side (above the joint)
            lay.bolts.append((x, joint + off))      # plate 1 side (below the joint)

    upper = [joint - end - j * pitch for j in range(n_y - 1, -1, -1)]
    lower = [joint + end + j * pitch for j in range(n_y)]
    marks = [visible] + upper + [joint] + lower + [visible + cover]
    kinds = (["end"] + ["pitch"] * (n_y - 1) + ["end"]) * 2
    lay.left_chain = [(marks[i], marks[i + 1], kinds[i]) for i in range(len(kinds))
                      if marks[i + 1] - marks[i] > 1e-6]
    _finish_top_chain(lay, xs)
    lay.right_spans = [(0.0, visible), (visible, visible + cover),
                       (visible + cover, lay.length)]
    lay.bottom_spans = [(0.0, width)]
    return lay


# --------------------------------------------------------------------------
# Canvas
# --------------------------------------------------------------------------
class _SpacingCanvas(QWidget):
    """Draws a JointLayout scaled to fit the widget (dimension text stays a
    constant, large, readable size)."""

    FONT_PT = 14.0          # dimension text size

    def __init__(self, model, is_light=True, parent=None):
        super().__init__(parent)
        self.model = model
        self.is_light = is_light
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        font = QFont(self.font())
        font.setPointSizeF(self.FONT_PT)
        self._font = font
        fm = QFontMetrics(font)
        th = fm.height()
        self._text_h = th
        self._arrow = max(7.0, th * 0.42)
        # widest label that can appear beside a vertical dimension
        # (a plain number or a grouped one such as "12 x 100")
        tw = max(fm.horizontalAdvance("0000.0"), fm.horizontalAdvance("00 \u00d7 000"))
        self._gap = th + 12                       # plate -> dimension line
        # margins (px) around the plate that hold the dimension lines + text
        self.m_left = int(self._gap + 6 + tw + 10)
        self.m_right = int(self._gap + 6 + tw + 10)
        self.m_top = int(self._gap + 2 * th + 12)
        self.m_bottom = int(self._gap + 16)
        # room for the labels of the longest vertical chain, even when they are all crowded
        labels = max(self._collapsed_count(model.left_chain), len(model.right_spans))
        min_draw_h = max(220, labels * (th + 2) + 12)
        self.setMinimumSize(QSize(self.m_left + self.m_right + 200,
                                  self.m_top + self.m_bottom + int(min_draw_h)))

    @staticmethod
    def _collapsed_count(chain):
        """Number of labels a chain needs once equal pitch/gauge runs are grouped."""
        n, prev = 0, None
        for a, b, kind in chain:
            key = (kind, round(b - a, 1))
            if kind in ("pitch", "gauge") and key == prev:
                continue
            n += 1
            prev = key
        return n

    # -- sizing ------------------------------------------------------------
    def preferred_size(self, max_draw_w=420.0, max_draw_h=460.0, min_draw_w=110.0,
                       hard_max_h=560.0):
        """Canvas size that gives the drawing a natural aspect (never a thin
        sliver, never huge)."""
        m = self.model
        s = min(max_draw_w / m.width, max_draw_h / m.length)
        s_thin = min(min_draw_w / m.width, hard_max_h / m.length)
        s = max(s, s_thin)
        return QSize(int(m.width * s) + self.m_left + self.m_right,
                     int(m.length * s) + self.m_top + self.m_bottom)

    def sizeHint(self):
        return self.preferred_size()

    # -- painting ----------------------------------------------------------
    def paintEvent(self, _event):
        m = self.model
        if m.length <= 0 or m.width <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setFont(self._font)
        fm = QFontMetrics(self._font)

        bg = QColor("#ffffff") if self.is_light else QColor("#4A4A4A")
        p.fillRect(self.rect(), bg)
        self._ink = QColor("#000000") if self.is_light else QColor("#e6e6e6")
        self._ext = QColor(self._ink)
        self._ext.setAlpha(120)

        avail_w = max(self.width() - self.m_left - self.m_right, 40)
        avail_h = max(self.height() - self.m_top - self.m_bottom, 40)
        s = min(avail_w / m.width, avail_h / m.length)
        dw, dh = m.width * s, m.length * s
        ox = self.m_left + (avail_w - dw) / 2.0
        oy = self.m_top + (avail_h - dh) / 2.0
        X = lambda x: ox + x * s
        Y = lambda y: oy + y * s
        self._last_xform = (ox, oy, s)           # (kept for the self-test)

        # plates (full-width bands)
        outline = QPen(QColor("#000000"), 1.0)
        for y0, y1, colour, _name in m.rects:
            p.setPen(outline)
            p.setBrush(QBrush(QColor(colour)))
            p.drawRect(QRectF(X(0), Y(y0), dw, (y1 - y0) * s))

        # bolts: circles of the CAD head radius (all the same size)
        radius = max(m.head_radius * s, 3.0)
        p.setPen(QPen(QColor(COLOR_BOLT_EDGE), 1.0))
        p.setBrush(QBrush(QColor(COLOR_BOLT)))
        for bx, by in m.bolts:
            p.drawEllipse(QPointF(X(bx), Y(by)), radius, radius)

        # extension-line anchors, so the dashes start at the bolts
        col_top, row_left = {}, {}
        for bx, by in m.bolts:
            kx, ky = round(bx, 3), round(by, 3)
            col_top[kx] = min(col_top.get(kx, by), by)       # top-most bolt in a column
            row_left[ky] = min(row_left.get(ky, bx), bx)     # left-most bolt in a row

        gap = self._gap

        # across the width (edge / gauge), above the plate
        top_y = oy - gap
        segs = [(X(a), X(b), b - a, k) for a, b, k in m.top_chain]
        anchors = {}
        for a, b, _k in m.top_chain:
            for pos in (a, b):
                anchors[round(X(pos), 1)] = Y(col_top.get(round(pos, 3), 0.0))
        self._hchain(p, fm, segs, top_y, anchors, up=True, max_tier=1, plate_edge_y=oy)

        # overall width, below the plate
        bot_y = oy + dh + gap
        self._hchain(p, fm, [(X(0), X(m.width), m.width, "overall")], bot_y, {},
                     up=False, max_tier=0, plate_edge_y=oy + dh)

        # along the length (end / pitch), left of the plate
        left_x = ox - gap
        vsegs = [(Y(a), Y(b), b - a, k) for a, b, k in m.left_chain]
        amap = {}
        for a, b, _k in m.left_chain:
            for pos in (a, b):
                amap[round(Y(pos), 1)] = X(row_left.get(round(pos, 3), 0.0))
        y_lo, y_hi = fm.height() / 2.0 + 3, self.height() - fm.height() / 2.0 - 3
        self._vchain(p, fm, vsegs, left_x, amap, side=-1, default_x=ox, y_lo=y_lo, y_hi=y_hi)

        # plate / cover lengths, right of the plate
        right_x = ox + dw + gap
        rsegs = [(Y(a), Y(b), b - a, "span") for a, b in m.right_spans]
        self._vchain(p, fm, rsegs, right_x, {}, side=+1, default_x=ox + dw, y_lo=y_lo, y_hi=y_hi)
        p.end()

    # -- dimension helpers -------------------------------------------------
    def _arrow_head(self, p, tip, direction):
        """Filled arrow head with the tip at ``tip`` pointing along
        ``direction`` (unit vector)."""
        size = self._arrow
        dx, dy = direction
        bx, by = tip.x() - dx * size, tip.y() - dy * size
        nx, ny = -dy, dx
        poly = QPolygonF([tip, QPointF(bx + nx * size / 3, by + ny * size / 3),
                          QPointF(bx - nx * size / 3, by - ny * size / 3)])
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self._ink))
        p.drawPolygon(poly)

    def _dim_line(self, p, a, b):
        """Dimension line from a to b (QPointF) with arrows at both ends;
        arrows go outside when the segment is too short."""
        length = math.hypot(b.x() - a.x(), b.y() - a.y())
        if length < 1e-6:
            return
        d = ((b.x() - a.x()) / length, (b.y() - a.y()) / length)
        p.setPen(QPen(self._ink, 1.0))
        if length >= 2 * self._arrow + 4:
            p.drawLine(a, b)
            self._arrow_head(p, a, (-d[0], -d[1]))
            self._arrow_head(p, b, d)
        else:
            ext = self._arrow + 3.0
            p.drawLine(QPointF(a.x() - d[0] * ext, a.y() - d[1] * ext),
                       QPointF(b.x() + d[0] * ext, b.y() + d[1] * ext))
            self._arrow_head(p, a, d)
            self._arrow_head(p, b, (-d[0], -d[1]))

    @staticmethod
    def _merge(segs, fm, vertical):
        """Collapse runs of equal pitch/gauge that are too tight to label
        individually into a single 'n x value' dimension."""
        out, i, n = [], 0, len(segs)
        while i < n:
            a, b, val, kind = segs[i]
            j = i
            if kind in ("pitch", "gauge"):
                while j + 1 < n and segs[j + 1][3] == kind and abs(segs[j + 1][2] - val) < 0.05:
                    j += 1
            count = j - i + 1
            if count > 1:
                text = _fmt(val)
                need = (fm.height() + 2) if vertical else (fm.horizontalAdvance(text) + 8)
                if abs(b - a) < need:
                    out.append((a, segs[j][1], f"{count} \u00d7 {_fmt(val)}"))
                    i = j + 1
                    continue
            out.append((a, b, _fmt(val)))
            i += 1
        return out

    def _hchain(self, p, fm, segs, line_y, anchors, up, max_tier, plate_edge_y):
        """Horizontal dimension chain; text sits above the line."""
        items = self._merge(segs, fm, vertical=False)
        th = fm.height()
        p.setPen(QPen(self._ext, 1.0, Qt.DashLine))
        bounds = sorted({round(x, 1) for a, b, _t in items for x in (a, b)})
        for x in bounds:
            if up:
                y0 = anchors.get(x, plate_edge_y)
                p.drawLine(QPointF(x, y0), QPointF(x, line_y - 4))
            else:
                p.drawLine(QPointF(x, plate_edge_y), QPointF(x, line_y + 4))
        placed = {t: [] for t in range(max_tier + 1)}
        for a, b, text in items:
            self._dim_line(p, QPointF(a, line_y), QPointF(b, line_y))
            tw = fm.horizontalAdvance(text)
            cx = (a + b) / 2.0
            chosen = None
            for tier in range(max_tier + 1):
                rect = QRectF(cx - tw / 2.0, line_y - 3 - th - tier * (th + 1), tw, th)
                if any(rect.adjusted(-3, 0, 3, 0).intersects(r) for r in placed[tier]):
                    continue
                chosen = (tier, rect)
                break
            if chosen is None:
                tier = max_tier
                chosen = (tier, QRectF(cx - tw / 2.0, line_y - 3 - th - tier * (th + 1), tw, th))
            tier, rect = chosen
            placed[tier].append(rect)
            if tier > 0:
                p.setPen(QPen(self._ext, 1.0))
                p.drawLine(QPointF(cx, line_y), QPointF(cx, rect.bottom()))
            p.setPen(QPen(self._ink))
            p.drawText(rect, Qt.AlignCenter, text)

    def _vchain(self, p, fm, segs, line_x, anchors, side, default_x, y_lo, y_hi):
        """Vertical dimension chain; text sits beside the line (side -1 = left,
        +1 = right).  Crowded labels are spread apart (centred on their own
        segments, kept between y_lo and y_hi) and joined to the line by a leader."""
        items = self._merge(segs, fm, vertical=True)
        th = fm.height()
        step = th + 2
        p.setPen(QPen(self._ext, 1.0, Qt.DashLine))
        bounds = sorted({round(y, 1) for a, b, _t in items for y in (a, b)})
        for y in bounds:
            x0 = anchors.get(y, default_x)
            p.drawLine(QPointF(x0, y), QPointF(line_x - side * 4, y))

        centres = [(a + b) / 2.0 for a, b, _t in items]
        pos = [min(max(c, y_lo), y_hi) for c in centres]
        for _ in range(80):                      # relax overlaps symmetrically
            moved = False
            for i in range(1, len(pos)):
                d = pos[i] - pos[i - 1]
                if d < step - 0.01:
                    push = (step - d) / 2.0
                    pos[i - 1] -= push
                    pos[i] += push
                    moved = True
            pos = [min(max(v, y_lo), y_hi) for v in pos]
            if not moved:
                break

        for (a, b, text), cy, py in zip(items, centres, pos):
            self._dim_line(p, QPointF(line_x, a), QPointF(line_x, b))
            tw = fm.horizontalAdvance(text)
            edge_x = line_x + side * 5
            left = edge_x - tw if side < 0 else edge_x
            rect = QRectF(left, py - th / 2.0, tw, th)
            if abs(py - cy) > 2.0:
                p.setPen(QPen(self._ext, 1.0))
                near = rect.right() if side < 0 else rect.left()
                p.drawLine(QPointF(line_x, cy), QPointF(near, py))
            p.setPen(QPen(self._ink))
            p.drawText(rect, Qt.AlignCenter, text)


# --------------------------------------------------------------------------
# Dialog
# --------------------------------------------------------------------------
class PlateJointSpacingDialog(QDialog):
    """
    Spacing viewer for Lap Joint (Bolted) and Butt Joint (Bolted).
    Same constructor signature as the other output-detail dialogs, so it can
    be launched through ``OutputDock.run_spacing_script``.
    """

    PANEL_WIDTH = 210

    def __init__(self, connection_obj, rows=0, cols=0, main=None):
        super().__init__()
        app = QApplication.instance()
        self.theme = app.theme_manager
        self.connection = connection_obj
        self.main = main if main is not None else connection_obj
        self.model, self.values = self._read_design(self.main)
        self.initUI()

    # -- data --------------------------------------------------------------
    @staticmethod
    def _read_design(main):
        try:
            is_butt = (main.module_name() == KEY_DISP_BUTTJOINTBOLTED)
        except Exception:
            is_butt = hasattr(main, "platec")

        g = lambda name, default=0.0: getattr(main, name, default)
        width = _num(g("width"))
        rows, cols = _count(g("rows")), _count(g("cols"))
        pitch, gauge = _num(g("final_pitch")), _num(g("final_gauge"))
        edge, end = _num(g("final_edge_dist")), _num(g("final_end_dist"))
        try:
            dia = _num(main.bolt.bolt_diameter_provided)
        except Exception:
            dia = 0.0

        if is_butt:
            model = build_butt_layout(width, rows, cols, pitch, gauge, edge, end, dia)
        else:
            model = build_lap_layout(width, rows, cols, g("number_bolts", 0), pitch,
                                     gauge, edge, end, g("len_conn"), dia)
        # The design values exactly as computed (shown even for a single
        # row / column, where they are the minimum values used for the layout).
        shown = [
            ("Pitch Distance", _fmt(pitch)),
            ("End Distance", _fmt(end)),
            ("Gauge Distance", _fmt(gauge)),
            ("Edge Distance", _fmt(edge if edge > 0 else width / 2.0)),
        ]
        return model, shown

    # -- UI ----------------------------------------------------------------
    def setupWrapper(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setObjectName("spacing_capacity_details")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(0)
        self.title_bar = CustomTitleBar()
        self.title_bar.setTitle("Spacing Details")
        main_layout.addWidget(self.title_bar)
        self.content_widget = QWidget(self)
        main_layout.addWidget(self.content_widget, 1)
        size_grip = QSizeGrip(self)
        size_grip.setFixedSize(16, 16)
        overlay = QHBoxLayout()
        overlay.setContentsMargins(0, 0, 4, 4)
        overlay.addStretch(1)
        overlay.addWidget(size_grip, 0, Qt.AlignBottom | Qt.AlignRight)
        main_layout.addLayout(overlay)

    def initUI(self):
        self.setupWrapper()

        body = QHBoxLayout()
        body.setContentsMargins(10, 10, 10, 6)
        body.setSpacing(10)

        panel = QWidget()
        panel.setFixedWidth(self.PANEL_WIDTH)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        for name, value in self.values:
            row = QHBoxLayout()
            label = QLabel(f"{name} :")
            label.setStyleSheet("font-size: 14px; font-weight: bold;")
            val = QLabel(value)
            val.setStyleSheet("font-size: 14px;")
            row.addWidget(label)
            row.addWidget(val)
            row.addStretch(1)
            panel_layout.addLayout(row)
        note = QLabel("(All Dimensions are in mm)")
        note.setStyleSheet("font-size: 12px; font-style: italic;")
        panel_layout.addWidget(note)
        panel_layout.addStretch(1)

        self.canvas = _SpacingCanvas(self.model, is_light=self.theme.is_light())
        body.addWidget(panel, 0)
        body.addWidget(self.canvas, 1)
        self.content_widget.setLayout(body)

        # Size the window to the drawing (bounded by the screen), centred.
        pref = self.canvas.preferred_size()
        width = pref.width() + self.PANEL_WIDTH + 10 + 20 + 2
        height = pref.height() + 32 + 16 + 6 + 10 + 16 + 2
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            width = min(width, int(geo.width() * 0.9))
            height = min(height, int(geo.height() * 0.9))
            x = geo.x() + (geo.width() - width) // 2
            y = geo.y() + (geo.height() - height) // 2
        else:
            x = y = 100
        self.setGeometry(x, y, int(width), int(height))
        self.setMinimumSize(self.PANEL_WIDTH + self.canvas.minimumWidth() + 40,
                            self.canvas.minimumHeight() + 90)
# <<< END plate_joint_spacing <<<
