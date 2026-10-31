import asyncio
import xml.etree.ElementTree as ET
import httpx

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


async def search_pubmed(query: str, limit: int = 5):
    """Prefer NCBI; Europe PMC supplies PubMed-indexed abstracts if unavailable."""
    try:
        return await _search_ncbi(query, limit)
    except (httpx.HTTPError, ValueError, KeyError, ET.ParseError):
        async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
            response = await client.get('https://www.ebi.ac.uk/europepmc/webservices/rest/search', params={
                'query': f'({query}) AND SRC:MED', 'format': 'json',
                'resultType': 'core', 'pageSize': max(1, min(limit, 10))})
            response.raise_for_status()
            data = response.json()
        papers = []
        for item in data.get('resultList', {}).get('result', []):
            pmid = item.get('pmid')
            if not pmid:
                continue
            papers.append({'pmid': pmid, 'title': item.get('title', ''),
                'journal': item.get('journalInfo', {}).get('journal', {}).get('title', ''),
                'year': item.get('pubYear', ''),
                'publication_types': item.get('pubTypeList', {}).get('pubType', []),
                'abstract': item.get('abstractText', '')[:10000],
                'url': f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/',
                'evidence_scope': '摘要，非全文', 'source': 'Europe PMC (PubMed indexed)'})
        return {'query': query, 'total': int(data.get('hitCount', 0)), 'papers': papers,
            'source': 'Europe PMC (PubMed indexed)', 'fallback_reason': 'NCBI接口暂不可用'}


async def _search_ncbi(query: str, limit: int = 5):
    limit = max(1, min(limit, 10))
    async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
        response = await client.get(BASE + "esearch.fcgi", params={"db": "pubmed", "term": query, "retmode": "json", "retmax": limit, "sort": "relevance", "tool": "BioLens"})
        response.raise_for_status()
        data = response.json()["esearchresult"]
        ids = data["idlist"]
        if not ids:
            return {"query": query, "total": int(data.get("count", 0)), "papers": []}
        await asyncio.sleep(.4)
        response = await client.get(BASE + "efetch.fcgi", params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml", "tool": "BioLens"})
        response.raise_for_status()
        root = ET.fromstring(response.text)
        papers = []
        for article in root.findall(".//PubmedArticle"):
            def content(xpath):
                el = article.find(xpath)
                return "".join(el.itertext()) if el is not None else ""
            pmid = content(".//PMID")
            abstract = "\n".join((el.get("Label", "") + ": " if el.get("Label") else "") + "".join(el.itertext()) for el in article.findall(".//AbstractText"))
            publication_types = ["".join(el.itertext()) for el in article.findall(".//PublicationType")]
            papers.append({"pmid": pmid, "title": content(".//ArticleTitle"), "journal": content(".//Journal/Title"), "year": content(".//PubDate/Year") or content(".//PubDate/MedlineDate"), "publication_types": publication_types, "abstract": abstract[:10000], "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", "evidence_scope": "摘要，非全文"})
        return {"query": query, "total": int(data.get("count", 0)), "papers": papers}
