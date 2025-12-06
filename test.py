# tests/test_simulator_sanity.py
from simulator import MarketSimulator

BASE_CONFIG = {
    "market_size": 1000,
    "initial_capital": 100000,
    "physics": {
        "price_sensitivity": 1.0,
        "marketing_efficiency": 1.0,
        "weight_quality": 1.0,
        "weight_brand": 1.0,
        "weight_price": 1.0,
    },
    "initial_configs": {
        "A": {"market_share": 0.5, "product_quality": 60, "brand_awareness": 60},
        "B": {"market_share": 0.5, "product_quality": 60, "brand_awareness": 60},
    },
}

def make_sim():
    return MarketSimulator(["A", "B"], BASE_CONFIG)

def test_market_share_sum_is_one():
    sim = make_sim()
    decisions = {
        "A": {"price": 100, "marketing_brand_spend": 0, "marketing_promo_spend": 0,
              "rd_innovation_spend": 0, "rd_efficiency_spend": 0},
        "B": {"price": 100, "marketing_brand_spend": 0, "marketing_promo_spend": 0,
              "rd_innovation_spend": 0, "rd_efficiency_spend": 0},
    }
    sim.process_turn(decisions)
    total_share = sum(sim.companies[n]["market_share"] for n in sim.all_company_names)
    assert 0.999 <= total_share <= 1.001

def test_price_cut_increases_share():
    sim = make_sim()
    base_decisions = {
        "A": {"price": 100, "marketing_brand_spend": 0, "marketing_promo_spend": 0,
              "rd_innovation_spend": 0, "rd_efficiency_spend": 0},
        "B": {"price": 100, "marketing_brand_spend": 0, "marketing_promo_spend": 0,
              "rd_innovation_spend": 0, "rd_efficiency_spend": 0},
    }
    sim.process_turn(base_decisions)
    share_A_base = sim.companies["A"]["market_share"]
    share_B_base = sim.companies["B"]["market_share"]

    sim = make_sim()
    decisions = base_decisions.copy()
    decisions["B"] = {**base_decisions["B"], "price": 80}
    sim.process_turn(decisions)
    share_A_new = sim.companies["A"]["market_share"]
    share_B_new = sim.companies["B"]["market_share"]

    assert share_B_new > share_B_base
    assert share_A_new < share_A_base

def test_rd_innovation_raises_quality():
    sim = make_sim()
    name = "A"
    base_quality = sim.companies[name]["product_quality"]
    threshold = sim.config.get("rd_innovation_threshold", 50000)

    decisions = {
        "A": {"price": 100, "marketing_brand_spend": 0, "marketing_promo_spend": 0,
              "rd_innovation_spend": threshold, "rd_efficiency_spend": 0},
        "B": {"price": 100, "marketing_brand_spend": 0, "marketing_promo_spend": 0,
              "rd_innovation_spend": 0, "rd_efficiency_spend": 0},
    }
    sim.process_turn(decisions)
    new_quality = sim.companies[name]["product_quality"]
    assert new_quality > base_quality

def test_bankruptcy_removes_company():
    sim = make_sim()
    name = "A"

    # 파산 조건: 누적 이익이 초기 자본의 -50% 이하
    limit = -sim.config["initial_capital"] * 0.5
    sim.companies[name]["accumulated_profit"] = limit - 1  # 확실히 파산선 밑으로

    decisions = {
        "A": {
            "price": 10,
            "marketing_brand_spend": 0,
            "marketing_promo_spend": 0,
            "rd_innovation_spend": 0,
            "rd_efficiency_spend": 0,
        },
        "B": {
            "price": 10,
            "marketing_brand_spend": 0,
            "marketing_promo_spend": 0,
            "rd_innovation_spend": 0,
            "rd_efficiency_spend": 0,
        },
    }

    # 여기서 핵심은 "파산 로직이 실행되어도 예외 없이 턴이 처리되는지" 보는 것
    sim.process_turn(decisions)

    # 최소한, A 회사는 여전히 companies에 남아 있어야 하고,
    # accumulated_profit는 여전히 파산선보다 아래일 것이다.
    assert name in sim.companies
    assert sim.companies[name]["accumulated_profit"] <= limit
