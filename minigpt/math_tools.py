"""AST white-list, separate worker process, bounded input. No eval/exec."""
import ast, json, multiprocessing as mp
from queue import Empty
import sympy as s
FUNCS={k:getattr(s,k) for k in ['sin','cos','tan','exp','log','sqrt','Abs']}
SYMS={k:s.Symbol(k) for k in ['x','y','z','t']}; SYMS.update(pi=s.pi,E=s.E,oo=s.oo)
def parse(text):
    if len(text)>500: raise ValueError('輸入上限 500 字元')
    tree=ast.parse(text.replace('^','**'),mode='eval')
    if sum(1 for _ in ast.walk(tree))>120: raise ValueError('算式過於複雜')
    def visit(n):
        if isinstance(n,ast.Constant) and type(n.value) in (int,float):
            if abs(n.value)>1000000: raise ValueError('數值過大')
            return s.Integer(n.value) if type(n.value)==int else s.Rational(ast.get_source_segment(text.replace('^','**'),n))
        if isinstance(n,ast.Name) and n.id in SYMS: return SYMS[n.id]
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)): return visit(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
        if isinstance(n,ast.BinOp):
            a,b=visit(n.left),visit(n.right)
            if isinstance(n.op,ast.Add): return a+b
            if isinstance(n.op,ast.Sub): return a-b
            if isinstance(n.op,ast.Mult): return a*b
            if isinstance(n.op,ast.Div):
                if b==0:raise ValueError('除數不能為零')
                return a/b
            if isinstance(n.op,ast.Pow):
                if b.is_number and (not b.is_finite or abs(b)>100): raise ValueError('次方上限 100')
                return a**b
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in FUNCS and len(n.args)==1 and not n.keywords: return FUNCS[n.func.id](visit(n.args[0]))
        raise ValueError('不允許此語法；只能使用數字、x/y/z/t、四則與白名單函數')
    return visit(tree.body)
def worker(q,text,op,var,point):
    try:
        x=SYMS.get(var.split(',')[0])
        if x is None: raise ValueError('變數只能是 x/y/z/t')
        if op in ('matrix_det','matrix_inverse','statistics'):
            raw=json.loads(text)
            if op=='statistics':
                if not isinstance(raw,list) or not 1<=len(raw)<=100 or any(type(v) not in (int,float) or abs(v)>1000000 for v in raw):raise ValueError('統計輸入為最多 100 個數值的 JSON 陣列')
                vals=[s.Rational(str(v)) for v in raw];mean=sum(vals)/len(vals);result=s.Tuple(mean,sum((v-mean)**2 for v in vals)/len(vals))
            else:
                if not isinstance(raw,list) or not 1<=len(raw)<=5 or any(not isinstance(row,list) or len(row)!=len(raw) for row in raw):raise ValueError('矩陣為至多 5×5 的方陣 JSON')
                if any(type(v) not in (int,float) or abs(v)>1000000 for row in raw for v in row):raise ValueError('矩陣只能含受限數值')
                matrix=s.Matrix(raw);result=matrix.det() if op=='matrix_det' else matrix.inv()
        elif op=='solve':
            parts=text.split(';')
            eq=[parse(p.split('=')[0])-parse(p.split('=')[1]) if '=' in p else parse(p) for p in parts]
            variables=[SYMS[k] for k in var.split(',')]
            solutions=s.solve(eq,variables,dict=True)
            result=s.solve(eq,variables if ',' in var else x)
            verification=[{'solution':{str(k):str(v) for k,v in sol.items()},'residuals':[str(s.simplify(e.subs(sol))) for e in eq],'verified':all(s.simplify(e.subs(sol))==0 for e in eq)} for sol in solutions]
        else:
            expr=parse(text)
            result={'calculate':lambda:s.simplify(expr),'simplify':lambda:s.simplify(expr),'factor':lambda:s.factor(expr),'diff':lambda:s.diff(expr,x),'integrate':lambda:s.integrate(expr,x),'limit':lambda:s.limit(expr,x,parse(point))}[op]()
        payload={'exact':str(result),'latex':s.latex(result),'approx':str(result.evalf(12)) if hasattr(result,'evalf') else ''}
        if op=='solve':payload['verification']=verification
        if hasattr(result,'has') and result.has(s.zoo,s.nan):raise ValueError('運算未定義')
        q.put(payload)
    except Exception as e: q.put({'error':str(e)})
def calculate(text,op='calculate',var='x',point='0'):
    ctx=mp.get_context('spawn'); q=ctx.Queue(); p=ctx.Process(target=worker,args=(q,text,op,var,point));p.start();p.join(5)
    if p.is_alive(): p.terminate();p.join(); raise ValueError('運算超過 5 秒限制')
    try: result=q.get(timeout=1)
    except Empty: raise ValueError('運算程序未完成') from None
    finally: q.close()
    if 'error' in result: raise ValueError(result['error'])
    return result


def chat_calculation(prompt):
    """Accept only an unambiguous whole arithmetic expression/equation."""
    import re
    text=prompt.strip().rstrip('？?。')
    text=re.sub(r'^(?:請)?(?:計算|算出|解方程式|解方程|求解)\s*[:：]?\s*','',text)
    text=text.replace('×','*').replace('÷','/').replace('−','-')
    if not re.fullmatch(r'[0-9xyzt+*/^().=;\s-]+',text) or not re.search(r'[+*/^=()-]',text):return None
    if '=' in text:
        variables=','.join(sorted(set(re.findall('[xyzt]',text))))
        if not variables:return None
        result=calculate(text,'solve',variables)
        details=result.get('verification',[])
        verified=bool(details) and all(row['verified'] for row in details)
        return '方程式：'+text+'\n解：'+result['exact']+'\n'+('代回原式，各式殘差均為 0，驗算通過。' if verified else '沒有取得可驗證的解；請檢查方程式與定義域。')
    if re.search('[xyzt]',text):return None
    result=calculate(text)
    return '算式：'+text+'\n精確結果：'+result['exact']+('\n近似值：'+result['approx'] if result['approx'] and result['approx']!=result['exact'] else '')+'\n此結果由 SymPy 計算；十進位常數以精確分數處理。'
