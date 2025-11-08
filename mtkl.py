from mesa import Agent, Model
from mesa.time import RandomActivation
import random
import numpy as np
import pandas as pd


# 死亡概率函数
def get_mortality_rate(age):
    if age >= 95:
        return 1.0
    mortality_rates = [
        (0, 1, 0.32257), (1, 4, 0.19523), (5, 9, 0.05141), (10, 14, 0.03697),
        (15, 19, 0.05017), (20, 24, 0.07110), (25, 29, 0.07951), (30, 34, 0.09175),
        (35, 39, 0.10709), (40, 44, 0.12838), (45, 49, 0.14754), (50, 54, 0.18383),
        (55, 59, 0.22024), (60, 64, 0.29059), (65, 69, 0.37125), (70, 74, 0.48085),
        (75, 79, 0.62398), (80, 84, 0.74408), (85, 89, 0.86924), (90, 94, 0.95201)
    ]
    for lower, upper, rate in mortality_rates:
        if lower <= age <= upper:
            return 1 - (1 - rate) ** (1 / 5)


class Person(Agent):
    def __init__(self, unique_id, model, gender, age, phase_name):
        super().__init__(unique_id, model)
        self.gender = gender
        self.age = age
        self.status = "alive"
        self.is_pregnant = False
        self.nursing_time_left = 0.0
        self.phase_name = phase_name
        self.death_age = None
        self.death_phase = None
        self.death_tick = None

    def step(self):
        if self.status == "dead":
            return

        if self.is_pregnant:
            self._handle_pregnancy()

        if self._check_mortality():
            self.status = "dead"
            self.death_age = self.age
            self.death_phase = self.phase_name
            self.death_tick = self.model.tick
            return

        self._handle_reproduction()

        self.age += 1

    def _handle_pregnancy(self):
        self.nursing_time_left -= 1
        if self.nursing_time_left <= 0:
            self.is_pregnant = False
        elif random.random() < self.nursing_time_left:
            self.is_pregnant = True
        else:
            self.is_pregnant = False

    def _check_mortality(self):
        mortality_rate = get_mortality_rate(self.age)
        return random.random() < mortality_rate

    def _handle_reproduction(self):
        if self.gender == "female" and 16 <= self.age <= 45 and not self.is_pregnant:
            if random.random() < 0.28:
                new_id = self.model.get_next_id()
                gender = random.choice(["male", "female"])
                new_person = Person(new_id, self.model, gender, 0, self.phase_name)
                self.model.schedule.add(new_person)
                self.is_pregnant = True
                self.nursing_time_left = 3.5


class PopulationModel(Model):
    def __init__(self, N, ph2_ticks):
        super().__init__()
        self.schedule = RandomActivation(self)
        self.current_phase = "ph1"
        self.tick = 0
        self.stats = {}
        self.running = True
        self.next_agent_id = 0
        self.N = N
        self.ph2_ticks = ph2_ticks
        self.ph2_alive_counts = {}
        self.ph2_death_counts = {}

    def get_next_id(self):
        agent_id = self.next_agent_id
        self.next_agent_id += 1
        return agent_id

    def setup(self):
        self.tick = 0
        self.stats = {}
        self.ph2_alive_counts = {}
        self.ph2_death_counts = {}
        self.schedule.agents.clear()
        self.current_phase = "ph1"
        self.next_agent_id = 0
        ages = np.linspace(0, 95, self.N, dtype=int)
        np.random.shuffle(ages)
        for i in range(self.N):
            gender = "male" if i < self.N // 2 else "female"
            unique_id = self.get_next_id()
            person = Person(unique_id, self, gender, ages[i], "ph1")
            self.schedule.add(person)

    def step(self):
        self.schedule.step()
        if self.current_phase == "ph2":
            deaths_in_this_tick = len([a for a in self.schedule.agents if a.status == "dead" and a.death_tick == self.tick])
            if self.tick + 1 in [100, 150, 200, 250, 300, 350, 400, 450, 500]:
                self.ph2_death_counts[f"death_at_tick_{self.tick + 1}"] = deaths_in_this_tick

        self.tick += 1

        if self.current_phase == "ph1" and self.tick == 100:
            self._collect_ph1_stats()
            for agent in self.schedule.agents:
                if agent.status == "alive" and agent.phase_name == "ph1":
                    agent.phase_name = "ph2"
            self.current_phase = "ph2"
            self.tick = 0

        elif self.current_phase == "ph2":
            if self.tick in [100, 200, 300, 400, 500]:
                self._collect_ph2_alive_stats(self.tick)
            if self.tick == self.ph2_ticks:
                self._collect_ph2_death_stats()
                self.running = False

    def _collect_ph1_stats(self):
        agents = [a for a in self.schedule.agents if a.status == "alive"]
        self.stats["ph1_total_alive"] = len(agents)
        self._collect_age_group_stats(agents, "ph1")

    def _collect_ph2_death_stats(self):
        dead_agents = [a for a in self.schedule.agents if a.status == "dead" and a.death_phase == "ph2"]
        self.stats["ph2_total_dead"] = len(dead_agents)
        self._collect_age_group_stats(dead_agents, "ph2")

    def _collect_age_group_stats(self, agents, phase):
        age_groups = {
            "0_10": (0, 10), "0_18": (0, 18), "20_30": (20, 30),
            "20_35": (20, 35), "35_50": (35, 50), "10_plus": (10, 100)
        }
        for group, (low, high) in age_groups.items():
            self.stats[f"{phase}_{group}_alive"] = len([a for a in agents if low <= a.age <= high])

    def _collect_ph2_alive_stats(self, tick):
        agents = [a for a in self.schedule.agents if a.status == "alive"]
        self.ph2_alive_counts[f"ph2_alive_at_tick_{tick}"] = len(agents)
        self._collect_age_group_stats(agents, f"ph2_at_tick_{tick}")


# 蒙特卡罗法的采样实验次数
num_samples = 100
# Define the range of N (population sizes) and ph2_ticks (time steps for the second phase)
N_values = [100, 200, 300]  # Example: population sizes for the experiment
ph2_ticks_values = [100, 150, 200]  # Example: number of ticks for the second phase
results = []

# 蒙特卡罗采样，重复进行num_samples次实验
for _ in range(num_samples):
    for N in N_values:
        for ph2_ticks in ph2_ticks_values:
            model = PopulationModel(N=N, ph2_ticks=ph2_ticks)
            model.setup()
            while model.running:
                model.step()

            # 收集每次运行的统计数据
            run_data = {
                "初始人数": model.N,
                "墓地沿用时间": model.ph2_ticks,

                # 第一阶段统计
                "第100个tick结束时活着的人口总数": model.stats.get("ph1_total_alive", 0),
                "第100个tick结束时活着的0～10岁人口数量": model.stats.get("ph1_0_10_alive", 0),
                "第100个tick结束时活着的0～18岁人口数量": model.stats.get("ph1_0_18_alive", 0),
                "第100个tick结束时活着的20～30岁人口数量": model.stats.get("ph1_20_30_alive", 0),
                "第100个tick结束时活着的20～35岁人口数量": model.stats.get("ph1_20_35_alive", 0),
                "第100个tick结束时活着的35～50岁人口数量": model.stats.get("ph1_35_50_alive", 0),
                "第100个tick结束时活着的50岁以上人口数量": model.stats.get("ph1_50_plus_alive", 0),
                "第100个tick结束时活着的人口数量大于等于10岁": model.stats.get("ph1_10_plus_alive", 0),

                # # 存活率计算
                # "第一阶段存活率": model.stats.get("ph1_total_alive", 0) / model.N if model.N else 0,

                # 第二阶段统计（死亡）
                "第500个tick结束时死亡的人口数量": model.stats.get("ph2_total_dead", 0),
                "第500个tick结束时0～10岁死亡人数": model.stats.get("ph2_0_10_dead", 0),
                "第500个tick结束时死亡人数0～18岁": model.stats.get("ph2_0_18_dead", 0),
                "第500个tick结束时死亡人数20～30岁": model.stats.get("ph2_20_30_dead", 0),
                "第500个tick结束时死亡人数20～35岁": model.stats.get("ph2_20_35_dead", 0),
                "第500个tick结束时死亡人数35～50岁": model.stats.get("ph2_35_50_dead", 0),
                "第500个tick结束时死亡人数50岁以上": model.stats.get("ph2_50_plus_dead", 0),
                "第500个tick结束时死亡人数10岁以上": model.stats.get("ph2_10_plus_dead", 0),
                #
                # # 存活率计算
                # "第二阶段存活率": (model.stats.get("ph1_total_alive", 0) - model.stats.get("ph2_total_dead",
                #                                                                     0)) / model.stats.get(
                #     "ph1_total_alive", 0) if model.stats.get("ph1_total_alive", 0) else 0,
                # "总存活率": (model.N - model.stats.get("ph2_total_dead", 0)) / model.N if model.N else 0,

                # 统计最大、最小、平均死亡年龄
                "最大死亡年龄": model.stats.get("max_death_age", 0),
                "最小死亡年龄": model.stats.get("min_death_age", 0),
                "死亡年龄平均值": model.stats.get("avg_death_age", 0),

                # 按性别统计（如果模型区分性别）
                "第100个tick结束时存活的男性数量": model.stats.get("ph1_male_alive", 0),
                "第100个tick结束时存活的女性数量": model.stats.get("ph1_female_alive", 0),
                "第500个tick结束时死亡的男性数量": model.stats.get("ph2_male_dead", 0),
                "第500个tick结束时死亡的女性数量": model.stats.get("ph2_female_dead", 0),
            }

            results.append(run_data)

# 保存到DataFrame并输出Excel
df = pd.DataFrame(results)
df.to_excel("D:/clip-image-search-main/墓地_蒙特卡罗.xlsx", index=False)
print("所有蒙特卡罗运行完成，结果已保存到 墓地_蒙特卡罗.xlsx")
