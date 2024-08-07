from datetime import datetime
from typing import List
from domain.corpus import Corpus, CorpusEntry
from repositories.corpus.corpus_repository import CorpusRepository
from repositories.corpus_entry.corpus_entry_repository import CorpusEntryRepository
from utils.id_generator import IdGenerator


class CorpusManagementService:
    def __init__(
        self, corpus_repo: CorpusRepository, corpus_entry_repo: CorpusEntryRepository
    ):
        self.corpus_repo = corpus_repo
        self.corpus_entry_repo = corpus_entry_repo

    def create_corpus(self, name: str, description: str) -> Corpus:
        """创建一个新的语料库。"""
        corpus = Corpus(
            id=IdGenerator.generate(),
            name=name,
            description=description,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        return self.corpus_repo.save(corpus)

    def list_corpora(self, skip: int = 0, limit: int = 100) -> List[Corpus]:
        return self.corpus_repo.list(skip=skip, limit=limit)

    def count_corpora(self) -> int:
        return self.corpus_repo.count()

    def add_entry_to_corpus(
        self, corpus_id: str, content: str, entry_type: str
    ) -> CorpusEntry:
        """向语料库中添加一个新的条目。"""
        # 首先检查语料库是否存在
        corpus = self.corpus_repo.get_by_id(corpus_id)
        if not corpus:
            raise ValueError(f"Corpus with id {corpus_id} does not exist")
        entry = CorpusEntry(
            id=IdGenerator.generate(),
            corpus=corpus_id,
            content=content,
            entry_type=entry_type,
            created_at=datetime.now(),
            metadata={},
        )
        return self.corpus_entry_repo.save(entry)

    def remove_entry_from_corpus(self, entry_id: str) -> bool:
        """从语料库中删除一个条目。"""
        return self.corpus_entry_repo.delete(entry_id)

    def get_corpus_entries(
        self, corpus: str, skip: int = 0, limit: int = 100
    ) -> List[CorpusEntry]:
        """获取语料库中的条目列表。"""
        return self.corpus_entry_repo.list_by_corpus(corpus, skip, limit)
