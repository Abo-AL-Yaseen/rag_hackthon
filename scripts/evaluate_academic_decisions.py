"""Offline real-index Backend evaluation; no question fixtures or remote providers.

Close the single owning Backend process first. Evidence and answers are saved
only to the explicitly supplied local report directory.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
CASES=[
 ('attendance_min','ما الحد الأدنى لنسبة الحضور في المادة؟',None,None,'answered','supported',['policy_absence_limit']),
 ('attendance_dialect','شو بصير إذا غبت أكثر من المسموح؟',None,None,'answered','supported',['policy_absence_penalty']),
 ('attendance_condition','إذا غبت أكثر من 12.5% بدون عذر مقبول، بقدر أقدم النهائي؟',None,None,'answered','supported',['policy_absence_penalty']),
 ('withdrawal','لحد إمتى بقدر أسحب مادة؟ وهل بحتفظ بالحق المالي؟',None,None,'answered','supported',['policy_late_withdrawal','policy_financial_withdrawal']),
 ('add_drop','متى يسمح بإضافة المساقات والانسحاب منها ببداية الفصل؟',None,None,'answered','supported',['policy_add_drop']),
 ('missing_scope','كم ساعة مساق 10871112؟',None,None,'insufficient_evidence','ambiguous',[]),
 ('civil_credits','كم ساعة مساق 10871112؟','civil-engineering','2021-1','answered','supported',['eng_civil-engineering_2021-1_10871112_ar']),
 ('geomatics_credits','كم ساعة مساق 10871112؟','geomatics-engineering','2025-1','answered','supported',['eng_geomatics-engineering_2025-1_10871112_ar']),
 ('graduation','كم مجموع ساعات التخرج؟','computer-engineering','2021-1','answered','supported',['eng_computer-engineering_2021-1_summary_ar']),
 ('prerequisite','شو المتطلب السابق لتركيب بيانات وخوارزميات 10636211؟','computer-engineering','2021-1','answered','supported',['eng_computer-engineering_2021-1_10636211_ar']),
 ('uncertain','شو المتطلبات السابقة لمساق 10641373؟','computer-engineering','2021-1','insufficient_evidence','ambiguous',[]),
 ('missing_course','كم ساعة مساق 99999999؟','civil-engineering','2021-1','insufficient_evidence','missing_evidence',[]),
 ('personal_load','أنا سنة ثالثة ومعدلي 2.1، كم ساعة بقدر أسجل؟',None,None,'insufficient_evidence','ambiguous',[]),
 ('schedule','متى امتحان الخوارزميات الأسبوع القادم؟',None,None,'insufficient_evidence','missing_evidence',[]),
 ('poem','اكتب لي قصيدة عن الجامعة',None,None,'insufficient_evidence','out_of_scope',[]),
 ('english','How many credits is course 11221102?','architectural-engineering','2025-1','answered','supported',['eng_architectural-engineering_2025-1_11221102_en']),
 ('attendance_selected','شو بصير إذا غبت أكثر من المسموح؟','computer-engineering','2021-1','answered','supported',['policy_absence_penalty']),
 ('paraphrase_ar','لو تغيبت عن المحاضرات زيادة عن الحد، شو العقوبة؟',None,None,'answered','supported',['policy_absence_penalty']),
 ('paraphrase_en','What are the credit hours for course 11221102?','architectural-engineering','2025-1','answered','supported',['eng_architectural-engineering_2025-1_11221102_en']),
 ('arabic_digits','قديش عدد ساعات المساق ١٠٨٧١١١٢؟','civil-engineering','2021-1','answered','supported',['eng_civil-engineering_2021-1_10871112_ar']),
 ('warning_no_scope','إمتى بنزل علي إنذار بسبب معدلي التراكمي؟',None,None,'insufficient_evidence','ambiguous',[]),
 ('warning_engineering','إمتى بنزل علي إنذار بسبب معدلي التراكمي؟','computer-engineering','2021-1','answered','supported',['policy_engineering_warning','policy_first_semester_warning']),
 ('explicit_scope','كم ساعة مساق 10871112 في الهندسة المدنية خطة 2021-1؟',None,None,'answered','supported',['eng_civil-engineering_2021-1_10871112_ar']),
 ('conflicting_scope','في هندسة الحاسوب خطة 2021-1 كم ساعة مساق 10871112؟','civil-engineering','2021-1','insufficient_evidence','ambiguous',[]),
]


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--index',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
 args=parser.parse_args()
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',LLM_PROVIDER='mock',ALLOW_PAID_API_CALLS='false',ALLOW_FREE_API_CALLS='false',BACKEND_LOAD_DOTENV='false')
 original=socket.socket.connect
 def local_only(sock,address):
  if isinstance(address,tuple) and address[0] in ('127.0.0.1','::1'):return original(sock,address)
  raise RuntimeError('External networking prohibited in offline evaluation')
 socket.socket.connect=local_only
 from backend.app import create_app
 from backend.config import BackendSettings
 from fastapi.testclient import TestClient
 settings=BackendSettings(index_path=args.index,catalog_path=ROOT/'backend/catalog/programs.json',mock_rules_path=None,cors_origins=(),load_dotenv_file=None,host='127.0.0.1',port=8000,allow_paid_api_calls=False,allow_free_api_calls=False,llm_provider='mock')
 results=[]
 with TestClient(create_app(settings)) as client:
  state=client.app.state.backend;assert state.rag_ready,state.startup_errors
  retriever=state.runtime.service.retriever;search=retriever.search;captured=[]
  def trace(q,k):
   hits=search(q,k);captured.extend(hits);return hits
  retriever.search=trace
  for ident,q,p,v,status,reason,required in CASES:
   captured.clear()
   body={'question':q,'language':'en' if ident in ('english','paraphrase_en') else 'ar'}
   if p:body.update(program_id=p,plan_version=v)
   response=client.post('/api/chat',json=body);r=response.json()
   sources=r.get('sources',[]);ids={s['document_id'] for s in sources}
   citations=all(any(h.chunk.document_id==s['document_id'] and s['supporting_excerpt'] in h.chunk.text for h in captured) for s in sources)
   effective_p,effective_v=(('civil-engineering','2021-1') if ident=='explicit_scope' else (p,v))
   isolation=all(state.runtime._documents[h.chunk.document_id]['scope']=='regulations' or
     (effective_p is not None and state.runtime._documents[h.chunk.document_id]['program_id']==effective_p and state.runtime._documents[h.chunk.document_id]['plan_version']==effective_v) for h in captured)
   passed=response.status_code==200 and r.get('status')==status and r.get('reason')==reason and set(required)<=ids and citations and isolation
   results.append({'id':ident,'request':body,'clarification_required':reason=='ambiguous' and ident!='uncertain','http_status':response.status_code,'response':r,'expected_documents':required,'citation_relevance':citations and set(required)<=ids,'scope_isolation':isolation,'outcome':'PASS' if passed else 'FAIL','provider':'local_extractive_non_llm; contract mode mock; no scripted fixtures','retrieved':[{'chunk_id':h.chunk.chunk_id,'document_id':h.chunk.document_id,'text':h.chunk.text,'source':state.runtime.source_locator(h.chunk.document_id)} for h in captured]})
 args.output.mkdir(parents=True,exist_ok=True)
 (args.output/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
 lines=['# Actual offline academic decision evaluation','Provider: non-scripted local extractive, NOT a real LLM. No external network permitted.','| Case | Result | Status/reason | Actual answer |','|---|---|---|---|']
 for r in results:lines.append('| '+r['id']+' | '+r['outcome']+' | '+r['response'].get('status','')+'/'+r['response'].get('reason','')+' | '+r['response'].get('answer','').replace('\n','<br>').replace('|',' / ')+' |')
 (args.output/'results.md').write_text('\n'.join(lines),encoding='utf8')
 print(json.dumps({'passed':sum(r['outcome']=='PASS' for r in results),'total':len(results),'failures':[{'id':r['id'],'actual':r['response']} for r in results if r['outcome']=='FAIL']},ensure_ascii=False))


if __name__=='__main__':main()
