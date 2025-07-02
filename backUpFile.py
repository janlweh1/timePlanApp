# for back-up, do not edit
# all main functions are working
import customtkinter as ctk
import os
from PIL import Image
from databaseManagement import DatabaseManager
from datetime import datetime, timedelta
import pytz
from tkinter import messagebox  # <-- Add this import
from tkinter import ttk  # <-- Add this import for ttk.Button

# Import the calendar widget from tkcalendar
from tkcalendar import Calendar


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class TimePlanApp(ctk.CTk):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title("TimePlan")
        self.geometry("1200x700")
        self.configure(bg="#F8F3FB")

        self.sidebar_expanded = True
        self.sidebar_width = 240
        self.sidebar_collapsed_width = 64
        
        # For task detail pane
        self.selected_task = None
        self.detail_pane_visible = False
        self.detail_pane_width = 340
        
        self.db_manager = DatabaseManager()
        self.current_user_id = 1        # Pre-fetch category IDs
        self.completed_category_id = self.db_manager.get_category_id_by_name("Completed")
        self.on_going_category_id = self.db_manager.get_category_id_by_name("On-going") # For un-completing tasks
        self.missed_category_id = self.db_manager.get_category_id_by_name("Missed") # For past due tasks
          # Get all category names for task editing
        self.all_categories = [cat[0] for cat in self.db_manager.get_task_categories()]
        
        if not self.completed_category_id:
            print("ERROR: 'Completed' category not found. Please ensure databaseManagement.py initializes it.")
        if not self.on_going_category_id:
            print("ERROR: 'On-going' category not found. Please ensure databaseManagement.py initializes it.")
        if not self.missed_category_id:
            print("ERROR: 'Missed' category not found. Please ensure databaseManagement.py initializes it.")

        # Load sidebar icons (rest of the icon loading code)
        self.icons = {}
        icon_folder = os.path.join(os.path.dirname(__file__), "icons")
        icon_files = {
            "Tasks": "tasks.png", "Calendar": "calendar.png", "Habit": "habit2.png",
            "Add Task": "addTask.png", "Search Task": "search.png", "Profile": "profile.png",
            "Sign Out": "signOut.png"
        }
        for key, filename in icon_files.items():
            path = os.path.join(icon_folder, filename)
            if os.path.exists(path):
                img = Image.open(path)
                w, h = img.size
                side = min(w, h)
                left = (w - side) // 2
                top = (h - side) // 2
                right = left + side
                bottom = top + side
                img = img.crop((left, top, right, bottom)).resize((56, 56), Image.LANCZOS)
                self.icons[key] = ctk.CTkImage(light_image=img, dark_image=img, size=(56, 56))
            else:
                print(f"Warning: Sidebar icon not found: {path}")
                self.icons[key] = None

        self.nav_icons = {}
        nav_icon_files = {
            "Today": "today.png", "Next 7 Days": "next7Days.png", "All Tasks": "allTasks.png",
            "On-going": "onGoing.png", "Completed": "completed.png", "Missed": "missing.png"
        }
        icon_size_nav = (40, 40)
        for key, filename in nav_icon_files.items():
            path = os.path.join(icon_folder, filename)
            if os.path.exists(path):
                img = Image.open(path)
                w, h = img.size
                side = min(w, h)
                left = (w - side) // 2
                top = (h - side) // 2
                right = left + side
                bottom = top + side
                img = img.crop((left, top, right, bottom))
                img = img.resize(icon_size_nav, Image.LANCZOS)
                self.nav_icons[key] = ctk.CTkImage(light_image=img, dark_image=img, size=icon_size_nav)
            else:
                print(f"Warning: Navigation icon not found: {path}")
                self.nav_icons[key] = None

        logo_path = os.path.join(icon_folder, "logoKuno.png")
        if os.path.exists(logo_path):
            logo_img = Image.open(logo_path)
            w, h = logo_img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            right = left + side
            bottom = top + side
            logo_img = logo_img.crop((left, top, right, bottom)).resize((40, 40), Image.LANCZOS)
            self.logo_image = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(40, 40))
        else:
            self.logo_image = None

        self.sidebar = ctk.CTkFrame(self, width=self.sidebar_width, corner_radius=0, fg_color="#C576E0")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        sidebar_logo_frame = ctk.CTkFrame(self.sidebar, fg_color="#C576E0")
        sidebar_logo_frame.pack(fill="x", pady=(8, 0), padx=8)
        if self.logo_image:
            ctk.CTkLabel(sidebar_logo_frame, image=self.logo_image, text="", width=40, height=40).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            sidebar_logo_frame,
            text="TimePlan",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white",
            bg_color="#C576E0"
        ).pack(side="left", pady=0)

        self.navbar = ctk.CTkFrame(self, width=300, fg_color="#F3E6F8")
        self.navbar_nav_items = []
        nav_items_data = [
            "Today", "Next 7 Days", "All Tasks",
            "On-going", "Completed", "Missed"
        ]
        for name in nav_items_data:
            # Create a lambda with a default argument to capture the current value of 'name'
            # This fixes the common lambda closure issue in loops
            btn = ctk.CTkButton(
                self.navbar,
                text=name,
                image=self.nav_icons.get(name),
                compound="left",
                width=180,
                height=40,
                font=ctk.CTkFont(size=16, weight="bold"),
                fg_color="transparent",
                text_color="#A85BC2",
                hover_color="#E5C6F2",
                anchor="w",
                # Use default argument to capture current value of name
                command=lambda filter_name=name: self.show_tasks_page(filter_name)
            )
            btn.pack(pady=6, anchor="w") 
            self.navbar_nav_items.append(btn)

        self.content = ctk.CTkFrame(self, fg_color="#F8F3FB")
        self.content.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        self.sidebar_buttons = []
        sidebar_buttons = [            ("Tasks", lambda: self.show_tasks_page('All Tasks')),
            ("Calendar", self.show_calendar_page),
            ("Habit", self.show_habit_page),
            ("Add Task", self.show_add_task_dialog),
            ("Search Task", self.show_search_dialog),
            ("Profile", None),
            ("Sign Out", None)
        ]
        for btn_text, btn_cmd in sidebar_buttons:
            b = ctk.CTkButton(
                self.sidebar,
                text=btn_text,
                image=self.icons.get(btn_text),
                compound="left",
                width=200,
                height=60,
                font=ctk.CTkFont(size=16, weight="bold"),
                fg_color="#C576E0",
                hover_color="#A85BC2",
                text_color="white",
                anchor="w",
                command=btn_cmd
            )
            b.pack(pady=2, padx=8, fill="none")
            b.pack_propagate(False)
            self.sidebar_buttons.append(b)

        self.collapse_btn = ctk.CTkButton(
            self,
            text="◀",
            width=24,
            height=48,
            fg_color="#C576E0",
            hover_color="#A85BC2",
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=0,
            border_width=0,
            command=self.toggle_sidebar
        )
        
        self.position_collapse_button()
        self.bind("<Configure>", self.on_window_configure)

        self.show_tasks_page('All Tasks')

        self.current_page = "tasks"  # Track current page: "tasks" or "calendar"

    def position_collapse_button(self):
        self.update_idletasks()
        current_width = self.sidebar_width if self.sidebar_expanded else self.sidebar_collapsed_width
        x_pos = current_width
        self.collapse_btn.place(x=x_pos, rely=0.5, anchor="w")

    def on_window_configure(self, event):
        if event.widget == self:
            self.position_collapse_button()

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def show_tasks_page(self, filter_type='All Tasks'):
        self.navbar.pack_forget()
        self.navbar.pack(side="left", fill="y", padx=(40, 0))

        # Update the filter buttons
        self.update_filter_buttons(filter_type)
        
        # Set current page to tasks
        self.current_page = "tasks"

        # Hide the detail pane if visible when switching task views
        if self.detail_pane_visible:
            self.hide_task_detail()

        self.content.pack_forget()
        self.content.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        
        self.clear_content()

        ctk.CTkLabel(
            self.content,
            text=f"{filter_type} Tasks",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#A85BC2"
        ).pack(anchor="nw", pady=(10, 0), padx=10)

        self.task_scroll_frame = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.task_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Fetch tasks from the database based on filter type
        tasks = self.db_manager.get_tasks(user_id=self.current_user_id, filter_type=filter_type)
        
        # Additional sorting based on due date (nearest first)
        if filter_type in ['All Tasks', 'On-going']:
            def get_due_date(task):
                due_date_str = task[4]  # due_date is at index 4
                if due_date_str:
                    try:
                        return datetime.strptime(due_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        return datetime.max.date()
                return datetime.max.date()  # Tasks with no due date will appear at the end
            tasks = sorted(tasks, key=get_due_date)

        if not tasks:
            ctk.CTkLabel(self.task_scroll_frame, text="No tasks found for this filter.",
                         font=ctk.CTkFont(size=16), text_color="#6A057F").pack(pady=20)
            return

        MISSED_BG_COLOR = "#FFCDD2" # Light Red
        COMPLETED_BG_COLOR = "#C8E6C9" # Light Green
        ONGOING_BG_COLOR = "white" # Default for uncompleted, non-missed tasks

        philippines_timezone = pytz.timezone('Asia/Manila')
        current_local_date = datetime.now(philippines_timezone).date()

        for i, task in enumerate(tasks):
            if len(task) != 6:
                print(f"Error: Task {i} has unexpected number of elements: {len(task)}. Expected 6. Task data: {task}")
                continue
            
            task_id, title, description, priority, due_date, category_name = task

            frame_bg_color = ONGOING_BG_COLOR
            title_color = "#333333"
            is_completed_by_category = (category_name == "Completed")
            is_missed = False
            
            if not is_completed_by_category and due_date:
                try:
                    due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                    if due_date_obj < current_local_date:
                        is_missed = True
                        # Do NOT update the database here to avoid UI lag
                        # Only update the UI to show as missed
                        # If you want to update the DB, do it in a batch elsewhere
                        category_name = "Missed"
                except ValueError:
                    pass

            if is_completed_by_category:
                frame_bg_color = COMPLETED_BG_COLOR
                title_color = "gray"
            elif is_missed:
                frame_bg_color = MISSED_BG_COLOR
                title_color = "red"
            
            task_frame = ctk.CTkFrame(self.task_scroll_frame, fg_color=frame_bg_color, corner_radius=10,
                                      border_width=1, border_color="#E5C6F2", cursor="hand2")
            task_frame.pack(fill="x", pady=5, padx=5)
            def on_task_click(event, tid=task_id):
                self.selected_task = tid
                self.show_task_detail(tid)
            task_frame.bind("<Button-1>", on_task_click)

            task_frame.grid_columnconfigure(0, weight=0)
            task_frame.grid_columnconfigure(1, weight=1)
            task_frame.grid_columnconfigure(2, weight=0)
            task_frame.grid_rowconfigure(0, weight=0)
            task_frame.grid_rowconfigure(1, weight=0)
            task_frame.grid_rowconfigure(2, weight=1)

            status_var = ctk.StringVar(value="on" if is_completed_by_category else "off")
            status_checkbox = ctk.CTkCheckBox(task_frame, text="", variable=status_var,
                                              onvalue="on", offvalue="off",
                                              command=lambda tid=task_id, svar=status_var, current_cat_name=category_name, ft=filter_type: self.toggle_task_completion(tid, svar, current_cat_name, ft))
            status_checkbox.grid(row=0, column=0, rowspan=3, padx=(10,0), pady=10, sticky="nsew")
            def prevent_propagation(e):
                e.widget.focus_set()
                return "break"
            status_checkbox.bind("<Button-1>", prevent_propagation, add="+")

            ctk.CTkLabel(task_frame, text=title, font=ctk.CTkFont(size=18, weight="bold"),
                         text_color=title_color, anchor="w", wraplength=400
                         ).grid(row=0, column=1, padx=(10, 5), pady=(10,0), sticky="ew")

            if priority:
                display_priority_text = "⚠️ Urgent" if priority == "Urgent" else "Not urgent"
                ctk.CTkLabel(task_frame, text=display_priority_text, font=ctk.CTkFont(size=14),
                             text_color=title_color, anchor="w"
                             ).grid(row=1, column=1, padx=(10, 5), pady=(0, 5), sticky="ew")

            if description:
                ctk.CTkLabel(task_frame, text=description, font=ctk.CTkFont(size=14),
                             text_color=title_color, anchor="nw", wraplength=400
                             ).grid(row=2, column=1, padx=(10, 5), pady=(0, 10), sticky="new")
            else:
                ctk.CTkLabel(task_frame, text="", font=ctk.CTkFont(size=1),
                             text_color=title_color, anchor="w").grid(row=2, column=1, padx=(10, 5), pady=(0, 0), sticky="ew")

            if category_name:
                category_label = ctk.CTkLabel(task_frame, text=category_name, font=ctk.CTkFont(size=12, weight="bold"),
                             text_color="#666666", anchor="ne", justify="right"
                             )
                category_label.grid(row=0, column=2, padx=10, pady=(10,0), sticky="ne")
                category_label.bind("<Button-1>", lambda e, tid=task_id: on_task_click(e, tid))
                category_label.configure(cursor="hand2")
                
                # Due date label (add this for calendar view task cards)
                if due_date:
                    try:
                        due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                        if due_date_obj == current_local_date:
                            formatted_date_str = "Due: Today"
                        elif due_date_obj == (current_local_date + timedelta(days=1)):
                            formatted_date_str = "Due: Tomorrow"
                        else:
                            formatted_date_str = f"Due: {due_date_obj.strftime('%b %d, %Y')}"
                    except ValueError:
                        formatted_date_str = "Due: Invalid Date"

                    due_date_label = ctk.CTkLabel(
                        task_frame,
                        text=formatted_date_str,
                        font=ctk.CTkFont(size=12),
                        text_color="#666666",
                        anchor="ne",
                        justify="right"
                    )
                    due_date_label.grid(row=1, column=2, padx=10, pady=(0,10), sticky="ne")
                    due_date_label.bind("<Button-1>", lambda e, tid=task_id: on_task_click(e, tid))
                    due_date_label.configure(cursor="hand2")
            
            # Recurring task indicator (new)
            is_recurring = self.db_manager.is_recurring_task(task_id)
            if is_recurring:
                recurring_label = ctk.CTkLabel(
                    task_frame,
                    text="🗓️ Recurring Task",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="#4CAF50",
                    anchor="se",
                    justify="right"
                )
                recurring_label.grid(row=2, column=2, padx=10, pady=(0, 10), sticky="se")
                recurring_label.bind("<Button-1>", lambda e, tid=task_id: on_task_click(e, tid))
                recurring_label.configure(cursor="hand2")

    def toggle_task_completion(self, task_id, status_var, current_category_name, current_filter_type):
        new_category_id = None
        if status_var.get() == "on": # Task is being marked as Completed
            if self.completed_category_id:
                new_category_id = self.completed_category_id
            else:
                messagebox.showwarning("Warning", "Could not find 'Completed' category. Task not updated.")
                status_var.set("off") # Revert checkbox state
                return
        else: # Task is being marked as Incomplete
            if self.on_going_category_id: # Revert to "On-going"
                new_category_id = self.on_going_category_id
            else:
                messagebox.showwarning("Warning", "Could not find 'On-going' category. Task not updated.")
                status_var.set("on") # Revert checkbox state
                return

        if self.db_manager.update_task_category(task_id, new_category_id):
            # Refresh the view based on current page
            if self.current_page == "calendar":
                self.show_calendar_page()
            else:
                self.show_tasks_page(current_filter_type)
        else:
            messagebox.showerror("Error", "Failed to update task status in database.")
            status_var.set("off" if status_var.get() == "on" else "on") # Revert checkbox on failure

    def show_calendar_page(self):
        self.navbar.pack_forget()
        self.content.pack_forget()
        self.content.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.clear_content()
        
        # Create main calendar container with split view
        split_frame = ctk.CTkFrame(self.content, fg_color="#FFFFFF", corner_radius=10)
        split_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Calendar frame on top
        calendar_frame = ctk.CTkFrame(split_frame, fg_color="transparent")
        calendar_frame.pack(fill="x", padx=5, pady=5)
        
        # Get all tasks from database and organize by date
        tasks = self.db_manager.get_tasks(user_id=self.current_user_id, filter_type='All Tasks')
        # Create a dictionary mapping due dates to tasks
        task_dates = {}
        
        # Add a heading for the calendar view
        ctk.CTkLabel(
            calendar_frame,
            text="Calendar View",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#A85BC2"
        ).pack(anchor="nw", pady=(0, 10))
        
        # Process tasks and organize by date
        for task in tasks:
            task_id, title, description, priority, due_date, category_name = task
            if due_date:
                # Ensure date format consistency - store as strings
                date_key = due_date.strip()  # Remove any whitespace
                if date_key not in task_dates:
                    task_dates[date_key] = []
                task_dates[date_key].append({
                    'id': task_id,  # Keep as 'id' for consistency with create_task_card
                    'title': title,  # Keep as 'title' for consistency with create_task_card
                    'description': description,
                    'priority': priority,
                    'due_date': date_key,
                    'category': category_name
                })
        
        philippines_timezone = pytz.timezone('Asia/Manila')
        current_local_date = datetime.now(philippines_timezone).date()
        
        # Create the tasks frame (below calendar) - initially empty
        tasks_container_frame = ctk.CTkFrame(split_frame, fg_color="transparent")
        tasks_container_frame.pack(fill="both", expand=True, padx=5, pady=10)
        
        # Header for tasks section
        tasks_header_frame = ctk.CTkFrame(tasks_container_frame, fg_color="transparent")
        tasks_header_frame.pack(fill="x", pady=(0, 5))
        
        selected_date_label = ctk.CTkLabel(
            tasks_header_frame,
            text="Select a date to view tasks",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#A85BC2"
        )
        selected_date_label.pack(anchor="w")
        
        # Create a scrollable frame for tasks
        tasks_scroll_frame = ctk.CTkScrollableFrame(tasks_container_frame, fg_color="transparent")
        tasks_scroll_frame.pack(fill="both", expand=True)
        
        # Create custom calendar
        cal = Calendar(calendar_frame, 
            selectmode='day',
            date_pattern='yyyy-mm-dd',
            background="white",
            selectbackground="#C576E0",
            othermonthforeground="gray",
            normalforeground="black",
            weekendbackground="white",
            weekendforeground="#A85BC2",
            showweeknumbers=False,
            showothermonthdays=True,
            font=("Arial", 12),
            headersbackground="#C576E0", 
            headersforeground="white",
            foreground="black",
            borderwidth=0
        )
        cal.pack(fill="x")

        # Configure calendar event tag for tasks - use calevent_create's tag format
        cal.tag_config("task_date", background='#F3E6F8')  # Light purple for task dates
        
        # Use the proper method to mark dates with tasks
        for date_str in task_dates.keys():
            try:
                # Parse the date string to a date object
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                # Mark the date on the calendar using calevent_create
                cal.calevent_create(date_obj, "Task Due", "task_date")
            except (ValueError, AttributeError) as e:
                print(f"Error marking date {date_str}: {str(e)}")
        
        # Function to update task display when a date is selected
        def update_tasks_for_selected_date(event):
            # Clear existing tasks
            for widget in tasks_scroll_frame.winfo_children():
                widget.destroy()
                
            # Get the selected date string in yyyy-mm-dd format
            selected_date = cal.get_date()
            
            try:
                # Format the date for display
                date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
                if date_obj == current_local_date:
                    formatted_date = "Today"
                elif date_obj == current_local_date + timedelta(days=1):
                    formatted_date = "Tomorrow"
                else:
                    formatted_date = date_obj.strftime("%B %d, %Y")
                
                # Update the header
                selected_date_label.configure(text=f"Tasks for {formatted_date}")
                
                # Get tasks for the selected date
                date_tasks = task_dates.get(selected_date, [])
                
                if date_tasks:
                    # Display tasks for the selected date
                    for task in date_tasks:
                        task_frame = ctk.CTkFrame(tasks_scroll_frame, corner_radius=10)
                        task_frame.pack(fill="x", pady=5, padx=5)
                        self.create_task_card(task_frame, task)
                else:
                    # No tasks for this date
                    no_tasks_label = ctk.CTkLabel(
                        tasks_scroll_frame,
                        text=f"No tasks scheduled for this date.",
                        font=ctk.CTkFont(size=14),
                        text_color="#6A057F"
                    )
                    no_tasks_label.pack(pady=20)
            except ValueError:
                # Handle invalid date format
                selected_date_label.configure(text="Invalid date format")
        
        # Bind the date selection event
        cal.bind("<<CalendarSelected>>", update_tasks_for_selected_date)
        
        # Select today's date by default and show tasks for today
        today_date_str = current_local_date.strftime('%Y-%m-%d')
        try:
            cal.selection_set(today_date_str)
            # Call the update function to show today's tasks
            self.after(100, lambda: update_tasks_for_selected_date(None))
        except Exception as e:
            print(f"Error setting initial date: {str(e)}")
        
        self.current_page = "calendar"  # Set current page to calendar

    def show_add_task_page(self):
        self.navbar.pack_forget()
        self.content.pack_forget()
        self.content.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.clear_content()

        ctk.CTkLabel(
            self.content,
            text="Add New Task",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#A85BC2"
        ).pack(anchor="nw", pady=(10, 0), padx=10)

        form_frame = ctk.CTkFrame(self.content, fg_color="white", corner_radius=10, padx=20, pady=20)
        form_frame.pack(fill="both", expand=True, padx=10, pady=10)
        form_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form_frame, text="Title:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        self.task_title_entry = ctk.CTkEntry(form_frame, placeholder_text="Task title", width=300)
        self.task_title_entry.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="ew")

        ctk.CTkLabel(form_frame, text="Description:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.task_description_entry = ctk.CTkEntry(form_frame, placeholder_text="Optional description", width=300)
        self.task_description_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Priority:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.task_priority_optionmenu = ctk.CTkOptionMenu(form_frame, values=["Urgent", "Not urgent"])
        self.task_priority_optionmenu.set("Not urgent")
        self.task_priority_optionmenu.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Due Date:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.task_due_date_entry = ctk.CTkEntry(form_frame, placeholder_text="YYYY-MM-DD (optional)", width=300)
        self.task_due_date_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Category:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        
        # Get all categories and filter out 'Completed' for new task entry default
        # Assuming new tasks will start as "On-going" or "Missed"
        self.category_names = [cat[0] for cat in self.db_manager.get_task_categories() if cat[0] not in ["Completed", "Missed"]]
        self.task_category_optionmenu = ctk.CTkOptionMenu(form_frame, values=self.category_names)
        
        if "On-going" in self.category_names: # Set 'On-going' as default if available
            self.task_category_optionmenu.set("On-going")
        elif self.category_names: # Otherwise, set the first available category
            self.task_category_optionmenu.set(self.category_names[0])
        else: # No categories available
            self.task_category_optionmenu.set("No Categories")
            self.task_category_optionmenu.configure(state="disabled")

        self.task_category_optionmenu.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkButton(form_frame, text="Add Task", command=self.submit_task,
                      font=ctk.CTkFont(size=16, weight="bold"),
                      fg_color="#A85BC2", hover_color="#C576E0").grid(row=5, column=0, columnspan=2, pady=20)

    def submit_task(self):
        title = self.task_title_entry.get()
        description = self.task_description_entry.get()
        priority = self.task_priority_optionmenu.get()
        due_date = self.task_due_date_entry.get()
        category_name = self.task_category_optionmenu.get()

        if not title:
            messagebox.showwarning("Warning", "Task title cannot be empty.")
            return
        
        if due_date:
            try:
                datetime.strptime(due_date, '%Y-%m-%d')
            except ValueError:
                messagebox.showwarning("Warning", "Due date must be in YYYY-MM-DD format (e.g., 2025-06-30).")
                return
        
        description = description if description else None
        due_date = due_date if due_date else None

        category_id = self.db_manager.get_category_id_by_name(category_name)

        if category_id is None: 
            # Fallback if selected category wasn't found (shouldn't happen if list is populated correctly)
            # or if "No Categories" was selected and no categories exist.
            default_category_id = self.db_manager.get_category_id_by_name("On-going")
            if default_category_id is not None:
                category_id = default_category_id
            else:
                messagebox.showwarning("Warning", "No valid categories available. Please add a category first.")
                return        # Add the new task to the database
        new_task_id = self.db_manager.add_task(self.current_user_id, title, description, priority, due_date, category_id)
        if new_task_id:
            # Show success popup
            messagebox.showinfo("Success", "Task added successfully!")
            
            # Clear input fields and reset dropdowns
            self.task_title_entry.delete(0, ctk.END)
            self.task_description_entry.delete(0, ctk.END)
            self.task_priority_optionmenu.set("Not urgent")
            self.task_due_date_entry.delete(0, ctk.END)
            if "On-going" in self.category_names: # Reset to 'On-going' if available
                self.task_category_optionmenu.set("On-going")
            elif self.category_names:
                self.task_category_optionmenu.set(self.category_names[0])
            
            # Get the current filter
            current_filter = self.get_current_filter()
            
            # After adding a new task, show All Tasks to make sure the new task is visible,
            # unless we're already in a filter that should show it (like All Tasks or On-going)
            if category_name == "On-going" and current_filter in ["All Tasks", "On-going"]:
                # Stay in current filter if it would show the new task
                self.show_tasks_page(current_filter)
            else:
                # Otherwise show All Tasks to ensure it's visible
                self.show_tasks_page('All Tasks')
            
            # Show the details of the newly created task
            self.show_task_detail(new_task_id)
        else:
            messagebox.showerror("Error", "Failed to add task. Check console for database errors.")

    def toggle_sidebar(self):
        if self.sidebar_expanded:
            self.sidebar.configure(width=self.sidebar_collapsed_width)
            for b in self.sidebar_buttons:
                b.configure(text="")
            self.sidebar_expanded = False
            self.collapse_btn.configure(text="▶")
        else:
            self.sidebar.configure(width=self.sidebar_width)
            for b, text in zip(self.sidebar_buttons, ["Tasks", "Calendar", "Habit", "Add Task", "Search Task", "Profile", "Sign Out"]):
                b.configure(text=text)
            self.sidebar_expanded = True
            self.collapse_btn.configure(text="◀")
        
        self.after(10, self.position_collapse_button)

    def select_task(self, task_id):
        """Select a task to view/edit details."""
        if self.selected_task == task_id:
            # If the selected task is clicked again, unselect it
            self.selected_task = None
            self.detail_pane_visible = False
        else:
            self.selected_task = task_id
            self.detail_pane_visible = True
        
        self.update_task_detail_pane()

    def update_task_detail_pane(self):
        """Update the task detail pane content."""
        if not self.detail_pane_visible or self.selected_task is None:
            # Hide or clear the detail pane
            if hasattr(self, 'task_detail_pane'):
                self.task_detail_pane.pack_forget()
                del self.task_detail_pane
            return
        
        task = self.db_manager.get_task_by_id(self.selected_task)
        if not task:
            return # Task not found, do not proceed
        
        task_id, task_title, description, priority, due_date, category_name = task

        # Create the detail pane if it doesn't exist
        if not hasattr(self, 'task_detail_pane'):
            self.task_detail_pane = ctk.CTkFrame(self.content, fg_color="#FFFFFF", corner_radius=10, padx=20, pady=20)
            self.task_detail_pane.pack(side="right", fill="y", padx=(10, 0), pady=10)
            
            # Title
            self.task_detail_title = ctk.CTkLabel(self.task_detail_pane, text="", font=ctk.CTkFont(size=18, weight="bold"),
                                                  text_color="#333333", anchor="w", wraplength=300)
            self.task_detail_title.pack(anchor="nw", pady=(0, 10))
            
            # Description
            self.task_detail_description = ctk.CTkLabel(self.task_detail_pane, text="", font=ctk.CTkFont(size=14),
                                                         text_color="#333333", anchor="w", wraplength=300)
            self.task_detail_description.pack(anchor="nw", pady=(0, 10))
            
            # Priority
            self.task_detail_priority = ctk.CTkLabel(self.task_detail_pane, text="", font=ctk.CTkFont(size=14),
                                                      text_color="#333333", anchor="w")
            self.task_detail_priority.pack(anchor="nw", pady=(0, 10))
            
            # Due Date
            self.task_detail_due_date = ctk.CTkLabel(self.task_detail_pane, text="", font=ctk.CTkFont(size=14),
                                                       text_color="#333333", anchor="w")
            self.task_detail_due_date.pack(anchor="nw", pady=(0, 10))
            
            # Category
            self.task_detail_category = ctk.CTkLabel(self.task_detail_pane, text="", font=ctk.CTkFont(size=14),
                                                       text_color="#333333", anchor="w")
            self.task_detail_category.pack(anchor="nw", pady=(0, 10))

            # Edit button
            self.edit_task_button = ctk.CTkButton(self.task_detail_pane, text="Edit Task", command=self.show_edit_task_page,
                                                   font=ctk.CTkFont(size=16, weight="bold"),
                                                   fg_color="#A85BC2", hover_color="#C576E0")
            self.edit_task_button.pack(side="bottom", fill="x", pady=10)
        
        # Update the detail pane content
        self.task_detail_title.configure(text=task_title)
        self.task_detail_description.configure(text=description if description else "No description provided.")
        self.task_detail_priority.configure(text=f"Priority: {priority}")
        self.task_detail_due_date.configure(text=f"Due Date: {due_date}" if due_date else "Due Date: Not set")
        self.task_detail_category.configure(text=f"Category: {category_name}")

        self.task_detail_pane.pack(side="right", fill="y", padx=(10, 0), pady=10)

    def show_edit_task_page(self):
        """Open the edit task page for the selected task."""
        if not self.selected_task:
            return # No task selected, do not proceed
        
        task = self.db_manager.get_task_by_id(self.selected_task)
        if not task:
            return # Task not found, do not proceed
        
        task_id, title, description, priority, due_date, category_name = task

        self.clear_content()

        ctk.CTkLabel(
            self.content,
            text="Edit Task",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#A85BC2"
        ).pack(anchor="nw", pady=(10, 0), padx=10)

        form_frame = ctk.CTkFrame(self.content, fg_color="white", corner_radius=10, padx=20, pady=20)
        form_frame.pack(fill="both", expand=True, padx=10, pady=10)
        form_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form_frame, text="Title:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        self.edit_task_title_entry = ctk.CTkEntry(form_frame, placeholder_text="Task title", width=300)
        self.edit_task_title_entry.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="ew")
        self.edit_task_title_entry.insert(0, title)

        ctk.CTkLabel(form_frame, text="Description:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.edit_task_description_entry = ctk.CTkEntry(form_frame, placeholder_text="Optional description", width=300)
        self.edit_task_description_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.edit_task_description_entry.insert(0, description if description else "")

        ctk.CTkLabel(form_frame, text="Priority:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.edit_task_priority_optionmenu = ctk.CTkOptionMenu(form_frame, values=["Urgent", "Not urgent"])
        self.edit_task_priority_optionmenu.set(priority)
        self.edit_task_priority_optionmenu.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkLabel(form_frame, text="Due Date:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        
        # Create a container frame for due date entry and calendar
        due_date_container = ctk.CTkFrame(form_frame, fg_color="transparent")
        due_date_container.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        due_date_container.grid_columnconfigure(0, weight=1)
        
        # Due date entry at the top of the container
        self.edit_task_due_date_entry = ctk.CTkEntry(due_date_container, placeholder_text="YYYY-MM-DD (optional)", width=300)
        self.edit_task_due_date_entry.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.edit_task_due_date_entry.insert(0, due_date if due_date else "")
          # Calendar widget below the entry
        calendar_frame = ctk.CTkFrame(due_date_container, fg_color="#FFFFFF", corner_radius=5)
        calendar_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))          # Calendar directly in the form
        cal = Calendar(calendar_frame, selectmode='day', date_pattern='yyyy-mm-dd',
                       background="#FFFFFF", 
                       selectbackground="#A85BC2",
                       headersbackground="#C576E0",
                       headersforeground="white",
                       normalbackground="#FFFFFF",
                       showweeknumbers=False, showothermonthdays=True,
                       font=("Arial", 10),
                       showmonth=True)
        
        def on_date_selected(event=None):
            selected_date = cal.get_date()
            self.edit_task_due_date_entry.delete(0, 'end')
            self.edit_task_due_date_entry.insert(0, selected_date)
        
        cal.bind("<<CalendarSelected>>", on_date_selected)
        
        if due_date:
            try:
                cal.selection_set(due_date)
            except:
                pass
        
        cal.pack(padx=5, pady=5, fill="both", expand=True)

        ctk.CTkLabel(form_frame, text="Category:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        
        self.edit_task_category_optionmenu = ctk.CTkOptionMenu(form_frame, values=self.all_categories)
        self.edit_task_category_optionmenu.set(category_name)
        self.edit_task_category_optionmenu.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkButton(form_frame, text="Save Changes", command=self.save_task_changes,
                      font=ctk.CTkFont(size=16, weight="bold"),
                      fg_color="#A85BC2", hover_color="#C576E0").grid(row=5, column=0, columnspan=2, pady=20)

    def save_task_changes(self):
        if not self.selected_task:
            return # No task selected, do not proceed
        
        task_title = self.edit_task_title_entry.get()
        description = self.edit_task_description_entry.get()
        priority = self.edit_task_priority_optionmenu.get()
        due_date = self.edit_task_due_date_entry.get()
        category_name = self.edit_task_category_optionmenu.get()

        if not task_title:
            messagebox.showwarning("Warning", "Task title cannot be empty.")
            return
        
        if due_date:
            try:
                due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                
                # Check if the due date has passed
                current_date = datetime.now().date()
                if due_date_obj < current_date and category_name != "Completed":
                    # If due date has passed and task is not completed, it should be marked as Missed
                    category_name = "Missed"
                    messagebox.showinfo("Notice", "Due date has passed. Task category set to 'Missed'.")
            except ValueError:
                messagebox.showwarning("Warning", "Due date must be in YYYY-MM-DD format (e.g., 2025-06-30).")
                return
        
        description = description if description else None
        due_date = due_date if due_date else None

        category_id = self.db_manager.get_category_id_by_name(category_name)

        if category_id is None: 
            # Fallback if selected category wasn't found (shouldn't happen if list is populated correctly)
            # or if "No Categories" was selected and no categories exist.
            default_category_id = self.db_manager.get_category_id_by_name("On-going")
            if default_category_id is not None:
                category_id = default_category_id
            else:
                messagebox.showwarning("Warning", "No valid categories available. Please add a category first.")
                return
        
        task_id = self.selected_task
        # Get the current filter before updating
        current_filter = self.get_current_filter()
        
        if self.db_manager.update_task(task_id, task_title, description, priority, due_date, category_id):
            # Show success popup
            messagebox.showinfo("Success", "Task updated successfully!")
              # Refresh the task list with the current filter
            self.show_tasks_page(current_filter)
            # Show updated task details
            self.show_task_detail(task_id)
        else:
            messagebox.showerror("Error", "Failed to update task. Check console for database errors.")
            
    def show_task_detail(self, task_id):
        # Note: task_id is already stored in self.selected_task by the click handler
        
        # Ensure the detail pane exists and is visible before fetching task data
        # This gives the appearance of instant responsiveness
        if not hasattr(self, 'detail_pane') or not self.detail_pane_visible:
            # Create a fresh detail pane immediately
            self.detail_pane = ctk.CTkFrame(self, width=self.detail_pane_width, fg_color="#F3E6F8", corner_radius=0)
            self.detail_pane.pack(side="right", fill="y")
            # Prevent the pane from resizing smaller than our defined width
            self.detail_pane.pack_propagate(False)
            self.detail_pane_visible = True
            
            # Create an immediate loading message while fetching data
            loading_label = ctk.CTkLabel(
                self.detail_pane,
                text="Loading task details...",
                font=ctk.CTkFont(size=16),
                text_color="#A85BC2"
            )
            loading_label.pack(expand=True)
            self.update_idletasks()  # Force immediate UI update
            
        # Now fetch the task details from the database
        task = self.get_task_by_id(task_id)
        if not task:
            print(f"Error: Could not find task with ID {task_id}")
            # If task no longer exists, hide the detail pane
            self.hide_task_detail()
            return
            
        # Unpack task data
        task_id, title, description, priority, due_date, category_name = task
        
        # Clear existing content in detail pane
        for widget in self.detail_pane.winfo_children():
            widget.destroy()
            
        # Create a close button at the top right
        close_btn = ctk.CTkButton(
            self.detail_pane,
            text="✕",
            width=30,
            height=30,
            fg_color="transparent",
            text_color="#A85BC2",
            hover_color="#E5C6F2",
            corner_radius=5,
            command=self.hide_task_detail
        )
        close_btn.pack(anchor="ne", padx=10, pady=10)

        # Task title
        ctk.CTkLabel(
            self.detail_pane,
            text="Task Details",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#A85BC2"
        ).pack(anchor="nw", padx=20, pady=(0, 20))
        
        # Create detail fields
        fields_frame = ctk.CTkFrame(self.detail_pane, fg_color="transparent")
        fields_frame.pack(fill="x", padx=20, pady=0)
        
        # Title
        ctk.CTkLabel(
            fields_frame, 
            text="Title:", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#6A057F"
        ).pack(anchor="w", pady=(5, 0))
        
        ctk.CTkLabel(
            fields_frame,
            text=title,
            font=ctk.CTkFont(size=16),
            wraplength=280,
            text_color="#333333"
        ).pack(anchor="w", pady=(0, 10), fill="x")
        
        # Due Date
        ctk.CTkLabel(
            fields_frame, 
            text="Due Date:", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#6A057F"
        ).pack(anchor="w", pady=(5, 0))
        
        due_date_text = f"{due_date}" if due_date else "Not set"
        ctk.CTkLabel(
            fields_frame,
            text=due_date_text,
            font=ctk.CTkFont(size=16),
            text_color="#333333"
        ).pack(anchor="w", pady=(0, 10))
        
        # Category
        ctk.CTkLabel(
            fields_frame, 
            text="Category:", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#6A057F"
        ).pack(anchor="w", pady=(5, 0))
        
        ctk.CTkLabel(
            fields_frame,
            text=category_name,
            font=ctk.CTkFont(size=16),
            text_color="#333333"
        ).pack(anchor="w", pady=(0, 10))
        
        # Priority
        ctk.CTkLabel(
            fields_frame, 
            text="Priority:", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#6A057F"
        ).pack(anchor="w", pady=(5, 0))
        
        priority_text = priority
        ctk.CTkLabel(
            fields_frame,
            text=priority_text,
            font=ctk.CTkFont(size=16),
            text_color="#333333"
        ).pack(anchor="w", pady=(0, 10))
        
        # Description
        ctk.CTkLabel(
            fields_frame, 
            text="Description:", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#6A057F"
        ).pack(anchor="w", pady=(5, 0))
        
        description_text = description if description else "No description"
        desc_label = ctk.CTkLabel(
            fields_frame,
            text=description_text,
            font=ctk.CTkFont(size=16),
            wraplength=280,
            text_color="#333333",
            justify="left"
        )
        desc_label.pack(anchor="w", pady=(0, 20), fill="x")
        
        # Add action buttons
        btn_frame = ctk.CTkFrame(self.detail_pane, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        edit_btn = ctk.CTkButton(
            btn_frame,
            text="Edit Task",
            command=lambda: self.show_edit_task_form(task_id),
            fg_color="#A85BC2",
            hover_color="#C576E0",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=35
        )
        edit_btn.pack(fill="x", pady=(0, 10))
        
        delete_btn = ctk.CTkButton(
            btn_frame,
            text="Delete Task",
            command=lambda: self.confirm_delete_task(task_id),
            fg_color="#E57373",
            hover_color="#EF5350",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=35
        )
        delete_btn.pack(fill="x")
    
    def hide_task_detail(self):
        if self.detail_pane_visible:
            self.detail_pane.pack_forget()
            self.detail_pane_visible = False
            # Clear the selected task ID so we can select the same task again
            self.selected_task = None
    
    def get_task_by_id(self, task_id):
        # Query the database for a specific task
        query = """
            SELECT t.task_id, t.task_title, t.description, p.priority_name, t.due_date, tc.category_name 
            FROM tasks t 
            JOIN task_category tc ON t.category_id = tc.category_id 
            LEFT JOIN priority p ON t.priority_id = p.priority_id
            WHERE t.task_id = ?
        """
        result = self.db_manager._fetch_one(query, (task_id,))
        return result

    def show_edit_task_form(self, task_id):
        # Clear detail pane first
        for widget in self.detail_pane.winfo_children():
            widget.destroy()
            
        task = self.get_task_by_id(task_id)
        if not task:
            print(f"Error: Could not find task with ID {task_id}")
            return
            
        task_id, title, description, priority, due_date, category_name = task
        
        # Detail heading
        ctk.CTkLabel(
            self.detail_pane,
            text="Edit Task",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#A85BC2"
        ).pack(anchor="nw", padx=20, pady=(20, 20))
        
        # Create edit form
        form_frame = ctk.CTkScrollableFrame(self.detail_pane, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=20, pady=0)
        
        # Title
        ctk.CTkLabel(
            form_frame, 
            text="Title:", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#6A057F"
        ).pack(anchor="w", pady=(5, 0))
        
        title_entry = ctk.CTkEntry(form_frame, width=280)
        title_entry.insert(0, title)
        title_entry.pack(anchor="w", pady=(0, 10), fill="x")
        
        # Category
        ctk.CTkLabel(
            form_frame, 
            text="Category:", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#6A057F"
        ).pack(anchor="w", pady=(5, 0))
        
        # Filter out "Completed" and "Missed" categories for direct selection
        editable_categories = [cat for cat in self.all_categories if cat not in ["Completed", "Missed"]]
        if not editable_categories:
            editable_categories = ["On-going"]  # Fallback
            
        category_menu = ctk.CTkOptionMenu(form_frame, values=editable_categories)
        if category_name in editable_categories:
            category_menu.set(category_name)
        else:
            # Default to first category if current one is not editable
            category_menu.set(editable_categories[0])
        category_menu.pack(anchor="w", pady=(0, 10), fill="x")
        
        # Due Date
        ctk.CTkLabel(
            form_frame, 
            text="Due Date:", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#6A057F"
        ).pack(anchor="w", pady=(5, 0))
        
        # Date entry and calendar in the same frame
        due_date_var = ctk.StringVar(value=due_date if due_date else "")
        
        date_label_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        date_label_frame.pack(fill="x", pady=(0, 5))
        
        due_date_entry = ctk.CTkEntry(date_label_frame, width=280, textvariable=due_date_var)
        due_date_entry.pack(fill="x", expand=True)
        
        # Calendar frame
        calendar_frame = ctk.CTkFrame(form_frame, fg_color="#FFFFFF", corner_radius=5)
        calendar_frame.pack(fill="x", pady=(0, 10), padx=5)
        # Calendar widget directly embedded in the form
        cal = Calendar(calendar_frame, selectmode='day', date_pattern='yyyy-mm-dd',
                       background="#FFFFFF", 
                       selectbackground="#A85BC2",
                       headersbackground="#C576E0",
                       headersforeground="white",
                       normalbackground="#FFFFFF",
                       showweeknumbers=False, showothermonthdays=True,
                       font=("Arial", 10),
                       showmonth=True,
                       foreground="black")
        
        def on_date_selected(event=None):
            selected_date = cal.get_date()
            due_date_var.set(selected_date)
        
        cal.bind("<<CalendarSelected>>", on_date_selected)
        
        if due_date:
            try:
                cal.selection_set(due_date)
            except:
                pass
        
        cal.pack(padx=5, pady=5, fill="both", expand=True)
        
        # Priority
        ctk.CTkLabel(
            form_frame, 
            text="Priority:", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#6A057F"
        ).pack(anchor="w", pady=(5, 0))
        
        priority_menu = ctk.CTkOptionMenu(form_frame, values=["Urgent", "Not urgent"])
        priority_menu.set(priority if priority in ["Urgent", "Not urgent"] else "Not urgent")
        priority_menu.pack(anchor="w", pady=(0, 10), fill="x")
        
        # Description
        ctk.CTkLabel(
            form_frame, 
            text="Description:", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#6A057F"
        ).pack(anchor="w", pady=(5, 0))
        
        description_textbox = ctk.CTkTextbox(form_frame, height=100, width=280)
        if description:
            description_textbox.insert("1.0", description)
        description_textbox.pack(anchor="w", pady=(0, 20), fill="x")
        
        # Button Frame
        btn_frame = ctk.CTkFrame(self.detail_pane, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Define save_habit function
        def save_habit():
            new_title = title_entry.get().strip()
            new_category = category_menu.get()
            new_due_date = due_date_var.get().strip()
            new_priority = priority_menu.get()
            new_description = description_textbox.get("1.0", ctk.END).strip()

            if not new_title:
                messagebox.showwarning("Warning", "Task title cannot be empty.")
                return

            if new_due_date:
                try:
                    datetime.strptime(new_due_date, '%Y-%m-%d')
                except ValueError:
                    messagebox.showwarning("Warning", "Due date must be in YYYY-MM-DD format (e.g., 2025-06-30).")
                    return

            category_id = self.db_manager.get_category_id_by_name(new_category)
            if category_id is None:
                messagebox.showwarning("Warning", "Invalid category selected.")
                return

            success = self.db_manager.update_task(
                task_id,
                new_title,
                new_description if new_description else None,
                new_priority,
                new_due_date if new_due_date else None,
                category_id
            )
            if success:
                messagebox.showinfo("Success", "Task updated successfully!")
                self.hide_task_detail()
                self.show_tasks_page(self.get_current_filter())
            else:
                messagebox.showerror("Error", "Failed to update task.")

        # Define delete_habit function
        def delete_habit():
            if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this task?"):
                success = self.db_manager.delete_task(task_id)
                if success:
                    messagebox.showinfo("Success", "Task deleted successfully!")
                    self.hide_task_detail()
                    self.show_tasks_page(self.get_current_filter())
                else:
                    messagebox.showerror("Error", "Failed to delete task.")

        # Save button (now on the left)
        ctk.CTkButton(
            btn_frame,
            text="Save",
            fg_color="#4CAF50",
            hover_color="#388E3C",
            command=save_habit
        ).pack(side="left", padx=(0, 10), fill="x", expand=True)
        
        # Delete button (now on the right)
        ctk.CTkButton(
            btn_frame,
            text="Delete",
            fg_color="#FF5252",
            hover_color="#FF1744",
            command=delete_habit
        ).pack(side="left", padx=(0, 10), fill="x", expand=True)
    
    def show_habit_page(self):
        """Display the habit page with recurring tasks grouped by recurrence pattern."""
        # Hide any open detail pane
        self.selected_task = None
        self.detail_pane_visible = False
        
        # Hide task detail pane if it exists
        if hasattr(self, 'task_detail_pane'):
            self.task_detail_pane.pack_forget()
        
        # Hide calendar detail pane if it exists
        if hasattr(self, 'detail_pane'):
            self.detail_pane.pack_forget()
            
        self.navbar.pack_forget()
        self.content.pack_forget()
        self.content.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.clear_content()
        
        # Set current page
        self.current_page = "habit"
        
        # Add heading for the habit page
        ctk.CTkLabel(
            self.content,
            text="Habits & Recurring Tasks",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#A85BC2"
        ).pack(anchor="nw", pady=(10, 0), padx=10)
        
        # Create a scrollable frame for habits
        habits_scroll_frame = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        habits_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Get all recurring tasks from the database
        recurring_tasks = self.db_manager.get_recurring_tasks(user_id=self.current_user_id)
        
        # Group tasks by recurrence pattern
        daily_tasks = []
        monthly_tasks = []
        annual_tasks = []
        other_tasks = []
        
        for task in recurring_tasks:
            rtask_id, rtask_title, description, start_date, recurrence_pattern, last_completed_date, status = task
            
            if recurrence_pattern.lower() == 'daily':
                daily_tasks.append(task)
            elif recurrence_pattern.lower() == 'monthly':
                monthly_tasks.append(task)
            elif recurrence_pattern.lower() == 'annual' or recurrence_pattern.lower() == 'yearly':
                annual_tasks.append(task)
            else:
                other_tasks.append(task)
        
        # Add button to create a new recurring task at the top
        add_habit_btn = ctk.CTkButton(
            habits_scroll_frame,
            text="Create New Habit",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#C576E0",
            hover_color="#A85BC2",
            command=self.show_add_recurring_task_dialog
        )
        add_habit_btn.pack(pady=(0, 15), anchor="e", padx=10)
        
        # If no recurring tasks found
        if not recurring_tasks:
            ctk.CTkLabel(
                habits_scroll_frame,
                text="No recurring tasks found. Create your first habit!",
                font=ctk.CTkFont(size=16),
                text_color="#6A057F"
            ).pack(pady=20)
            return
        
        # Display Daily Tasks
        if daily_tasks:
            self._create_habit_section(habits_scroll_frame, "Daily Habits", daily_tasks)
        
        # Display Monthly Tasks
        if monthly_tasks:
            self._create_habit_section(habits_scroll_frame, "Monthly Habits", monthly_tasks)
        
        # Display Annual Tasks
        if annual_tasks:
            self._create_habit_section(habits_scroll_frame, "Annual Habits", annual_tasks)
        
        # Display Other Tasks with custom recurrence patterns
        if other_tasks:
            self._create_habit_section(habits_scroll_frame, "Other Recurring Tasks", other_tasks)
    
    def _create_habit_section(self, parent_frame, section_title, tasks):
        """Helper method to create a section of habits with the given title and tasks."""
        # Create a section frame with a title
        section_frame = ctk.CTkFrame(parent_frame, fg_color="#F0E6F5", corner_radius=10)
        section_frame.pack(fill="x", pady=8, padx=5)
        
        # Add section title
        ctk.CTkLabel(
            section_frame,
            text=section_title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#6A057F"
        ).pack(anchor="nw", pady=(10, 5), padx=10)
        
        # Add a separator line
        separator = ctk.CTkFrame(section_frame, height=2, fg_color="#D1B4E0")
        separator.pack(fill="x", padx=10, pady=(0, 10))
        
        philippines_timezone = pytz.timezone('Asia/Manila')
        current_local_date = datetime.now(philippines_timezone).date()
        
        for task in tasks:
            rtask_id, rtask_title, description, start_date, recurrence_pattern, last_completed_date, status = task
            
            # Determine colors based on status
            is_completed = (status == 'Completed')
            bg_color = "#C8E6C9" if is_completed else "white"  # Light green if completed
            
            # Create task card
            task_frame = ctk.CTkFrame(section_frame, fg_color=bg_color, corner_radius=8,
                                    border_width=1, border_color="#E5C6F2")
            task_frame.pack(fill="x", pady=5, padx=10)
            
            # Layout the task card
            task_frame.grid_columnconfigure(0, weight=0)  # For checkbox
            task_frame.grid_columnconfigure(1, weight=1)  # For title and description
            task_frame.grid_columnconfigure(2, weight=0)  # For last completed
            task_frame.grid_rowconfigure(0, weight=0)
            task_frame.grid_rowconfigure(1, weight=0)
            
            # Create checkbox for completing the habit
            status_var = ctk.StringVar(value="on" if is_completed else "off")
            status_checkbox = ctk.CTkCheckBox(
                task_frame, 
                text="", 
                variable=status_var,
                onvalue="on", 
                offvalue="off",
                command=lambda tid=rtask_id, svar=status_var: self.toggle_habit_completion(tid, svar)
            )
            status_checkbox.grid(row=0, column=0, rowspan=2, padx=(10, 0), pady=10, sticky="nsew")
            
            # Prevent event propagation on checkbox
            def prevent_propagation(e):
                e.widget.focus_set()
                return "break"
            status_checkbox.bind("<Button-1>", prevent_propagation, add="+")
            
            # Display task title
            ctk.CTkLabel(
                task_frame, 
                text=rtask_title, 
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#333333", 
                anchor="w", 
                wraplength=400
            ).grid(row=0, column=1, padx=(10, 5), pady=(10, 0), sticky="ew")
            
            # Display task description if available
            if description:
                ctk.CTkLabel(
                    task_frame, 
                    text=description, 
                    font=ctk.CTkFont(size=14),
                    text_color="#666666", 
                    anchor="w", 
                    wraplength=400
                ).grid(row=1, column=1, padx=(10, 5), pady=(0, 10), sticky="new")
            
            # Display last completed date if available
            last_completed_text = f"Last done: {last_completed_date}" if last_completed_date else "Never completed"
            ctk.CTkLabel(
                task_frame, 
                text=last_completed_text,
                font=ctk.CTkFont(size=12),
                text_color="#888888", 
                anchor="e"
            ).grid(row=0, column=2, padx=(5, 10), pady=(10, 0), sticky="ne")
            
            # Add edit button
            edit_btn = ctk.CTkButton(
                task_frame,
                text="Edit",
                font=ctk.CTkFont(size=12),
                width=60,
                height=24,
                fg_color="#9575CD",
                hover_color="#7E57C2",
                command=lambda tid=rtask_id: self.show_edit_recurring_task_dialog(tid)
            )
            edit_btn.grid(row=1, column=2, padx=(5, 10), pady=(0, 10), sticky="se")
    
    def show_add_recurring_task_dialog(self):
        """Show dialog to add a new recurring task."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Habit")
        dialog.geometry("500x450")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Title
        ctk.CTkLabel(
            dialog,
            text="Create New Habit",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#6A057F"
        ).pack(pady=(20, 10), padx=20)
        
        # Task title
        ctk.CTkLabel(
            dialog, 
            text="Habit Title:",
            font=ctk.CTkFont(size=14),
            anchor="w"
        ).pack(anchor="w", padx=20, pady=(10, 0))
        
        title_entry = ctk.CTkEntry(
            dialog,
            width=460,
            placeholder_text="Enter habit title..."
        )
        title_entry.pack(padx=20, pady=5, fill="x")
        
        # Description
        ctk.CTkLabel(
            dialog,
            text="Description (Optional):",
            font=ctk.CTkFont(size=14),
            anchor="w"
        ).pack(anchor="w", padx=20, pady=(10, 0))
        
        description_entry = ctk.CTkEntry(
            dialog,
            width=460,
            placeholder_text="Enter habit description..."
        )
        description_entry.pack(padx=20, pady=5, fill="x")
        
        # Start date
        ctk.CTkLabel(
            dialog,
            text="Start Date:",
            font=ctk.CTkFont(size=14),
            anchor="w"
        ).pack(anchor="w", padx=20, pady=(10, 0))
        
        def pick_date():
            date_dialog = ctk.CTkToplevel(dialog)
            date_dialog.title("Select Date")
            date_dialog.geometry("300x300")
            date_dialog.transient(dialog)
            date_dialog.grab_set()
            
            cal = Calendar(date_dialog, selectmode='day', date_pattern='yyyy-mm-dd')
            cal.pack(pady=20)
            
            def set_date():
                selected_date = cal.get_date()
                start_date_entry.delete(0, ctk.END)
                start_date_entry.insert(0, selected_date)
                date_dialog.destroy()
            
            ctk.CTkButton(
                date_dialog,
                text="Select",
                command=set_date
            ).pack(pady=10)
        
        date_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        date_frame.pack(fill="x", padx=20, pady=5)
        
        start_date_entry = ctk.CTkEntry(date_frame, width=360)
        start_date_entry.pack(side="left", fill="x", expand=True)
        
        # Set default date to today
        philippines_timezone = pytz.timezone('Asia/Manila')
        current_local_date = datetime.now(philippines_timezone).date().strftime('%Y-%m-%d')
        start_date_entry.insert(0, current_local_date)
        
        date_picker_btn = ctk.CTkButton(
            date_frame,
            text="📅",
            width=30,
            command=pick_date
        )
        date_picker_btn.pack(side="right", padx=(5, 0))
        
        # Recurrence pattern
        ctk.CTkLabel(
            dialog,
            text="Recurrence Pattern:",
            font=ctk.CTkFont(size=14),
            anchor="w"
        ).pack(anchor="w", padx=20, pady=(10, 0))
        
        recurrence_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        recurrence_frame.pack(fill="x", padx=20, pady=5)
        
        recurrence_var = ctk.StringVar(value="Daily")
        recurrence_options = ["Daily", "Weekly", "Monthly", "Annual"]
        
        for i, option in enumerate(recurrence_options):
            recurrence_btn = ctk.CTkRadioButton(
                recurrence_frame,
                text=option,
                variable=recurrence_var,
                value=option,
                font=ctk.CTkFont(size=14)
            )
            recurrence_btn.pack(side="left", padx=(0 if i == 0 else 10, 0))
        
        # Buttons
        buttons_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            fg_color="#E0E0E0",
            text_color="#333333",
            hover_color="#C0C0C0",
            command=dialog.destroy
        ).pack(side="left", padx=(0, 10), fill="x", expand=True)
        
        def save_habit():
            rtask_title = title_entry.get().strip()
            description = description_entry.get().strip()
            start_date = start_date_entry.get().strip()
            recurrence_pattern = recurrence_var.get()
            
            if not rtask_title:
                messagebox.showwarning("Warning", "Please enter a habit title.")
                return
                
            # Add the habit to the database
            success = self.db_manager.add_recurring_task(
                self.current_user_id,
                rtask_title,
                description if description else None,
                start_date,
                recurrence_pattern
            )
            
            if success:
                messagebox.showinfo("Success", "New habit created successfully!")
                dialog.destroy()
                # Refresh the habit page
                if self.current_page == "habit":
                    self.show_habit_page()
            else:
                messagebox.showerror("Error", "Failed to create habit. Please try again.")
        
        ctk.CTkButton(
            buttons_frame,
            text="Save",
            fg_color="#C576E0",
            hover_color="#A85BC2",
            command=save_habit
        ).pack(side="right", fill="x", expand=True)
    
    def show_edit_recurring_task_dialog(self, rtask_id):
        """Show dialog to edit an existing recurring task."""
        # Get the recurring task from database
        tasks = self.db_manager._fetch_all(
            "SELECT rtask_id, rtask_title, description, start_date, recurrence_pattern, last_completed_date FROM recurring_tasks WHERE rtask_id = ?", 
            (rtask_id,)
        )
        
        if not tasks or len(tasks) == 0:
            messagebox.showerror("Error", "Recurring task not found.")
            return
        
        task = tasks[0]
        rtask_id, rtask_title, description, start_date, recurrence_pattern, last_completed_date = task
        
        # Create dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Habit")
        dialog.geometry("500x490")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Title
        ctk.CTkLabel(
            dialog,
            text="Edit Habit",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#6A057F"
        ).pack(pady=(20, 10), padx=20)
        
        # Task title
        ctk.CTkLabel(
            dialog, 
            text="Habit Title:",
            font=ctk.CTkFont(size=14),
            anchor="w"
        ).pack(anchor="w", padx=20, pady=(10, 0))
        
        title_entry = ctk.CTkEntry(
            dialog,
            width=460,
            placeholder_text="Enter habit title..."
        )
        title_entry.insert(0, rtask_title)
        title_entry.pack(padx=20, pady=5, fill="x")
        
        # Description
        ctk.CTkLabel(
            dialog,
            text="Description (Optional):",
            font=ctk.CTkFont(size=14),
            anchor="w"
        ).pack(anchor="w", padx=20, pady=(10, 0))
        
        description_entry = ctk.CTkEntry(
            dialog,
            width=460,
            placeholder_text="Enter habit description..."
        )
        if description:
            description_entry.insert(0, description)
        description_entry.pack(padx=20, pady=5, fill="x")
        
        # Start date
        ctk.CTkLabel(
            dialog,
            text="Start Date:",
            font=ctk.CTkFont(size=14),
            anchor="w"
        ).pack(anchor="w", padx=20, pady=(10, 0))
        
        def pick_date():
            date_dialog = ctk.CTkToplevel(dialog)
            date_dialog.title("Select Date")
            date_dialog.geometry("300x300")
            date_dialog.transient(dialog)
            date_dialog.grab_set()
            
            cal = Calendar(date_dialog, selectmode='day', date_pattern='yyyy-mm-dd')
            cal.pack(pady=20)
            
            def set_date():
                selected_date = cal.get_date()
                start_date_entry.delete(0, ctk.END)
                start_date_entry.insert(0, selected_date)
                date_dialog.destroy()
            
            ctk.CTkButton(
                date_dialog,
                text="Select",
                command=set_date
            ).pack(pady=10)
        
        date_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        date_frame.pack(fill="x", padx=20, pady=5)
        
        start_date_entry = ctk.CTkEntry(date_frame, width=360)
        start_date_entry.pack(side="left", fill="x", expand=True)
        
        if start_date:
            start_date_entry.insert(0, start_date)
        else:
            # Set default date to today
            philippines_timezone = pytz.timezone('Asia/Manila')
            current_local_date = datetime.now(philippines_timezone).date().strftime('%Y-%m-%d')
            start_date_entry.insert(0, current_local_date)
        
        date_picker_btn = ctk.CTkButton(
            date_frame,
            text="📅",
            width=30,
            command=pick_date
        )
        date_picker_btn.pack(side="right", padx=(5, 0))
        
        # Recurrence pattern
        ctk.CTkLabel(
            dialog,
            text="Recurrence Pattern:",
            font=ctk.CTkFont(size=14),
            anchor="w"
        ).pack(anchor="w", padx=20, pady=(10, 0))
        
        recurrence_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        recurrence_frame.pack(fill="x", padx=20, pady=5)
        
        recurrence_var = ctk.StringVar(value=recurrence_pattern.capitalize() if recurrence_pattern else "Daily")
        recurrence_options = ["Daily", "Weekly", "Monthly", "Annual"]
        
        for i, option in enumerate(recurrence_options):
            recurrence_btn = ctk.CTkRadioButton(
                recurrence_frame,
                text=option,
                variable=recurrence_var,
                value=option,
                font=ctk.CTkFont(size=14)
            )
            recurrence_btn.pack(side="left", padx=(0 if i == 0 else 10, 0))
        
        # Last completed date (display only)
        if last_completed_date:
            # Create a frame for the last completed date to place it on the right
            last_completed_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            last_completed_frame.pack(fill="x", padx=20, pady=(10, 0))
            
            # Add explanation text
            ctk.CTkLabel(
                last_completed_frame,
                text="Last done:",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#6A057F"
            ).pack(side="left")
            
            # Add date
            ctk.CTkLabel(
                last_completed_frame,
                text=last_completed_date,
                font=ctk.CTkFont(size=14, slant="italic"),
                text_color="#888888"
            ).pack(side="left", padx=(5, 0))
        
        # Define action functions
        def delete_habit():
            if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this habit?"):
                success = self.db_manager.delete_recurring_task(rtask_id)
                if success:
                    messagebox.showinfo("Success", "Habit deleted successfully!")
                    dialog.destroy()
                    # Refresh the habit page
                    if self.current_page == "habit":
                        self.show_habit_page()
                else:
                    messagebox.showerror("Error", "Failed to delete habit. Please try again.")
        
        def save_habit():
            new_rtask_title = title_entry.get().strip()
            new_description = description_entry.get().strip()
            new_start_date = start_date_entry.get().strip()
            new_recurrence_pattern = recurrence_var.get().lower()
            
            if not new_rtask_title:
                messagebox.showwarning("Warning", "Please enter a habit title.")
                return
            
            # Update the habit in the database
            success = self.db_manager.update_recurring_task(
                rtask_id,
                new_rtask_title,
                new_description if new_description else None,
                new_start_date,
                new_recurrence_pattern
            )
            
            if success:
                messagebox.showinfo("Success", "Habit updated successfully!")
                dialog.destroy()
                # Refresh the habit page
                if self.current_page == "habit":
                    self.show_habit_page()
            else:
                messagebox.showerror("Error", "Failed to update habit. Please try again.")
        
        # Buttons
        buttons_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=20, pady=20)
        
        # Save button (now on the left)
        ctk.CTkButton(
            buttons_frame,
            text="Save",
            fg_color="#4CAF50",
            hover_color="#388E3C",
            command=save_habit
        ).pack(side="left", padx=(0, 10), fill="x", expand=True)
        
        # Delete button (now on the right)
        ctk.CTkButton(
            buttons_frame,
            text="Delete",
            fg_color="#FF5252",
            hover_color="#FF1744",
            command=delete_habit
        ).pack(side="left", padx=(0, 10), fill="x", expand=True)
    
    def toggle_habit_completion(self, rtask_id, status_var):
        """Toggle completion status of a recurring task."""
        philippines_timezone = pytz.timezone('Asia/Manila')
        current_local_date = datetime.now(philippines_timezone).date().strftime('%Y-%m-%d')
        
        if status_var.get() == "on":
            # Mark as completed today and set status to 'Completed'
            self.db_manager.update_recurring_task_completion(rtask_id, current_local_date)
        else:
            # Mark as not completed (remove completion date) and set status to 'Pending'
            self.db_manager.remove_recurring_task_completion(rtask_id, current_local_date)
        
        # Refresh the habit page to show updated status
        self.show_habit_page()

    def confirm_delete_task(self, task_id):
        confirm = messagebox.askyesno(
            title="Confirm Delete",
            message="Are you sure you want to delete this task? This action cannot be undone."
        )
        
        if confirm:
            # Get the current filter before deleting
            current_filter = self.get_current_filter()
            
            success = self.db_manager.delete_task(task_id)
            if success:
                # Show success popup
                messagebox.showinfo("Success", "Task deleted successfully!")
                
                # First hide the detail pane since the task no longer exists
                self.hide_task_detail()
                
                # Determine which page to return to based on where the user came from
                if self.current_page == "calendar":
                    # If user was on calendar page, return there
                    self.show_calendar_page()
                              
                else:
                    # Otherwise, refresh the task list with the current filter
                    self.show_tasks_page(current_filter)
            else:
                messagebox.showerror("Error", "Failed to delete task.")

    def get_current_filter(self):
        """Get the name of the currently selected filter."""
        current_filter = "All Tasks"  # Default
        for btn in self.navbar_nav_items:
            if btn.cget("fg_color") != "transparent":  # This is the selected button
                current_filter = btn.cget("text")
                break
        return current_filter
        
    def update_filter_buttons(self, selected_filter):
        """Update the filter buttons to highlight the selected one."""
        for btn in self.navbar_nav_items:
            if btn.cget("text") == selected_filter:
                btn.configure(fg_color="#A85BC2", text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color="#A85BC2")

    def determine_category_by_date(self, due_date_str):
        """Determine the task category based on the due date."""
        if not due_date_str:
            return self.on_going_category_id

        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            today = datetime.now().date()
            
            if due_date < today:
                return self.missed_category_id
            else:
                return self.on_going_category_id
        except ValueError:
            return self.on_Going_category_id

    def show_add_task_dialog(self):
        # Create the popup window
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Task")
        dialog.geometry("400x600")  # More compact size
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog on the screen
        window_width = 400
        window_height = 600
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        center_x = int((screen_width - window_width) / 2)
        center_y = int((screen_height - window_height) / 2)
        dialog.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

        # Create a scrollable frame
        scroll_container = ctk.CTkScrollableFrame(dialog, fg_color="white", corner_radius=10)
        scroll_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Heading
        ctk.CTkLabel(
            scroll_container,
            text="Add New Task",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#A85BC2"
        ).pack(pady=(10, 20))

        # Title
        ctk.CTkLabel(scroll_container, text="Title:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#6A057F").pack(anchor="w")
        title_entry = ctk.CTkEntry(scroll_container, placeholder_text="Task title")
        title_entry.pack(fill="x", pady=(0, 15))

        # Description
        ctk.CTkLabel(scroll_container, text="Description:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#6A057F").pack(anchor="w")
        description_entry = ctk.CTkTextbox(scroll_container, height=80)  # Reduced height
        description_entry.pack(fill="x", pady=(0, 15))

        # Priority
        ctk.CTkLabel(scroll_container, text="Priority:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#6A057F").pack(anchor="w")
        priority_menu = ctk.CTkOptionMenu(scroll_container, values=["Not urgent", "Urgent"])
        priority_menu.set("Not urgent")
        priority_menu.pack(fill="x", pady=(0, 15))

        # Due Date
        ctk.CTkLabel(scroll_container, text="Due Date:", font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(anchor="w")
        due_date_var = ctk.StringVar()
        due_date_entry = ctk.CTkEntry(scroll_container, textvariable=due_date_var)
        due_date_entry.pack(fill="x", pady=(0, 5))

        # Calendar Frame
        calendar_frame = ctk.CTkFrame(scroll_container, fg_color="#FFFFFF", corner_radius=5)
        calendar_frame.pack(fill="x", pady=(0, 10), padx=5)

        cal = Calendar(calendar_frame, selectmode='day', date_pattern='yyyy-mm-dd',
                      background="#FFFFFF",
                      selectbackground="#A85BC2",
                      headersbackground="#C576E0",
                      headersforeground="white",
                      normalbackground="#FFFFFF",
                      showweeknumbers=False, showothermonthdays=True,
                      font=("Arial", 10),
                      showmonth=True,
                      foreground="black")

        def on_date_selected(event=None):
            due_date_var.set(cal.get_date())
        
        cal.bind("<<CalendarSelected>>", on_date_selected)
        cal.pack(padx=5, pady=5, fill="x")

        # Add Task Button
        def save_task():
            title = title_entry.get().strip()
            if not title:
                messagebox.showerror("Error", "Title is required!")
                return

            description = description_entry.get("1.0", ctk.END).strip()
            due_date = due_date_var.get()
            priority = priority_menu.get()

            # Determine category based on due date
            category_id = self.determine_category_by_date(due_date)

            success = self.db_manager.add_task(
                self.current_user_id,
                title,
                description if description else None,
                priority,
                due_date if due_date else None,
                category_id
            )

            if success:
                messagebox.showinfo("Success", "Task added successfully!")
                dialog.destroy()
                self.show_tasks_page("All Tasks")
            else:
                messagebox.showerror("Error", "Failed to add task!")

        save_btn = ctk.CTkButton(
            scroll_container,
            text="Add Task",
            command=save_task,
            fg_color="#A85BC2",
            hover_color="#C576E0"
        )
        save_btn.pack(fill="x", pady=20)

    def show_search_dialog(self):
        # Create the popup window
        dialog = ctk.CTkToplevel(self)
        dialog.title("Search Task")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog on the screen
        window_width = 400
        window_height = 300
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        center_x = int((screen_width - window_width) / 2)
        center_y = int((screen_height - window_height) / 2)
        dialog.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

        # Create content frame
        content_frame = ctk.CTkFrame(dialog, fg_color="white", corner_radius=10)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Heading
        ctk.CTkLabel(
            content_frame,
            text="Search Task",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#A85BC2"
        ).pack(pady=(20, 30))

        # Search entry with icon
        search_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(0, 20))

        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(
            search_frame, 
            placeholder_text="Enter task title to search...",
            textvariable=search_var,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        search_entry.pack(fill="x", side="left", expand=True)

        # Results combobox
        results_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        results_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Label for results
        results_label = ctk.CTkLabel(
            results_frame,
            text="No results found",
            font=ctk.CTkFont(size=12),
            text_color="#666666"
        )
        results_label.pack(fill="x", pady=(10, 0))

        # Combobox for results
        results_combobox = ttk.Combobox(
            results_frame,
            state="readonly",
            height=5,
            font=("Arial", 12)
        )
        results_combobox.pack(fill="x", pady=(5, 0))

        # Dictionary to store task IDs mapped to their display strings
        task_map = {}
        # Dictionary to store type of task (regular or recurring)
        task_type = {}

        def on_search(*args):
            search_text = search_var.get().strip().lower()
            if len(search_text) < 2:
                results_label.configure(text="Enter at least 2 characters to search")
                results_combobox['values'] = ()
                task_map.clear()
                task_type.clear()
                return

            # Search for regular tasks in database
            regular_query = """
                SELECT t.task_id, t.task_title, t.due_date, tc.category_name
                FROM tasks t
                JOIN task_category tc ON t.category_id = tc.category_id
                WHERE LOWER(t.task_title) LIKE ? AND t.user_id = ?
                ORDER BY t.due_date DESC
            """
            search_pattern = f"%{search_text}%"
            regular_results = self.db_manager._fetch_all(regular_query, (search_pattern, self.current_user_id))
            
            # Search for recurring tasks in database
            recurring_query = """
                SELECT rtask_id, rtask_title, start_date, recurrence_pattern, last_completed_date, status
                FROM recurring_tasks
                WHERE LOWER(rtask_title) LIKE ? AND user_id = ?
                ORDER BY recurrence_pattern
            """
            recurring_results = self.db_manager._fetch_all(recurring_query, (search_pattern, self.current_user_id))

            if not regular_results and not recurring_results:
                results_label.configure(text="No matching tasks found")
                results_combobox['values'] = ()
                task_map.clear()
                task_type.clear()
                return

            # Format results for display
            display_results = []
            task_map.clear()
            task_type.clear()
            
            # Add regular tasks
            for task_id, title, due_date, category in regular_results:
                if due_date:
                    display_text = f"{title} ({category} - Due: {due_date})"
                else:
                    display_text = f"{title} ({category})"
                display_results.append(display_text)
                task_map[display_text] = task_id
                task_type[display_text] = "regular"
            
            # Add recurring tasks
            for rtask_id, rtask_title, start_date, recurrence_pattern, last_completed_date, status in recurring_results:
                recurring_prefix = "🔄 "  # Add a recurring icon
                display_text = f"{recurring_prefix}{rtask_title} (Recurring - {recurrence_pattern.capitalize()} - {status})"
                display_results.append(display_text)
                task_map[display_text] = rtask_id
                task_type[display_text] = "recurring"

            total_results = len(regular_results) + len(recurring_results)
            results_label.configure(text=f"Found {total_results} matching tasks")
            results_combobox['values'] = display_results
            if display_results:
                results_combobox.set(display_results[0])

        def on_select(event):
            selected = results_combobox.get()
            if selected and selected in task_map:
                item_id = task_map[selected]
                dialog.destroy()
                
                if task_type[selected] == "regular":
                    # Regular task selected
                    # Get the category of the selected task
                    query = """
                        SELECT tc.category_name 
                        FROM tasks t 
                        JOIN task_category tc ON t.category_id = tc.category_id 
                        WHERE t.task_id = ?
                    """
                    result = self.db_manager._fetch_one(query, (item_id,))
                    if result:
                        category_name = result[0]
                        # Show the appropriate filtered page
                        self.show_tasks_page(category_name)
                        # Show the task details
                        self.show_task_detail(item_id)
                else:
                    # Recurring task selected
                    # Show the habit page
                    self.show_habit_page()
                    # Open the edit dialog for the recurring task
                    self.show_edit_recurring_task_dialog(item_id)

        # Bind events
        search_var.trace('w', on_search)
        results_combobox.bind('<<ComboboxSelected>>', on_select)
        
        # Set focus to search entry
        search_entry.focus_set()
        
    def create_task_card(self, task_frame, task):
        """Helper function to create a task card with unified styling"""
        # Define color constants
        ONGOING_BG_COLOR = "white"  # Default for uncompleted, non-missed tasks
        MISSED_BG_COLOR = "#FFCDD2" # Light Red
        COMPLETED_BG_COLOR = "#C8E6C9" # Light Green

        task_id = task['id']  # Keep as 'id' since this is used for calendar view dictionary
        category_name = task['category']
        due_date = task.get('due_date', None)
        title = task['title']  # Keep as 'title' since this is used for calendar view dictionarytle']  # Keep as 'title' since this is used for calendar view dictionary
        description = task.get('description', '')
        priority = task.get('priority', '')

        # Get current date for comparison
        philippines_timezone = pytz.timezone('Asia/Manila')
        current_local_date = datetime.now(philippines_timezone).date()

        # Determine task status and colors
        frame_bg_color = ONGOING_BG_COLOR
        title_color = "#333333"
        is_completed_by_category = (category_name == "Completed")
        is_missed = False

        if not is_completed_by_category and due_date:
            try:
                due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                if due_date_obj < current_local_date:
                    is_missed = True
                    category_name = "Missed"
            except ValueError:
                pass

        if is_completed_by_category:
            frame_bg_color = COMPLETED_BG_COLOR
            title_color = "gray"
        elif is_missed:
            frame_bg_color = MISSED_BG_COLOR
            title_color = "red"
        
        task_frame.configure(fg_color=frame_bg_color, border_width=1, border_color="#E5C6F2")
        
        # Grid configuration for consistent layout
        task_frame.grid_columnconfigure(0, weight=0)  # For checkbox
        task_frame.grid_columnconfigure(1, weight=1)  # For title and description
        task_frame.grid_columnconfigure(2, weight=0)  # For last completed
        task_frame.grid_rowconfigure(0, weight=0)
        task_frame.grid_rowconfigure(1, weight=0)
        task_frame.grid_rowconfigure(2, weight=1)

        # Add checkbox for task completion
        status_var = ctk.StringVar(value="on" if is_completed_by_category else "off")
        status_checkbox = ctk.CTkCheckBox(
            task_frame, 
            text="",
            variable=status_var,
            onvalue="on",
            offvalue="off",
            command=lambda tid=task_id, svar=status_var, current_cat_name=category_name: self.toggle_task_completion(tid, svar, current_cat_name, "All Tasks")
        )
        status_checkbox.grid(row=0, column=0, rowspan=3, padx=(10,0), pady=10, sticky="nsew")
        
        # Prevent checkbox clicks from triggering the task detail view
        def prevent_propagation(e):
            e.widget.focus_set()
            return "break"
        status_checkbox.bind("<Button-1>", prevent_propagation, add="+")

        # Make the entire frame clickable to show task details
        def on_task_click(event, tid=task_id):
            self.selected_task = tid
            self.show_task_detail(tid)
        task_frame.bind("<Button-1>", lambda e, tid=task_id: on_task_click(e, tid))
        task_frame.configure(cursor="hand2")

        # Title with priority
        title_label = ctk.CTkLabel(
            task_frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=title_color,
            anchor="w",
            wraplength=400
        )
        title_label.grid(row=0, column=1, padx=(10, 5), pady=(10, 0), sticky="ew")
        title_label.bind("<Button-1>", lambda e, tid=task_id: on_task_click(e, tid))
        title_label.configure(cursor="hand2")

        # Priority
        if priority:
            display_priority_text = "⚠️ Urgent" if priority == "Urgent" else "Not urgent"
            priority_label = ctk.CTkLabel(
                task_frame,
                text=display_priority_text,
                font=ctk.CTkFont(size=14),
                text_color=title_color,
                anchor="w"
            )
            priority_label.grid(row=1, column=1, padx=(10, 5), pady=(0, 5), sticky="ew")
            priority_label.bind("<Button-1>", lambda e, tid=task_id: on_task_click(e, tid))
            priority_label.configure(cursor="hand2")

        # Description
        if description:
            desc_label = ctk.CTkLabel(
                task_frame,
                text=description,
                font=ctk.CTkFont(size=12),
                text_color=title_color,
                wraplength=400,
                anchor="nw"
            )
            desc_label.grid(row=2, column=1, padx=(10, 5), pady=(0, 10), sticky="new")
            desc_label.bind("<Button-1>", lambda e, tid=task_id: on_task_click(e, tid))
            desc_label.configure(cursor="hand2")

        # Category label
        category_label = ctk.CTkLabel(
            task_frame,
            text=category_name,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#666666",
            anchor="ne"
        )
        # Category label
        category_label = ctk.CTkLabel(
            task_frame,
            text=category_name,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#666666",
            anchor="ne"
        )
        category_label.grid(row=0, column=2, padx=10, pady=(10,0), sticky="ne")
        category_label.bind("<Button-1>", lambda e, tid=task_id: on_task_click(e, tid))
        category_label.configure(cursor="hand2")
        
        # Due date label
        if due_date:
            try:
                due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                if due_date_obj == current_local_date:
                    formatted_date_str = "Due: Today"
                elif due_date_obj == (current_local_date + timedelta(days=1)):
                    formatted_date_str = "Due: Tomorrow"
                else:
                    formatted_date_str = f"Due: {due_date_obj.strftime('%b %d, %Y')}"
            except ValueError:
                formatted_date_str = "Due: Invalid Date"

            due_date_label = ctk.CTkLabel(
                task_frame,
                text=formatted_date_str,
                font=ctk.CTkFont(size=12),
                text_color="#666666",
                anchor="ne",
                justify="right"
            )
            due_date_label.grid(row=1, column=2, padx=10, pady=(0,10), sticky="ne")
            due_date_label.bind("<Button-1>", lambda e, tid=task_id: on_task_click(e, tid))
            due_date_label.configure(cursor="hand2")
            
        # For regular tasks, we don't need to check if they're recurring
        # Since regular tasks and recurring tasks are in separate tables
        # If you want to link them in the future, you could add a recurring_task_id reference in the tasks table
# Application entry point
if __name__ == "__main__":
    app = TimePlanApp()
    app.mainloop()