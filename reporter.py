# reporter.py

import pandas as pd
import matplotlib.pyplot as plt
import os

def generate_report(csv_filepath="simulation_results.csv"):
    """
    시뮬레이션 결과가 담긴 CSV 파일을 읽어, 시각적 리포트(그래프 이미지)를 생성합니다.
    """
    print(f"\n--- '{csv_filepath}' 파일을 바탕으로 리포트 생성 시작 ---")

    # 결과 폴더가 없으면 생성
    if not os.path.exists("results"):
        os.makedirs("results")

    try:
        # 1. CSV 파일 읽기
        df = pd.read_csv(csv_filepath)
    except FileNotFoundError:
        print(f"오류: '{csv_filepath}' 파일을 찾을 수 없습니다. main.py를 먼저 실행하세요.")
        return

    # 회사 이름들을 동적으로 찾아내기 (예: 'Apple_price' -> 'Apple')
    company_names = sorted(list(set([col.split('_')[0] for col in df.columns if '_' in col])))
    
    # --- 그래프 생성 (Matplotlib 사용) ---
    # 전체 그래프의 크기를 설정합니다.
    plt.figure(figsize=(18, 10))
    
    # 폰트 설정 (한글 깨짐 방지 - 윈도우)
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False # 마이너스 부호 깨짐 방지

    # 1. 시장 점유율 변화 그래프
    plt.subplot(2, 2, 1) # 2x2 격자의 1번째 위치
    for name in company_names:
        plt.plot(df['turn'], df[f'{name}_market_share'], marker='o', linestyle='-', label=name)
    plt.title('턴별 시장 점유율 변화', fontsize=16)
    plt.xlabel('턴(Turn)')
    plt.ylabel('시장 점유율 (Market Share)')
    plt.grid(True)
    plt.legend()

    # 2. 가격 변화 그래프
    plt.subplot(2, 2, 2) # 2x2 격자의 2번째 위치
    for name in company_names:
        plt.plot(df['turn'], df[f'{name}_price'], marker='o', linestyle='-', label=name)
    plt.title('턴별 가격 변화', fontsize=16)
    plt.xlabel('턴(Turn)')
    plt.ylabel('가격 (Price)')
    plt.grid(True)
    plt.legend()

    # 3. 이익 변화 그래프
    plt.subplot(2, 2, 3) # 2x2 격자의 3번째 위치
    for name in company_names:
        plt.plot(df['turn'], df[f'{name}_profit'], marker='o', linestyle='-', label=name)
    plt.title('턴별 이익 변화', fontsize=16)
    plt.xlabel('턴(Turn)')
    plt.ylabel('이익 (Profit)')
    plt.grid(True)
    plt.legend()
    
    # 4. 마케팅 비용 변화 그래프
    plt.subplot(2, 2, 4) # 2x2 격자의 4번째 위치
    for name in company_names:
        plt.plot(df['turn'], df[f'{name}_marketing_spend'], marker='o', linestyle='-', label=name)
    plt.title('턴별 마케팅 비용 변화', fontsize=16)
    plt.xlabel('턴(Turn)')
    plt.ylabel('마케팅 비용 (Marketing Spend)')
    plt.grid(True)
    plt.legend()

    # 그래프 레이아웃 조정 및 저장
    plt.tight_layout()
    report_path = "results/simulation_report.png"
    plt.savefig(report_path)
    
    print(f"리포트가 성공적으로 '{report_path}' 경로에 이미지 파일로 저장되었습니다.")
    # plt.show() # 로컬에서 바로 그래프를 보고 싶을 때 주석 해제

# --- 이 파일 단독으로 테스트하기 위한 코드 ---
if __name__ == '__main__':
    # 이 스크립트를 직접 실행하면, 이미 존재하는 CSV 파일로 리포트를 생성합니다.
    generate_report()