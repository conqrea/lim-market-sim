# reporter.py (R&D 그래프 추가)

import pandas as pd
import matplotlib.pyplot as plt
import os

def generate_report(csv_filepath="simulation_results.csv"):
    """
    시뮬레이션 결과가 담긴 CSV 파일을 읽어, 시각적 리포트(그래프 이미지)를 생성합니다.
    """
    print(f"\n--- '{csv_filepath}' 파일을 바탕으로 리포트 생성 시작 ---")

    if not os.path.exists("results"):
        os.makedirs("results")

    try:
        df = pd.read_csv(csv_filepath)
    except FileNotFoundError:
        print(f"오류: '{csv_filepath}' 파일을 찾을 수 없습니다. main.py를 먼저 실행하세요.")
        return
    except pd.errors.EmptyDataError:
        print(f"오류: '{csv_filepath}' 파일이 비어있습니다.")
        return

    company_names = sorted(list(set([col.split('_')[0] for col in df.columns if '_' in col and 'accumulated' not in col])))
    # [R&D 수정] 'Others'가 그래프에 너무 많이 나와서 AI 회사만 필터링 (선택적)
    ai_company_names = [name for name in company_names if name != 'Others']
    if not ai_company_names: # AI 회사가 없는 경우 (tuner 등)
        ai_company_names = company_names

    # --- 그래프 생성 (Matplotlib 사용) ---
    # [R&D 수정] 그래프 6개를 위한 크기 및 레이아웃 변경
    plt.figure(figsize=(24, 10)) 
    
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False 

    # 1. 누적 이익 그래프
    plt.subplot(2, 3, 1) # 2x3 격자의 1번째
    for name in ai_company_names:
        if f'{name}_accumulated_profit' in df.columns:
            plt.plot(df['turn'], df[f'{name}_accumulated_profit'], marker='o', linestyle='-', label=name)
    plt.title('턴별 누적 이익 (Accumulated Profit)', fontsize=16)
    plt.xlabel('턴(Turn)')
    plt.ylabel('누적 이익')
    plt.grid(True)
    plt.legend()

    # 2. 시장 점유율 그래프
    plt.subplot(2, 3, 2) # 2x3 격자의 2번째
    for name in company_names: # 점유율은 'Others'도 포함
        plt.plot(df['turn'], df[f'{name}_market_share'], marker='o', linestyle='-', label=name)
    plt.title('턴별 시장 점유율 (Market Share)', fontsize=16)
    plt.xlabel('턴(Turn)')
    plt.ylabel('시장 점유율')
    plt.grid(True)
    plt.legend()

    # 3. 가격 변화 그래프
    plt.subplot(2, 3, 3) # 2x3 격자의 3번째
    for name in company_names:
        plt.plot(df['turn'], df[f'{name}_price'], marker='o', linestyle='-', label=name)
    plt.title('턴별 가격 변화 (Price)', fontsize=16)
    plt.xlabel('턴(Turn)')
    plt.ylabel('가격')
    plt.grid(True)
    plt.legend()
    
    # 4. 마케팅 비용 그래프
    plt.subplot(2, 3, 4) # 2x3 격자의 4번째
    for name in company_names:
        plt.plot(df['turn'], df[f'{name}_marketing_spend'], marker='o', linestyle='-', label=name)
    plt.title('턴별 마케팅 비용 (Marketing Spend)', fontsize=16)
    plt.xlabel('턴(Turn)')
    plt.ylabel('마케팅 비용')
    plt.grid(True)
    plt.legend()

    # 5. [R&D 수정] R&D 비용 그래프 (신규)
    plt.subplot(2, 3, 5) # 2x3 격자의 5번째
    for name in company_names:
        if f'{name}_rd_spend' in df.columns:
            plt.plot(df['turn'], df[f'{name}_rd_spend'], marker='o', linestyle='-', label=name)
    plt.title('턴별 R&D 비용 (R&D Spend)', fontsize=16)
    plt.xlabel('턴(Turn)')
    plt.ylabel('R&D 비용')
    plt.grid(True)
    plt.legend()

    # 6. [R&D 수정] 단위 원가 그래프 (신규)
    plt.subplot(2, 3, 6) # 2x3 격자의 6번째
    for name in company_names:
        if f'{name}_unit_cost' in df.columns:
            plt.plot(df['turn'], df[f'{name}_unit_cost'], marker='o', linestyle='-', label=name)
    plt.title('턴별 단위 원가 변화 (Unit Cost)', fontsize=16)
    plt.xlabel('턴(Turn)')
    plt.ylabel('단위 원가')
    plt.grid(True)
    plt.legend()

    # 그래프 레이아웃 조정 및 저장
    plt.tight_layout()
    report_path = "results/simulation_report.png"
    plt.savefig(report_path)
    
    print(f"리포트가 성공적으로 '{report_path}' 경로에 이미지 파일로 저장되었습니다.")
    # plt.show()

# --- 이 파일 단독으로 테스트하기 위한 코드 ---
if __name__ == '__main__':
    generate_report()