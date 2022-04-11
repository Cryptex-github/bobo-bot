if __name__ == '__main__':
    import uvloop

    uvloop.install()
    del uvloop

    from core import BoboBot

    BoboBot().run()
