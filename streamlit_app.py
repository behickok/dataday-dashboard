import streamlit as st
from PIL import Image
import fitz  # PyMuPDF, also known as MuPDF
import io
import pandas as pd
import json
from streamlit_drawable_canvas import st_canvas

def load_page_as_image(document, page_number):
    """ Load a PDF page as a PIL Image. """
    if 0 <= page_number < document.page_count:
        page = document.load_page(page_number)
        pix = page.get_pixmap()
        img_data = pix.tobytes("png")  # Convert to PNG bytes
        image = Image.open(io.BytesIO(img_data))
        return image
    return None

# Initialize session state for columns and rows
if 'columns' not in st.session_state:
    st.session_state.columns = pd.DataFrame()
if 'rows' not in st.session_state:
    st.session_state.rows = pd.DataFrame()
if 'boxes' not in st.session_state:
    st.session_state.boxes = []

st.title("PDF Annotation App")
box_type = st.sidebar.radio("Box Type", ["column", "row"])
# Sidebar options
drawing_mode = st.sidebar.radio("Drawing tool:", ("rect", "transform"))
stroke_color = "#000000"
bg_color = "#FFFFFF"
realtime_update = True  # Set to True to see updates on drawing
stroke_width = 1

uploaded_file = st.sidebar.file_uploader("Choose a file", type="pdf")
if uploaded_file is not None:
    document = fitz.open(stream=uploaded_file.read())
    
    page_num_label = f'Go to page (1-{document.page_count})'
    if 'page_num' not in st.session_state:
        st.session_state.page_num = 0
    st.session_state.page_num = st.sidebar.number_input(page_num_label, min_value=1, max_value=document.page_count, value=st.session_state.page_num + 1, step=1) - 1
    
    bg_image = load_page_as_image(document, st.session_state.page_num)
    
    if bg_image is not None:
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",  # Fixed fill color with some opacity
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            background_color=bg_color,
            background_image=bg_image,
            update_streamlit=realtime_update,
            height=bg_image.height,
            width=bg_image.width,
            drawing_mode=drawing_mode,
            key="canvas",
        )
        
        if canvas_result.json_data is not None and "objects" in canvas_result.json_data:
            if st.button("Save Annotations"):
                # Extract annotation data
                annotations = canvas_result.json_data["objects"]
                # Convert to DataFrame
                annotations_df = pd.DataFrame(annotations)
                for col in annotations_df.select_dtypes(include=['object']):
                    annotations_df[col] = annotations_df[col].astype("str")
                
                # Save annotations based on box_type
                if box_type == "column":
                    st.session_state.columns = annotations_df
                elif box_type == "row":
                    st.session_state.rows = annotations_df
                
                # Display the appropriate DataFrame
            st.write("Column Annotations:")
            st.dataframe(st.session_state.columns)
            st.write("Row Annotations:")
            st.dataframe(st.session_state.rows)
    else:
        st.error("Page not available.")

# Calculate bounding box intersections
def calculate_intersections(columns_df, rows_df, current_page):
    intersections = {
        "page": current_page,
        "values": []
    }
    for _, row in rows_df.iterrows():
        row_intersections = []
        for _, col in columns_df.iterrows():
            x1 = max(col['left'], row['left'])
            y1 = max(col['top'], row['top'])
            x2 = min(col['left'] + col['width'], row['left'] + row['width'])
            y2 = min(col['top'] + col['height'], row['top'] + row['height'])
            
            if x1 < x2 and y1 < y2:
                bbox = f"({x1},{y1},{x2-x1},{y2-y1})"
                row_intersections.append(bbox)
            else:
                row_intersections.append("")
        intersections["values"].append(row_intersections)
    return intersections

# Button to create boxes
if st.button("Create Boxes"):
    if not st.session_state.columns.empty and not st.session_state.rows.empty:
        st.session_state.boxes.append(calculate_intersections(st.session_state.columns, st.session_state.rows, st.session_state.page_num + 1))
        st.write("Bounding Box Intersections (JSON):")
        st.json(st.session_state.boxes)
    else:
        st.error("Please save both column and row annotations before creating boxes.")

# Button to clear annotations
if st.button("Clear Annotations"):
    st.session_state.columns = pd.DataFrame()
    st.session_state.rows = pd.DataFrame()
    st.success("Annotations cleared.")
