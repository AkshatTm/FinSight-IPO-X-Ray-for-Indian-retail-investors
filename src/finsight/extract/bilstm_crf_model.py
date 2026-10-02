"""The BiLSTM-CRF tagger (Rung 4, E11): words + characters -> BiLSTM -> CRF over BIO tags.

Plain PyTorch, no other imports, so the very same source runs in the Kaggle notebook (it is
pasted into the notebook when the run is pushed) and on the laptop. Word vectors are learned
from our own text (no pretrained embeddings, no internet); a character CNN reads the shape of
numbers and rare words, which is what an IPO cover page is made of.
"""

from __future__ import annotations

import re
from collections import Counter

import torch
from torch import nn

PAD, UNK = 0, 1
_DIGITS = re.compile(r"\d")


def norm_word(word: str) -> str:
    """Lower-case with every digit turned into 0, so two amounts share one vector."""
    return _DIGITS.sub("0", word.lower())


class Vocab:
    def __init__(self, words: list[str], chars: list[str], tags: list[str]) -> None:
        self.words, self.chars, self.tags = words, chars, tags
        self.w2i = {w: i for i, w in enumerate(words)}
        self.c2i = {c: i for i, c in enumerate(chars)}
        self.t2i = {t: i for i, t in enumerate(tags)}

    @classmethod
    def build(cls, sequences: list[dict], min_freq: int = 2) -> Vocab:
        wc: Counter[str] = Counter()
        cc: Counter[str] = Counter()
        tags: set[str] = {"O"}
        for s in sequences:
            wc.update(norm_word(t) for t in s["tokens"])
            for t in s["tokens"]:
                cc.update(t)
            tags.update(s["tags"])
        words = ["<pad>", "<unk>", *[w for w, n in wc.most_common() if n >= min_freq]]
        chars = ["<pad>", "<unk>", *sorted(c for c, n in cc.items() if n >= 3)]
        return cls(words, chars, ["O", *sorted(t for t in tags if t != "O")])

    def to_json(self) -> dict:
        return {"words": self.words, "chars": self.chars, "tags": self.tags}

    @classmethod
    def from_json(cls, data: dict) -> Vocab:
        return cls(data["words"], data["chars"], data["tags"])

    def encode(self, tokens: list[str], max_chars: int = 20) -> tuple[list[int], list[list[int]]]:
        w = [self.w2i.get(norm_word(t), UNK) for t in tokens]
        c = [[self.c2i.get(ch, UNK) for ch in t[:max_chars]] for t in tokens]
        return w, c


def pad_batch(
    vocab: Vocab, batch: list[list[str]], max_chars: int = 20
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """``words (B, T)``, ``chars (B, T, C)``, ``mask (B, T)`` for lists of tokens."""
    longest = max(1, max(len(b) for b in batch))
    words = torch.zeros(len(batch), longest, dtype=torch.long)
    chars = torch.zeros(len(batch), longest, max_chars, dtype=torch.long)
    mask = torch.zeros(len(batch), longest, dtype=torch.bool)
    for i, tokens in enumerate(batch):
        w, c = vocab.encode(tokens, max_chars)
        if not w:
            continue
        words[i, : len(w)] = torch.tensor(w, dtype=torch.long)
        mask[i, : len(w)] = True
        for j, ch in enumerate(c):
            if ch:
                chars[i, j, : len(ch)] = torch.tensor(ch, dtype=torch.long)
    return words, chars, mask


class CRF(nn.Module):
    """Linear-chain CRF: the forward algorithm for the loss, Viterbi for decoding."""

    def __init__(self, n_tags: int) -> None:
        super().__init__()
        self.start = nn.Parameter(torch.zeros(n_tags))
        self.end = nn.Parameter(torch.zeros(n_tags))
        self.trans = nn.Parameter(torch.empty(n_tags, n_tags))  # [from, to]
        nn.init.uniform_(self.trans, -0.1, 0.1)

    def nll(self, emissions: torch.Tensor, tags: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Mean negative log-likelihood of the gold tag paths. Masks are right-padded."""
        b, t, _ = emissions.shape
        rows = torch.arange(b, device=emissions.device)
        score = self.start[tags[:, 0]] + emissions[rows, 0, tags[:, 0]]
        alpha = self.start + emissions[:, 0]
        for i in range(1, t):
            m = mask[:, i]
            step = self.trans[tags[:, i - 1], tags[:, i]] + emissions[rows, i, tags[:, i]]
            score = score + step * m
            nxt = torch.logsumexp(alpha.unsqueeze(2) + self.trans.unsqueeze(0), dim=1)
            alpha = torch.where(m.unsqueeze(1), nxt + emissions[:, i], alpha)
        last = tags[rows, mask.long().sum(1) - 1]
        score = score + self.end[last]
        log_z = torch.logsumexp(alpha + self.end, dim=1)
        return (log_z - score).mean()

    @torch.no_grad()
    def decode(self, emissions: torch.Tensor, mask: torch.Tensor) -> list[list[int]]:
        b, t, n = emissions.shape
        score = self.start + emissions[:, 0]
        back: list[torch.Tensor] = []
        keep = torch.arange(n, device=emissions.device).expand(b, n)
        for i in range(1, t):
            best, idx = (score.unsqueeze(2) + self.trans.unsqueeze(0)).max(dim=1)
            m = mask[:, i].unsqueeze(1)
            score = torch.where(m, best + emissions[:, i], score)
            back.append(torch.where(m, idx, keep))  # a padded step leaves the path unchanged
        score = score + self.end
        out = []
        for k, length in enumerate(mask.long().sum(1).tolist()):
            tag = int(score[k].argmax())
            path = [tag]
            for i in range(length - 2, -1, -1):
                tag = int(back[i][k, tag])
                path.append(tag)
            out.append(path[::-1])
        return out


class BiLSTMCRF(nn.Module):
    def __init__(
        self,
        n_words: int,
        n_chars: int,
        n_tags: int,
        word_dim: int = 100,
        char_dim: int = 30,
        char_filters: int = 50,
        hidden: int = 128,
        dropout: float = 0.4,
    ) -> None:
        super().__init__()
        self.word_emb = nn.Embedding(n_words, word_dim, padding_idx=PAD)
        self.char_emb = nn.Embedding(n_chars, char_dim, padding_idx=PAD)
        self.char_cnn = nn.Conv1d(char_dim, char_filters, kernel_size=3, padding=1)
        self.drop = nn.Dropout(dropout)
        self.lstm = nn.LSTM(word_dim + char_filters, hidden, batch_first=True, bidirectional=True)
        self.out = nn.Linear(2 * hidden, n_tags)
        self.crf = CRF(n_tags)

    def emissions(
        self, words: torch.Tensor, chars: torch.Tensor, mask: torch.Tensor
    ) -> torch.Tensor:
        b, t, c = chars.shape
        ch = self.char_emb(chars.view(b * t, c)).transpose(1, 2)
        ch = torch.relu(self.char_cnn(ch)).max(dim=2).values.view(b, t, -1)
        x = self.drop(torch.cat([self.word_emb(words), ch], dim=-1))
        lengths = mask.long().sum(1).clamp(min=1).cpu()
        packed = nn.utils.rnn.pack_padded_sequence(
            x, lengths, batch_first=True, enforce_sorted=False
        )
        h, _ = self.lstm(packed)
        h, _ = nn.utils.rnn.pad_packed_sequence(h, batch_first=True, total_length=t)
        return self.out(self.drop(h))

    def loss(self, words, chars, mask, tags):  # type: ignore[no-untyped-def]
        return self.crf.nll(self.emissions(words, chars, mask), tags, mask)

    @torch.no_grad()
    def predict(self, words, chars, mask):  # type: ignore[no-untyped-def]
        return self.crf.decode(self.emissions(words, chars, mask), mask)


def spans_from_tags(tags: list[str]) -> list[tuple[str, int, int]]:
    """``(field, first_token, last_token)`` for every B-/I- run; a stray I- starts a span."""
    spans: list[tuple[str, int, int]] = []
    for i, tag in enumerate(tags):
        if tag == "O":
            continue
        field = tag[2:]
        if tag.startswith("I-") and spans and spans[-1][0] == field and spans[-1][2] == i - 1:
            spans[-1] = (field, spans[-1][1], i)
        else:
            spans.append((field, i, i))
    return spans
