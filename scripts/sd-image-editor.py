import gradio as gr
import os
import string

from modules import script_callbacks
from modules.ui_components import ResizeHandleRow
from modules import shared
from modules.shared import opts, cmd_opts
import modules.infotext_utils as parameters_copypaste

from PIL import Image, ImageEnhance, ImageFilter, ImageTransform

save_path = os.path.join("output", "img2img-images", "sd-image-editor")

def edit(img, degree, expand, flip, interpolate_mode, color, contrast, brightness, sharpness):
    if img is None:
        return None
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
    os.makedirs(save_path, exist_ok=True)
    # Save
    img.save(os.path.join(save_path, filename), format="PNG")
    return

def open_folder():
    os.makedirs(save_path, exist_ok=True)
    os.startfile(save_path)
    return

def on_ui_tabs():
    with gr.Blocks(analytics_enabled=False) as image_editor_interface:
        with ResizeHandleRow():
            with gr.Column():
                init_img = gr.Image(label="Image for editing", 
                                    elem_id="image_editing", 
                                    show_label=False, 
                                    source="upload", 
                                    interactive=True, 
                                    type="pil", 
                                    tool="editor", 
                                    image_mode="RGBA",
                                    height=500)

                with gr.TabItem('Transform', id='transform', elem_id="transform_tab") as tab_transform:
                    with gr.Row():
                        rotate_slider = gr.Slider(
                            minimum=-180,
                            maximum=180,
                            step=5,
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
                        with gr.Accordion(label="Advanced", open=False):
                            interpolation_options = gr.Radio(
                                ["Nearest", "Bilinear", "Bicubic"],
                                value="Bicubic",
                                label="Interpolation mode",
                                info="in increasing order of quality (with performance cost)"
                            )
                        
                with gr.TabItem('Adjust', id='adjust', elem_id="adjust_tab") as tab_adjust:
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
                                      interactive=False)
                with gr.Row():
                    render_button = gr.Button(value="Render")
                with gr.Row():
                    save_button = gr.Button(value="Save to img2img",
                                            variant="primary",
                                            scale=4)
                    if os.name == "nt":
                        folder_symbol = '\U0001f4c2'  # 📂
                        open_folder_button = gr.Button(value=folder_symbol,
                                                       scale=1)
                
                with gr.Row():
                    buttons = parameters_copypaste.create_buttons(["img2img", "inpaint", "extras"])
                for tabname, button in buttons.items():
                    parameters_copypaste.register_paste_params_button(parameters_copypaste.ParamBinding(
                        paste_button=button, tabname=tabname, source_image_component=output_img,
                    ))


            control_inputs = [rotate_slider, rotate_expand_option, flip_option, interpolation_options, color_slider,\
                contrast_slider, brightness_slider, sharpness_slider]
            
            # Event listeners for all editing options
            
            init_img.upload(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            render_button.click(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            save_button.click(save_image, inputs=[output_img], outputs=[])
            open_folder_button.click(open_folder, inputs=[], outputs=[])
            
            rotate_slider.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            rotate_expand_option.select(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            flip_option.select(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            interpolation_options.select(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            color_slider.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            contrast_slider.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            brightness_slider.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            sharpness_slider.release(edit, inputs=[init_img, *control_inputs], outputs=[output_img])
            
    return [(image_editor_interface, "Image Editor", "image_editor_tab")]

      
script_callbacks.on_ui_tabs(on_ui_tabs)