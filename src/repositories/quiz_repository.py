from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from ..models.quiz_question import QuizQuestion

class QuizRepository:

    def __init__(self, session: Session):
        self.session = session

    def create_question(self, job_id: int, question_id: str, question: str,
                       question_type: str, answer_config: Dict[str, Any],
                       context: str = None, max_score: int = 1) -> QuizQuestion:
        quiz_question = QuizQuestion(
            job_id=job_id,
            question_id=question_id,
            question=question,
            type=question_type,
            answer_config=answer_config,
            context=context,
            max_score=max_score
        )
        self.session.add(quiz_question)
        self.session.commit()
        self.session.refresh(quiz_question)
        return quiz_question

    def create_questions_batch(self, questions: List[Dict[str, Any]]) -> List[QuizQuestion]:
        quiz_questions = []
        for q_data in questions:
            quiz_question = QuizQuestion(**q_data)
            quiz_questions.append(quiz_question)
            self.session.add(quiz_question)

        self.session.commit()
        for quiz_question in quiz_questions:
            self.session.refresh(quiz_question)
        return quiz_questions

    def get_questions_by_job_id(self, job_id: int) -> List[QuizQuestion]:
        return (
            self.session.query(QuizQuestion)
            .filter(QuizQuestion.job_id == job_id)
            .order_by(QuizQuestion.question_id)
            .all()
        )

    def get_question_by_id(self, job_id: int, question_id: str) -> Optional[QuizQuestion]:
        return (
            self.session.query(QuizQuestion)
            .filter(QuizQuestion.job_id == job_id, QuizQuestion.question_id == question_id)
            .first()
        )

    def get_questions_count_by_job_id(self, job_id: int) -> int:
        return (
            self.session.query(QuizQuestion)
            .filter(QuizQuestion.job_id == job_id)
            .count()
        )

    def get_total_score_by_job_id(self, job_id: int) -> int:
        from sqlalchemy import func
        result = (
            self.session.query(func.sum(QuizQuestion.max_score))
            .filter(QuizQuestion.job_id == job_id)
            .scalar()
        )
        return result or 0

    def delete_questions_by_job_id(self, job_id: int) -> int:
        deleted_count = (
            self.session.query(QuizQuestion)
            .filter(QuizQuestion.job_id == job_id)
            .delete()
        )
        self.session.commit()
        return deleted_count