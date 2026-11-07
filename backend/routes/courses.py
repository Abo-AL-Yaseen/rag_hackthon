from fastapi import APIRouter, HTTPException, Query, Request

router=APIRouter(prefix='/api/programs',tags=['courses'])

@router.get('/{program_id}/plans/{plan_version}/courses')
def courses(program_id:str,plan_version:str,request:Request,language:str='ar',offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=50),year:int|None=None):
    state=request.app.state.backend
    if not state.rag_ready:raise HTTPException(503,detail='rag_not_ready')
    try:return state.runtime.course_catalog.page(program_id,plan_version,language,offset,limit,year)
    except KeyError:raise HTTPException(404,detail='verified_plan_not_found') from None
    except ValueError as exc:raise HTTPException(422,detail=str(exc)) from None
