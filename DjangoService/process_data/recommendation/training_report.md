# A_damage 模型训练报告

## 原始9组数据（论文表2）
- speed=2500.0, fz=0.01, A_damage=3.5834
- speed=2500.0, fz=0.05, A_damage=65.7846
- speed=2500.0, fz=0.1, A_damage=115.64538
- speed=5000.0, fz=0.01, A_damage=3.36352
- speed=5000.0, fz=0.05, A_damage=59.79448
- speed=5000.0, fz=0.1, A_damage=101.71934
- speed=10000.0, fz=0.01, A_damage=2.8
- speed=10000.0, fz=0.05, A_damage=51.24078
- speed=10000.0, fz=0.1, A_damage=109.14466

## 扩增方法
- 以 9 个种子点构成 speed-fz 规则网格并进行二维插值。
- 在插值曲面上添加小幅高斯噪声（约 3%），并裁剪到正值。
- 生成 2000 条样本（保留原始 9 条）。

## 模型对比
| 模型 | R² | MAE | RMSE |
|---|---:|---:|---:|
| LinearRegression | 0.9850 | 2.8485 | 3.6503 |
| Polynomial(2)+LinearRegression | 0.9912 | 2.1060 | 2.7951 |
| RandomForestRegressor | -1.0000 | -1.0000 | -1.0000 |

## 最终模型
- **Polynomial(2)+LinearRegression**

## 损伤等级区间（按三分位）
- low: {'min': 2.7887956076959597, 'max': 42.302136152125875}
- medium: {'min': 42.302136152125875, 'max': 76.75019033995515}
- high: {'min': 76.75019033995515, 'max': 116.5468394999862}

- 环境缺少 scikit-learn 时，RandomForest 指标将显示为占位值。
