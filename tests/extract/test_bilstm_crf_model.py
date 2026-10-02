import itertools

import torch

from finsight.extract.bilstm_crf_model import (
    CRF,
    BiLSTMCRF,
    Vocab,
    norm_word,
    pad_batch,
    spans_from_tags,
)


def brute_scores(crf: CRF, em: torch.Tensor) -> dict[tuple[int, ...], float]:
    t, n = em.shape
    out = {}
    for path in itertools.product(range(n), repeat=t):
        s = crf.start[path[0]] + em[0, path[0]] + crf.end[path[-1]]
        for i in range(1, t):
            s = s + crf.trans[path[i - 1], path[i]] + em[i, path[i]]
        out[path] = float(s)
    return out


def test_crf_loss_and_viterbi_match_brute_force() -> None:
    torch.manual_seed(0)
    crf = CRF(3)
    em = torch.randn(1, 4, 3)
    scores = brute_scores(crf, em[0])
    log_z = torch.logsumexp(torch.tensor(list(scores.values())), 0)
    gold = (0, 2, 1, 1)
    loss = crf.nll(em, torch.tensor([gold]), torch.ones(1, 4, dtype=torch.bool))
    assert abs(float(loss) - (float(log_z) - scores[gold])) < 1e-4
    best = max(scores, key=lambda p: scores[p])
    assert crf.decode(em, torch.ones(1, 4, dtype=torch.bool))[0] == list(best)


def test_padding_does_not_change_a_sequence() -> None:
    torch.manual_seed(1)
    crf = CRF(3)
    short = torch.randn(1, 3, 3)
    padded = torch.cat([short, torch.randn(1, 2, 3)], dim=1)
    mask = torch.tensor([[True, True, True, False, False]])
    gold = torch.tensor([[0, 1, 2, 0, 0]])
    a = crf.nll(short, gold[:, :3], torch.ones(1, 3, dtype=torch.bool))
    b = crf.nll(padded, gold, mask)
    assert abs(float(a) - float(b)) < 1e-5
    assert crf.decode(padded, mask)[0] == crf.decode(short, torch.ones(1, 3, dtype=torch.bool))[0]


def test_model_overfits_a_tiny_set() -> None:
    torch.manual_seed(0)
    seqs = [
        {"tokens": ["face", "value", "₹", "10", "each"], "tags": ["O", "O", "B-fv", "I-fv", "O"]},
        {"tokens": ["face", "value", "₹", "5", "each"], "tags": ["O", "O", "B-fv", "I-fv", "O"]},
        {"tokens": ["the", "registrar", "is", "Kfin"], "tags": ["O", "O", "O", "B-reg"]},
    ]
    vocab = Vocab.build(seqs, min_freq=1)
    model = BiLSTMCRF(len(vocab.words), len(vocab.chars), len(vocab.tags), hidden=16)
    words, chars, mask = pad_batch(vocab, [s["tokens"] for s in seqs])
    tags = torch.zeros_like(words)
    for i, s in enumerate(seqs):
        tags[i, : len(s["tags"])] = torch.tensor([vocab.t2i[t] for t in s["tags"]])
    opt = torch.optim.Adam(model.parameters(), lr=0.02)
    for _ in range(150):
        opt.zero_grad()
        model.loss(words, chars, mask, tags).backward()
        opt.step()
    model.eval()
    pred = model.predict(words, chars, mask)
    got = [[vocab.tags[i] for i in p] for p in pred]
    assert got == [s["tags"] for s in seqs]


def test_digits_share_a_vector_and_spans() -> None:
    assert norm_word("19,000.50") == norm_word("31,111.99")
    assert spans_from_tags(["O", "B-a", "I-a", "O", "I-b", "B-a"]) == [
        ("a", 1, 2), ("b", 4, 4), ("a", 5, 5),
    ]  # fmt: skip
