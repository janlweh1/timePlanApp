import sqlite3
import hashlib
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox
from tkcalendar import Calendar #install sa bash yung tkcalendar "pip install tkcalendar"
from datetime import datetime, timedelta
import babel.numbers

dbName = "timePlanDB.db"

def Connect():
    conn = sqlite3.connect(dbName)
    return conn

def CheckAndUpdateSchema():
    conn = Connect()
    cursor = conn.cursor()
    
    # get current columns in the tasks table
    cursor.execute("PRAGMA table_info(tasks)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    # check if recurrence_pattern column exists
    if 'recurrence_pattern' not in column_names:
        cursor.execute('ALTER TABLE tasks ADD COLUMN recurrence_pattern TEXT')
        conn.commit()
    
    conn.close()

def CreateTable():
    conn = Connect()
    cursor = conn.cursor()
    
    # create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category_id INTEGER,
            priority TEXT,
            due_date TEXT,
            is_recurring INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            time_spent INTEGER DEFAULT 0,
            last_completed_date TEXT,
            user_id INTEGER NOT NULL,
            recurrence_pattern TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES task_category(category_id)
        )
    ''')
    conn.commit()
    conn.close()

    # check and update schema if needed
    CheckAndUpdateSchema()

def AddTask(title, description, category_id, priority, dueDate, isRecurring, user_id, recurrence_pattern=None):
    print(f"Adding task to database: Title={title}, CategoryID={category_id}, Priority={priority}")
    conn = Connect()
    cursor = conn.cursor()
    try:
        cursor.execute('''INSERT INTO tasks (
            title, description, category_id, priority, due_date, is_recurring, 
            last_completed_date, user_id, recurrence_pattern
        ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)''', 
            (title, description, category_id, priority, dueDate, isRecurring, user_id, recurrence_pattern))
        conn.commit()
        print("Task added successfully to database")
    except Exception as e:
        print(f"Database error: {str(e)}")
        raise e
    finally:
        conn.close()

def GetTasksFiltered(user_id, category_filter=None, priority_filter=None):
    conn = Connect()
    cursor = conn.cursor()
    query = """
        SELECT 
            t.id, 
            t.title, 
            t.due_date, 
            c.category_name, 
            t.priority,
            t.last_completed_date,
            date('now', 'localtime') as today
        FROM tasks t
        LEFT JOIN task_category c ON t.category_id = c.category_id
        WHERE t.user_id = ?
    """
    params = [user_id]
    if category_filter and category_filter != "All":
        query += " AND c.category_name = ?"
        params.append(category_filter)
    if priority_filter and priority_filter != "All":
        query += " AND t.priority = ?"
        params.append(priority_filter)
    query += " ORDER BY t.due_date"
    cursor.execute(query, params)
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def DeleteTask(taskId, user_id):
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE task_id = ? AND user_id = ?', (taskId, user_id))
    conn.commit()
    conn.close()

def UpdateTask(taskId, **kwargs):
    conn = Connect()
    cursor = conn.cursor()
    fields = ', '.join([f"{key}=?" for key in kwargs])
    values = list(kwargs.values())
    values.append(taskId)
    cursor.execute(f'UPDATE tasks SET {fields} WHERE task_id = ?', values)
    conn.commit()
    conn.close()

def CreateUserTable():
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def HashPassword(password):
    return hashlib.sha256(password.encode()).hexdigest()

def RegisterUser(username, password):
    conn = Connect()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                       (username, HashPassword(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # username already exists
    finally:
        conn.close()

def AuthenticateUser(username, password):
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                   (username, HashPassword(password)))
    user = cursor.fetchone()
    conn.close()
    return user

def UpdateTaskStatus(taskId, new_status):
    conn = Connect()
    cursor = conn.cursor()
    # Get the category_id for the new_status
    cursor.execute('SELECT category_id FROM task_category WHERE category_name = ?', (new_status,))
    result = cursor.fetchone()
    if result:
        category_id = result[0]
        cursor.execute('UPDATE tasks SET category_id = ? WHERE task_id = ?', (category_id, taskId))
        conn.commit()
    conn.close()

def MarkRecurringTaskComplete(taskId):
    conn = Connect()
    cursor = conn.cursor()
    today = cursor.execute("SELECT date('now', 'localtime')").fetchone()[0]
    cursor.execute('UPDATE tasks SET last_completed_date = ? WHERE task_id = ?', (today, taskId))
    conn.commit()
    conn.close()

def UpdateMissedTasks(user_id):
    conn = Connect()
    cursor = conn.cursor()
    # Get the category_id for 'Missed'
    cursor.execute('SELECT category_id FROM task_category WHERE category_name = ?', ('Missed',))
    result = cursor.fetchone()
    if result:
        missed_category_id = result[0]
        cursor.execute('''
            UPDATE tasks 
            SET category_id = ?
            WHERE user_id = ?
            AND (category_id IS NULL OR category_id NOT IN (
                SELECT category_id FROM task_category WHERE category_name IN ('Recurring', 'Done', 'Missed')
            ))
            AND due_date < date('now', 'localtime')
            AND due_date IS NOT NULL
            AND due_date != ''
        ''', (missed_category_id, user_id))
        conn.commit()
    conn.close()

class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("TimePlan Login")
        self.geometry("350x200")
        self.resizable(False, False)

        # center the window on the screen
        self.center_window()

        CreateUserTable()  # ensure users table exists

        ttk.Label(self, text="Username:").pack(pady=(20, 5))
        self.username_entry = ttk.Entry(self)
        self.username_entry.pack(fill=tk.X, padx=20)

        ttk.Label(self, text="Password:").pack(pady=(10, 5))
        self.password_entry = ttk.Entry(self, show="*")
        self.password_entry.pack(fill=tk.X, padx=20)

        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(pady=20)

        ttk.Button(buttons_frame, text="Login", command=self.login).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Sign Up", command=self.open_signup).pack(side=tk.LEFT, padx=10)

        # protocol for window close button
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # bind enter key to login
        self.bind('<Return>', lambda e: self.login())

    def center_window(self):
        # get screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # calculate position coordinates
        x = (screen_width/2) - (350/2)
        y = (screen_height/2) - (200/2)
        
        # set the position
        self.geometry(f'350x200+{int(x)}+{int(y)}')

    def on_closing(self):
        if tkinter.messagebox.askyesno("Exit", "Are you sure you want to exit the application?"):
            self.destroy()

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            tkinter.messagebox.showerror("Error", "Please enter username and password.")
            return

        user = AuthenticateUser(username, password)
        if user:
            tkinter.messagebox.showinfo("Success", f"Welcome {username}!")
            self.destroy()
            app = TimePlanApp(user[0], username)
            app.mainloop()
        else:
            tkinter.messagebox.showerror("Error", "Invalid username or password.")

    def open_signup(self):
        self.withdraw()
        signup_win = SignUpWindow(self)
        signup_win.grab_set()

class SignUpWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)

        self.title("Sign Up")
        self.geometry("400x350")  # increased window size
        self.resizable(False, False)

        # main container frame with padding
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Create a new account", font=("Helvetica", 14, "bold")).pack(pady=(0, 20))

        ttk.Label(main_frame, text="Username:").pack(anchor=tk.W, pady=(0, 5))
        self.username_entry = ttk.Entry(main_frame)
        self.username_entry.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(main_frame, text="Password:").pack(anchor=tk.W, pady=(0, 5))
        self.password_entry = ttk.Entry(main_frame, show="*")
        self.password_entry.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(main_frame, text="Confirm Password:").pack(anchor=tk.W, pady=(0, 5))
        self.confirm_password_entry = ttk.Entry(main_frame, show="*")
        self.confirm_password_entry.pack(fill=tk.X, pady=(0, 25))

        # buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(buttons_frame, text="Register", command=self.register_user).pack(fill=tk.X, pady=(0, 10))
        ttk.Button(buttons_frame, text="Back to Login", command=self.back_to_login).pack(fill=tk.X)

    def register_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        confirm_password = self.confirm_password_entry.get().strip()

        if not username or not password or not confirm_password:
            tkinter.messagebox.showerror("Error", "All fields are required.")
            return

        if password != confirm_password:
            tkinter.messagebox.showerror("Error", "Passwords do not match.")
            return

        if RegisterUser(username, password):
            tkinter.messagebox.showinfo("Success", "Account created successfully!")
            self.destroy()
            self.master.deiconify()
        else:
            tkinter.messagebox.showerror("Error", "Username already exists.")

    def back_to_login(self):
        self.destroy()
        self.master.deiconify()

class TimePlanApp(tk.Tk):
    def __init__(self, user_id, username):
        super().__init__()

        self.user_id = user_id
        self.username = username
        self.title(f"TimePlan Productivity System - {username}")
        self.geometry("1200x600")
        self.configure(bg="white")  # set background color

        CreateTable()
        UpdateMissedTasks(self.user_id)
        
        # configure styles
        style = ttk.Style()
        style.configure("Dashboard.TFrame", background="#f7f0fd")
        style.configure("Filter.TLabel", font=("Arial", 10, "bold"))
        style.configure("Delete.TButton", foreground="red")
        
        # create the menu bar first
        self.create_menu_bar()
        
        # create main container
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # create frames for different views
        self.dashboard_view = None
        self.task_view = None

        # create views
        self.create_views()

        # initially show dashboard
        self.show_dashboard()

        # protocol for window close button
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_views(self):
        # create dashboard view if not exists
        if not self.dashboard_view:
            self.dashboard_view = self.create_dashboard_view()
            self.dashboard_view.pack_forget()  # Initially hidden

        # create task view if not exists
        if not self.task_view:
            self.task_view = self.create_task_view()
            self.task_view.pack_forget()  # Initially hidden

    def create_menu_bar(self):
        # create a frame for the menu bar with a background color
        self.menu_frame = tk.Frame(self, bg="#d39ffb", height=30)
        self.menu_frame.pack(fill=tk.X)
        
        # make the frame keep its height
        self.menu_frame.pack_propagate(False)

        # create the menu bar
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # file menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Dashboard", command=self.show_dashboard)
        file_menu.add_command(label="Task Manager", command=self.show_task_view)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)

        # view menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Dashboard", command=self.show_dashboard)
        view_menu.add_command(label="Task Manager", command=self.show_task_view)

        # user menu
        user_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=f"User: {self.username}", menu=user_menu)
        user_menu.add_command(label="Profile", command=lambda: tkinter.messagebox.showinfo("Coming Soon", "Profile feature coming soon!"))
        user_menu.add_command(label="Settings", command=lambda: tkinter.messagebox.showinfo("Coming Soon", "Settings feature coming soon!"))
        user_menu.add_separator()
        user_menu.add_command(label="Sign Out", command=self.sign_out)

        # help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=lambda: tkinter.messagebox.showinfo("About", "TimePlan Productivity System\nVersion 1.0"))
        help_menu.add_command(label="Documentation", command=lambda: tkinter.messagebox.showinfo("Help", "Documentation coming soon!"))

    def create_dashboard_view(self):
        # create main dashboard frame
        dashboard_frame = ttk.Frame(self.main_container)
        dashboard_frame.configure(style="Dashboard.TFrame")

        # sidebar
        sidebar = tk.Frame(dashboard_frame, bg="#d39ffb", width=180)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)  # Prevent sidebar from shrinking

        # logo and title
        title_frame = tk.Frame(sidebar, bg="#d39ffb")
        title_frame.pack(fill="x", pady=20)
        tk.Label(title_frame, text="🅣", bg="#d39ffb", fg="white", 
                font=("Arial", 24, "bold")).pack(side="left", padx=10)
        tk.Label(title_frame, text="Time Plan", bg="#d39ffb", fg="white", 
                font=("Arial", 16, "bold")).pack(side="left")

        # sidebar buttons with improved styling
        buttons = [
            ("📊 DASHBOARD", self.show_dashboard),
            ("📝 TASK MANAGER", self.show_task_view),
            ("👤 MY PROFILE", lambda: tkinter.messagebox.showinfo("Coming Soon", "Profile feature coming soon!")),
            ("⚙️ SETTINGS", lambda: tkinter.messagebox.showinfo("Coming Soon", "Settings feature coming soon!"))
        ]
        
        for text, command in buttons:
            btn = tk.Button(sidebar, text=text, bg="#d39ffb", fg="white",
                          relief="flat", anchor="w", padx=20, 
                          font=("Arial", 11),
                          command=command,
                          cursor="hand2")
            btn.pack(fill="x", pady=5)
            
            # add hover effect
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg="#c180f2"))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg="#d39ffb"))

        # main Content Frame
        main_frame = tk.Frame(dashboard_frame, bg="white")
        main_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        # progress Section
        self.progress_frame = tk.LabelFrame(main_frame, text="Task Progress", 
                                          font=("Arial", 14, "bold"), bg="white",
                                          padx=10, pady=10)
        self.progress_frame.pack(fill="x", pady=(0, 20))

        # calendar Section
        calendar_frame = tk.LabelFrame(main_frame, text="Calendar", 
                                     font=("Arial", 14, "bold"), bg="white",
                                     padx=10, pady=10)
        calendar_frame.pack(fill="both", expand=True, pady=(0, 20))

        # create calendar widget
        self.calendar = Calendar(calendar_frame, selectmode='day',
                               date_pattern='yyyy-mm-dd',
                               showweeknumbers=False,
                               background="#d39ffb",
                               selectbackground="#8a3ff6")
        self.calendar.pack(fill="both", expand=True, pady=10)

        # upcoming schedule section
        self.upcoming_frame = tk.LabelFrame(main_frame, text="Upcoming Tasks",
                                          font=("Arial", 14, "bold"), bg="white",
                                          padx=10, pady=10)
        self.upcoming_frame.pack(fill="x")

        return dashboard_frame

    def create_task_view(self):
        # create main task frame
        task_frame = ttk.Frame(self.main_container)
        task_frame.configure(style="Dashboard.TFrame")

        # sidebar
        sidebar = tk.Frame(task_frame, bg="#d39ffb", width=180)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)  # Prevent sidebar from shrinking

        # logo and title
        title_frame = tk.Frame(sidebar, bg="#d39ffb")
        title_frame.pack(fill="x", pady=20)
        tk.Label(title_frame, text="🅣", bg="#d39ffb", fg="white", 
                font=("Arial", 24, "bold")).pack(side="left", padx=10)
        tk.Label(title_frame, text="Time Plan", bg="#d39ffb", fg="white", 
                font=("Arial", 16, "bold")).pack(side="left")

        # sidebar buttons with improved styling
        buttons = [
            ("📊 DASHBOARD", self.show_dashboard),
            ("📝 TASK MANAGER", self.show_task_view),
            ("👤 MY PROFILE", lambda: tkinter.messagebox.showinfo("Coming Soon", "Profile feature coming soon!")),
            ("⚙️ SETTINGS", lambda: tkinter.messagebox.showinfo("Coming Soon", "Settings feature coming soon!"))
        ]
        
        for text, command in buttons:
            btn = tk.Button(sidebar, text=text, bg="#d39ffb", fg="white",
                          relief="flat", anchor="w", padx=20, 
                          font=("Arial", 11),
                          command=command,
                          cursor="hand2")
            btn.pack(fill="x", pady=5)
            
            # add hover effect
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg="#c180f2"))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg="#d39ffb"))

        # main Content Frame with padding
        main_frame = tk.Frame(task_frame, bg="white")
        main_frame.pack(side="right", fill="both", expand=True, padx=20, pady=10)

        # split main frame into left (calendar) and right (tasks) sections
        left_frame = tk.Frame(main_frame, bg="white", width=300)
        left_frame.pack(side="left", fill="y", padx=(0, 20))
        left_frame.pack_propagate(False)  # Keep the width fixed

        right_frame = tk.Frame(main_frame, bg="white")
        right_frame.pack(side="right", fill="both", expand=True)

        # add calendar to left frame
        calendar_frame = ttk.LabelFrame(left_frame, text="Calendar", padding=10)
        calendar_frame.pack(fill="x", pady=(0, 20))

        self.calendar = Calendar(calendar_frame, 
                               selectmode='day',
                               date_pattern='yyyy-mm-dd',
                               showweeknumbers=False,
                               background="#d39ffb",
                               selectbackground="#8a3ff6")
        self.calendar.pack(fill="both", expand=True)
        self.calendar.bind('<<CalendarSelected>>', self.on_date_selected)

        # add task preview below calendar
        preview_frame = ttk.LabelFrame(left_frame, text="Tasks for selected date", padding=10)
        preview_frame.pack(fill="both", expand=True)

        # add scrollbar for preview
        preview_scroll = ttk.Scrollbar(preview_frame)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # create text widget for task preview
        self.task_preview = tk.Text(preview_frame, height=8, wrap=tk.WORD,
                                  yscrollcommand=preview_scroll.set)
        self.task_preview.pack(fill="both", expand=True)
        preview_scroll.config(command=self.task_preview.yview)
        self.task_preview.config(state=tk.DISABLED)

        # date navigation frame
        date_nav_frame = tk.Frame(right_frame, bg="white")
        date_nav_frame.pack(fill="x", pady=(0, 20))

        # date navigation buttons
        date_frame = tk.Frame(date_nav_frame, bg="white")
        date_frame.pack(fill="x", pady=(0, 10))

        from datetime import datetime, timedelta
        today = datetime.now()
        
        # store date references
        self.current_date = today
        self.date_buttons = {}
        
        # calculate the start of the current week (Sunday)
        current_weekday = today.weekday()  # 0 is Monday, 6 is Sunday
        days_from_sunday = (current_weekday + 1) % 7  # Convert to 0 is Sunday
        sunday = today - timedelta(days=days_from_sunday)
        
        # create buttons for each day of the current week
        weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        for i in range(7):
            current_date = sunday + timedelta(days=i)
            weekday = weekdays[i]
            
            # determine if this is today
            is_today = current_date.date() == today.date()
            
            # create the button text
            if is_today:
                button_text = "Today"
            else:
                button_text = weekday
            
            btn = tk.Button(
                date_frame,
                text=f"{button_text}\n{current_date.strftime('%d %b')}",
                font=("Arial", 11),
                bg="#d39ffb" if is_today else "white",
                fg="white" if is_today else "black",
                relief="flat",
                cursor="hand2",
                width=12,  # Set fixed width for consistent sizing
                command=lambda d=current_date: self.filter_tasks_by_date(d)
            )
            btn.pack(side="left", padx=5)
            
            # store button reference
            self.date_buttons[current_date.strftime("%Y-%m-%d")] = btn
            
            # add hover effect
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg="#e6d1fc" if b.cget("bg") == "white" else "#c180f2"))
            btn.bind("<Leave>", lambda e, b=btn, d=current_date: b.configure(
                bg="white" if d.strftime("%Y-%m-%d") != self.current_date.strftime("%Y-%m-%d") else "#d39ffb"
            ))

        # buttons frame below date navigation
        add_btn_frame = tk.Frame(date_nav_frame, bg="white")
        add_btn_frame.pack(fill=tk.X)

        # create a frame for the buttons to be side by side
        button_container = tk.Frame(add_btn_frame, bg="white")
        button_container.pack(pady=(0, 10))

        # Add New Task button
        add_btn = tk.Button(
            button_container,
            text=" Add New Task ➕",
            font=("Arial", 11, "bold"),
            fg="white",
            bg="#d39ffb",
            relief="flat",
            command=self.show_task_form,
            cursor="hand2",
            padx=15,
            pady=5
        )
        add_btn.pack(side=tk.LEFT, padx=(0, 10))

        # All Tasks button
        all_tasks_btn = tk.Button(
            button_container,
            text=" All Tasks 📋",
            font=("Arial", 11, "bold"),
            fg="white",
            bg="#d39ffb",
            relief="flat",
            command=self.show_all_tasks,
            cursor="hand2",
            padx=15,
            pady=5
        )
        all_tasks_btn.pack(side=tk.LEFT)

        # add hover effect for both buttons
        def on_enter(e, btn):
            btn['background'] = '#c180f2'
        def on_leave(e, btn):
            btn['background'] = '#d39ffb'

        add_btn.bind("<Enter>", lambda e: on_enter(e, add_btn))
        add_btn.bind("<Leave>", lambda e: on_leave(e, add_btn))
        all_tasks_btn.bind("<Enter>", lambda e: on_enter(e, all_tasks_btn))
        all_tasks_btn.bind("<Leave>", lambda e: on_leave(e, all_tasks_btn))

        # create notebook for tabs
        self.task_notebook = ttk.Notebook(right_frame)
        self.task_notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # create tabs for each category
        self.all_tasks_tab = ttk.Frame(self.task_notebook)
        self.ongoing_tab = ttk.Frame(self.task_notebook)
        self.recurring_tab = ttk.Notebook(self.task_notebook)
        self.missed_tab = ttk.Frame(self.task_notebook)
        self.done_tab = ttk.Frame(self.task_notebook)

        # initialize all treeviews first
        self.all_tasks_tree = None
        self.ongoing_tree = None
        self.recurring_trees = {}
        self.missed_tree = None
        self.done_tree = None

        # add tabs to notebook - add the All Tasks tab first
        self.task_notebook.add(self.all_tasks_tab, text="All Tasks")
        self.task_notebook.add(self.ongoing_tab, text="On-going")
        self.task_notebook.add(self.recurring_tab, text="Recurring")
        self.task_notebook.add(self.missed_tab, text="Missed")
        self.task_notebook.add(self.done_tab, text="Done")

        # create recurring sub-tabs
        self.daily_tab = ttk.Frame(self.recurring_tab)
        self.weekly_tab = ttk.Frame(self.recurring_tab)
        self.monthly_tab = ttk.Frame(self.recurring_tab)
        self.annual_tab = ttk.Frame(self.recurring_tab)

        # add sub-tabs to recurring notebook
        self.recurring_tab.add(self.daily_tab, text="Daily")
        self.recurring_tab.add(self.weekly_tab, text="Weekly")
        self.recurring_tab.add(self.monthly_tab, text="Monthly")
        self.recurring_tab.add(self.annual_tab, text="Annually")

        # create treeviews for each tab
        self.create_tab_treeview(self.all_tasks_tab, "All")
        self.create_tab_treeview(self.ongoing_tab, "On-going")
        self.create_recurring_treeviews()
        self.create_tab_treeview(self.missed_tab, "Missed")
        self.create_tab_treeview(self.done_tab, "Done")

        # initialize task IDs dictionary
        self.task_ids = {}

        # bind tab change event
        self.task_notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # update calendar with tasks
        self.update_calendar_tasks()

        return task_frame

    def create_recurring_treeviews(self):
        # create treeviews for each recurring pattern
        patterns = {
            "Daily": self.daily_tab,
            "Weekly": self.weekly_tab,
            "Monthly": self.monthly_tab,
            "Annually": self.annual_tab
        }

        for pattern, tab in patterns.items():
            tree_frame = ttk.Frame(tab)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # create scrollbar
            tree_scroll = ttk.Scrollbar(tree_frame)
            tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

            # configure columns
            columns = ("title", "due_date", "status")
            headings = ("Task Name", "Starting Date", "Last Done")
            widths = (300, 100, 100)

            # create treeview
            tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                              yscrollcommand=tree_scroll.set)
            tree_scroll.config(command=tree.yview)

            # configure columns
            for col, heading, width in zip(columns, headings, widths):
                tree.heading(col, text=heading)
                tree.column(col, width=width, minwidth=width)

            tree.pack(fill=tk.BOTH, expand=True)

            # configure tags
            tree.tag_configure('completed', background='#e8f5e9')
            tree.tag_configure('pending', background='#fff3e0')

            # store tree reference
            self.recurring_trees[pattern] = tree

            # add action buttons
            action_frame = ttk.Frame(tab)
            action_frame.pack(fill=tk.X, pady=(5, 0))

            ttk.Button(action_frame, text="Mark Done Today",
                      command=lambda p=pattern: self.mark_recurring_done_today(p)).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(action_frame, text="Delete Task",
                      command=lambda p=pattern: self.delete_recurring_task(p),
                      style="Delete.TButton").pack(side=tk.LEFT, padx=(0, 5))

            # bind selection event
            tree.bind('<<TreeviewSelect>>', self.on_task_select)

    def filter_tasks_by_date(self, selected_date):
        # update current date
        self.current_date = selected_date
        
        # Reset all date button styles when showing all tasks
        if selected_date is None:
            for btn in self.date_buttons.values():
                btn.configure(bg="white", fg="black")
        # Update button styles only if a date is selected
        else:
            for date_str, btn in self.date_buttons.items():
                if date_str == selected_date.strftime("%Y-%m-%d"):
                    btn.configure(bg="#d39ffb", fg="white")
                else:
                    btn.configure(bg="white", fg="black")

        try:
            # clear all trees first
            for category in ["ongoing", "missed", "done"]:
                tree = getattr(self, f"{category}_tree")
                if tree and tree.winfo_exists():
                    for item in tree.get_children():
                        tree.delete(item)
            
            # clear recurring trees
            for tree in self.recurring_trees.values():
                if tree and tree.winfo_exists():
                    for item in tree.get_children():
                        tree.delete(item)

            # clear all tasks tree
            if self.all_tasks_tree and self.all_tasks_tree.winfo_exists():
                for item in self.all_tasks_tree.get_children():
                    self.all_tasks_tree.delete(item)

            # update missed tasks
            UpdateMissedTasks(self.user_id)
            
            # get tasks - always get tasks for the selected date
            conn = Connect()
            cursor = conn.cursor()
            
            if selected_date is not None:
                cursor.execute('''
                    SELECT 
                        id, title, description, due_date, category_id, priority, 
                        last_completed_date, recurrence_pattern,
                        date('now', 'localtime') as today
                    FROM tasks 
                    WHERE user_id = ? 
                    AND (
                        date(due_date) = date(?) 
                        OR (
                            category_id IN (
                                SELECT category_id FROM task_category WHERE category_name = 'Recurring'
                            ) 
                            AND recurrence_pattern IS NOT NULL
                        )
                    )
                    ORDER BY 
                        CASE 
                            WHEN priority = 'Urgent' THEN 1 
                            ELSE 2 
                        END,
                        due_date ASC
                ''', (self.user_id, selected_date.strftime("%Y-%m-%d")))
            else:
                # If no date selected, show today's tasks
                today = datetime.now()
                cursor.execute('''
                    SELECT 
                        id, title, description, due_date, category_id, priority, 
                        last_completed_date, recurrence_pattern,
                        date('now', 'localtime') as today
                    FROM tasks 
                    WHERE user_id = ? 
                    AND (date(due_date) = date('now', 'localtime') OR category_id IN (SELECT category_id FROM task_category WHERE category_name = 'Recurring'))
                    ORDER BY 
                        CASE 
                            WHEN priority = 'Urgent' THEN 1 
                            ELSE 2 
                        END,
                        due_date ASC
                ''', (self.user_id,))
            
            tasks = cursor.fetchall()
            conn.close()

            # clear task IDs dictionary
            self.task_ids.clear()

            # Get current date for comparisons
            current_date = datetime.now().date()
            selected_datetime = selected_date.date() if isinstance(selected_date, datetime) else selected_date

            # process tasks for each category
            for task in tasks:
                task_id, title, desc, date, category_id, priority, last_completed, pattern, today = task
                
                # For recurring tasks, check if they actually occur on the selected date
                if category_id in [3] and pattern:  # 3 is the ID for 'Recurring'
                    task_date = datetime.strptime(date, '%Y-%m-%d').date()
                    temp_date = task_date
                    is_on_date = False
                    
                    # Check if this recurring task occurs on the selected date
                    while temp_date <= selected_datetime:
                        if temp_date == selected_datetime:
                            is_on_date = True
                            break
                            
                        # Calculate next occurrence based on pattern
                        if pattern == "Daily":
                            temp_date += timedelta(days=1)
                        elif pattern == "Weekly":
                            temp_date += timedelta(days=7)
                        elif pattern == "Monthly":
                            # Handle month rollover
                            year = temp_date.year + (temp_date.month // 12)
                            month = (temp_date.month % 12) + 1
                            try:
                                temp_date = temp_date.replace(year=year, month=month)
                            except ValueError:
                                if month == 2 and temp_date.day > 28:
                                    temp_date = temp_date.replace(year=year, month=month, day=28)
                                else:
                                    if month == 12:
                                        next_month = datetime(year + 1, 1, 1)
                                    else:
                                        next_month = datetime(year, month + 1, 1)
                                    last_day = (next_month - timedelta(days=1)).day
                                    temp_date = temp_date.replace(year=year, month=month, day=last_day)
                        elif pattern == "Annually":
                            try:
                                temp_date = temp_date.replace(year=temp_date.year + 1)
                            except ValueError:
                                temp_date = temp_date.replace(year=temp_date.year + 1, month=2, day=28)
                    
                    # Only add the task if it occurs on the selected date
                    if not is_on_date:
                        continue
                
                # Add to All Tasks tab
                if self.all_tasks_tree:
                    status = ""
                    if category_id == 2:  # 2 is the ID for 'On-going'
                        status = "🔔 Active" if priority == "Urgent" else "📝 Active"
                    elif category_id == 3:  # 3 is the ID for 'Recurring'
                        status = "✅ Done Today" if last_completed == today else "⏳ Pending"
                    elif category_id == 4:  # 4 is the ID for 'Missed'
                        status = "❌ Missed"
                    elif category_id == 5:  # 5 is the ID for 'Done'
                        status = "✅ Completed"
                    
                    values = (title, date, category_id, 
                             f"⚡ {priority}" if priority else "", 
                             status)
                    item_id = self.all_tasks_tree.insert("", tk.END, values=values)
                    
                    # Apply appropriate tag
                    if category_id == 5:
                        self.all_tasks_tree.item(item_id, tags=('completed',))
                    elif category_id == 4:
                        self.all_tasks_tree.item(item_id, tags=('missed',))
                    elif category_id == 3:
                        self.all_tasks_tree.item(item_id, tags=('recurring',))
                    elif priority == "Urgent":
                        self.all_tasks_tree.item(item_id, tags=('urgent',))
                    
                    self.task_ids[item_id] = task_id

                if category_id == 2:  # 2 is the ID for 'On-going'
                    tree = self.ongoing_tree
                    status = "🔔 Active" if priority == "Urgent" else "📝 Active"
                    values = (title, date, f"⚡ {priority}" if priority else "", status)
                    item_id = tree.insert("", tk.END, values=values)
                    if priority == "Urgent":
                        tree.item(item_id, tags=('urgent',))
                    self.task_ids[item_id] = task_id
                
                elif category_id == 3:  # 3 is the ID for 'Recurring'
                    # skip if no pattern is set
                    if not pattern:
                        continue
                        
                    # get the appropriate tree for this pattern
                    tree = self.recurring_trees.get(pattern)
                    if not tree:
                        continue

                    # For all tasks view, just show the recurring task with its base date
                    status = "✅ Done Today" if last_completed == today else "⏳ Pending"
                    values = (title, date, status)
                    item_id = tree.insert("", tk.END, values=values)
                    if last_completed == today:
                        tree.item(item_id, tags=('completed',))
                    else:
                        tree.item(item_id, tags=('pending',))
                    self.task_ids[item_id] = task_id
                
                elif category_id == 4:  # 4 is the ID for 'Missed'
                    tree = self.missed_tree
                    values = (title, date, "❌ Missed")
                    item_id = tree.insert("", tk.END, values=values)
                    tree.item(item_id, tags=('missed',))
                    self.task_ids[item_id] = task_id
                
                elif category_id == 5:  # 5 is the ID for 'Done'
                    tree = self.done_tree
                    values = (title, date, "✅ Completed")
                    item_id = tree.insert("", tk.END, values=values)
                    tree.item(item_id, tags=('completed',))
                    self.task_ids[item_id] = task_id

        except Exception as e:
            print(f"Error filtering tasks: {str(e)}")
            tkinter.messagebox.showerror("Error", f"Failed to filter tasks: {str(e)}")

    def create_tab_treeview(self, tab, category):
        # Create a frame for the treeview and its scrollbar
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # create the treeview scrollbar
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # configure columns based on category
        if category == "All":
            columns = ("title", "due_date", "category", "priority", "status")
            headings = ("Task Name", "Due Date", "Category", "Priority", "Status")
            widths = (200, 100, 100, 100, 100)
        elif category == "On-going":
            columns = ("title", "due_date", "priority", "status")
            headings = ("Task Name", "Due Date", "Priority", "Status")
            widths = (250, 100, 100, 100)
        elif category == "Recurring":
            columns = ("title", "due_date", "pattern", "status")
            headings = ("Task Name", "Starting Date", "Pattern", "Last Done")
            widths = (250, 100, 100, 100)
        else:  # missed and Done
            columns = ("title", "due_date", "status")
            headings = ("Task Name", "Due Date", "Status")
            widths = (300, 100, 100)

        # create treeview with configured columns
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                           yscrollcommand=tree_scroll.set)
        
        # configure the scrollbar
        tree_scroll.config(command=tree.yview)

        # configure column headings and widths
        for col, heading, width in zip(columns, headings, widths):
            tree.heading(col, text=heading)
            tree.column(col, width=width, minwidth=width)

        tree.pack(fill=tk.BOTH, expand=True)

        # configure row tags for different states
        tree.tag_configure('completed', background='#e8f5e9')  # light green
        tree.tag_configure('overdue', background='#ffebee')    # light red
        tree.tag_configure('urgent', background='#fff3e0')     # light orange
        tree.tag_configure('recurring', background='#e3f2fd')  # light blue

        # store tree reference with correct name
        if category == "All":
            self.all_tasks_tree = tree
        elif category == "On-going":
            self.ongoing_tree = tree
        elif category == "Missed":
            self.missed_tree = tree
        elif category == "Done":
            self.done_tree = tree
        # do not handle recurring_trees here; handled in create_recurring_treeviews

        # add action buttons frame
        action_frame = ttk.Frame(tab)
        action_frame.pack(fill=tk.X, pady=(5, 0))

        if category == "Recurring":
            ttk.Button(action_frame, text="Mark Done Today", 
                      command=self.mark_recurring_done_today).pack(side=tk.LEFT, padx=(0, 5))
        elif category in ["On-going", "Missed", "All"]:  # Add "All" here
            ttk.Button(action_frame, text="Mark as Done",
                      command=self.mark_task_as_done).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(action_frame, text="Delete Task",
                  command=self.delete_task,
                  style="Delete.TButton").pack(side=tk.LEFT, padx=(0, 5))

        # bind selection event
        tree.bind('<<TreeviewSelect>>', self.on_task_select)

    def on_tab_changed(self, event=None):
        # reload tasks for current selection when tab changes
        if hasattr(self, 'current_date'):
            # If we're showing all tasks (current_date is None) or have a specific date selected
            if self.current_date is None:
                self.show_all_tasks()
            else:
                self.filter_tasks_by_date(self.current_date)

    def mark_recurring_done_today(self, pattern=None):
        if pattern:
            current_tree = self.recurring_trees[pattern]
        else:
            return
            
        selected_items = current_tree.selection()
        if not selected_items:
            return
            
        item_id = selected_items[0]
        task_id = self.task_ids.get(item_id)
        
        if task_id:
            try:
                MarkRecurringTaskComplete(task_id)
                self.filter_tasks_by_date(self.current_date)
                self.update_calendar_tasks()
                tkinter.messagebox.showinfo("Success", "Task marked as done for today!")
            except Exception as e:
                tkinter.messagebox.showerror("Error", f"Failed to mark task as done: {str(e)}")

    def mark_task_as_done(self):
        current_tree = None
        current_tab = self.task_notebook.select()
        
        if current_tab == str(self.ongoing_tab):
            current_tree = self.ongoing_tree
        elif current_tab == str(self.missed_tab):
            current_tree = self.missed_tree
            
        if not current_tree:
            return
            
        selected_items = current_tree.selection()
        if not selected_items:
            return
        
        item_id = selected_items[0]
        task_id = self.task_ids.get(item_id)
        
        if task_id:
            try:
                UpdateTaskStatus(task_id, "Done")
                self.filter_tasks_by_date(self.current_date)
                tkinter.messagebox.showinfo("Success", "Task marked as done!")
            except Exception as e:
                tkinter.messagebox.showerror("Error", f"Failed to mark task as done: {str(e)}")

    def delete_task(self):
        current_tree = None
        current_tab = self.task_notebook.select()
        
        # Get the appropriate tree based on the current tab
        if current_tab == str(self.ongoing_tab):
            current_tree = self.ongoing_tree
        elif current_tab == str(self.recurring_tab):
            current_tree = self.recurring_trees[self.recurring_tab.select()]
        elif current_tab == str(self.missed_tab):
            current_tree = self.missed_tree
        elif current_tab == str(self.done_tab):
            current_tree = self.done_tree
        elif current_tab == str(self.all_tasks_tab):
            current_tree = self.all_tasks_tree
            
        if not current_tree:
            return
            
        selected_items = current_tree.selection()
        if not selected_items:
            return
        
        item_id = selected_items[0]
        task_id = self.task_ids.get(item_id)
        task_title = current_tree.item(item_id)['values'][0]
        
        if task_id and tkinter.messagebox.askyesno("Delete Task", 
                                                  f"Are you sure you want to delete the task:\n\n{task_title}?",
                                                  icon='warning'):
            try:
                DeleteTask(task_id, self.user_id)
                # Refresh the view based on current state
                if self.current_date is None:
                    self.show_all_tasks()
                else:
                    self.filter_tasks_by_date(self.current_date)
                self.update_calendar_tasks()
                tkinter.messagebox.showinfo("Success", "Task deleted successfully!")
            except Exception as e:
                tkinter.messagebox.showerror("Error", f"Failed to delete task: {str(e)}")

    def delete_recurring_task(self, pattern=None):
        if pattern:
            current_tree = self.recurring_trees[pattern]
        else:
            return
            
        selected_items = current_tree.selection()
        if not selected_items:
            return
        
        item_id = selected_items[0]
        task_id = self.task_ids.get(item_id)
        task_title = current_tree.item(item_id)['values'][0]
        
        if task_id and tkinter.messagebox.askyesno("Delete Task", 
                                                  f"Are you sure you want to delete the recurring task:\n\n{task_title}?",
                                                  icon='warning'):
            try:
                DeleteTask(task_id, self.user_id)
                self.filter_tasks_by_date(self.current_date)
                self.update_calendar_tasks()
                tkinter.messagebox.showinfo("Success", "Task deleted successfully!")
            except Exception as e:
                tkinter.messagebox.showerror("Error", f"Failed to delete task: {str(e)}")

    def sign_out(self):
        if tkinter.messagebox.askyesno("Sign Out", "Are you sure you want to sign out?"):
            self.destroy()
            login_window = LoginWindow()
            login_window.mainloop()

    def on_closing(self):
        if tkinter.messagebox.askyesno("Exit", "Are you sure you want to exit the application?"):
            self.destroy()

    def update_dashboard(self):
        # clear existing widgets
        for widget in self.progress_frame.winfo_children():
            widget.destroy()
        for widget in self.upcoming_frame.winfo_children():
            widget.destroy()

        # get task statistics
        conn = Connect()
        cursor = conn.cursor()
        
        # get total tasks
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN category_id = (SELECT category_id FROM task_category WHERE category_name = 'On-going') THEN 1 ELSE 0 END) as ongoing,
                SUM(CASE WHEN category_id = (SELECT category_id FROM task_category WHERE category_name = 'Done') THEN 1 ELSE 0 END) as done,
                SUM(CASE WHEN category_id = (SELECT category_id FROM task_category WHERE category_name = 'Missed') THEN 1 ELSE 0 END) as missed
            FROM tasks 
            WHERE user_id = ?
        ''', (self.user_id,))
        
        stats = cursor.fetchone()
        total = stats[0] if stats and stats[0] else 0
        
        # calculate percentages
        ongoing_percent = round((stats[1] / total * 100) if stats[1] and total else 0)
        done_percent = round((stats[2] / total * 100) if stats[2] and total else 0)
        missed_percent = round((stats[3] / total * 100) if stats[3] and total else 0)
        
        # display progress circles
        self.progress_circle(self.progress_frame, "ON-GOING", ongoing_percent)
        self.progress_circle(self.progress_frame, "DONE", done_percent)
        self.progress_circle(self.progress_frame, "MISSED", missed_percent)
        
        # get upcoming tasks
        cursor.execute('''
            SELECT title, due_date, strftime('%d', due_date) as day
            FROM tasks 
            WHERE user_id = ? 
            AND category_id = (SELECT category_id FROM task_category WHERE category_name = 'On-going')
            AND due_date >= date('now')
            ORDER BY due_date
            LIMIT 5
        ''', (self.user_id,))
        
        upcoming_tasks = cursor.fetchall()
        
        # display upcoming tasks
        colors = ["#8b3ffc", "#d3a8f9"]  # Alternate colors
        for i, task in enumerate(upcoming_tasks):
            title, due_date, day = task
            self.schedule_box(
                self.upcoming_frame,
                day,
                title,
                due_date,
                colors[i % len(colors)]
            )
            
        conn.close()

        # schedule next update
        self.after(60000, self.update_dashboard)  # Update every minute

    def progress_circle(self, frame, label, percent):
        f = tk.Frame(frame, bg="white", bd=1, relief="solid")
        f.pack(side="left", padx=10)
        tk.Label(f, text=label, font=("Arial", 10, "bold"), bg="white").pack(pady=5)
        tk.Label(f, text=f"{percent}%", font=("Arial", 12, "bold"),
                bg="white", fg="#8a3ff6").pack(pady=5)

    def schedule_box(self, frame, day, title, time, color):
        f = tk.Frame(frame, bg=color, padx=10, pady=10)
        f.pack(pady=10, fill="x")
        tk.Label(f, text=day, bg=color, fg="white",
                font=("Arial", 12, "bold")).pack(side="left")
        details = tk.Frame(f, bg=color)
        details.pack(side="left", padx=10)
        tk.Label(details, text=title, bg=color, fg="white",
                font=("Arial", 12, "bold")).pack(anchor="w")
        tk.Label(details, text=time, bg=color, fg="white",
                font=("Arial", 10)).pack(anchor="w")

    def _on_mousewheel(self, event):
        self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def create_calendar_frame(self):
        calendar_frame = ttk.Frame(self.left_frame)
        calendar_frame.pack(fill=tk.X, pady=(0, 20))
        
        # create the calendar widget
        self.calendar = Calendar(calendar_frame, 
                               selectmode='day',
                               date_pattern='yyyy-mm-dd',
                               showweeknumbers=False)
        self.calendar.pack(fill=tk.X)
        
        # bind the calendar selection event
        self.calendar.bind('<<CalendarSelected>>', self.on_date_selected)
        
        # create a frame for task preview with scrollbar
        self.preview_frame = ttk.Frame(calendar_frame)
        self.preview_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(self.preview_frame, text="Tasks for selected date:", 
                 font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
        
        # create a frame for the preview text and scrollbar
        preview_container = ttk.Frame(self.preview_frame)
        preview_container.pack(fill=tk.X)
        
        # add scrollbar for preview
        preview_scroll = ttk.Scrollbar(preview_container)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # create a text widget for task preview
        self.task_preview = tk.Text(preview_container, height=4, wrap=tk.WORD,
                                  yscrollcommand=preview_scroll.set)
        self.task_preview.pack(side=tk.LEFT, fill=tk.X, expand=True)
        preview_scroll.config(command=self.task_preview.yview)
        self.task_preview.config(state=tk.DISABLED)

    def update_calendar_tasks(self):
        conn = Connect()
        cursor = conn.cursor()
        
        # get all tasks including recurring ones
        cursor.execute('''
            SELECT due_date, title, category_id, recurrence_pattern, last_completed_date 
            FROM tasks 
            WHERE user_id = ? 
            AND due_date IS NOT NULL 
            AND due_date != ''
        ''', (self.user_id,))
        tasks = cursor.fetchall()
        conn.close()

        # reset calendar colors
        self.calendar.calevent_remove('all')

        from datetime import datetime, timedelta
        current_date = datetime.now().date()
        
        # process each task
        for due_date, title, category_id, recurrence_pattern, last_completed in tasks:
            try:
                task_date = datetime.strptime(due_date, '%Y-%m-%d').date()
                
                # for recurring tasks, add multiple instances
                if category_id == 3 and recurrence_pattern:  # 3 is the ID for 'Recurring'
                    # calculate next occurrences
                    dates_to_add = []
                    temp_date = task_date
                    
                    # calculate for the next 6 months
                    end_date = current_date + timedelta(days=180)  # 6 months ahead
                    
                    while temp_date <= end_date:
                        if temp_date >= current_date:
                            # check if this occurrence is completed
                            is_completed = False
                            if last_completed:
                                last_completed_date = datetime.strptime(last_completed, '%Y-%m-%d').date()
                                is_completed = (temp_date == last_completed_date)
                            
                            dates_to_add.append((temp_date, is_completed))
                        
                        # calculate next occurrence based on pattern
                        if recurrence_pattern == "Daily":
                            temp_date += timedelta(days=1)
                        elif recurrence_pattern == "Weekly":
                            temp_date += timedelta(days=7)
                        elif recurrence_pattern == "Monthly":
                            # handle month rollover
                            year = temp_date.year + (temp_date.month // 12)
                            month = (temp_date.month % 12) + 1
                            # try to maintain the same day, but handle month length differences
                            try:
                                temp_date = temp_date.replace(year=year, month=month)
                            except ValueError:
                                # if the day doesn't exist in the target month, use the last day
                                if month == 2 and temp_date.day > 28:
                                    temp_date = temp_date.replace(year=year, month=month, day=28)
                                else:
                                    # get the last day of the target month
                                    if month == 12:
                                        next_month = datetime(year + 1, 1, 1)
                                    else:
                                        next_month = datetime(year, month + 1, 1)
                                    last_day = (next_month - timedelta(days=1)).day
                                    temp_date = temp_date.replace(year=year, month=month, day=last_day)
                        elif recurrence_pattern == "Annually":
                            # handle leap year for February 29
                            try:
                                temp_date = temp_date.replace(year=temp_date.year + 1)
                            except ValueError:
                                temp_date = temp_date.replace(year=temp_date.year + 1, month=2, day=28)
                    
                    # add all calculated dates to calendar with appropriate status
                    for date, is_completed in dates_to_add:
                        status_symbol = "✓ " if is_completed else "🔄 "
                        self.calendar.calevent_create(
                            date,
                            f"{status_symbol}{title}",
                            "recurring_completed" if is_completed else "recurring"
                        )
                else:
                    # for non-recurring tasks
                    if task_date >= current_date:
                        if category_id == 5:  # 5 is the ID for 'Done'
                            self.calendar.calevent_create(task_date, f"✓ {title}", "completed")
                        elif category_id == 4:  # 4 is the ID for 'Missed'
                            self.calendar.calevent_create(task_date, f"❌ {title}", "missed")
                        else:  # on-going tasks
                            self.calendar.calevent_create(task_date, f"⏳ {title}", "task")
            except (ValueError, TypeError) as e:
                print(f"Error processing task date: {e}")
                continue

        # configure tags with colors
        self.calendar.tag_config("task", background="lightblue")
        self.calendar.tag_config("recurring", background="lightgreen")
        self.calendar.tag_config("recurring_completed", background="darkseagreen")
        self.calendar.tag_config("completed", background="#e8f5e9")  # Light green
        self.calendar.tag_config("missed", background="#ffebee")  # Light red

    def on_date_selected(self, event):
        selected_date = self.calendar.get_date()
        
        conn = Connect()
        cursor = conn.cursor()
        
        # first get all tasks for the selected date
        cursor.execute('''
            SELECT title, category_id, priority, recurrence_pattern, due_date, last_completed_date 
            FROM tasks 
            WHERE user_id = ?
            ORDER BY category_id, priority
        ''', (self.user_id,))
        tasks = cursor.fetchall()
        conn.close()

        self.task_preview.config(state=tk.NORMAL)
        self.task_preview.delete(1.0, tk.END)
        
        from datetime import datetime, timedelta
        
        # convert selected date to datetime for comparison
        selected_datetime = datetime.strptime(selected_date, '%Y-%m-%d').date()
        tasks_for_date = []

        for title, category_id, priority, recurrence_pattern, due_date, last_completed in tasks:
            try:
                task_date = datetime.strptime(due_date, '%Y-%m-%d').date()
                
                # handle recurring tasks
                if category_id == 3 and recurrence_pattern:  # 3 is the ID for 'Recurring'
                    # calculate if this task occurs on selected date
                    temp_date = task_date
                    is_on_date = False
                    is_completed = False
                    
                    # check up to the selected date
                    while temp_date <= selected_datetime:
                        if temp_date == selected_datetime:
                            is_on_date = True
                            # check if it was completed on this date
                            if last_completed:
                                last_completed_date = datetime.strptime(last_completed, '%Y-%m-%d').date()
                                is_completed = (selected_datetime == last_completed_date)
                            break
                            
                        # move to next occurrence
                        if recurrence_pattern == "Daily":
                            temp_date += timedelta(days=1)
                        elif recurrence_pattern == "Weekly":
                            temp_date += timedelta(days=7)
                        elif recurrence_pattern == "Monthly":
                            # handle month rollover
                            year = temp_date.year + (temp_date.month // 12)
                            month = (temp_date.month % 12) + 1
                            try:
                                temp_date = temp_date.replace(year=year, month=month)
                            except ValueError:
                                # handle month length differences
                                if month == 2 and temp_date.day > 28:
                                    temp_date = temp_date.replace(year=year, month=month, day=28)
                                else:
                                    # get last day of target month
                                    if month == 12:
                                        next_month = datetime(year + 1, 1, 1)
                                    else:
                                        next_month = datetime(year, month + 1, 1)
                                    last_day = (next_month - timedelta(days=1)).day
                                    temp_date = temp_date.replace(year=year, month=month, day=last_day)
                        elif recurrence_pattern == "Annually":
                            try:
                                temp_date = temp_date.replace(year=temp_date.year + 1)
                            except ValueError:
                                # handle February 29 in non-leap years
                                temp_date = temp_date.replace(year=temp_date.year + 1, month=2, day=28)
                    
                    if is_on_date:
                        status = "✓ Done Today" if is_completed else "⏳ Not Done Today"
                        tasks_for_date.append((title, category_id, priority, status, recurrence_pattern))
                
                # handle non-recurring tasks
                elif task_date == selected_datetime:
                    status = ""
                    if category_id == 5:  # 5 is the ID for 'Done'
                        status = "✓ Completed"
                    elif category_id == 4:  # 4 is the ID for 'Missed'
                        status = "❌ Missed"
                    elif category_id == 2:  # 2 is the ID for 'On-going'
                        status = "⏳ Pending"
                    tasks_for_date.append((title, category_id, priority, status, None))
                    
            except (ValueError, TypeError) as e:
                print(f"Error processing task date: {e}")
                continue

        if tasks_for_date:
            for title, category_id, priority, status, recurrence_pattern in tasks_for_date:
                priority_text = f" ({priority})" if priority else ""
                recurrence_text = f" [{recurrence_pattern}]" if recurrence_pattern else ""
                status_text = f" - {status}" if status else ""
                self.task_preview.insert(tk.END, f"• {title}{priority_text}{recurrence_text}{status_text}\n")
        else:
            self.task_preview.insert(tk.END, "No tasks scheduled for this date.")
        
        self.task_preview.config(state=tk.DISABLED)

    def show_task_form(self):
        # ensure the window is created and kept in memory
        self.task_form = TaskFormWindow(self, self.user_id)
        self.task_form.focus_force()  # force focus on the new window

    def show_dashboard(self):
        if self.task_view:
            self.task_view.pack_forget()
        if not self.dashboard_view:
            self.dashboard_view = self.create_dashboard_view()
        self.dashboard_view.pack(fill=tk.BOTH, expand=True)
        self.update_dashboard()
        self.update_calendar_tasks()  # update calendar when showing dashboard
        self.title(f"TimePlan Dashboard - {self.username}")

    def show_task_view(self):
        if self.dashboard_view:
            self.dashboard_view.pack_forget()
        if not self.task_view:
            self.task_view = self.create_task_view()
        self.task_view.pack(fill=tk.BOTH, expand=True)
        # load tasks for today by default
        self.filter_tasks_by_date(datetime.now())
        self.update_calendar_tasks()  # update calendar when showing task view
        self.title(f"TimePlan Task Manager - {self.username}")

    def on_task_select(self, event=None):
        # get the current tab and tree
        current_tab = self.task_notebook.select()
        current_tree = None
        
        if current_tab == str(self.ongoing_tab):
            current_tree = self.ongoing_tree
        elif current_tab == str(self.recurring_tab):
            current_tree = self.recurring_trees[self.recurring_tab.select()]
        elif current_tab == str(self.missed_tab):
            current_tree = self.missed_tree
        elif current_tab == str(self.done_tab):
            current_tree = self.done_tree
            
        if not current_tree:
            return
            
        # get selected items
        selected_items = current_tree.selection()
        if not selected_items:
            return
            
        # get the task ID
        item_id = selected_items[0]
        task_id = self.task_ids.get(item_id)
        
        if task_id:
            # get task details
            conn = Connect()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT title, description, category_id, priority, due_date, recurrence_pattern
                FROM tasks 
                WHERE id = ? AND user_id = ?
            ''', (task_id, self.user_id))
            task = cursor.fetchone()
            conn.close()
            
            if task:
                title, description, category_id, priority, due_date, recurrence_pattern = task
                
                # show task details in a popup
                details = f"Title: {title}\n"
                if description:
                    details += f"Description: {description}\n"
                details += f"Category: {category_id}\n"
                if priority:
                    details += f"Priority: {priority}\n"
                if due_date:
                    details += f"Due Date: {due_date}\n"
                if recurrence_pattern:
                    details += f"Recurrence: {recurrence_pattern}"
                
                tkinter.messagebox.showinfo("Task Details", details)

    def show_all_tasks(self):
        # Reset button styles
        for btn in self.date_buttons.values():
            btn.configure(bg="white", fg="black")

        try:
            # Clear all trees first
            for category in ["ongoing", "missed", "done"]:
                tree = getattr(self, f"{category}_tree")
                if tree and tree.winfo_exists():
                    for item in tree.get_children():
                        tree.delete(item)
            
            # Clear recurring trees
            for tree in self.recurring_trees.values():
                if tree and tree.winfo_exists():
                    for item in tree.get_children():
                        tree.delete(item)

            # Clear all tasks tree
            if self.all_tasks_tree and self.all_tasks_tree.winfo_exists():
                for item in self.all_tasks_tree.get_children():
                    self.all_tasks_tree.delete(item)

            # Get all tasks
            conn = Connect()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    id, title, description, due_date, category_id, priority, 
                    last_completed_date, recurrence_pattern,
                    date('now', 'localtime') as today
                FROM tasks 
                WHERE user_id = ? 
                ORDER BY 
                    CASE 
                        WHEN priority = 'Urgent' THEN 1 
                        ELSE 2 
                    END,
                    due_date ASC
            ''', (self.user_id,))
            
            tasks = cursor.fetchall()
            conn.close()

            # Clear task IDs dictionary
            self.task_ids.clear()

            # Process tasks for each category
            for task in tasks:
                task_id, title, desc, date, category_id, priority, last_completed, pattern, today = task
                
                # Add to All Tasks tab
                if self.all_tasks_tree:
                    status = ""
                    if category_id == 2:  # 2 is the ID for 'On-going'
                        status = "🔔 Active" if priority == "Urgent" else "📝 Active"
                    elif category_id == 3:  # 3 is the ID for 'Recurring'
                        status = "✅ Done Today" if last_completed == today else "⏳ Pending"
                    elif category_id == 4:  # 4 is the ID for 'Missed'
                        status = "❌ Missed"
                    elif category_id == 5:  # 5 is the ID for 'Done'
                        status = "✅ Completed"
                    
                    values = (title, date, category_id, 
                             f"⚡ {priority}" if priority else "", 
                             status)
                    item_id = self.all_tasks_tree.insert("", tk.END, values=values)
                    
                    # Apply appropriate tag
                    if category_id == 5:
                        self.all_tasks_tree.item(item_id, tags=('completed',))
                    elif category_id == 4:
                        self.all_tasks_tree.item(item_id, tags=('overdue',))
                    elif category_id == 3:
                        self.all_tasks_tree.item(item_id, tags=('recurring',))
                    elif priority == "Urgent":
                        self.all_tasks_tree.item(item_id, tags=('urgent',))
                    
                    self.task_ids[item_id] = task_id

                # Add to respective category tabs
                if category_id == 2:  # 2 is the ID for 'On-going'
                    tree = self.ongoing_tree
                    status = "🔔 Active" if priority == "Urgent" else "📝 Active"
                    values = (title, date, f"⚡ {priority}" if priority else "", status)
                    item_id = tree.insert("", tk.END, values=values)
                    if priority == "Urgent":
                        tree.item(item_id, tags=('urgent',))
                    self.task_ids[item_id] = task_id
                
                elif category_id == 3:  # 3 is the ID for 'Recurring'
                    tree = self.recurring_trees.get(pattern)
                    if tree:
                        status = "✅ Done Today" if last_completed == today else "⏳ Pending"
                        values = (title, date, status)
                        item_id = tree.insert("", tk.END, values=values)
                        if last_completed == today:
                            tree.item(item_id, tags=('completed',))
                        else:
                            tree.item(item_id, tags=('pending',))
                        self.task_ids[item_id] = task_id
                
                elif category_id == 4:  # 4 is the ID for 'Missed'
                    tree = self.missed_tree
                    values = (title, date, "❌ Missed")
                    item_id = tree.insert("", tk.END, values=values)
                    tree.item(item_id, tags=('overdue',))
                    self.task_ids[item_id] = task_id
                
                elif category_id == 5:  # 5 is the ID for 'Done'
                    tree = self.done_tree
                    values = (title, date, "✅ Completed")
                    item_id = tree.insert("", tk.END, values=values)
                    tree.item(item_id, tags=('completed',))
                    self.task_ids[item_id] = task_id

        except Exception as e:
            print(f"Error showing all tasks: {str(e)}")
            tkinter.messagebox.showerror("Error", f"Failed to show all tasks: {str(e)}")

def get_categories():
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute("SELECT category_id, category_name FROM task_category")
    categories = cursor.fetchall()
    conn.close()
    return categories

class TaskFormWindow(tk.Toplevel):
    def __init__(self, master, user_id):
        super().__init__(master)
        self.user_id = user_id
        self.title("Add New Task")
        self.geometry("500x600")
        self.configure(bg="white")
        
        # make window modal
        self.transient(master)
        self.grab_set()
        
        # center the window
        self.center_window()
        
        # create the form
        self.create_form()

    def center_window(self):
        # get screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # calculate position coordinates
        x = (screen_width/2) - (500/2)
        y = (screen_height/2) - (600/2)
        
        # set the position
        self.geometry(f'500x600+{int(x)}+{int(y)}')

    def create_form(self):
        # main container with padding
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # title
        ttk.Label(main_frame, text="Create New Task", 
                 font=("Arial", 16, "bold")).pack(pady=(0, 20))

        # task Name
        ttk.Label(main_frame, text="Task Name:").pack(anchor=tk.W, pady=(5,0))
        self.task_name_entry = ttk.Entry(main_frame)
        self.task_name_entry.pack(fill=tk.X)

        # description
        ttk.Label(main_frame, text="Description:").pack(anchor=tk.W, pady=(10,0))
        self.description_text = tk.Text(main_frame, height=3)
        self.description_text.pack(fill=tk.X)

        # category dropdown
        ttk.Label(main_frame, text="Category:").pack(anchor=tk.W, pady=(10,0))
        categories = get_categories()
        self.category_var = tk.StringVar()
        self.category_dropdown = ttk.Combobox(
            main_frame,
            textvariable=self.category_var,
            values=[cat[1] for cat in categories],  # Show names
            state="readonly"
        )
        self.category_dropdown.pack(fill=tk.X)
        self.category_dropdown.bind("<<ComboboxSelected>>", self.on_category_change)

        # date frame
        self.date_frame = ttk.Frame(main_frame)
        self.date_frame.pack(fill=tk.X, pady=(10,0))
        
        self.date_label = ttk.Label(self.date_frame, text="Due Date (YYYY-MM-DD):")
        self.date_label.pack(anchor=tk.W)
        
        date_entry_frame = ttk.Frame(self.date_frame)
        date_entry_frame.pack(fill=tk.X)
        
        self.date_entry = ttk.Entry(date_entry_frame)
        self.date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # calendar button
        ttk.Button(date_entry_frame, text="📅", width=3,
                  command=self.show_calendar).pack(side=tk.LEFT, padx=(5, 0))

        # priority dropdown (initially hidden)
        self.priority_label = ttk.Label(main_frame, text="Priority:")
        self.priority_var = tk.StringVar()
        self.priority_dropdown = ttk.Combobox(
            main_frame,
            textvariable=self.priority_var,
            values=["Urgent", "Not Urgent"],
            state="readonly"
        )

        # recurrence pattern frame (initially hidden)
        self.recurrence_frame = ttk.Frame(main_frame)
        ttk.Label(self.recurrence_frame, text="Recurrence Pattern:").pack(anchor=tk.W)
        self.recurrence_var = tk.StringVar()
        self.recurrence_dropdown = ttk.Combobox(
            self.recurrence_frame,
            textvariable=self.recurrence_var,
            values=["Daily", "Weekly", "Monthly", "Annually"],
            state="readonly"
        )
        self.recurrence_dropdown.pack(fill=tk.X)

        # buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(20,0))
        
        ttk.Button(buttons_frame, text="Save Task", 
                  command=self.save_task).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))
        ttk.Button(buttons_frame, text="Cancel",
                  command=self.destroy).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5,0))

    def on_category_change(self, event=None):
        category = self.category_var.get()
        
        # hide both optional sections first
        self.priority_label.pack_forget()
        self.priority_dropdown.pack_forget()
        self.recurrence_frame.pack_forget()
        
        if category == "Recurring":
            self.priority_var.set("")
            self.recurrence_frame.pack(fill=tk.X, pady=(10,0))
            self.date_label.config(text="Starting Date (YYYY-MM-DD):")
        elif category == "On-going":
            self.recurrence_var.set("")
            self.priority_label.pack(anchor=tk.W, pady=(10,0))
            self.priority_dropdown.pack(fill=tk.X)
            self.date_label.config(text="Due Date (YYYY-MM-DD):")
        else:
            self.priority_var.set("")
            self.recurrence_var.set("")
            self.date_label.config(text="Due Date (YYYY-MM-DD):")
            
    def show_calendar(self):
        top = tk.Toplevel(self)
        top.title("Select Date")
        
        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd')
        cal.pack(padx=10, pady=10)
        
        def set_date():
            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, cal.get_date())
            top.destroy()
        
        ttk.Button(top, text="Select", command=set_date).pack(pady=10)

    def save_task(self):
        title = self.task_name_entry.get().strip()
        description = self.description_text.get("1.0", tk.END).strip()
        date = self.date_entry.get().strip()
        category = self.category_var.get()
        priority = self.priority_var.get() if category == "On-going" else ""
        is_recurring = 1 if category == "Recurring" else 0
        recurrence_pattern = self.recurrence_var.get() if category == "Recurring" else None

        if not title:
            tkinter.messagebox.showerror("Error", "Task Name is required.")
            return

        if not date:
            error_msg = "Starting Date is required." if category == "Recurring" else "Due Date is required."
            tkinter.messagebox.showerror("Error", error_msg)
            return

        if category == "Recurring" and not recurrence_pattern:
            tkinter.messagebox.showerror("Error", "Please select a recurrence pattern for recurring tasks.")
            return

        try:
            print(f"Saving task: Title={title}, Category={category}, Priority={priority}")
            category_name = self.category_var.get()
            categories = get_categories()  # Fetch categories here
            category_id = next((cat[0] for cat in categories if cat[1] == category_name), None)
            AddTask(title, description, category_id, priority, date, is_recurring, 
                   self.user_id, recurrence_pattern)
            tkinter.messagebox.showinfo("Success", "Task saved successfully!")
            
            # refresh the task list and calendar in the main window
            if hasattr(self.master, 'task_view') and self.master.task_view:
                print("Refreshing task list")
                self.master.filter_tasks_by_date(datetime.now())
                self.master.update_calendar_tasks()  # update calendar after adding task
            self.destroy()
        except Exception as e:
            print(f"Error saving task: {str(e)}")
            tkinter.messagebox.showerror("Error", f"Failed to save task: {str(e)}")

if __name__ == "__main__":
    login_win = LoginWindow()
    login_win.mainloop()
