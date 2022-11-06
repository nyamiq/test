import pulp 

# 重さ
w = [2, 1, 3, 2, 1, 4]

# 価値
v = [3, 2, 6, 1, 3, 8]

# 限度：10kg
W = 10

r = range(len(w))

# 数理モデル
m = pulp.LpProblem(sense=pulp.LpMaximize)

# 変数
x = [pulp.LpVariable('x%d'%i, cat=pulp.LpBinary) for i in r]

# 目的関数
m += pulp.lpDot(v, x)

# 限度を設定し、問題を解く
m += pulp.lpDot(w, x) <= W
m.solve()
print('最大価値:{} / 組み合わせ:{}'.format(pulp.value(m.objective), [i for i in r if pulp.value(x[i]) > 0.5]))