# Import
# -----------------------------------------------------------------------------
from __future__ import annotations
import random
import time
from typing import Tuple
# 
import mip
# -----------------------------------------------------------------------------


# Main
# -----------------------------------------------------------------------------
# 
print(f'Input generation \n')
# ----------------------------------------------------------------------
# # Vertices
n: int = 300
#
# Vertices
V: list[int] = [i for i in range(1, n + 1)]
#
# (型ヒントを使用)
VertexType = type(V[0])
ArcType = Tuple[VertexType, VertexType]
# 
# Directed arcs
A: list[ArcType] = [(i, j) for i in V for j in V if i != j]
#
# Distance function
random.seed(1)
d: dict[ArcType, int] = {a: random.randint(1, 99) for a in A}
# 
# (便宜上、最初に出発する都市を設定)
v_first: VertexType = V[0]
# 
# Time limit
time_limit_s: int = 60 * 60
# 
# Debug
# print(f'  V={V}')
# print(f'  A={A}')
# print(f'  d={d}')
# print(f'  v_first={v_first}')
# print(f'  Time limit={time_limit_s}(s) \n')
# ----------------------------------------------------------------------


print(f'Instance generation \n')
# ----------------------------------------------------------------------
formulation_time_start_s: float = time.perf_counter()
# 
# Model
#   ここでソルバーを指定する。ソルバーを指定しない場合、
#   Guorbiを(pipやcondaからではなく)インストーラーから入れ
#   環境変数GUROBI_HOMEやパスが設定されているならば、Gurobiが選ばれる。
#   そうでない場合は、Python-MIPに同こんされているCOIN-CBCが選ばれる。
m = mip.Model(name='TSPorHamiltonianPathFF')

#   Variables
x: dict[ArcType, mip.Var] = {}
for a in A:
    x[a] = m.add_var(name=f'Var_x({a})', var_type=mip.BINARY)
    del a
#
f: dict[ArcType, mip.Var] = {}
for a in [aa for aa in A if aa[1] is not v_first]:
    f[a] = m.add_var(name=f'Var_f({a})')
    del a

#   Objective
m.objective = mip.minimize(mip.xsum((d[a]) * x[a] for a in A))

#   Constraints
#       x
for v in V:
    m.add_constr(
        mip.xsum(x[a] for a in A if a[1] is v) == 1, 
        name=f'Con_In({v})')
    m.add_constr(
        mip.xsum(x[a] for a in A if a[0] is v) == 1, 
        name=f'Con_Out({v})')
    del v
#
#       f
for v in [vv for vv in V if vv is not v_first]:
    m.add_constr(
           mip.xsum(f[a] for a in A if a[1] is v) 
         - mip.xsum(f[a] for a in A if a[0] is v and a[1] is not v_first) 
        == 1, 
        name=f'Con_flow({v}')
    del v
#
#       f-x
for a in [aa for aa in A if aa[0] is v_first]:
    m.add_constr(f[a] == (len(V) - 1) * x[a], name=f'Con_f-x({a})')
    del a
for a in [aa for aa in A if aa[0] is not v_first and aa[1] is not v_first]:
    m.add_constr(f[a] <= (len(V) - 2) * x[a], name=f'Con_f-x({a})')
    del a
#
formulation_time: float = time.perf_counter() - formulation_time_start_s
del formulation_time_start_s
# ----------------------------------------------------------------------


print(f'Optimization')
# ----------------------------------------------------------------------
optimization_time_start_s: float = time.perf_counter()
#
#   使用スレッド数: 
#       0 = お任せ(デフォルト, 複数スレ使ってくれている?)
#       -1 = 計算機の全スレ(SMTスレも使うので物理コア数だけ使うより非効率な場合も?)
#       1以上 = 指定した数のスレ(指定したぶんだけちゃんと使ってくれている?)
m.threads = -1
status: mip.OptimizationStatus = m.optimize(max_seconds=time_limit_s)
obj_val: float = m.objective_value
is_optimal: bool = (status == mip.OptimizationStatus.OPTIMAL)
#
optimization_time: float = time.perf_counter() - optimization_time_start_s
del optimization_time_start_s
print(f'')
# ----------------------------------------------------------------------


print(f'Solution check')
# ----------------------------------------------------------------------
# x and f
#   x[a] = 1 である枝を集める
xa_1s: list[ArcType] = [
    a for a in A if a in x.keys() and x[a].x > 1.0 - 0.01]
#   f[a]の値の大きい順( = 訪問順)に枝並べ替えするが、
#   最後の枝だけは f[a] が未定義なので、一度抜いて並べ替えて後で最後に差し込む
xa_lasts: list[ArcType] = [xa for xa in xa_1s if xa not in f.keys()]
assert len(xa_lasts) == 1, f'x[a] = 1 で f[a] が未定義の a が 1 つではありません'
xa_1s.remove(xa_lasts[0])
xa_1s.sort(key=lambda a: f[a].x, reverse=True)
xa_1s.append(xa_lasts[0])
del xa_lasts
assert len(xa_1s) == len(V), f'{xa_1s} と 頂点数 {len(V)} が一致しません'
# Debug
# for a in xa_ones:
#     print(
#           f'  arc={a}: ' 
#         + f'x={x[a].x}, f={f[a].x if a in f.keys() else "Undefined"}, ' 
#         + 'd={d[a]}')
#     del a
# print(f'  Sum of d[a]: {sum([d[a] for a in xa_ones])} \n')
#
# 並べ替えた枝が巡回路を構成しているか確かめる
prev_xa: ArcType = xa_1s[0]
for xa in xa_1s:
    # 最初の要素は xa is prev_xa なので検査しない
    if xa is xa_1s[0]:
        continue
    # 次の要素からは検査
    assert xa[0] is prev_xa[1], f'{prev_xa}-{xa} がつながっていません'
    prev_xa = xa
    # 最後の要素は追加検査
    if xa is xa_1s[-1]:
        assert xa[1] is xa_1s[0][0], f'{xa_1s[-1]}-{xa_1s[0]} がつながっていません'
    del xa
del prev_xa
# 
A_sol: list[ArcType] = [a for a in xa_1s]
del xa_1s
V_sol: list[VertexType] = [a[0] for a in A_sol]
V_sol.append(A_sol[-1][1])
assert len(V_sol) == len(V) + 1, f'{V_sol} と 頂点数 {len(V)} + 1 が一致しません'
assert len(V_sol) == len(set(V_sol)) + 1, f'{V_sol} に始点以外で重複要素があります'
sum_d_A_sol: int = sum(d[a] for a in A_sol)
del A_sol
assert abs(obj_val - sum_d_A_sol) < 1.0, f'{obj_val} != {sum_d_A_sol} です'
del obj_val
print(f'')
# ----------------------------------------------------------------------


print(f'Solution')
# ----------------------------------------------------------------------
print(f'  Tour                = {V_sol}')
print(f'  Sum of distance     = {sum_d_A_sol}')
print(f'  Optimality          = {is_optimal}')
print(f'  Time (formulation)  = {formulation_time:6.1f} (s)')
print(f'       (optimization) = {optimization_time:6.1f} (s)')
# ----------------------------------------------------------------------
# -----------------------------------------------------------------------------

