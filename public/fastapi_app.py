# public/fastapi_app.py
from fastapi import FastAPI, HTTPException
import sys
import os

app = FastAPI()

@app.get("/corpus_analysis")
@app.route('/corpus_analysis/')
async def run_corpus_analysis():
    try:
        script_dir = os.path.join(os.path.dirname(__file__), 'corpus_analysis')
        sys.path.append(script_dir)
        
        import test
        
        if hasattr(test, 'main'):
            result = test.main()
        else:
            result = "Script executed successfully"
            
        return {"result": str(result)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
