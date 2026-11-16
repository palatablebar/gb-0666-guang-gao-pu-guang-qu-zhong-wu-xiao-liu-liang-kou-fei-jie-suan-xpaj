from fastapi import APIRouter,Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.config import MODULES,TITLE,RULE_VERSION
from app.modules.m7_batches.service import run
from app.store import fetch
router=APIRouter();templates=Jinja2Templates(directory="app/templates")
@router.get("/")
def home():return RedirectResponse("/model")
def page(request,slug,run_id):
    data=fetch(run_id) if run_id else run({"sample":"dirty"})
    return templates.TemplateResponse(request=request,name=slug+".html",context={"data":data,"title":TITLE,"modules":MODULES,"slug":slug,"page_title":dict(MODULES)[slug],"version":RULE_VERSION})
for slug,label in MODULES:
    def view(request:Request,run_id:str|None=None,_slug=slug):return page(request,_slug,run_id)
    router.add_api_route("/"+slug,view,methods=["GET"],include_in_schema=False)
