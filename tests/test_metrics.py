import pytest

from rag_hackathon.evaluation import precision_recall_at_k, summarize


@pytest.mark.parametrize('retrieved,relevant,k,p,r', [
    (['a','b','c'], ['a','c'], 3, 2/3, 1),
    (['a','a','b'], ['a','b','c'], 3, 2/3, 2/3),
    (['a'], ['a','b'], 3, 1/3, 1/2),
    ([], ['a'], 3, 0, 0),
    (['a'], [], 1, None, None),
    (['b','a'], ['a'], 1, 0, 0),
])
def test_metrics_hand_calculated(retrieved, relevant, k, p, r):
    assert precision_recall_at_k(retrieved, relevant, k) == {'precision':p,'recall':r}


def test_invalid_k():
    with pytest.raises(ValueError):
        precision_recall_at_k([], [], 0)


def test_summary_errors_and_na_are_explicit():
    rows = [{'precision@1':1,'recall@1':0.5,'latency_ms':2,'error':None},
            {'precision@1':None,'recall@1':None,'latency_ms':4,'error':None},
            {'precision@1':None,'recall@1':None,'latency_ms':None,'error':'timeout'}]
    result = summarize(rows, 1)
    assert result['questions_total'] == 3 and result['questions_scored'] == 1
    assert result['errors'] == 1 and result['latency_n'] == 2
    assert result['precision@1'] == 1 and result['latency_ms_p50'] == 3
