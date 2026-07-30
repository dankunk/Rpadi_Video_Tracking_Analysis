# ROI Grabbing Tools

## Introduction

This directory contains the python tools for allowing users to grab regions of interest coordinates from video files.

The `.ipynb` file used here should be run using the uv environment that is contained in the parent directory `../.venv/`.

## Loading the uv venv in the kernel.

When opening the file `ROIgrabbing.ipynb` you should then select the kernel in the VScode GUI using the `Select Kernel` button on the top right of the interactive notebook.

If starting from scratch please see the `Rpadi_Video_Tracking_Analysis/README.md` file in the parent directory/repository relavtive to the current working directory where this file is located (`Rpadi_Video_Tracking_Analysis/ROItools`).

## The function

The current function in the .ipynb essentially prompts the user to choose a file via a file browser. Then the first frame is displayed on the screen and the user is allowed to place bounding boxes over each arena. When each arena has been selected, the user can press `enter` and lock that ROI in or they can re-drag and draw the box if its not looking great. Once they hit enter, the box will be logged on the screen and they will be allowed to select the next box until all 6 boxes are selected. 

Once all 6 boxes are selected, the function will save the coordinates to the `.json` file that matches the video name exactly for preservation purposes.

Additionally, we have written some code that will plot these annotated frames and ROIs to the viewer for the user to visualize and verify. 

Currently, we do not check for overlapping boxes. But we can update our loop when presenting the visualizations to check for any overlaps. If they are there, just run the function again.

To-do:
Add this if needed.
```python
# Run the GUI tool
frame, boxes, base_name = grabROI(max_boxes=6)

# Render the frame and coordinates inline for visual verification
if frame is not None and len(boxes) > 0:
    
    # Automated Overlap Verification Check
    def check_box_overlaps(box_list):
        overlapping_pairs = []
        for i in range(len(box_list)):
            for j in range(i + 1, len(box_list)):
                b1, b2 = box_list[i], box_list[j]
                
                # Check for intersection on both X and Y axes
                intersect_x = (b1["x_min"] < b2["x_max"]) and (b1["x_max"] > b2["x_min"])
                intersect_y = (b1["y_min"] < b2["y_max"]) and (b1["y_max"] > b2["y_min"])
                
                if intersect_x and intersect_y:
                    overlapping_pairs.append((b1["label"], b2["label"]))
        return overlapping_pairs

    overlaps = check_box_overlaps(boxes)
    if overlaps:
        print(f"WARNING: Overlapping boxes detected between: {overlaps}")
    else:
        print("All bounding boxes are mutually exclusive (no overlaps).")

    # Plotting the audit figure
    plt.figure(figsize=(10, 6))
    
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    plt.imshow(frame_rgb)
    
    mpl_colors = ['red', 'green', 'yellow', 'magenta', 'cyan', 'orange']
    
    for box in boxes:
        x1, y1 = box["x_min"], box["y_min"]
        x2, y2 = box["x_max"], box["y_max"]
        label = box["label"]
        
        box_color = mpl_colors[(label - 1) % len(mpl_colors)]
        
        rect = plt.Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, color=box_color, linewidth=2)
        plt.gca().add_patch(rect)
        
        text_color = 'black' if box_color in ['yellow', 'cyan'] else 'white'
        plt.text(
            x1, y1 - 10 if y1 > 20 else y1 + 20, 
            f"Box {label}", 
            color=text_color, 
            fontsize=10, 
            weight='bold',
            bbox=dict(facecolor=box_color, alpha=0.8, edgecolor='none', pad=2)
        )

    plt.title(f"{base_name}: Left-to-Right ROI Order")
    plt.axis("off")
    plt.show()

    display(pd.DataFrame(boxes)[["label", "x_min", "y_min", "x_max", "y_max", "width", "height"]])
```