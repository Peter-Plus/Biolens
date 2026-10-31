import asyncio
from pathlib import Path
import numpy as np
import pytest
from biolens.local import resolve_file, read_file
from biolens.analysis import analyze_expression
from biolens.schemas import TurnIn
from biolens.agent import Runner, TOOLS
from biolens.agent import explicit_search_request, validate_citations
from biolens import store

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "expression-demo"


@pytest.mark.asyncio
async def test_explicit_search_and_negation():
    assert await explicit_search_request("请在PubMed检索结核病血液转录组诊断标志物的研究。")
    assert not await explicit_search_request("请分析这些数据，不需要外部检索。")


def test_unverified_citation_is_flagged():
    text = validate_citations("结论 [PMID: 12345678]", {})
    assert "12345678" not in text and "未核验" in text


def test_local_requires_permission(tmp_path):
    (tmp_path / "data.txt").write_text("hello")
    with pytest.raises(PermissionError):
        read_file(str(tmp_path), "data.txt", False)


def test_read_omitted_suffix_is_unique_and_scoped(tmp_path):
    (tmp_path / "README.md").write_text("demo", encoding="utf-8")
    result = read_file(str(tmp_path), "README", True)
    assert result["source"] == "README.md" and result["text"] == "demo"
    with pytest.raises(PermissionError):
        read_file(str(tmp_path), "README", False)
    with pytest.raises(PermissionError):
        read_file(str(tmp_path), "../README", True)
    (tmp_path / "README.txt").write_text("different", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="多个匹配"):
        read_file(str(tmp_path), "README", True)
    (tmp_path / "key.txt").write_text("secret", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        read_file(str(tmp_path), "key", True)


def test_path_escape_and_secrets(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (tmp_path / "outside.txt").write_text("private")
    (project / "key.txt").write_text("credential")
    with pytest.raises(PermissionError):
        resolve_file(str(project), "../outside.txt", True)
    with pytest.raises(PermissionError):
        resolve_file(str(project), "key.txt", True)


def test_pca_and_correlation_against_numpy(tmp_path):
    import pandas as pd
    result = analyze_expression(str(EXAMPLE), True, tmp_path, "expression.csv", "samples.csv", "group")
    x = pd.read_csv(EXAMPLE / "expression.csv", index_col=0).to_numpy().T
    centered = x - x.mean(axis=0)
    singular = np.linalg.svd(centered, compute_uv=False)
    reference = singular[:2] ** 2 / np.sum(singular ** 2)
    np.testing.assert_allclose(result["pca_explained_variance"], reference, rtol=1e-8)
    corr = pd.read_csv(tmp_path / "sample_correlation.csv", index_col=0).to_numpy()
    np.testing.assert_allclose(corr, np.corrcoef(x), atol=1e-12)
    assert result["samples"] == 12 and result["genes"] == 120
    assert result["transform"] == "none"
    assert sorted(p.name for p in tmp_path.glob('*.html')) == ['analysis.html']
    assert (tmp_path / 'analysis.html').read_text('utf-8').count('class="chart-section"') == 5


def test_mismatch_never_silently_drops_samples(tmp_path):
    with pytest.raises(ValueError, match="不完全一致"):
        analyze_expression(str(EXAMPLE), True, tmp_path, "expression.csv", "samples-mismatch.csv", "group")


@pytest.mark.asyncio
async def test_tools_enforce_current_permissions():
    r = Runner("permission-test", "test", {"name": "test", "path": str(EXAMPLE)}, TurnIn(prompt="test"))
    r.available = []
    with pytest.raises(PermissionError):
        await r.tool("read_file", {"path": "README.md"})
    r.available = TOOLS
    with pytest.raises(PermissionError):
        await r.tool("create_report", {"title": "x", "sections": []})
    with pytest.raises(PermissionError):
        await r.tool("search_pubmed", {"query": "TB"})


@pytest.mark.asyncio
async def test_agent_calls_tools_and_preserves_evidence(monkeypatch):
    from biolens import agent
    store.init()
    chat = store.uid()
    store.message(chat, "user", "阅读README")
    run = store.uid()
    store.execute("INSERT INTO runs VALUES(?,?,?,?,?)", (run, chat, "{}", "running", store.now()))
    responses = iter([
        {"content": None, "tool_calls": [{"id": "call1", "type": "function", "function": {"name": "read_file", "arguments": '{"path":"README.md"}'}}]},
        {"content": "这是合成数据，仅供软件演示。"}])
    async def fake(messages, tools=None, model=None):
        assert model == "selected-model"
        if messages[-1]["role"] == "tool":
            assert "合成" in messages[-1]["content"]
        return next(responses)
    monkeypatch.setattr(agent, "completion", fake)
    r = Runner(run, chat, {"name": "test", "path": str(EXAMPLE)}, TurnIn(prompt="阅读README", local=True, model="selected-model"))
    await r.run()
    events = store.rows("SELECT * FROM events WHERE run_id=?", (run,))
    assert any(e["kind"] == "tool_end" for e in events)
    assert store.rows("SELECT status FROM runs WHERE id=?", (run,))[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_enabled_search_without_request_exposes_no_search_tool(monkeypatch):
    from biolens import agent
    store.init()
    chat, run = store.uid(), store.uid()
    store.message(chat, "user", "解释NMF")
    store.execute("INSERT INTO runs VALUES(?,?,?,?,?)", (run, chat, "{}", "running", store.now()))
    async def classify(prompt, model=None): return False
    async def fake(messages, tools=None):
        assert not any(t["function"]["name"] == "search_pubmed" for t in tools or [])
        return {"content": "NMF是非负矩阵分解。"}
    monkeypatch.setattr(agent, "explicit_search_request", classify)
    monkeypatch.setattr(agent, "completion", fake)
    await Runner(run, chat, {"name": "test", "path": ""}, TurnIn(prompt="解释NMF", external=True)).run()
    assert store.rows("SELECT status FROM runs WHERE id=?", (run,))[0]["status"] == "completed"
