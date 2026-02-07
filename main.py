from fastapi import FastAPI, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import SQLModel, Field, Session, create_engine, select


# ---------- Database setup ----------

sqlite_url = "sqlite:///./survey.db"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)


class SurveyResponse(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str
    rating: int
    feedback_text: str


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


# ---------- FastAPI app ----------

app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
      <head><title>Survey App</title></head>
      <body>
        <h1>Survey App</h1>
        <p><a href="/survey">Fill out the survey</a></p>
        <p><a href="/responses">View responses</a></p>
      </body>
    </html>
    """


@app.post("/survey", response_class=HTMLResponse)
def submit_survey(
    name: str = Form(...),
    email: str = Form(...),
    rating: int = Form(...),
    feedback_text: str = Form(...),
    session: Session = Depends(get_session),
):
    errors = []

    # Basic string checks
    if len(name.strip()) < 2:
        errors.append("Name must be at least 2 characters long.")
    if "@" not in email or "." not in email:
        errors.append("Please enter a valid email address.")

    # Numeric validation for rating
    if rating < 1 or rating > 5:
        errors.append("Rating must be between 1 and 5.")
    if len(feedback_text.strip()) < 5:
        errors.append("Feedback must be at least 5 characters long.")

    if errors:
        # Show the same form again with error messages on top
        error_list = "".join(f"<li>{e}</li>" for e in errors)
        return HTMLResponse(
            content=f"""
            <html>
              <head><title>Survey Error</title></head>
              <body>
                <h1>There were problems with your submission</h1>
                <ul>{error_list}</ul>
                <p><a href="/survey">Go back to the survey</a></p>
              </body>
            </html>
            """,
            status_code=400,
        )

    # If everything is OK, save to DB
    response = SurveyResponse(
        name=name.strip(),
        email=email.strip(),
        rating=rating,
        feedback_text=feedback_text.strip(),
    )
    session.add(response)
    session.commit()
    session.refresh(response)

    return RedirectResponse(url="/thank-you", status_code=303)


@app.post("/survey")
def submit_survey(
    name: str = Form(...),
    email: str = Form(...),
    rating: int = Form(...),
    feedback_text: str = Form(...),
    session: Session = Depends(get_session),
):
    response = SurveyResponse(
        name=name,
        email=email,
        rating=rating,
        feedback_text=feedback_text,
    )
    session.add(response)
    session.commit()
    session.refresh(response)

    return RedirectResponse(url="/thank-you", status_code=303)


@app.get("/thank-you", response_class=HTMLResponse)
def thank_you():
    return """
    <html>
      <head><title>Thank You</title></head>
      <body>
        <h1>Thank you for your feedback!</h1>
        <p><a href="/responses">View all responses</a></p>
        <p><a href="/survey">Submit another response</a></p>
      </body>
    </html>
    """


@app.get("/responses", response_class=HTMLResponse)
def list_responses(session: Session = Depends(get_session)):
    statement = select(SurveyResponse)
    results = session.exec(statement).all()

    rows_html = ""
    for r in results:
        rows_html += f"""
        <tr>
          <td>{r.id}</td>
          <td>{r.name}</td>
          <td>{r.email}</td>
          <td>{r.rating}</td>
          <td>{r.feedback_text}</td>
        </tr>
        """

    return f"""
    <html>
      <head><title>Responses</title></head>
      <body>
        <h1>Survey Responses</h1>
        <table border="1" cellpadding="5" cellspacing="0">
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Email</th>
            <th>Rating</th>
            <th>Feedback</th>
          </tr>
          {rows_html}
        </table>
        <p><a href="/survey">Back to survey</a></p>
      </body>
    </html>
    """