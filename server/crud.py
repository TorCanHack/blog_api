from sqlalchemy.orm import Session
from models import User, Comment, BlogPost
from schemas import UserCreate, BlogPostCreate, BlogPostUpdate, CommentCreate, CommentUpdate
from auth import get_password_hash

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int= 100):
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_blog_post(db: Session, post_id: int):
    return db.query(BlogPost).filter(BlogPost.id == post_id).first()

def get_blog_posts(db: Session, skip: int = 0, limit: int = 10):
    return db.query(BlogPost).offset(skip).limit(limit).all()

def create_blog_post(db: Session, post: BlogPostCreate, author_id: int):
    db_post = BlogPost(**dict(), author_id=author_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

def update_blog_post(db: Session, post_id: int, post_update: BlogPostUpdate):
    db_post = db.query(BlogPost).filter(BlogPost.id == post_id)
    if db_post:
        update_data = post_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_post, field, value)
        db.commit()
        db.refresh(db_post)
    return(db_post)


