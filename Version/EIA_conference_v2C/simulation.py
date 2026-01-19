import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from scipy.interpolate import make_interp_spline

# --- CẤU HÌNH GIAO DIỆN BIỂU ĐỒ (CHO ĐẸP MẮT - CHUẨN PAPER) ---
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 12, 'font.family': 'sans-serif'})

# ==========================================
# 1. THIẾT LẬP THAM SỐ MÔ PHỎNG (CONFIG)
# ==========================================
SIMULATION_DAYS = 7
HOURS_PER_DAY = 10  # 8h sáng đến 6h chiều
TOTAL_STEPS = SIMULATION_DAYS * HOURS_PER_DAY

# Tham số Sinh học (Bio-Battery Parameters)
E_MAX = 100.0       # Pin đầy
E_CRITICAL = 20.0   # Ngưỡng sập nguồn (Burnout threshold)
E_SAFE_MARGIN = 40.0 # Ngưỡng an toàn để Bio-PKT bắt đầu "phanh" lại

# Tham số Tác vụ (Task Parameters)
# High Load (Toán/Lý): Tốn pin nhanh, điểm cao
ALPHA_HIGH = 18.0   # Mất 18% pin/giờ
GAIN_HIGH = 10.0    # Học được 10 điểm kiến thức

# Low Load (Sử/Nhạc/Video): Tốn pin ít (Active Rest), điểm thấp hơn
ALPHA_LOW = 3.0     # Chỉ mất 3% pin/giờ (gần như nghỉ ngơi)
GAIN_LOW = 4.0      # Học được 4 điểm kiến thức

# Burnout Penalty (Hình phạt)
RECOVERY_RATE = 15.0 # Tốc độ hồi phục khi nghỉ hoàn toàn
BURNOUT_LOCKOUT = 2  # Nếu sập nguồn, bắt buộc nghỉ 2 tiếng (mất trắng thời gian)

# ==========================================
# 2. XÂY DỰNG CLASS MÔ PHỎNG (AGENT)
# ==========================================

class VirtualLearner:
    def __init__(self, strategy_name):
        self.strategy = strategy_name
        self.energy = E_MAX
        self.total_knowledge = 0
        self.burnout_count = 0
        self.is_burnt_out = 0  # Đếm ngược thời gian bị phạt nghỉ
        
        # History logs để vẽ biểu đồ
        self.energy_history = []
        self.knowledge_history = []
        self.action_history = [] # 0: Rest, 1: Low, 2: High

    def step(self):
        # A. Xử lý trạng thái Burnout (Nếu đang bị phạt)
        if self.is_burnt_out > 0:
            self.energy = min(E_MAX, self.energy + RECOVERY_RATE)
            self.knowledge_history.append(self.total_knowledge)
            self.energy_history.append(self.energy)
            self.action_history.append(0) # Action 0 = Forced Rest
            self.is_burnt_out -= 1
            return

        # B. Ra quyết định (Decision Making) dựa trên Chiến lược
        action_type = "REST"
        
        # --- CHIẾN LƯỢC 1: GREEDY (THAM LAM) ---
        # Luôn chọn High Load nếu chưa sập nguồn
        if self.strategy == "Greedy (Baseline)":
            if self.energy > 0: 
                action_type = "HIGH"
            else:
                action_type = "REST" # Hết sạch pin mới chịu nghỉ

        # --- CHIẾN LƯỢC 2: BIO-PKT (MPC / SANDWICH) ---
        # Nhìn trước và điều phối
        elif self.strategy == "Bio-PKT (Proposed)":
            # Logic Sandwich: Nếu pin xuống thấp hơn Margin, chèn môn Nhẹ vào
            if self.energy > E_SAFE_MARGIN:
                action_type = "HIGH"
            elif self.energy > E_CRITICAL:
                action_type = "LOW"  # Active Rest (Học nhẹ để giữ đà)
            else:
                action_type = "REST" # Chủ động nghỉ ngắn để tránh Burnout dài

        # C. Thực thi hành động (Dynamics)
        current_gain = 0
        energy_cost = 0

        if action_type == "HIGH":
            current_gain = GAIN_HIGH
            energy_cost = ALPHA_HIGH
            self.action_history.append(2)
        elif action_type == "LOW":
            current_gain = GAIN_LOW
            energy_cost = ALPHA_LOW
            self.action_history.append(1)
        else: # REST
            current_gain = 0
            energy_cost = -RECOVERY_RATE # Hồi phục
            self.action_history.append(0)

        # Cập nhật trạng thái
        self.total_knowledge += current_gain
        self.energy -= energy_cost
        
        # Clip năng lượng trong khoảng [0, 100]
        self.energy = max(0, min(E_MAX, self.energy))

        # D. Kiểm tra sự kiện Sập nguồn (Burnout Check)
        # Chỉ áp dụng penalty nặng cho Greedy nếu chạm đáy
        if self.energy < E_CRITICAL and action_type == "HIGH":
            # Bio-PKT hiếm khi bị cái này vì nó chuyển sang LOW từ sớm
            self.is_burnt_out = BURNOUT_LOCKOUT
            self.burnout_count += 1
            # Phạt thêm: Khi burnout, hiệu suất của bước vừa rồi bị giảm 50%
            self.total_knowledge -= current_gain * 0.5 

        # Log lại dữ liệu
        self.energy_history.append(self.energy)
        self.knowledge_history.append(self.total_knowledge)

# ==========================================
# 3. CHẠY MÔ PHỎNG (RUN EXPERIMENT)
# ==========================================

# Khởi tạo 2 tác nhân
agent_greedy = VirtualLearner("Greedy (Baseline)")
agent_bio = VirtualLearner("Bio-PKT (Proposed)")

# Chạy vòng lặp thời gian
for t in range(TOTAL_STEPS):
    # Reset năng lượng mỗi đầu ngày mới (Giả sử ngủ đêm hồi phục full)
    if t > 0 and t % HOURS_PER_DAY == 0:
        agent_greedy.energy = E_MAX
        agent_bio.energy = E_MAX
        
    agent_greedy.step()
    agent_bio.step()

# ==========================================
# 4. TRỰC QUAN HÓA (VISUALIZATION)
# ==========================================

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))

# --- BIỂU ĐỒ 1: COGNITIVE ENERGY DYNAMICS (ĐỘNG LỰC HỌC NĂNG LƯỢNG) ---
time_axis = np.arange(TOTAL_STEPS)

# Vẽ vùng nguy hiểm
ax1.fill_between(time_axis, 0, E_CRITICAL, color='red', alpha=0.1, label='Burnout Zone')
ax1.axhline(y=E_CRITICAL, color='red', linestyle='--', linewidth=1)

# Vẽ đường năng lượng
ax1.plot(time_axis, agent_greedy.energy_history, color='tab:red', label='Greedy (Baseline)', linewidth=2, linestyle='-')
ax1.plot(time_axis, agent_bio.energy_history, color='tab:green', label='Bio-PKT (MPC)', linewidth=2.5)

ax1.set_title('Fig 4a. Cognitive Energy Dynamics (Intra-week)', fontsize=14, fontweight='bold')
ax1.set_ylabel('Bio-Energy State ($E_t$)', fontsize=12)
ax1.set_xlabel('Time (Hours over 1 Week)', fontsize=12)
ax1.set_ylim(0, 110)
ax1.legend(loc='upper right')
ax1.grid(True, which='both', linestyle='--', alpha=0.7)

# Highlight ngày đầu tiên để thấy rõ chi tiết "Răng cưa"
ax1.set_xlim(0, 30) # Zoom vào 3 ngày đầu
ax1.text(2, 10, 'CRASH', color='red', fontweight='bold')
ax1.text(5, 30, 'Oscillation (Sandwich)', color='green', fontweight='bold')

# --- BIỂU ĐỒ 2: CUMULATIVE LEARNING GAIN (HIỆU SUẤT TÍCH LŨY) ---
ax2.plot(time_axis, agent_greedy.knowledge_history, color='tab:red', label='Greedy (Baseline)', linewidth=2, linestyle='--')
ax2.plot(time_axis, agent_bio.knowledge_history, color='tab:green', label='Bio-PKT (Proposed)', linewidth=3)

# Tính % cải thiện
improvement = (agent_bio.total_knowledge - agent_greedy.total_knowledge) / agent_greedy.total_knowledge * 100
ax2.text(TOTAL_STEPS-10, agent_bio.total_knowledge, f'+{improvement:.1f}% Gain', color='green', fontweight='bold', fontsize=12)

ax2.set_title('Fig 4b. Cumulative Knowledge Gain vs. Sustainability', fontsize=14, fontweight='bold')
ax2.set_ylabel('Total Knowledge Points', fontsize=12)
ax2.set_xlabel('Time (Hours)', fontsize=12)
ax2.legend()

plt.tight_layout()
plt.show()

# ==========================================
# 5. IN KẾT QUẢ RA MÀN HÌNH
# ==========================================
print("-" * 30)
print("SIMULATION RESULTS SUMMARY")
print("-" * 30)
print(f"1. Total Burnout Events (Greedy): {agent_greedy.burnout_count}")
print(f"2. Total Burnout Events (Bio-PKT): {agent_bio.burnout_count}")
print(f"3. Final Knowledge Score (Greedy): {agent_greedy.total_knowledge:.2f}")
print(f"4. Final Knowledge Score (Bio-PKT): {agent_bio.total_knowledge:.2f}")
print(f"5. Improvement: +{improvement:.2f}%")
print("-" * 30)