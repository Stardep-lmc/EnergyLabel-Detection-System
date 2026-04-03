#!/bin/bash
# 一键训练：Teacher → Student DPFD
# 后台运行，断开SSH也不会中断

set -e

cd /home/std03/Projects/LMC/yolo-distiller

# 激活conda环境
eval "$(conda shell.bash hook)"
conda activate yolo_distiller_lmc

echo "$(date): 开始训练Teacher模型..." | tee -a train_all.log
python scripts/train_teacher.py 2>&1 | tee -a train_all.log

echo "$(date): Teacher训练完成，开始DPFD蒸馏训练Student..." | tee -a train_all.log
python scripts/train_student_dpfd.py 2>&1 | tee -a train_all.log

echo "$(date): 全部训练完成！" | tee -a train_all.log
echo "Teacher模型: runs/teacher/yolo11m_energy_label/weights/best.pt" | tee -a train_all.log
echo "Student模型: runs/student/yolo11n_dpfd_energy_label/weights/best.pt" | tee -a train_all.log