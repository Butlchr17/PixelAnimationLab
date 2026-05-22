import pygame
from ui.main_window import MainWindow
from utils.config import Config

def main():
    pygame.init()
    config = Config(width=1200, height=800, title="PixelAnimationLab")
    window = MainWindow(config)
    window.run()

if __name__ == "main":
    main()