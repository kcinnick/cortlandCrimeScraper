from sqlalchemy import Column, String

from database import Base


class AlreadyScrapedPdfs(Base):
    __tablename__ = 'already_scraped_pdfs'
    __table_args__ = {'schema': 'public'}

    pdf_date = Column(String, primary_key=True)