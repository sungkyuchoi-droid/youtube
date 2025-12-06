import sys
import os
import requests
# PyQt6 -> PyQt5 로 변경됨
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QLabel, QMessageBox)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import yt_dlp

# --- 다운로드 작업을 백그라운드에서 처리할 스레드 클래스 ---
class DownloadThread(QThread):
    progress_signal = pyqtSignal(str) # 상태 메시지 전달용
    finished_signal = pyqtSignal()    # 완료 신호용

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        # yt-dlp 옵션 설정
        ydl_opts = {
            'format': 'best',  # 가장 좋은 화질/음질 자동 선택
            'outtmpl': '%(title)s.%(ext)s', # 파일명 저장 형식
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            self.progress_signal.emit("다운로드 시작... 잠시만 기다려주세요.")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.progress_signal.emit("다운로드 완료!")
            self.finished_signal.emit()
        except Exception as e:
            self.progress_signal.emit(f"에러 발생: {str(e)}")

# --- 메인 GUI 클래스 ---
class YouTubeDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.video_info = None # 검색된 비디오 정보를 담을 변수

    def initUI(self):
        # 윈도우 설정
        self.setWindowTitle('나만의 유튜브 다운로더 (PyQt5)')
        self.setGeometry(300, 300, 500, 600)

        # 레이아웃 설정
        layout = QVBoxLayout()

        # 1. 링크 입력 및 조회 버튼
        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("유튜브 링크를 여기에 붙여넣으세요")
        self.search_btn = QPushButton("조회")
        self.search_btn.clicked.connect(self.search_video)
        
        input_layout.addWidget(self.url_input)
        input_layout.addWidget(self.search_btn)
        layout.addLayout(input_layout)

        # 2. 썸네일 이미지 표시
        self.img_label = QLabel()
        # PyQt5 스타일 정렬 (AlignmentFlag 사용 안 함)
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setMinimumHeight(200)
        self.img_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        self.img_label.setText("썸네일이 여기에 표시됩니다")
        layout.addWidget(self.img_label)

        # 3. 정보 표시 (제목, 조회수, 좋아요)
        self.title_label = QLabel("제목: -")
        self.title_label.setWordWrap(True) # 제목이 길면 줄바꿈
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.view_label = QLabel("조회수: -")
        self.like_label = QLabel("좋아요: -")

        layout.addWidget(self.title_label)
        layout.addWidget(self.view_label)
        layout.addWidget(self.like_label)

        # 여백 추가
        layout.addStretch(1)

        # 4. 상태 메시지 및 다운로드 버튼
        self.status_label = QLabel("준비")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.download_btn = QPushButton("다운로드")
        self.download_btn.setFixedHeight(40)
        self.download_btn.setEnabled(False) # 조회 전에는 비활성화
        self.download_btn.setStyleSheet("background-color: #ff0000; color: white; font-weight: bold;")
        self.download_btn.clicked.connect(self.start_download)
        layout.addWidget(self.download_btn)

        self.setLayout(layout)

    def search_video(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "경고", "링크를 입력해주세요.")
            return

        self.status_label.setText("정보를 가져오는 중...")
        self.search_btn.setEnabled(False) # 중복 클릭 방지
        QApplication.processEvents() # UI 갱신

        try:
            # yt-dlp로 정보 추출 (download=False로 설정하여 정보만 가져옴)
            ydl_opts = {'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            self.video_info = info
            
            # 정보 파싱
            title = info.get('title', '제목 없음')
            view_count = info.get('view_count', 0)
            like_count = info.get('like_count', 0)
            thumbnail_url = info.get('thumbnail')

            # UI 업데이트
            self.title_label.setText(f"제목: {title}")
            self.view_label.setText(f"조회수: {view_count:,}회") # 천단위 콤마
            
            # 좋아요 수는 유튜브 정책상 None일 수 있음
            if like_count:
                self.like_label.setText(f"좋아요: {like_count:,}개")
            else:
                self.like_label.setText("좋아요: 비공개 또는 알 수 없음")

            # 썸네일 이미지 다운로드 및 표시
            if thumbnail_url:
                image_data = requests.get(thumbnail_url).content
                image = QImage()
                image.loadFromData(image_data)
                pixmap = QPixmap(image)
                # PyQt5 스타일 이미지 리사이즈
                scaled_pixmap = pixmap.scaledToWidth(450, Qt.SmoothTransformation)
                self.img_label.setPixmap(scaled_pixmap)
                self.img_label.setText("") # 텍스트 제거

            self.status_label.setText("조회 성공! 다운로드가 가능합니다.")
            self.download_btn.setEnabled(True)

        except Exception as e:
            # 에러 메시지 자세히 출력
            QMessageBox.critical(self, "에러", f"정보를 가져오는데 실패했습니다.\n{str(e)}")
            self.status_label.setText("조회 실패")
            self.video_info = None
            self.download_btn.setEnabled(False)
        
        finally:
            self.search_btn.setEnabled(True)

    def start_download(self):
        if not self.video_info:
            return

        url = self.url_input.text().strip()
        
        # 버튼 비활성화 (중복 다운로드 방지)
        self.download_btn.setEnabled(False)
        self.search_btn.setEnabled(False)
        
        # 스레드 생성 및 실행
        self.worker = DownloadThread(url)
        self.worker.progress_signal.connect(self.update_status)
        self.worker.finished_signal.connect(self.download_finished)
        self.worker.start()

    def update_status(self, msg):
        self.status_label.setText(msg)

    def download_finished(self):
        self.status_label.setText("다운로드가 완료되었습니다. (폴더 확인)")
        QMessageBox.information(self, "알림", "다운로드가 완료되었습니다!")
        self.download_btn.setEnabled(True)
        self.search_btn.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = YouTubeDownloader()
    ex.show()
    # PyQt5는 app.exec_()를 사용합니다.
    sys.exit(app.exec_())