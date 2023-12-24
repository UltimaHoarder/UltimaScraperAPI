class MediaStatsModel:
    def __init__(self, option: dict[str, int]):
        self.videos_count: int = option["videosCount"]
        self.photos_count: int = option["photosCount"]
        self.gifs_count: int = option["gifsCount"]
        self.audios_count: int = option["audiosCount"]
