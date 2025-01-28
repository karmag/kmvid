import kmvid.data.text as text

if __name__ == '__main__':
    text.font_cache.register_path("path/to/more/fonts")
    text.font_cache.pprint()
