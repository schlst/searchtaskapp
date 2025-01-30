import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
import json
import tkinter.font as tkFont
import platform
import csv
import time
import random
import math

###################################
# Global references
###################################
run_btn = None
distr_auto_enabled = True  # for auto distribution of leftover items among distractors

# We'll store the ID of any pending 'after' call for debounce
debounce_id = None
DEBOUNCE_DELAY_MS = 300

root = tk.Tk()
root.title("RP-CNBI Search Task")
# reduce height by ~10%; originally 900 -> 810
root.geometry("1400x810")

main_container = ttk.Frame(root)
main_container.grid(row=0, column=0, sticky="nsew")

root.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=1)

canvas = tk.Canvas(main_container)
canvas.grid(row=0, column=0, sticky="nsew")

scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
scrollbar.grid(row=0, column=1, sticky="ns")

canvas.configure(yscrollcommand=scrollbar.set)
main_container.rowconfigure(0, weight=1)
main_container.columnconfigure(0, weight=1)

content_frame = ttk.Frame(canvas)
canvas.create_window((0, 0), window=content_frame, anchor="nw")

def on_configure(event):
    canvas.config(scrollregion=canvas.bbox("all"))

content_frame.bind("<Configure>", on_configure)

def _on_mousewheel(event):
    # Adjust for different platforms
    if platform.system() == 'Windows':
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    else:
        canvas.yview_scroll(int(-1*event.delta), "units")

content_frame.bind_all("<MouseWheel>", _on_mousewheel)

###################################
# Debounce logic
###################################
def schedule_debounced_update():
    """
    Schedules the preview update to happen after DEBOUNCE_DELAY_MS,
    canceling any already-scheduled update if the user keeps typing.
    """
    global debounce_id
    if debounce_id is not None:
        root.after_cancel(debounce_id)
    debounce_id = root.after(DEBOUNCE_DELAY_MS, do_debounced_update)

def do_debounced_update():
    """
    Actually calls update_preview_canvas() + check_sums_and_required
    after the user stops typing for DEBOUNCE_DELAY_MS.
    """
    global debounce_id
    debounce_id = None
    # Safeguard: if the preview canvas no longer exists, skip.
    if not preview_canvas or not preview_canvas.winfo_exists():
        return
    update_preview_canvas()

###################################
# Two columns: left=Settings, right=Preview
###################################
left_frame = ttk.Frame(content_frame, padding=10)
left_frame.grid(row=0, column=0, sticky="nsew")

right_frame = ttk.Frame(content_frame, padding=10)
right_frame.grid(row=0, column=1, sticky="nsew")

content_frame.columnconfigure(0, weight=1)
content_frame.columnconfigure(1, weight=1)
content_frame.rowconfigure(0, weight=1)

FONT_OPTIONS = ["Arial", "Times New Roman", "Rockwell", "Verdana", "Helvetica"]

# For Targets
target_symbol_vars = []
font_var_vars = []
text_size_vars = []
bold_vars = []
underline_vars = []
italic_vars = []
text_color_vars = []
target_quantity_vars = []

# For Distractors
distractor_symbol_vars = []
distractor_font_var_vars = []
distractor_text_size_vars = []
distractor_bold_vars = []
distractor_underline_vars = []
distractor_italic_vars = []
distractor_text_color_vars = []
distractor_quantity_vars = []

screen_size_options = ["same as computer", "3:2, 2880 x 1920", "16:9, 1920 x 1080"]
refresh_rate_options = ["same as computer", "120Hz", "144Hz"]

PREVIEW_DEFAULT_WIDTH = 450
PREVIEW_DEFAULT_HEIGHT = 300

MAX_TARGET_ROWS = 25
MAX_DISTRACTOR_ROWS = 25

###################################
# Safe parse from IntVar / StringVar
###################################
def safe_get_int(var: tk.IntVar, default=0):
    try:
        return var.get()
    except tk.TclError:
        return default

def safe_get_int_from_stringvar(var: tk.StringVar, default=0):
    val = var.get().strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default

###################################
# Build Font & Preview
###################################
def build_font(family, size, bold, italic, underline):
    weight = "bold" if bold else "normal"
    slant = "italic" if italic else "roman"
    ft = tkFont.Font(family=family, size=size, weight=weight, slant=slant)
    ft.configure(underline=1 if underline else 0)
    return ft

def update_preview_canvas():
    preview_canvas.delete("all")
    y_pos = PREVIEW_DEFAULT_HEIGHT // 2

    # measure total width to size the canvas properly
    total_width = 0
    # targets
    for i in range(len(target_symbol_vars)):
        sym = target_symbol_vars[i].get()
        if sym:
            sz = safe_get_int(text_size_vars[i], 18)
            total_width += sz + 10
    # distractors
    for i in range(len(distractor_symbol_vars)):
        sym = distractor_symbol_vars[i].get()
        if sym:
            sz = safe_get_int(distractor_text_size_vars[i], 18)
            total_width += sz + 10

    new_width = max(total_width + 20, PREVIEW_DEFAULT_WIDTH)
    preview_canvas.config(width=new_width)
    x_mid = new_width // 2

    # measure total width of targets alone
    t_width = 0
    for i in range(len(target_symbol_vars)):
        sym = target_symbol_vars[i].get()
        if sym:
            s = safe_get_int(text_size_vars[i], 18)
            t_width += s + 10

    # measure total width of distractors alone
    d_width = 0
    for i in range(len(distractor_symbol_vars)):
        sym = distractor_symbol_vars[i].get()
        if sym:
            s = safe_get_int(distractor_text_size_vars[i], 18)
            d_width += s + 10

    x_targets_start = x_mid - 50 - t_width
    if x_targets_start < 10:
        x_targets_start = 10
    x_t = x_targets_start
    x_d = x_mid + 50

    def draw_symbol(x, y, sym, family, sz, color, b, it, un):
        ft = build_font(family, sz, b, it, un)
        preview_canvas.create_text(x, y, text=sym, font=ft, fill=color, anchor="n")

    # draw targets (side-by-side)
    for i in range(len(target_symbol_vars)):
        sym = target_symbol_vars[i].get()
        if sym:
            family = font_var_vars[i].get()
            sz = safe_get_int(text_size_vars[i], 18)
            color = text_color_vars[i].get()
            b = bold_vars[i].get()
            it = italic_vars[i].get()
            un = underline_vars[i].get()
            draw_symbol(x_t, y_pos, sym, family, sz, color, b, it, un)
            x_t += sz + 10

    # draw distractors (side-by-side)
    for i in range(len(distractor_symbol_vars)):
        sym = distractor_symbol_vars[i].get()
        if sym:
            family = distractor_font_var_vars[i].get()
            sz = safe_get_int(distractor_text_size_vars[i], 18)
            color = distractor_text_color_vars[i].get()
            b = distractor_bold_vars[i].get()
            it = distractor_italic_vars[i].get()
            un = distractor_underline_vars[i].get()
            draw_symbol(x_d, y_pos, sym, family, sz, color, b, it, un)
            x_d += sz + 10

    check_sums_and_required()

###################################
# Auto distribution
###################################
def auto_distribute_distractors():
    if not distr_auto_enabled:
        return
    total_val = safe_get_int_from_stringvar(total_items_var, 0)
    if total_val <= 0:
        return
    t_sum = sum(v.get() for v in target_quantity_vars)
    leftover = total_val - t_sum
    if leftover < 0:
        return
    rowcount = len(distractor_quantity_vars)
    if rowcount == 0:
        return
    base_val = leftover // rowcount
    remainder = leftover % rowcount
    for i in range(rowcount):
        newVal = base_val + 1 if i < remainder else base_val
        distractor_quantity_vars[i].set(newVal)

###################################
# Sum & Required Check
###################################
def check_sums_and_required(*args):
    auto_distribute_distractors()
    t_sum = sum(v.get() for v in target_quantity_vars)
    d_sum = sum(v.get() for v in distractor_quantity_vars)
    total_val = safe_get_int_from_stringvar(total_items_var, 0)

    sum_ok = (t_sum + d_sum == total_val) and (total_val > 0)
    if sum_ok:
        sum_status_label.config(text="OK", foreground="green")
    else:
        if total_val == 0:
            sum_status_label.config(text="", foreground="black")
        else:
            sum_status_label.config(text="Mismatch", foreground="red")

    # Check required fields
    all_req_filled = (
        study_id_entry.get().strip() and
        session_entry.get().strip() and
        admin_entry.get().strip()
    )
    if all_req_filled and sum_ok:
        run_btn.state(["!disabled"])
    else:
        run_btn.state(["disabled"])

###################################
# Color logic
###################################
def choose_preview_background_color():
    chosen = colorchooser.askcolor(title="Choose background color")[1]
    if chosen:
        preview_canvas.configure(bg=chosen)

def choose_color(idx, section):
    chosen = colorchooser.askcolor(title="Choose text color")[1]
    if chosen:
        if section == "targets":
            text_color_vars[idx].set(chosen)
        else:
            distractor_text_color_vars[idx].set(chosen)
    schedule_debounced_update()

###################################
# LEFT COLUMN WIDGETS
###################################
rpcnbi_title = ttk.Label(left_frame, text="RP-CNBI Search Task", font=("Arial", 16))
rpcnbi_title.grid(row=0, column=0, pady=10, sticky="w")

setup_label = ttk.Label(left_frame, text="Set up", font=("Arial", 14))
setup_label.grid(row=1, column=0, sticky="w", pady=5)

study_id_label = ttk.Label(left_frame, text="Study ID:* ")
study_id_label.grid(row=2, column=0, sticky="w")
study_id_entry = ttk.Entry(left_frame, width=20)
study_id_entry.grid(row=2, column=1, sticky="w", padx=5)
study_id_entry.bind("<KeyRelease>", lambda e: schedule_debounced_update())

session_label = ttk.Label(left_frame, text="Session #:* ")
session_label.grid(row=3, column=0, sticky="w", pady=(5,0))
session_entry = ttk.Entry(left_frame, width=20)
session_entry.grid(row=3, column=1, sticky="w", padx=5)
session_entry.bind("<KeyRelease>", lambda e: schedule_debounced_update())

admin_label = ttk.Label(left_frame, text="Administrator:* ")
admin_label.grid(row=4, column=0, sticky="w", pady=(5,0))
admin_entry = ttk.Entry(left_frame, width=20)
admin_entry.grid(row=4, column=1, sticky="w", padx=5)
admin_entry.bind("<KeyRelease>", lambda e: schedule_debounced_update())

advanced_button = ttk.Button(left_frame, text="Advanced Settings")
advanced_button.grid(row=5, column=0, pady=5, sticky="w")

advanced_settings_frame = ttk.Frame(left_frame, padding=10)
advanced_settings_frame.grid(row=6, column=0, columnspan=2, sticky="ew")
advanced_settings_frame.grid_remove()

screen_size_var = tk.StringVar(value="same as computer")
refresh_rate_var = tk.StringVar(value="same as computer")
input_type_var = tk.StringVar(value="Mouse")

screen_size_label = ttk.Label(advanced_settings_frame, text="Screen Size:")
screen_size_label.grid(row=0, column=0, sticky="w")
screen_size_dropdown = ttk.Combobox(
    advanced_settings_frame,
    textvariable=screen_size_var,
    values=screen_size_options,
    state="readonly"
)
screen_size_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")

refresh_rate_label = ttk.Label(advanced_settings_frame, text="Refresh Rate:")
refresh_rate_label.grid(row=1, column=0, sticky="w")
refresh_rate_dropdown = ttk.Combobox(
    advanced_settings_frame,
    textvariable=refresh_rate_var,
    values=refresh_rate_options,
    state="readonly"
)
refresh_rate_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")

input_type_label = ttk.Label(advanced_settings_frame, text="Input Type:")
input_type_label.grid(row=2, column=0, sticky="w")
touch_radio = ttk.Radiobutton(advanced_settings_frame, text="Touch", variable=input_type_var, value="Touch")
touch_radio.grid(row=2, column=1, sticky="w")
mouse_radio = ttk.Radiobutton(advanced_settings_frame, text="Mouse", variable=input_type_var, value="Mouse")
mouse_radio.grid(row=2, column=2, sticky="w")

def toggle_advanced_settings():
    if advanced_settings_frame.winfo_viewable():
        advanced_settings_frame.grid_remove()
    else:
        advanced_settings_frame.grid()

advanced_button.config(command=toggle_advanced_settings)

trial_settings_label = ttk.Label(left_frame, text="Trial Settings", font=("Arial", 14))
trial_settings_label.grid(row=7, column=0, sticky="w", pady=10)

total_items_var = tk.StringVar(value="")
def total_items_spin_event(*args):
    schedule_debounced_update()

num_items_lbl = ttk.Label(left_frame, text="Number of items total:", font=("Arial", 12, "bold"))
num_items_lbl.grid(row=8, column=0, sticky="w", pady=(5,2))

total_items_spin = tk.Spinbox(left_frame, from_=1, to=9999,
    textvariable=total_items_var, width=5, font=("Arial", 11),
    command=total_items_spin_event)
total_items_spin.grid(row=8, column=1, sticky="w")
total_items_var.trace_add("write", total_items_spin_event)

sum_status_label = ttk.Label(left_frame, text="", font=("Arial", 10, "bold"))
sum_status_label.grid(row=8, column=2, sticky="w", padx=5)

note_label = ttk.Label(
    left_frame,
    text="(# distractors = total - # targets)",
    font=("Arial", 8)
)
note_label.grid(row=9, column=0, columnspan=3, sticky="w", pady=(2,10))

targets_label = ttk.Label(left_frame, text="Targets", font=("Arial", 12))
targets_label.grid(row=11, column=0, sticky="w", pady=5)
targets_frame = ttk.Frame(left_frame, padding=10)
targets_frame.grid(row=12, column=0, columnspan=3, sticky="ew")

distractors_label = ttk.Label(left_frame, text="Distractors", font=("Arial", 12))
distractors_label.grid(row=13, column=0, sticky="w", pady=5)
distractors_frame = ttk.Frame(left_frame, padding=10)
distractors_frame.grid(row=14, column=0, columnspan=3, sticky="ew")

left_frame.rowconfigure(15, weight=1)

############################################
# RIGHT COLUMN: PREVIEW
############################################
preview_lbl = ttk.Label(right_frame, text="Preview", font=("Arial", 14, "bold"))
preview_lbl.grid(row=7, column=0, sticky="w", pady=5)

preview_canvas = tk.Canvas(
    right_frame,
    width=PREVIEW_DEFAULT_WIDTH,
    height=PREVIEW_DEFAULT_HEIGHT,
    bg="white",
    highlightthickness=1,
    highlightbackground="black"
)
preview_canvas.grid(row=8, column=0, padx=10, pady=5)

bg_color_button = ttk.Button(right_frame, text="Change Background Color", command=choose_preview_background_color)
bg_color_button.grid(row=9, column=0, pady=10)

right_frame.rowconfigure(10, weight=1)
right_frame.columnconfigure(0, weight=1)

############################################
# BOTTOM BUTTONS
############################################
bottom_btns_frame = ttk.Frame(content_frame, padding=10)
bottom_btns_frame.grid(row=1, column=0, columnspan=2, sticky="ew")

bottom_btns_frame.columnconfigure(0, weight=1)
bottom_btns_frame.columnconfigure(1, weight=1)
bottom_btns_frame.columnconfigure(2, weight=1)

error_label = ttk.Label(bottom_btns_frame, text="", foreground="red", font=("Arial", 10, "bold"))
error_label.grid(row=1, column=0, columnspan=3, sticky="n")

############################################
# GET/SET CONFIG
############################################
def get_configuration():
    """
    Gather all variables for JSON or for the actual task.
    """
    cfg = {}
    cfg["study_id"] = study_id_entry.get().strip()
    cfg["session"] = session_entry.get().strip()
    cfg["administrator"] = admin_entry.get().strip()
    cfg["screen_size"] = screen_size_var.get()
    cfg["refresh_rate"] = refresh_rate_var.get()
    cfg["input_type"] = input_type_var.get()

    cfg["total_items"] = safe_get_int_from_stringvar(total_items_var, 0)

    # Targets
    cfg["targets"] = []
    for i in range(len(target_symbol_vars)):
        cfg["targets"].append({
            "symbol": target_symbol_vars[i].get(),
            "font": font_var_vars[i].get(),
            "size": safe_get_int(text_size_vars[i], 18),
            "bold": bold_vars[i].get(),
            "underline": underline_vars[i].get(),
            "italic": italic_vars[i].get(),
            "color": text_color_vars[i].get(),
            "quantity": target_quantity_vars[i].get(),
        })

    # Distractors
    cfg["distractors"] = []
    for i in range(len(distractor_symbol_vars)):
        cfg["distractors"].append({
            "symbol": distractor_symbol_vars[i].get(),
            "font": distractor_font_var_vars[i].get(),
            "size": safe_get_int(distractor_text_size_vars[i], 18),
            "bold": distractor_bold_vars[i].get(),
            "underline": distractor_underline_vars[i].get(),
            "italic": distractor_italic_vars[i].get(),
            "color": distractor_text_color_vars[i].get(),
            "quantity": distractor_quantity_vars[i].get(),
        })
    return cfg

def set_configuration(cfg):
    # If you implement an "Import" feature that sets all fields
    # from a JSON, you would fill this out. For now, it's unused.
    pass

def export_configuration_to_json():
    filename = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if filename:
        cfg = get_configuration()
        with open(filename, "w") as f:
            json.dump(cfg, f, indent=2)

def import_configuration_from_json():
    filename = filedialog.askopenfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if filename:
        with open(filename, "r") as f:
            cfg = json.load(f)
        set_configuration(cfg)

export_btn = ttk.Button(bottom_btns_frame, text="Export Settings to JSON", width=25, command=export_configuration_to_json)
export_btn.grid(row=0, column=0, padx=5, pady=5)

import_btn = ttk.Button(bottom_btns_frame, text="Import Settings from JSON", width=25, command=import_configuration_from_json)
import_btn.grid(row=0, column=1, padx=5, pady=5)

############################################
# MAIN TASK LOGIC
############################################
def start_task(config):
    """
    Replaces the UI with the actual search display.
    Randomly places the chosen symbols (targets and distractors).
    Logs clicks to a CSV with columns matching your snippet:
        "ClickX","ClickY",
        "NearestLetterChar","NearestLetterType",
        "LetterCenterX","LetterCenterY",
        "DistanceToSelection","DistanceToNearestTarget"

    Each symbol disappears on click and is no longer clickable.
    """
    # 1) Clear out the old UI frames
    for child in root.winfo_children():
        child.destroy()

    # 2) Build a new full-frame canvas for the task
    task_canvas = tk.Canvas(root, bg="white")
    task_canvas.pack(fill="both", expand=True)

    # 3) Prepare CSV logging (matching your snippet's columns)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    csv_filename = f"responses_{config['study_id']}_session{config['session']}_{timestamp}.csv"
    csv_file = open(csv_filename, mode="w", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    writer.writerow([
        "ClickX","ClickY",
        "NearestLetterChar","NearestLetterType",
        "LetterCenterX","LetterCenterY",
        "DistanceToSelection","DistanceToNearestTarget"
    ])

    # 4) Expand targets/distractors
    items_to_place = []
    for t in config["targets"]:
        # t is a dict with "symbol","font","size","color",...
        for _ in range(t["quantity"]):
            items_to_place.append((t, True))  # (dict, is_target=True)

    for d in config["distractors"]:
        for _ in range(d["quantity"]):
            items_to_place.append((d, False)) # (dict, is_target=False)

    # 5) Random placement with a min distance so they don't overlap
    min_dist = 40  # adjust as needed
    placed_items = []  # store dicts: { cid, symbol, type, x, y, w, h }

    def measure_text_bbox(sym_conf):
        ft = build_font(
            sym_conf["font"],
            sym_conf["size"],
            sym_conf["bold"],
            sym_conf["italic"],
            sym_conf["underline"]
        )
        tmp_id = task_canvas.create_text(-9999, -9999, text=sym_conf["symbol"], font=ft)
        bbox = task_canvas.bbox(tmp_id)  # (x1,y1,x2,y2)
        task_canvas.delete(tmp_id)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        return w,h

    def boxes_overlap(x1, y1, w1, h1, x2, y2, w2, h2, dist_threshold):
        # We'll check center distance
        cx1, cy1 = x1 + w1/2, y1 + h1/2
        cx2, cy2 = x2 + w2/2, y2 + h2/2
        dist = math.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
        return (dist < dist_threshold)

    root.update_idletasks()
    c_width = task_canvas.winfo_width()
    c_height = task_canvas.winfo_height()

    random.shuffle(items_to_place)

    # place them
    for (sym_conf, is_t) in items_to_place:
        w_text, h_text = measure_text_bbox(sym_conf)
        max_tries = 1000
        placed = False
        for _ in range(max_tries):
            x_rand = random.randint(0, max(0, c_width - w_text))
            y_rand = random.randint(0, max(0, c_height - h_text))

            overlap_found = False
            for item in placed_items:
                if boxes_overlap(x_rand, y_rand, w_text, h_text,
                                 item["x"], item["y"], item["w"], item["h"],
                                 min_dist):
                    overlap_found = True
                    break
            if not overlap_found:
                # place it
                ft = build_font(
                    sym_conf["font"],
                    sym_conf["size"],
                    sym_conf["bold"],
                    sym_conf["italic"],
                    sym_conf["underline"]
                )
                cid = task_canvas.create_text(x_rand, y_rand,
                                              text=sym_conf["symbol"],
                                              font=ft,
                                              fill=sym_conf["color"],
                                              anchor="nw")
                placed_items.append({
                    "cid": cid,
                    "symbol": sym_conf["symbol"],
                    "is_target": is_t,
                    "x": x_rand,
                    "y": y_rand,
                    "w": w_text,
                    "h": h_text
                })
                placed = True
                break
        if not placed:
            print(f"Warning: Could not place '{sym_conf['symbol']}' after many tries.")

    # 6) On click: find nearest letter, log CSV row, remove that letter
    def on_click(event):
        if not placed_items:
            return
        click_x, click_y = event.x, event.y

        # Find nearest letter
        min_dist_sel = float("inf")
        nearest_item = None
        for itm in placed_items:
            # center of that item
            cx = itm["x"] + itm["w"]/2
            cy = itm["y"] + itm["h"]/2
            dist = math.hypot(click_x - cx, click_y - cy)
            if dist < min_dist_sel:
                min_dist_sel = dist
                nearest_item = itm

        if nearest_item is not None:
            # Now find distance from that item to the nearest target
            min_target_dist = float("inf")
            cx_item = nearest_item["x"] + nearest_item["w"]/2
            cy_item = nearest_item["y"] + nearest_item["h"]/2
            for itm2 in placed_items:
                if itm2["is_target"]:
                    # center of itm2
                    cx_t = itm2["x"] + itm2["w"]/2
                    cy_t = itm2["y"] + itm2["h"]/2
                    dist_t = math.hypot(cx_item - cx_t, cy_item - cy_t)
                    if dist_t < min_target_dist:
                        min_target_dist = dist_t

            # Write a row to CSV using the 8 columns from your snippet
            # "ClickX","ClickY","NearestLetterChar","NearestLetterType",
            # "LetterCenterX","LetterCenterY","DistanceToSelection","DistanceToNearestTarget"
            letter_type_str = "target" if nearest_item["is_target"] else "distractor"
            writer.writerow([
                click_x,
                click_y,
                nearest_item["symbol"],
                letter_type_str,
                cx_item,
                cy_item,
                min_dist_sel,
                min_target_dist
            ])
            # Remove from canvas, remove from placed_items
            task_canvas.delete(nearest_item["cid"])
            placed_items.remove(nearest_item)

    task_canvas.bind("<Button-1>", on_click)

    # 7) On closing the window, close CSV
    def on_closing():
        csv_file.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

############################################
# Validate & Run
############################################
def validate_and_run():
    global debounce_id
    if not study_id_entry.get().strip() or not session_entry.get().strip() or not admin_entry.get().strip():
        error_label.config(text="Error: Fill out Study ID, Session #, and Administrator.")
    else:
        total_val = safe_get_int_from_stringvar(total_items_var, 0)
        if total_val <= 0:
            error_label.config(text="Error: 'Number of items total' invalid or blank.")
            return
        t_sum = sum(v.get() for v in target_quantity_vars)
        d_sum = sum(v.get() for v in distractor_quantity_vars)
        if t_sum + d_sum != total_val:
            error_label.config(text="Error: sum of target + distractor must equal total items.")
        else:
            error_label.config(text="")
            # Cancel pending debounce so it doesn't fire after UI is destroyed
            if debounce_id is not None:
                root.after_cancel(debounce_id)
            # Now start the actual task
            config = get_configuration()
            start_task(config)

run_btn = ttk.Button(bottom_btns_frame, text="\u25B6 RUN TASK", command=validate_and_run)
run_btn.config(width=50)
run_btn.grid(row=0, column=2, padx=5, pady=5)
run_btn.state(["disabled"])

###################################
# CREATE/REMOVE TARGETS & DISTRACTORS
###################################
def turn_off_auto_distr(*args):
    global distr_auto_enabled
    distr_auto_enabled = False

def add_target():
    if len(target_symbol_vars) >= MAX_TARGET_ROWS:
        messagebox.showwarning("Limit Reached", f"Maximum of {MAX_TARGET_ROWS} target rows allowed.")
        return
    target_symbol_vars.append(tk.StringVar(value=""))
    font_var_vars.append(tk.StringVar(value="Arial"))
    text_size_vars.append(tk.IntVar(value=18))
    bold_vars.append(tk.BooleanVar())
    underline_vars.append(tk.BooleanVar())
    italic_vars.append(tk.BooleanVar())
    text_color_vars.append(tk.StringVar(value="#000000"))
    target_quantity_vars.append(tk.IntVar(value=1))
    refresh_targets_frame()
    schedule_debounced_update()

def remove_target(i):
    del target_symbol_vars[i]
    del font_var_vars[i]
    del text_size_vars[i]
    del bold_vars[i]
    del underline_vars[i]
    del italic_vars[i]
    del text_color_vars[i]
    del target_quantity_vars[i]
    refresh_targets_frame()
    schedule_debounced_update()

def refresh_targets_frame():
    for w in targets_frame.winfo_children():
        w.destroy()
    for i in range(len(target_symbol_vars)):
        create_target_entry(i)
    btn = ttk.Button(targets_frame, text="Add Another Target", command=add_target)
    btn.grid(row=999, column=0, columnspan=11, pady=10, sticky="w")

def create_target_entry(i):
    row = i
    e_symbol = ttk.Entry(targets_frame, textvariable=target_symbol_vars[i], width=3)
    e_symbol.grid(row=row, column=0, padx=5, sticky="w")

    cb_font = ttk.Combobox(
        targets_frame,
        textvariable=font_var_vars[i],
        values=FONT_OPTIONS,
        state="readonly"
    )
    cb_font.grid(row=row, column=1, padx=5, sticky="w")

    lbl_size = ttk.Label(targets_frame, text="Size:")
    lbl_size.grid(row=row, column=2, padx=2, sticky="w")

    sbox_size = tk.Spinbox(targets_frame, from_=1, to=999, textvariable=text_size_vars[i], width=5)
    sbox_size.grid(row=row, column=3, padx=5, sticky="w")

    ttk.Checkbutton(targets_frame, text="Bold", variable=bold_vars[i]).grid(row=row, column=4, sticky="w")
    ttk.Checkbutton(targets_frame, text="Underline", variable=underline_vars[i]).grid(row=row, column=5, sticky="w")
    ttk.Checkbutton(targets_frame, text="Italic", variable=italic_vars[i]).grid(row=row, column=6, sticky="w")

    color_btn = ttk.Button(targets_frame, text="Text color", command=lambda idx=i: choose_color(idx, "targets"))
    color_btn.grid(row=row, column=7, padx=5, sticky="w")

    remove_btn = ttk.Button(targets_frame, text="Remove", command=lambda idx=i: remove_target(idx))
    remove_btn.grid(row=row, column=8, padx=5, sticky="w")

    q_lbl = ttk.Label(targets_frame, text=f"# Target {i+1}:")
    q_lbl.grid(row=row, column=9, padx=5, sticky="e")

    q_spin = tk.Spinbox(targets_frame, from_=1, to=9999, textvariable=target_quantity_vars[i], width=5)
    q_spin.grid(row=row, column=10, padx=5, sticky="w")

    e_symbol.bind("<KeyRelease>", lambda e: schedule_debounced_update())
    cb_font.bind("<<ComboboxSelected>>", lambda e: schedule_debounced_update())
    sbox_size.bind("<KeyRelease>", lambda e: schedule_debounced_update())
    q_spin.bind("<KeyRelease>", lambda e: schedule_debounced_update())

    for var in (bold_vars[i], underline_vars[i], italic_vars[i], target_quantity_vars[i]):
        var.trace_add("write", lambda *_: schedule_debounced_update())

def add_distractor():
    if len(distractor_symbol_vars) >= MAX_DISTRACTOR_ROWS:
        messagebox.showwarning("Limit Reached", f"Maximum of {MAX_DISTRACTOR_ROWS} distractor rows allowed.")
        return
    distractor_symbol_vars.append(tk.StringVar(value=""))
    distractor_font_var_vars.append(tk.StringVar(value="Arial"))
    distractor_text_size_vars.append(tk.IntVar(value=18))
    distractor_bold_vars.append(tk.BooleanVar())
    distractor_underline_vars.append(tk.BooleanVar())
    distractor_italic_vars.append(tk.BooleanVar())
    distractor_text_color_vars.append(tk.StringVar(value="#000000"))
    distractor_quantity_vars.append(tk.IntVar(value=1))
    refresh_distractors_frame()
    schedule_debounced_update()

def remove_distractor(i):
    del distractor_symbol_vars[i]
    del distractor_font_var_vars[i]
    del distractor_text_size_vars[i]
    del distractor_bold_vars[i]
    del distractor_underline_vars[i]
    del distractor_italic_vars[i]
    del distractor_text_color_vars[i]
    del distractor_quantity_vars[i]
    refresh_distractors_frame()
    schedule_debounced_update()

def refresh_distractors_frame():
    for w in distractors_frame.winfo_children():
        w.destroy()
    for i in range(len(distractor_symbol_vars)):
        create_distractor_entry(i)
    btn = ttk.Button(distractors_frame, text="Add Another Distractor", command=add_distractor)
    btn.grid(row=999, column=0, columnspan=11, pady=10, sticky="w")

def create_distractor_entry(i):
    row = i
    e_symbol = ttk.Entry(distractors_frame, textvariable=distractor_symbol_vars[i], width=3)
    e_symbol.grid(row=row, column=0, padx=5, sticky="w")

    cb_font = ttk.Combobox(
        distractors_frame,
        textvariable=distractor_font_var_vars[i],
        values=FONT_OPTIONS,
        state="readonly"
    )
    cb_font.grid(row=row, column=1, padx=5, sticky="w")

    lbl_size = ttk.Label(distractors_frame, text="Size:")
    lbl_size.grid(row=row, column=2, padx=2, sticky="w")

    sbox_size = tk.Spinbox(distractors_frame, from_=1, to=999, textvariable=distractor_text_size_vars[i], width=5)
    sbox_size.grid(row=row, column=3, padx=5, sticky="w")

    ttk.Checkbutton(distractors_frame, text="Bold", variable=distractor_bold_vars[i]).grid(row=row, column=4, sticky="w")
    ttk.Checkbutton(distractors_frame, text="Underline", variable=distractor_underline_vars[i]).grid(row=row, column=5, sticky="w")
    ttk.Checkbutton(distractors_frame, text="Italic", variable=distractor_italic_vars[i]).grid(row=row, column=6, sticky="w")

    color_btn = ttk.Button(distractors_frame, text="Text color",
                           command=lambda idx=i: choose_color(idx, "distractors"))
    color_btn.grid(row=row, column=7, padx=5, sticky="w")

    remove_btn = ttk.Button(distractors_frame, text="Remove",
                            command=lambda idx=i: remove_distractor(idx))
    remove_btn.grid(row=row, column=8, padx=5, sticky="w")

    q_lbl = ttk.Label(distractors_frame, text=f"# Distractor {i+1}:")
    q_lbl.grid(row=row, column=9, padx=5, sticky="e")

    q_spin = tk.Spinbox(distractors_frame, from_=1, to=9999, textvariable=distractor_quantity_vars[i], width=5)
    q_spin.grid(row=row, column=10, padx=5, sticky="w")

    def disable_auto_and_update():
        global distr_auto_enabled
        distr_auto_enabled = False
        schedule_debounced_update()

    q_spin.config(command=disable_auto_and_update)

    e_symbol.bind("<KeyRelease>", lambda e: schedule_debounced_update())
    cb_font.bind("<<ComboboxSelected>>", lambda e: schedule_debounced_update())
    sbox_size.bind("<KeyRelease>", lambda e: schedule_debounced_update())

    for var in (
        distractor_bold_vars[i],
        distractor_underline_vars[i],
        distractor_italic_vars[i],
        distractor_quantity_vars[i]
    ):
        var.trace_add("write", lambda *_: schedule_debounced_update())


###################################
# INIT: add 1 row each
###################################
def initialize():
    add_target()
    add_distractor()

initialize()

root.mainloop()