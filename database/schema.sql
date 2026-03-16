USE RamskonDB;
GO

CREATE TABLE users (
    id INT PRIMARY KEY IDENTITY(1,1),
    full_name NVARCHAR(100) NOT NULL,
    email NVARCHAR(120) NOT NULL UNIQUE,
    password_hash NVARCHAR(255) NOT NULL,
    role NVARCHAR(20) NOT NULL DEFAULT 'user',
    is_approved BIT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT GETDATE()
);
GO

CREATE TABLE courses (
    id INT PRIMARY KEY IDENTITY(1,1),
    course_name NVARCHAR(100) NOT NULL UNIQUE,
    description NVARCHAR(255),
    duration_days INT NOT NULL DEFAULT 30
);
GO

CREATE TABLE course_requests (
    id INT PRIMARY KEY IDENTITY(1,1),
    user_id INT NOT NULL,
    course_id INT NOT NULL,
    status NVARCHAR(20) NOT NULL DEFAULT 'pending',
    requested_at DATETIME NOT NULL DEFAULT GETDATE(),
    approved_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (course_id) REFERENCES courses(id)
);
GO

CREATE TABLE course_topics (
    id INT PRIMARY KEY IDENTITY(1,1),
    course_id INT NOT NULL,
    day_number INT NOT NULL,
    topic_title NVARCHAR(200) NOT NULL,
    topic_description NVARCHAR(MAX) NULL,
    FOREIGN KEY (course_id) REFERENCES courses(id)
);
GO

CREATE TABLE user_progress (
    id INT PRIMARY KEY IDENTITY(1,1),
    user_id INT NOT NULL,
    course_id INT NOT NULL,
    topic_id INT NOT NULL,
    day_number INT NOT NULL,
    is_completed BIT NOT NULL DEFAULT 0,
    completed_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    FOREIGN KEY (topic_id) REFERENCES course_topics(id)
);
GO