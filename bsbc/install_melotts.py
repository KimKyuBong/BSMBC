#!/usr/bin/env python3
"""
MeloTTS 설치 도우미 스크립트
설치 시 발생할 수 있는 의존성 문제를 해결합니다.
"""
import os
import sys
import subprocess
import platform

def run_cmd(cmd):
    """명령어 실행 함수"""
    print(f"실행: {cmd}")
    process = subprocess.Popen(
        cmd, 
        shell=True, 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    # 실시간 출력
    for line in process.stdout:
        print(line, end='')
    
    process.wait()
    return process.returncode

def install_prerequisites():
    """사전 필요 패키지 설치"""
    print("[*] 사전 필요 패키지 설치 중...")
    
    # 기본 패키지
    basic_packages = [
        "wheel",
        "setuptools>=42",
        "numpy",
        "requests",
        "tqdm"
    ]
    
    # torch와 torchaudio 별도 설치 (호환성 문제 방지)
    torch_cmd = "pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118"
    if platform.system() == "Darwin":  # MacOS
        torch_cmd = "pip install torch torchaudio"
    
    # 기본 패키지 설치
    cmd = f"pip install {' '.join(basic_packages)}"
    if run_cmd(cmd) != 0:
        print("[!] 기본 패키지 설치 실패")
        return False
    
    # PyTorch 설치
    print("[*] PyTorch 설치 중 (시간이 걸릴 수 있습니다)...")
    if run_cmd(torch_cmd) != 0:
        print("[!] PyTorch 설치 실패")
        return False
    
    # MeloTTS 필수 의존성
    melotts_deps = [
        "cached-path",
        "transformers==4.27.4",
        "unidecode",
        "inflect",
        "pydub",
        "tqdm",
        "loguru"
    ]
    
    # 의존성 설치
    cmd = f"pip install {' '.join(melotts_deps)}"
    if run_cmd(cmd) != 0:
        print("[!] MeloTTS 의존성 설치 실패")
        return False
    
    print("[*] 사전 필요 패키지 설치 완료")
    return True

def install_melotts():
    """MeloTTS 설치"""
    print("[*] MeloTTS 설치 시작...")
    
    # 다양한 설치 방법 시도
    install_methods = [
        # 1. GitHub에서 직접 설치 (최신 버전)
        "pip install git+https://github.com/myshell-ai/MeloTTS.git",
        
        # 2. PyPI 버전 설치 (더 안정적일 수 있음)
        "pip install MeloTTS"
    ]
    
    for method in install_methods:
        print(f"[*] 설치 방법 시도: {method}")
        if run_cmd(method) == 0:
            print("[*] MeloTTS 설치 성공!")
            return True
        print("[!] 이 방법으로 설치 실패, 다른 방법 시도...")
    
    print("[!] 모든 설치 방법 실패")
    return False

def test_melotts():
    """MeloTTS 테스트"""
    print("[*] MeloTTS 기본 테스트 중...")
    
    test_code = '''
import sys
try:
    from melo import Text2Speech
    print("[*] MeloTTS 모듈 로드 성공")
    print(f"[*] 사용 가능한 스피커:")
    speakers = ["KR", "EN-Default", "JP", "ZH", "ES", "FR"]
    for speaker in speakers:
        print(f"  - {speaker}")
    print("[*] MeloTTS 테스트 성공")
    sys.exit(0)
except Exception as e:
    print(f"[!] MeloTTS 테스트 실패: {e}")
    sys.exit(1)
'''
    
    # 임시 파일 생성 및 실행
    test_file = "melotts_test.py"
    with open(test_file, "w") as f:
        f.write(test_code)
    
    result = run_cmd(f"python {test_file}")
    
    # 임시 파일 삭제
    if os.path.exists(test_file):
        os.remove(test_file)
    
    return result == 0

if __name__ == "__main__":
    print("[*] MeloTTS 설치 도우미 시작")
    
    # 1. 사전 필요 패키지 설치
    if not install_prerequisites():
        print("[!] 사전 필요 패키지 설치 실패. 설치를 중단합니다.")
        sys.exit(1)
    
    # 2. MeloTTS 설치
    if not install_melotts():
        print("[!] MeloTTS 설치 실패. 도움말:")
        print("  - Visual C++ Build Tools가 설치되어 있는지 확인하세요")
        print("  - https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        print("  - 또는 miniconda/anaconda 환경 사용을 고려하세요")
        sys.exit(1)
    
    # 3. MeloTTS 테스트
    if test_melotts():
        print("[*] MeloTTS 설치 및 테스트 성공!")
        print("[*] 이제 MeloTTS를 사용할 수 있습니다.")
    else:
        print("[!] MeloTTS 테스트 실패. 설치는 완료되었지만 모듈 로드에 문제가 있습니다.")
        
    print("[*] 설치 프로세스 완료") 