import gradio as gr
import os
import string

from modules import script_callbacks, shared, util
from modules.ui_components import ResizeHandleRow, InputAccordion, FormColumn, FormRow
from modules.paths_internal import default_output_dir
import modules.infotext_utils as parameters_copypaste

from PIL import Image, ImageEnhance, ImageDraw

def on_ui_settings():
    section = ('saving-paths', "Paths for saving")
    shared.opts.add_option(
        "sd_image_editor_outdir",
        shared.OptionInfo(
            util.truncate_path(os.path.join(default_output_dir, 'sd-image-editor')),
            'Output directory for sd-image-editor',
            component_args=shared.hide_dirs,
            section=('saving-paths', "Paths for saving"),
        )
    )


def draw_bbox(img, crop_enabled, bbox_w, bbox_h, bbox_center_x, bbox_center_y):
    if img is None:
        return None
    if crop_enabled:
        # Calculate coordinates of bbox corners
        w, h = img.size
        left = (bbox_center_x - bbox_w/2)/100 * w 
        upper = (bbox_center_y - bbox_h/2)/100 * h
        right = (bbox_center_x + bbox_w/2)/100 * w
        lower = (bbox_center_y + bbox_h/2)/100 * h
        # Check bounding condition
        left = 0 if left < 0 else left
        upper = 0 if upper < 0 else upper
        right = w if right > w else right
        lower = h if lower > h else lower
        # Draw bounding box
        TINT_COLOR = (0, 0, 0)  # Black
        TRANSPARENCY = .6  # Degree of transparency, 0-100%
        OPACITY = int(255 * TRANSPARENCY)
        OUTLINE_OPACITY = int(255 * TRANSPARENCY * 1)
        BBOX_COLOR = (220, 220, 220)
        # Create a bounding box overlay
        overlay = Image.new('RGBA', img.size, TINT_COLOR+(OPACITY,)) # Shade everything outside bbox
        draw = ImageDraw.Draw(overlay)  # Create a context for drawing things on it
        draw.rectangle(((left, upper), (right, lower)), 
                       fill=(255, 255, 255, 0), 
                       outline=BBOX_COLOR+(OUTLINE_OPACITY,),
                       width=2) # Make bounding box transparent
        # Draw lines separating each side into 3 parts
        third_left = left*1/3 + right*2/3
        third_right = left*2/3 + right*1/3
        third_up = lower*1/3+upper*2/3
        third_down = lower*2/3+upper*1/3
        draw.line([(third_left, upper), (third_left, lower)], fill=BBOX_COLOR+(OUTLINE_OPACITY,), width=1)
        draw.line([(third_right, upper), (third_right, lower)], fill=BBOX_COLOR+(OUTLINE_OPACITY,), width=1)
        draw.line([(left, third_up), (right, third_up)], fill=BBOX_COLOR+(OUTLINE_OPACITY,), width=1)
        draw.line([(left, third_down), (right, third_down)], fill=BBOX_COLOR+(OUTLINE_OPACITY,), width=1)
        # Merge image with bounding box overlay with alpha composite
        img = Image.alpha_composite(img, overlay) 
    return img


def store_image(img):
    return img


def edit(img, degree, expand, flip, crop_enabled, bbox_w, bbox_h, bbox_center_x, bbox_center_y, interpolate_mode, color, contrast, brightness, sharpness):
    if img is None:
        return None
    # Crop
    if crop_enabled:
        # Calculate coordinates of bbox corners
        w, h = img.size
        left = (bbox_center_x - bbox_w/2)/100 * w
        upper = (bbox_center_y - bbox_h/2)/100 * h
        right = (bbox_center_x + bbox_w/2)/100 * w
        lower = (bbox_center_y + bbox_h/2)/100 * h
        img = img.crop((left, upper, right, lower))
    # Flip
    if flip:
        img = img.transpose(method=Image.Transpose.FLIP_LEFT_RIGHT)
    # Rotate
    if interpolate_mode == "Nearest":
        resample_obj = Image.NEAREST
    elif interpolate_mode == "Bilinear":
        resample_obj = Image.BILINEAR
    elif interpolate_mode == "Bicubic":
        resample_obj = Image.BICUBIC
    img = img.rotate(-degree, expand=expand, resample=resample_obj) # Rotate closewise
    # Enhance
    img_enhance = ImageEnhance.Color(img)
    img = img_enhance.enhance(color)
    img_enhance = ImageEnhance.Contrast(img)
    img = img_enhance.enhance(contrast)
    img_enhance = ImageEnhance.Brightness(img)
    img = img_enhance.enhance(brightness)
    img_enhance = ImageEnhance.Sharpness(img)
    img = img_enhance.enhance(sharpness)
    return img


def save_image(img):
    from random import choices
    # Generate filename
    filename = ''.join(choices(string.ascii_letters + string.digits, k=12)) + ".png"
    # Construct path to save
    os.makedirs(shared.opts.sd_image_editor_outdir, exist_ok=True)
    # Save
    img.save(os.path.join(shared.opts.sd_image_editor_outdir, filename), format="PNG")
    return


def open_folder():
    # adopted from https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/20123d427b09901396133643be78f6b692393b0c/modules/util.py#L176-L208
    """Open a folder in the file manager of the respect OS."""
    import platform
    import sys
    import subprocess
    path = shared.opts.sd_image_editor_outdir
    if not os.path.exists(path):
        msg = f'Folder "{path}" does not exist. after you save an image, the folder will be created.'
        print(msg)
        gr.Info(msg)
        return
    elif not os.path.isdir(path):
        msg = f"""
            WARNING
            An open_folder request was made with an path that is not a folder.
            This could be an error or a malicious attempt to run code on your computer.
            Requested path was: {path}
            """
        print(msg, file=sys.stderr)
        gr.Warning(msg)
        return

    path = os.path.normpath(path)
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    elif "microsoft-standard-WSL2" in platform.uname().release:
        subprocess.Popen(["wsl-open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def on_ui_tabs():
    with gr.Blocks(analytics_enabled=False) as image_editor_interface:
        with ResizeHandleRow():
            with gr.Column():
                input_img = gr.Image(label="Image for editing", 
                                     elem_id="image_editing", 
                                     show_label=False, 
                                     source="upload", 
                                     interactive=True, 
                                     type="pil", 
                                     tool=None,
                                     image_mode="RGBA",
                                     height=500)
                init_img = gr.Image(label="Unedited image", 
                                    elem_id="original_image",
                                    height=500, 
                                    type="pil",
                                    image_mode="RGBA",
                                    interactive=False,
                                    visible=False)
                with gr.TabItem('Transform', id='transform', elem_id="transform_tab") as tab_transform:
                    with gr.Row():
                        rotate_slider = gr.Slider(
                            minimum=-180,
                            maximum=180,
                            step=1,
                            value=0,
                            label="Rotate"
                        )
                        rotate_expand_option = gr.Checkbox(
                            True,
                            label="Expand to fit"
                        )
                        flip_option = gr.Checkbox(
                            False,
                            label="Flip image"
                        )
                    with gr.Row():
                        with InputAccordion(False, label="Crop") as crop_enabled:
                            with gr.Row():
                                with gr.Column(variant="panel"):
                                    gr.HTML(value="Bounding box dimension (%)")
                                    bbox_w = gr.Slider(
                                        minimum=0,
                                        maximum=100,
                                        step=0.1,
                                        value=100,
                                        label="Width"
                                    )
                                    bbox_h = gr.Slider(
                                        minimum=0,
                                        maximum=100,
                                        step=0.1,
                                        value=100,
                                        label="height"
                                    )
                                with gr.Column(variant="panel"):
                                    gr.HTML(value="Bounding box center (%)")
                                    bbox_center_x = gr.Slider(
                                        minimum=0,
                                        maximum=100,
                                        step=0.1,
                                        value=50,
                                        label="Horizontal (left to right)"
                                    )
                                    bbox_center_y = gr.Slider(
                                        minimum=0,
                                        maximum=100,
                                        step=0.1,
                                        value=50,
                                        label="Vertical (up to down)"
                                    )
                    with gr.Row():
                        with gr.Accordion(label="Advanced", open=False):
                            interpolation_options = gr.Radio(
                                ["Nearest", "Bilinear", "Bicubic"],
                                value="Bicubic",
                                label="Interpolation mode",
                                info="in increasing order of quality (with performance cost)"
                            )
                        
                with gr.TabItem('Enhance', id='enhance', elem_id="enhance_tab") as tab_adjust:
                    with gr.Row():
                        color_slider = gr.Slider(
                            minimum=0,
                            maximum=2,
                            step=0.05,
                            value=1,
                            label="Color balance"
                        )
                    with gr.Row():
                        contrast_slider = gr.Slider(
                            minimum=0,
                            maximum=2,
                            step=0.05,
                            value=1,
                            label="Contrast"
                        )
                    with gr.Row():
                        brightness_slider = gr.Slider(
                            minimum=0,
                            maximum=4,
                            step=0.05,
                            value=1,
                            label="Brightness"
                        )
                    with gr.Row():
                        sharpness_slider = gr.Slider(
                            minimum=-2,
                            maximum=4,
                            step=0.1,
                            value=1,
                            label="Sharpness"
                        )
                        
            with gr.Column():
                output_img = gr.Image(label="Output image",
                                      height=500,
                                      type="pil",
                                      image_mode="RGBA",
                                      interactive=False)
                with gr.Row():
                    render_button = gr.Button(value="Render")
                with gr.Row():
                    save_button = gr.Button(value="Save to output folder",
                                            variant="primary",
                                            scale=4)
                    folder_symbol = '\U0001f4c2'  # 📂
                    open_folder_button = gr.Button(value=folder_symbol, scale=1)
                
                with gr.Row():
                    buttons = parameters_copypaste.create_buttons(["img2img", "inpaint", "extras"])
                    for tabname, button in buttons.items():
                        parameters_copypaste.register_paste_params_button(parameters_copypaste.ParamBinding(
                            paste_button=button, tabname=tabname, source_image_component=output_img,
                        ))
            
            # Event listeners for all editing options
            control_inputs = \
                [rotate_slider, rotate_expand_option, flip_option, crop_enabled, bbox_w, bbox_h, bbox_center_x, bbox_center_y, interpolation_options, \
                color_slider, contrast_slider, brightness_slider, sharpness_slider]
            bbox_inputs = [crop_enabled, bbox_w, bbox_h, bbox_center_x, bbox_center_y]
            # I/O
            input_img.upload(store_image, inputs=[input_img], outputs=[init_img]) # Store persistent copy of the initial uploaded image in init_img
            input_img.clear(store_image, inputs=[input_img], outputs=[init_img])
            
            init_img.change(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            render_button.click(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            save_button.click(save_image, inputs=[output_img], outputs=[])
            open_folder_button.click(open_folder, inputs=[], outputs=[])
            # Tranform tab
            rotate_slider.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            rotate_expand_option.select(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            flip_option.select(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            crop_enabled.select(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            bbox_w.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            bbox_h.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            bbox_center_x.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            bbox_center_y.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            interpolation_options.input(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            # Draw bounding box
            init_img.change(draw_bbox, inputs=[init_img, *bbox_inputs], outputs=[input_img])
            crop_enabled.select(draw_bbox, inputs=[init_img, *bbox_inputs], outputs=[input_img])
            bbox_w.release(draw_bbox, inputs=[init_img, *bbox_inputs], outputs=[input_img])
            bbox_h.release(draw_bbox, inputs=[init_img, *bbox_inputs], outputs=[input_img])
            bbox_center_x.release(draw_bbox, inputs=[init_img, *bbox_inputs], outputs=[input_img])
            bbox_center_y.release(draw_bbox, inputs=[init_img, *bbox_inputs], outputs=[input_img])
            # Enhance tab
            color_slider.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            contrast_slider.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            brightness_slider.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            sharpness_slider.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
        
    return [(image_editor_interface, "Image Editor", "image_editor_tab")]

      
script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_settings(on_ui_settings)
