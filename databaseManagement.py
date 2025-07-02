import sqlite3
from datetime import datetime, timedelta
import pytz # Make sure pytz is installed: pip install pytz

class DatabaseManager:
    def __init__(self, db_name='timePlanDB.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self._connect()
        self.create_tables()

    def _connect(self, retries=3):
        for i in range(retries):
            try:
                self.conn = sqlite3.connect(self.db_name)
                self.cursor = self.conn.cursor()
                print(f"Connected to database: {self.db_name}")
                return True
            except sqlite3.Error as e:
                print(f"Database connection error (attempt {i+1}/{retries}): {e}")
                if i < retries - 1:
                    import time
                    time.sleep(1) # Wait a bit before retrying
        self.conn = None
        self.cursor = None
        return False

    def _close(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

    def _execute_query(self, query, params=()):
        if not self.conn:
            if not self._connect(): # Attempt to reconnect if not connected
                print("Failed to execute query: Not connected to database.")
                return False
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database query error: {e} for query: {query} with params: {params}")
            self.conn.rollback() # Rollback changes on error
            return False

    def _fetch_all(self, query, params=()):
        if not self.conn:
            if not self._connect():
                return []
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database fetch error: {e} for query: {query} with params: {params}")
            return []

    def _fetch_one(self, query, params=()):
        if not self.conn:
            if not self._connect():
                return None
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Database fetch error: {e} for query: {query} with params: {params}")
            return None

    def create_tables(self):
        # Create users table
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS users (
                user_id          INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
                username    TEXT    UNIQUE NOT NULL,
                password    TEXT    NOT NULL
            );
        """)

        # Create task_category table
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS task_category (
                category_id   INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
                category_name TEXT    NOT NULL UNIQUE
            );
        """)

        # Create priority table
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS priority (
                priority_id   INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
                priority_name TEXT    NOT NULL UNIQUE,
                priority_level INTEGER NOT NULL
            );
        """)
        
        # Insert default priorities if they don't exist
        default_priorities = [
            ("Urgent", 1),
            ("Not urgent", 2)
        ]
        for priority_name, level in default_priorities:
            self._execute_query(
                "INSERT OR IGNORE INTO priority (priority_name, priority_level) VALUES (?, ?)",
                (priority_name, level)
            )

        # Create tasks table (STATUS COLUMN REMOVED IN PREVIOUS STEP, REMAINS GONE)
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id     INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
                task_title       TEXT    NOT NULL,
                description TEXT,
                priority_id INTEGER REFERENCES priority (priority_id) NOT NULL,
                due_date    DATE,
                user_id     INTEGER NOT NULL DEFAULT 1 REFERENCES users (user_id),
                category_id INTEGER REFERENCES task_category (category_id) NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create recurring_tasks table (No status column here either)
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS recurring_tasks (
                rtask_id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                rtask_title                 TEXT    NOT NULL,
                description           TEXT,
                start_date            TEXT,
                recurrence_pattern    TEXT    NOT NULL,
                last_completed_date TEXT,
                user_id               INTEGER NOT NULL,
                status              TEXT    DEFAULT 'Pending',
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            );
        """)
        
        # Add a default user if none exists (for testing/initial setup)
        if not self._fetch_one("SELECT * FROM users WHERE user_id = 1"):
            self.add_user("default_user", "password123")
        
        # Add default categories: "On-going", "Missed", "Completed"
        default_categories = ["On-going", "Missed", "Completed"]
        existing_categories = [row[0] for row in self.get_task_categories()]
        for cat in default_categories:
            if cat not in existing_categories:
                self.add_category(cat)
        
        # Update database schema for any missing columns
        self.update_database_schema()


    # --- CRUD operations for Tasks ---
    # add_task method remains unchanged as it never had a 'status' argument after previous removal
    def add_task(self, user_id, task_title, description=None, priority_name=None, due_date=None, category_id=1):
        """Add a new task and return the new task ID on success."""
        description = description if description else None
        due_date = due_date if due_date else None # due_date should be 'YYYY-MM-DD' format
        
        # Convert priority name to priority_id
        priority_id = None
        if priority_name:
            priority_id = self.get_priority_id_by_name(priority_name)
            if not priority_id:
                # Default to "Not urgent" if invalid priority name
                priority_id = self.get_priority_id_by_name("Not urgent")

        query = """
            INSERT INTO tasks (user_id, task_title, description, priority_id, due_date, category_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        success = self._execute_query(query, (user_id, task_title, description, priority_id, due_date, category_id))
        
        if success:
            # Get the ID of the last inserted row
            last_id = self._fetch_one("SELECT last_insert_rowid()")
            return last_id[0] if last_id else None
        return None
        
    def get_tasks(self, user_id, filter_type='All Tasks'):
        query = """
            SELECT t.task_id, t.task_title, t.description, p.priority_name, t.due_date, tc.category_name
            FROM tasks t 
            JOIN task_category tc ON t.category_id = tc.category_id 
            LEFT JOIN priority p ON t.priority_id = p.priority_id
        """ \
                "WHERE t.user_id = ? "
        params = [user_id]
        
        philippines_timezone = pytz.timezone('Asia/Manila')
        current_local_date = datetime.now(philippines_timezone)
        current_local_date_str = current_local_date.strftime('%Y-%m-%d')
        
        # Get the IDs of important categories
        completed_cat_id_row = self._fetch_one("SELECT category_id FROM task_category WHERE category_name = ?", ("Completed",))
        completed_category_id = completed_cat_id_row[0] if completed_cat_id_row else None
        
        ongoing_cat_id_row = self._fetch_one("SELECT category_id FROM task_category WHERE category_name = ?", ("On-going",))
        ongoing_category_id = ongoing_cat_id_row[0] if ongoing_cat_id_row else None
        
        missed_cat_id_row = self._fetch_one("SELECT category_id FROM task_category WHERE category_name = ?", ("Missed",))
        missed_category_id = missed_cat_id_row[0] if missed_cat_id_row else None

        # Apply filters based on the filter type
        if filter_type == 'Today':
            # Today: display the on-going tasks for today
            query += "AND t.due_date = ? AND tc.category_name = 'On-going' "
            params.append(current_local_date_str)
        elif filter_type == 'Next 7 Days':
            # Next 7 days: display the on-going tasks for the next 7 days
            next_7_days_str = (current_local_date + timedelta(days=7)).strftime('%Y-%m-%d')
            query += "AND t.due_date BETWEEN ? AND ? AND tc.category_name = 'On-going' "
            params.extend([current_local_date_str, next_7_days_str])
        elif filter_type == 'All Tasks':
            # All tasks: display all tasks, regardless of category (no additional filter)
            pass
        elif filter_type == 'On-going':
            # On-going: display all on-going tasks that are not past due
            if ongoing_category_id:
                query += """AND t.category_id = ? 
                    AND (t.due_date IS NULL 
                         OR DATE(t.due_date) >= DATE(?))"""
                params.extend([ongoing_category_id, current_local_date_str])
        elif filter_type == 'Completed':
            # Completed: display all completed tasks
            if completed_category_id:
                query += "AND t.category_id = ? "
                params.append(completed_category_id)
        elif filter_type == 'Missed':
            # Missed: display all missed tasks
            if missed_category_id:
                query += "AND t.category_id = ? "
                params.append(missed_category_id)

        # Add ordering by date
        # For all filters, sort by due date (nearest first)
        # Tasks with NULL due_date will be at the end
        if filter_type in ['All Tasks', 'On-going', 'Today', 'Next 7 Days']:
            # For tasks that need closest due date first
            query += "ORDER BY CASE WHEN t.due_date IS NULL THEN 1 ELSE 0 END, t.due_date ASC, p.priority_level ASC"
        elif filter_type in ['Completed', 'Missed']:
            # For completed/missed tasks, sort by date (could be oldest first or newest first)
            query += "ORDER BY t.due_date DESC" # Most recently completed/missed first
        
        return self._fetch_all(query, params)

    def get_task_by_id(self, task_id):
        """Get a specific task by its ID.
        
        Args:
            task_id: The ID of the task to retrieve
            
        Returns:
            A tuple containing (task_id, title, description, priority, due_date, category_name)
            or None if the task is not found.
        """
        query = """
            SELECT t.task_id, t.task_title, t.description, p.priority_name, t.due_date, tc.category_name 
            FROM tasks t 
            JOIN task_category tc ON t.category_id = tc.category_id 
            LEFT JOIN priority p ON t.priority_id = p.priority_id
            WHERE t.task_id = ?
        """
        return self._fetch_one(query, (task_id,))

    def update_task_details(self, task_id, task_title=None, description=None, priority=None, due_date=None, category_id=None):
        updates = []
        params = []
        if task_title is not None:
            updates.append("task_title = ?")
            params.append(task_title)
        if description is not None:
            updates.append("description = ?")
            params.append(description if description else None)
        if priority is not None:
            priority_id = self.get_priority_id_by_name(priority)
            if priority_id:
                updates.append("priority_id = ?")
                params.append(priority_id)
        if due_date is not None:
            updates.append("due_date = ?")
            params.append(due_date if due_date else None)
        if category_id is not None:
            updates.append("category_id = ?")
            params.append(category_id)
        
        if not updates:
            print("No details to update.")
            return False

        query = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?"
        params.append(task_id)
        return self._execute_query(query, tuple(params))

    # New method to update a task's category (for "completing" or "uncompleting" tasks)
    def update_task_category(self, task_id, new_category_id):
        query = "UPDATE tasks SET category_id = ? WHERE task_id = ?"
        return self._execute_query(query, (new_category_id, task_id))

    def delete_task(self, task_id):
        query = "DELETE FROM tasks WHERE task_id = ?"
        return self._execute_query(query, (task_id,))

    # --- CRUD operations for Task Categories ---
    def get_task_categories(self):
        query = "SELECT category_name, category_id FROM task_category ORDER BY category_name"
        return self._fetch_all(query)

    def add_category(self, category_name):
        query = "INSERT INTO task_category (category_name) VALUES (?)"
        return self._execute_query(query, (category_name,))

    def get_category_id_by_name(self, category_name):
        query = "SELECT category_id FROM task_category WHERE category_name = ?"
        result = self._fetch_one(query, (category_name,))
        return result[0] if result else None

    # --- CRUD operations for Users ---
    def add_user(self, username, password):
        query = "INSERT INTO users (username, password) VALUES (?, ?)"
        return self._execute_query(query, (username, password))

    def get_user_by_username(self, username):
        query = "SELECT user_id, username, password FROM users WHERE username = ?"
        return self._fetch_one(query, (username,))

    def update_task(self, task_id, task_title, description, priority_name, due_date, category_id):
        """Update all fields of a task at once."""
        # Convert priority name to priority_id
        priority_id = None
        if priority_name:
            priority_id = self.get_priority_id_by_name(priority_name)
            if not priority_id:
                priority_id = self.get_priority_id_by_name("Not urgent")

        # Parse the due date
        due_date_obj = self._parse_date(due_date)
        formatted_date = self._format_date(due_date_obj)

        query = """
            UPDATE tasks 
            SET task_title = ?, 
                description = ?, 
                priority_id = ?, 
                due_date = ?, 
                category_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """
        return self._execute_query(query, (task_title, description, priority_id, formatted_date, category_id, task_id))

    # --- Priority Management Methods ---
    def get_priority_id_by_name(self, priority_name):
        """Get priority ID from priority name."""
        query = "SELECT priority_id FROM priority WHERE priority_name = ?"
        result = self._fetch_one(query, (priority_name,))
        return result[0] if result else None

    def get_priority_name_by_id(self, priority_id):
        """Get priority name from priority ID."""
        query = "SELECT priority_name FROM priority WHERE priority_id = ?"
        result = self._fetch_one(query, (priority_id,))
        return result[0] if result else None

    def get_all_priorities(self):
        """Get all priority names ordered by priority level."""
        query = "SELECT priority_name FROM priority ORDER BY priority_level"
        results = self._fetch_all(query)
        return [row[0] for row in results] if results else ["Not urgent", "Urgent"]  # Fallback to defaults if query fails

    def _get_ph_timezone(self):
        """Get Philippines timezone"""
        return pytz.timezone('Asia/Manila')
    
    def _get_current_local_date(self):
        """Get current date in PH timezone"""
        ph_tz = self._get_ph_timezone()
        return datetime.now(ph_tz).date()
    
    def _parse_date(self, date_str):
        """Convert string date to datetime.date object"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            print(f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD")
            return None
            
    def _format_date(self, date_obj):
        """Convert datetime.date object to string"""
        if not date_obj:
            return None
        try:
            return date_obj.strftime('%Y-%m-%d')
        except AttributeError:
            print(f"Invalid date object: {date_obj}")
            return None

    def update_past_due_tasks(self):
        """Move all past due On-going tasks to the Missed category."""
        # Get the category IDs
        ongoing_cat_id_row = self._fetch_one("SELECT category_id FROM task_category WHERE category_name = ?", ("On-going",))
        missed_cat_id_row = self._fetch_one("SELECT category_id FROM task_category WHERE category_name = ?", ("Missed",))
        
        if not ongoing_cat_id_row or not missed_cat_id_row:
            print("Error: Could not find required categories.")
            return False
            
        ongoing_category_id = ongoing_cat_id_row[0]
        missed_category_id = missed_cat_id_row[0]
        
        philippines_timezone = pytz.timezone('Asia/Manila')
        current_local_date = datetime.now(philippines_timezone).strftime('%Y-%m-%d')
        
        # Update all past due tasks from On-going to Missed
        query = """
            UPDATE tasks 
            SET category_id = ?
            WHERE category_id = ? 
            AND due_date < ?
            AND due_date IS NOT NULL
        """
        
        return self._execute_query(query, (missed_category_id, ongoing_category_id, current_local_date))

    # --- Recurring Tasks Management ---
    def get_recurring_tasks(self, user_id):
        """Get all recurring tasks for a user and calculate their current status."""
        query = """
            SELECT rtask_id, rtask_title, description, start_date, recurrence_pattern, last_completed_date, status
            FROM recurring_tasks
            WHERE user_id = ?
            ORDER BY start_date
        """
        tasks = self._fetch_all(query, (user_id,))
        
        # Update the status of each task based on its recurrence pattern and last completed date
        updated_tasks = []
        for task in tasks:
            rtask_id, rtask_title, description, start_date, recurrence_pattern, last_completed_date, current_status = task
            
            # Calculate the correct status
            correct_status = self._calculate_recurring_task_status(recurrence_pattern, last_completed_date)
            
            # Update the database if the status has changed
            if correct_status != current_status:
                self._execute_query(
                    "UPDATE recurring_tasks SET status = ? WHERE rtask_id = ?", 
                    (correct_status, rtask_id)
                )
            
            # Include the updated status in the result
            updated_task = (rtask_id, rtask_title, description, start_date, recurrence_pattern, last_completed_date, correct_status)
            updated_tasks.append(updated_task)
            
        return updated_tasks

    def add_recurring_task(self, user_id, rtask_title, description, start_date, recurrence_pattern):
        """Add a new recurring task."""
        query = """
            INSERT INTO recurring_tasks (user_id, rtask_title, description, start_date, recurrence_pattern)
            VALUES (?, ?, ?, ?, ?)
        """
        if self._execute_query(query, (user_id, rtask_title, description, start_date, recurrence_pattern)):
            result = self._fetch_one("SELECT last_insert_rowid()")
            return result[0] if result else None
        return None
        
    def update_recurring_task_completion(self, rtask_id, completed_date):
        """Update the last completion date of a recurring task and set status to 'Completed'."""
        query = """
            UPDATE recurring_tasks
            SET last_completed_date = ?, status = 'Completed'
            WHERE rtask_id = ?
        """
        return self._execute_query(query, (completed_date, rtask_id))

    def remove_recurring_task_completion(self, rtask_id, completed_date):
        """Remove completion date for a recurring task and set status to 'Pending'."""
        query = """
            UPDATE recurring_tasks
            SET last_completed_date = NULL, status = 'Pending'
            WHERE rtask_id = ? AND last_completed_date = ?
        """
        return self._execute_query(query, (rtask_id, completed_date))

    def get_habit_completion_dates(self, rtask_id):
        """Get all completion dates for a recurring task."""
        query = """
            SELECT DISTINCT last_completed_date 
            FROM recurring_tasks 
            WHERE rtask_id = ? AND last_completed_date IS NOT NULL
            ORDER BY last_completed_date DESC
        """
        results = self._fetch_all(query, (rtask_id,))
        return [result[0] for result in results] if results else []

    def update_recurring_task(self, rtask_id, rtask_title, description, start_date, recurrence_pattern):
        """Update an existing recurring task."""
        query = """
            UPDATE recurring_tasks
            SET rtask_title = ?,
                description = ?,
                start_date = ?,
                recurrence_pattern = ?
            WHERE rtask_id = ?
        """
        return self._execute_query(query, (rtask_title, description, start_date, recurrence_pattern, rtask_id))

    def delete_recurring_task(self, rtask_id):
        """Delete a recurring task."""
        query = "DELETE FROM recurring_tasks WHERE rtask_id = ?"
        return self._execute_query(query, (rtask_id,))

    def search_tasks(self, user_id, search_term):
        """Search for tasks by title or description."""
        query = """
            SELECT t.task_id, t.task_title, t.description, p.priority_name, t.due_date, tc.category_name 
            FROM tasks t 
            JOIN task_category tc ON t.category_id = tc.category_id 
            LEFT JOIN priority p ON t.priority_id = p.priority_id
            WHERE t.user_id = ? 
            AND (LOWER(t.task_title) LIKE LOWER(?) OR LOWER(t.description) LIKE LOWER(?))
            ORDER BY t.due_date ASC, t.task_title ASC
        """
        search_pattern = f"%{search_term}%"
        return self._fetch_all(query, (user_id, search_pattern, search_pattern))

    def update_database_schema(self):
        """Update database schema to add missing columns."""
        # Check if updated_at column exists in tasks table
        table_info = self._fetch_all("PRAGMA table_info(tasks)")
        column_names = [column[1] for column in table_info]
        
        if 'updated_at' not in column_names:
            print("Adding updated_at column to tasks table...")
            # Add updated_at column
            alter_query = """
                ALTER TABLE tasks 
                ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            """
            if self._execute_query(alter_query):
                print("Successfully added updated_at column to tasks table.")
            else:
                print("Failed to add updated_at column to tasks table.")
        else:
            print("updated_at column already exists in tasks table.")
        
        if 'created_at' not in column_names:
            print("Adding created_at column to tasks table...")
            # Add created_at column
            alter_query = """
                ALTER TABLE tasks 
                ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            """
            if self._execute_query(alter_query):
                print("Successfully added created_at column to tasks table.")
            else:
                print("Failed to add created_at column to tasks table.")
        else:
            print("created_at column already exists in tasks table.")

    def is_recurring_task(self, task_id):
        """Check if a task is marked as recurring by checking if it exists in the recurring_tasks table."""
        query = """
            SELECT COUNT(*) FROM recurring_tasks WHERE rtask_id = ?
        """
        result = self._fetch_one(query, (task_id,))
        return result[0] > 0 if result else False

    def _calculate_recurring_task_status(self, recurrence_pattern, last_completed_date):
        """
        Calculate the current status of a recurring task based on its recurrence pattern and last completion date.
        
        Args:
            recurrence_pattern: The pattern of recurrence (daily, weekly, monthly, annual)
            last_completed_date: The last date the task was completed
            
        Returns:
            'Completed' if the task is completed within the current period, 'Pending' otherwise
        """
        if not last_completed_date:
            return 'Pending'
            
        # Convert string date to datetime.date object
        try:
            last_completed = datetime.strptime(last_completed_date, '%Y-%m-%d').date()
        except ValueError:
            print(f"Invalid last_completed_date format: {last_completed_date}. Expected format: YYYY-MM-DD")
            return 'Pending'
        
        # Get current date in PH timezone
        current_date = self._get_current_local_date()
        
        # Check status based on recurrence pattern
        recurrence_pattern = recurrence_pattern.lower()
        
        if recurrence_pattern == 'daily':
            # For daily tasks, check if completed today
            return 'Completed' if last_completed == current_date else 'Pending'
            
        elif recurrence_pattern == 'weekly':
            # For weekly tasks, check if completed this week (starting Sunday)
            # Calculate the start of the current week (Sunday)
            days_since_sunday = current_date.weekday() + 1  # +1 because weekday() returns 0 for Monday, we want 0 for Sunday
            if days_since_sunday == 7:  # If it's Sunday, days_since_sunday should be 0
                days_since_sunday = 0
            start_of_week = current_date - timedelta(days=days_since_sunday)
            
            # Check if last completion date is within the current week
            return 'Completed' if last_completed >= start_of_week else 'Pending'
            
        elif recurrence_pattern == 'monthly':
            # For monthly tasks, check if completed this month
            return 'Completed' if (last_completed.year == current_date.year and 
                                  last_completed.month == current_date.month) else 'Pending'
            
        elif recurrence_pattern in ['annual', 'yearly']:
            # For annual tasks, check if completed this year
            return 'Completed' if last_completed.year == current_date.year else 'Pending'
            
        else:
            # For any other pattern, default to checking if completed today
            return 'Completed' if last_completed == current_date else 'Pending'

# For testing the DatabaseManager separately
if __name__ == '__main__':
    db_manager = DatabaseManager()
    print("Database initialized successfully.")
    db_manager._close()