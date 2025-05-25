from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
import uvicorn 
import os
from dotenv import load_dotenv

from database import get_db, engine, Base
from models import User, BlogPost, Comment
from schemas import *
from auth import get_current_user, get_current_active_user, create_access_token, verify_password, get_password_hash
from crud import *

load_dotenv()

Base.metadata.create.all(bind=engine)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Blog", description="Blog with jwt authentication", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    alow_headers=["*"]
)

security = HTTPBearer()

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minutes")
async def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):

    if get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    if get_user_by_username(db, user.usename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST
            detail="Username already taken"
        )
    
    db_user = create_user(db, user)
    return db_user

@app.post("/auth/login", response_model=Token)
@limiter.limit("10/minutes")
async def login(request: Request, user_credentails: UserLogin, db: Session = Depends(get_db));
    user = authenticate_user(db, user_credentails.email, user_credentails.password)
    if not user: 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"acccess_token": access_token, "token_type": "bearer"}

@app.get("/posts", response_model=List[BlogPostResponse])
@limiter.limit("30/minutes")
async def get_posts( request: Request, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    posts = get_blog_posts(db, skip=skip, limit=limit)
    return posts

@app.get("/posts/{post_id}", response_model=BlogPostResponse)
@limiter.limit("30/minutes")
async def get_post(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = get_blog_post(db, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
            detail="Blog post not found"
        )
    return post
    
@app.post("/posts", response_model=BlogPostResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minutes")
async def create_post(request: Request, post: BlogPostCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    db_post = create_blog_post(db, post, current_user.id)
    return db_post

@app.put("/posts/{post_id}", response_model=BlogPostResponse)
@limiter.limit("10/minutes")
async def update_post(request: Request, post_id: int, pots_update: BlogPostUpdate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    db_post = get_blog_post(db, post_id)
    if not db_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )
    
    if db_post.id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN
            detail="Not enough permissions"
        )

    updated_post = update_blog_post(db, post_id, post_update)
    return updated_post

@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_post(request: Request, post_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    db_post = get_blog_post(db, post_id)
    if not db_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )
    
    if db_post.id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN
            detail="Not enough permissions"
        )
    
    delete_blog_post(db, post_id)

@app.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
@limiter.limit("30/minutes")
async def get_post_comments(
    request: Request, 
    post_id: int,
    skip: int = 0,
    limit: int = 0,
    db: Session = Depends(get_db)
):
    comments = get_comments_by_post(db, post_id, skip=skip, limit=limit)
    return comments

@app.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("15/minutes")
async def create_comment(request: Request, post_id: int, comment: CommentCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    post = get_blog_post(db, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )
    
    db_comment = create_comment(db, comment, post_id, current_user.id)
    return db_comment

@app.put("/comments/{comments_id}", response_model=CommentResponse)
@limiter.limit("10/minute")
async def update_comment(
    request: Request,
    comment_id: int,
    comment_update: CommentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_comment = get_comment(db, comment_id)
    if not db_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    if db_comment.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    updated_comment = update_comment(db, comment_id, comment_update)
    return updated_comment

@app.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minutes")
async def delete_comment(
    request: Request,
    comment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_comment = get_comment(db, comment_id)
    if not db_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    if db_comment.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permission"
        )
    
    delete_comment(db, comment_id)

@app.get("/admin/user", response_model=List[UserResponse])
async def get_all_users( current_user: User = Depends(get_current_active_user), dp: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin Access Required"
        )
    
    users = get_user(db)
    return users

@app.put("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_update: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin Access Required"
        )
    
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.role = role_update.get("role", user.role)
    db.commit()
    db.refresh(user)

    return {"message": f"User role updated to {user.role}"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
