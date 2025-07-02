import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QGridLayout,
    QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QFrame, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QCalendarWidget, QToolTip, QScrollArea
)
from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QPainter, QColor, QPen
from datetime import datetime, date
#
import calendar
import sqlite3
import hashlib

# Reuse database functions from original code
def Connect():
    conn = sqlite3.connect("timePlanDB.db")
    return conn

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

def AuthenticateUser(username, password):
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                   (username, HashPassword(password)))
    user = cursor.fetchone()
    conn.close()
    return user

def CreateHabitCompletionsTable():
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habit_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            completion_date TEXT NOT NULL,
            FOREIGN KEY (habit_id) REFERENCES habits(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

def CreateHabitsTable():
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            last_completed TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TimePlan Login")
        self.setFixedSize(350, 200)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Create user table
        CreateUserTable()
        
        # Username field
        username_label = QLabel("Username:")
        self.username_entry = QLineEdit()
        layout.addWidget(username_label)
        layout.addWidget(self.username_entry)
        
        # Password field
        password_label = QLabel("Password:")
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(password_label)
        layout.addWidget(self.password_entry)
        
        # Buttons frame
        buttons_frame = QFrame()
        buttons_layout = QHBoxLayout(buttons_frame)
        
        # Login button
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.login)
        buttons_layout.addWidget(login_btn)
        
        # Sign up button
        signup_btn = QPushButton("Sign Up")
        signup_btn.clicked.connect(self.open_signup)
        buttons_layout.addWidget(signup_btn)
        
        layout.addWidget(buttons_frame)
        
        # Center window
        self.center_window()
        
        # Connect return key to login
        self.username_entry.returnPressed.connect(self.login)
        self.password_entry.returnPressed.connect(self.login)

    def center_window(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def login(self):
        username = self.username_entry.text().strip()
        password = self.password_entry.text().strip()

        if not username or not password:
            QMessageBox.critical(self, "Error", "Please enter username and password.")
            return

        user = AuthenticateUser(username, password)
        if user:
            self.main_window = TimePlanMainWindow(user[0], username)  # Store as instance variable
            self.main_window.show()
            self.hide()  # Hide instead of close
        else:
            QMessageBox.critical(self, "Error", "Invalid username or password.")

    def open_signup(self):
        self.signup_window = SignUpWindow(self)
        self.signup_window.show()
        self.hide()

class SignUpWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Sign Up")
        self.setFixedSize(400, 350)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("Create a new account")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Username field
        username_label = QLabel("Username:")
        self.username_entry = QLineEdit()
        layout.addWidget(username_label)
        layout.addWidget(self.username_entry)
        
        # Password field
        password_label = QLabel("Password:")
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(password_label)
        layout.addWidget(self.password_entry)
        
        # Confirm password field
        confirm_label = QLabel("Confirm Password:")
        self.confirm_entry = QLineEdit()
        self.confirm_entry.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(confirm_label)
        layout.addWidget(self.confirm_entry)
        
        # Register button
        register_btn = QPushButton("Register")
        register_btn.clicked.connect(self.register_user)
        layout.addWidget(register_btn)
        
        # Back button
        back_btn = QPushButton("Back to Login")
        back_btn.clicked.connect(self.back_to_login)
        layout.addWidget(back_btn)
        
        # Center window
        self.center_window()

    def center_window(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def register_user(self):
        # TODO: Implement user registration
        pass

    def back_to_login(self):
        self.parent.show()
        self.close()

class CollapsibleSidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = True
        self.setFixedWidth(200)  # Default expanded width
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # App name label
        self.app_name = QLabel("TimePlan")
        self.app_name.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                padding: 20px;
                background-color: #2c3e50;
                color: white;
            }
        """)
        layout.addWidget(self.app_name)

        # Navigation buttons
        self.nav_buttons = []
        nav_items = [
            ("Tasks", "📋"),
            ("Calendar", "📅"),
            ("Habit", "🔄"),
            ("Add Task", "➕"),
            ("Search Task", "🔍"),
            ("Profile", "👤"),
            ("Sign Out", "🚪")
        ]

        for text, icon in nav_items:
            btn = QPushButton(f"{icon} {text}")
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    border: none;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: #34495e;
                    color: white;
                }
            """)
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()

        # Toggle button
        self.toggle_btn = QPushButton("◀")
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                padding: 5px;
                border: none;
                background-color: #2c3e50;
                color: white;
            }
        """)
        layout.addWidget(self.toggle_btn)

        self.setStyleSheet("""
            CollapsibleSidebar {
                background-color: #ecf0f1;
                border-right: 1px solid #bdc3c7;
            }
        """)

    def toggle_sidebar(self):
        if self.is_expanded:
            self.setFixedWidth(50)
            self.toggle_btn.setText("▶")
            self.app_name.hide()
            for btn in self.nav_buttons:
                text = btn.text().split(" ")[0]  # Keep only the emoji
                btn.setText(text)
        else:
            self.setFixedWidth(200)
            self.toggle_btn.setText("◀")
            self.app_name.show()
            for i, btn in enumerate(self.nav_buttons):
                text = ["Tasks", "Calendar", "Habit", "Add Task", "Search Task", "Profile", "Sign Out"][i]
                emoji = btn.text()
                btn.setText(f"{emoji} {text}")
        
        self.is_expanded = not self.is_expanded

class TaskCalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = {}  # Dictionary to store tasks by date
        
    def paintCell(self, painter: QPainter, rect: QRect, date):
        # Paint the original cell
        super().paintCell(painter, rect, date)
        
        # If there are tasks for this date
        date_str = date.toString("yyyy-MM-dd")
        if date_str in self.tasks:
            # Draw a colored dot or task count
            tasks = self.tasks[date_str]
            task_count = len(tasks)
            
            if task_count > 0:
                # Draw task count
                painter.save()
                painter.setPen(QColor("#2980b9"))
                painter.drawText(
                    rect, 
                    Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
                    f"{task_count}"
                )
                
                # Draw colored dot
                dot_size = 8
                painter.setBrush(QColor("#2980b9"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(
                    rect.right() - dot_size - 4,
                    rect.top() + 4,
                    dot_size,
                    dot_size
                )
                painter.restore()
    
    def updateTasks(self, user_id):
        self.tasks.clear()
        conn = Connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT title, due_date, status 
                FROM tasks 
                WHERE user_id = ?
                AND due_date IS NOT NULL
                AND due_date != ''
            """, (user_id,))
            
            for title, due_date, status in cursor.fetchall():
                if due_date:  # Check if due_date is not None or empty
                    try:
                        # Handle different date formats
                        if ' ' in due_date:  # If date contains time
                            date_str = due_date.split()[0]  # Get just the date part
                        else:
                            date_str = due_date  # Use the whole string as date
                            
                        if date_str not in self.tasks:
                            self.tasks[date_str] = []
                        self.tasks[date_str].append({
                            'title': title,
                            'status': status
                        })
                    except Exception as e:
                        print(f"Error processing date '{due_date}': {e}")
                        continue
            
            self.updateCells()  # Refresh calendar display
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()

class PlannerWidget(QWidget):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.tasks = {}
        self.current_date = datetime.now()
        self.initUI()
        # Load tasks immediately after initialization
        self.load_tasks()
        self.update_calendar()

    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Month navigation
        nav_layout = QHBoxLayout()
        self.prev_month = QPushButton("◀")
        self.next_month = QPushButton("▶")
        self.month_label = QLabel()
        self.month_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        nav_layout.addWidget(self.prev_month)
        nav_layout.addWidget(self.month_label)
        nav_layout.addWidget(self.next_month)
        layout.addLayout(nav_layout)

        # Connect navigation buttons
        self.prev_month.clicked.connect(self.previous_month)
        self.next_month.clicked.connect(self.next_month_clicked)

        # Create grid layout for calendar
        self.grid = QGridLayout()
        layout.addLayout(self.grid)
        
        # Initial calendar display
        self.update_calendar()

    def update_calendar(self):
        # Clear existing grid
        for i in reversed(range(self.grid.count())):
            self.grid.itemAt(i).widget().setParent(None)

        # Update month label
        self.month_label.setText(self.current_date.strftime("%B %Y"))

        # Add day headers
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for i, day in enumerate(days):
            label = QLabel(day)
            label.setStyleSheet("""
                padding: 10px;
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                font-weight: bold;
            """)
            self.grid.addWidget(label, 0, i)

        # Get calendar data
        cal = calendar.monthcalendar(self.current_date.year, self.current_date.month)

        # Add day cells
        for row, week in enumerate(cal, 1):
            for col, day in enumerate(week):
                if day != 0:
                    cell = self.create_day_cell(day)
                    self.grid.addWidget(cell, row, col)
                else:
                    # Empty cell for days outside current month
                    empty = QWidget()
                    empty.setStyleSheet("background-color: #f9f9f9;")
                    self.grid.addWidget(empty, row, col)

    def create_day_cell(self, day):
        cell = QWidget()
        cell_layout = QVBoxLayout(cell)
        cell_layout.setContentsMargins(5, 5, 5, 5)
        
        # Format date string to match database format
        date_str = f"{self.current_date.year}-{self.current_date.month:02d}-{day:02d}"
        
        # Highlight today's date
        is_today = (date.today().strftime("%Y-%m-%d") == date_str)
        
        # Date number
        date_label = QLabel(f"{day}")
        if is_today:
            date_label.setStyleSheet("""
                font-weight: bold;
                color: white;
                background-color: #2980b9;
                padding: 2px 5px;
                border-radius: 2px;
            """)
        else:
            date_label.setStyleSheet("font-weight: bold;")
        cell_layout.addWidget(date_label)
        
        # Task list
        task_list = QTreeWidget()
        task_list.setHeaderHidden(True)
        task_list.setMaximumHeight(100)
        task_list.setStyleSheet("""
            QTreeWidget {
                border: none;
                background-color: transparent;
            }
            QTreeWidget::item {
                padding: 2px;
            }
        """)

        # Add tasks for this day
        if date_str in self.tasks:
            for task in self.tasks[date_str]:
                item = QTreeWidgetItem([task['title']])
                if task['status'] == 'Completed':
                    item.setForeground(0, QColor('#27ae60'))
                elif task['status'] == 'Missed':
                    item.setForeground(0, QColor('#e74c3c'))
                task_list.addTopLevelItem(item)

        cell_layout.addWidget(task_list)
        
        # Style the cell
        cell.setStyleSheet(f"""
            QWidget {{
                background-color: {'#f0f7ff' if is_today else 'white'};
                border: 1px solid {'#2980b9' if is_today else '#ddd'};
            }}
        """)
        return cell

    def load_tasks(self):
        self.tasks.clear()
        conn = Connect()
        cursor = conn.cursor()
        
        try:
            # Get all tasks for current month
            month_start = f"{self.current_date.year}-{self.current_date.month:02d}-01"
            if self.current_date.month == 12:
                next_month_year = self.current_date.year + 1
                next_month = 1
            else:
                next_month_year = self.current_date.year
                next_month = self.current_date.month + 1
            month_end = f"{next_month_year}-{next_month:02d}-01"
            
            cursor.execute("""
                SELECT title, due_date, status 
                FROM tasks 
                WHERE user_id = ?
                AND date(due_date) >= date(?)
                AND date(due_date) < date(?)
                AND due_date IS NOT NULL
                AND due_date != ''
            """, (self.user_id, month_start, month_end))
            
            for title, due_date, status in cursor.fetchall():
                try:
                    if due_date:
                        date_str = due_date.split()[0] if ' ' in due_date else due_date
                        if date_str not in self.tasks:
                            self.tasks[date_str] = []
                        self.tasks[date_str].append({
                            'title': title,
                            'status': status
                        })
                except Exception as e:
                    print(f"Error processing task date '{due_date}': {e}")
                    continue
            
            print(f"Loaded {len(self.tasks)} days with tasks")
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()

    def previous_month(self):
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month - 1)
        self.load_tasks()
        self.update_calendar()

    def next_month_clicked(self):
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month + 1)
        self.load_tasks()
        self.update_calendar()

class HabitWidget(QWidget):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.initUI()
        self.load_recurring_tasks()

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Left panel for recurring tasks list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Header
        header = QLabel("Recurring Tasks")
        header.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 20px;
        """)
        left_layout.addWidget(header)

        # Task list
        self.task_list = QTreeWidget()
        self.task_list.setHeaderLabels(["Task", "Recurrence", "Last Completed"])
        self.task_list.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background-color: white;
            }
            QTreeWidget::item {
                padding: 8px;
            }
            QTreeWidget::item:hover {
                background-color: #f5f6fa;
            }
        """)
        left_layout.addWidget(self.task_list)
        
        # Right panel for calendar
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Calendar widget
        self.calendar = TaskCalendarWidget(self)
        self.calendar.setMinimumWidth(400)
        right_layout.addWidget(self.calendar)

        # Add panels to main layout
        layout.addWidget(left_panel, stretch=1)
        layout.addWidget(right_panel, stretch=1)

        # Connect task selection to calendar update
        self.task_list.itemSelectionChanged.connect(self.update_calendar_checkmarks)

    def load_recurring_tasks(self):
        conn = Connect()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT id, title, recurrence, last_completed
                FROM tasks 
                WHERE user_id = ? AND category = 'Recurring'
                ORDER BY title
            ''', (self.user_id,))
            
            tasks = cursor.fetchall()
            self.task_list.clear()
            
            for task in tasks:
                item = QTreeWidgetItem(self.task_list)
                task_id, title, recurrence, last_completed = task
                
                # Store task_id for later use
                item.setData(0, Qt.ItemDataRole.UserRole, task_id)
                
                # Set column values
                item.setText(0, title)
                item.setText(1, f"Every {recurrence} days")
                item.setText(2, last_completed if last_completed else "Never")
                
                # Check if task is due (highlight if overdue)
                if last_completed:
                    last_date = datetime.strptime(last_completed, '%Y-%m-%d').date()
                    days_since = (date.today() - last_date).days
                    if days_since >= recurrence:
                        item.setForeground(0, QColor('red'))
                
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Database Error", str(e))
        finally:
            conn.close()

    def update_calendar_checkmarks(self):
        selected_items = self.task_list.selectedItems()
        if not selected_items:
            return
            
        task_item = selected_items[0]
        task_id = task_item.data(0, Qt.ItemDataRole.UserRole)
        
        # Clear existing marks
        self.calendar.tasks.clear()
        
        # Get the last completed date for selected task
        conn = Connect()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT last_completed FROM tasks 
                WHERE task_id = ? AND user_id = ?
            ''', (task_id, self.user_id))
            result = cursor.fetchone()
            
            if result and result[0]:
                last_completed = result[0]
                self.calendar.tasks[last_completed] = True
                
            self.calendar.updateCell()
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Database Error", str(e))
        finally:
            conn.close()

class TimePlanMainWindow(QMainWindow):
    def __init__(self, user_id, username):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.setWindowTitle("TimePlan")
        self.setMinimumSize(1000, 600)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add collapsible sidebar
        self.sidebar = CollapsibleSidebar()
        main_layout.addWidget(self.sidebar)

        # Create stacked widget for different views
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create views
        self.tasks_view = self.create_tasks_view()
        self.calendar_view = self.create_calendar_view()
        self.habit_view = self.create_habit_view()

        # Add views to stacked widget
        self.stacked_widget.addWidget(self.tasks_view)
        self.stacked_widget.addWidget(self.calendar_view)
        self.stacked_widget.addWidget(self.habit_view)

        # Connect sidebar buttons
        self.sidebar.nav_buttons[0].clicked.connect(
            lambda: self.stacked_widget.setCurrentWidget(self.tasks_view)
        )
        self.sidebar.nav_buttons[1].clicked.connect(self.show_calendar_view)
        self.sidebar.nav_buttons[2].clicked.connect(self.show_habit_view)

        self.center_window()

    def create_tasks_view(self):
        tasks_widget = QWidget()
        layout = QHBoxLayout(tasks_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create categories sidebar
        categories_sidebar = QWidget()
        categories_sidebar.setFixedWidth(250)
        categories_sidebar.setStyleSheet("""
            QWidget {
                background-color: #f5f6fa;
                border-right: 1px solid #dcdde1;
            }
            QTreeWidget {
                border: none;
                background-color: transparent;
            }
            QTreeWidget::item {
                padding: 10px;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #dcdde1;
            }
        """)
        
        categories_layout = QVBoxLayout(categories_sidebar)
        categories_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add categories tree widget
        categories = QTreeWidget()
        categories.setHeaderHidden(True)
        
        # Task Categories
        task_categories = [
            ("📅 Today", "today"),
            ("📆 Next 7 Days", "next7"),
            ("📋 All Tasks", "all"),
            ("🔄 On-going", "ongoing"),
            ("✅ Completed", "completed"),
            ("❗ Missed", "missed")
        ]
        
        for label, category_id in task_categories:
            category_item = QTreeWidgetItem(categories, [label])
            category_item.setData(0, Qt.ItemDataRole.UserRole, category_id)
        
        categories.itemClicked.connect(self.on_category_selected)
        categories_layout.addWidget(categories)
        
        # Create main content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 20)
        
        self.category_title = QLabel("📅 Today")
        self.category_title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2d3436;
        """)
        header_layout.addWidget(self.category_title)
        
        # Add task count
        self.task_count = QLabel("0 tasks")
        self.task_count.setStyleSheet("color: #636e72;")
        header_layout.addWidget(self.task_count)
        header_layout.addStretch()
        
        content_layout.addWidget(header)
        
        # Add task list
        self.task_list = QTreeWidget()
        self.task_list.setHeaderLabels(["Task", "Due Date", "Status"])
        self.task_list.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background-color: white;
            }
            QTreeWidget::item {
                padding: 8px;
            }
        """)
        content_layout.addWidget(self.task_list)
        
        # Add widgets to main layout
        layout.addWidget(categories_sidebar)
        layout.addWidget(content, stretch=1)
        
        return tasks_widget

    def on_category_selected(self, item):
        category_id = item.data(0, Qt.ItemDataRole.UserRole)
        self.category_title.setText(item.text(0))
        self.load_tasks(category_id)
        
    def load_tasks(self, category):
        self.task_list.clear()
        conn = Connect()
        cursor = conn.cursor()
        
        query_map = {
            "today": """
                SELECT id, title, due_date, category 
                FROM tasks 
                WHERE user_id = ? 
                AND date(due_date) = date('now')
            """,
            "next7": """
                SELECT id, title, due_date, category 
                FROM tasks 
                WHERE user_id = ? 
                AND date(due_date) BETWEEN date('now') 
                AND date('now', '+7 days')
            """,
            "all": """
                SELECT id, title, due_date, category 
                FROM tasks 
                WHERE user_id = ?
                AND (is_recurring = 0 OR is_recurring IS NULL)
            """,
            "ongoing": """
                SELECT id, title, due_date, category 
                FROM tasks 
                WHERE user_id = ? 
                AND (category = 'On-going')
                AND category != 'Completed'
            """,
            "completed": """
                SELECT id, title, due_date, category 
                FROM tasks 
                WHERE user_id = ? 
                AND (category = 'Completed')
            """,
            "missed": """
                SELECT id, title, due_date, category 
                FROM tasks 
                WHERE user_id = ? 
                AND date(due_date) < date('now')
                AND category NOT IN ('Completed', 'Done')
            """
        }
        
        try:
            cursor.execute(query_map[category], (self.user_id,))
            tasks = cursor.fetchall()
            
            for task in tasks:
                item = QTreeWidgetItem(self.task_list)
                item.setText(0, task[1])  # Title
                item.setText(1, task[2])  # Due Date
                item.setText(2, task[3])  # Status
                item.setData(0, Qt.ItemDataRole.UserRole, task[0])  # Store task ID
            
            self.task_count.setText(f"{len(tasks)} tasks")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()

    def create_calendar_view(self):
        scroll = QScrollArea()
        self.planner = PlannerWidget(user_id=self.user_id)  # Pass user_id here
        scroll.setWidget(self.planner)
        scroll.setWidgetResizable(True)
        return scroll

    def create_habit_view(self):
        return HabitWidget(self.user_id)

    def on_date_selected(self, date):
        date_str = date.toString("yyyy-MM-dd")
        if date_str in self.calendar.tasks:
            tasks = self.calendar.tasks[date_str]
            tasks_str = "\n".join([f"• {task['title']} ({task['status']})" 
                                  for task in tasks])
            QToolTip.showText(
                self.mapToGlobal(self.calendar.pos()),
                f"Tasks for {date.toString('MMMM d, yyyy')}:\n{tasks_str}",
                self.calendar
            )

    def center_window(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def show_calendar_view(self):
        self.stacked_widget.setCurrentWidget(self.calendar_view)
        # Refresh tasks when switching to calendar
        if hasattr(self, 'planner'):
            self.planner.load_tasks()
            self.planner.update_calendar()

    def show_habit_view(self):
        self.stacked_widget.setCurrentWidget(self.habit_view)
        # Refresh habits when switching to the view
        if hasattr(self, 'habit_view'):
            self.habit_view.load_habits()

def main():
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()