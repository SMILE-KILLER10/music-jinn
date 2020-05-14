from aiohttp import web


def setup_routes(app, handler):
    h = handler
    app.add_routes(
        [
            web.get('/', h.index, name='index'),
            web.get(r"/f/{id:\d+}.html", h.info, name='info'),
            web.get(r"/download/{id:\d+}/{name}", h.download_get),
            web.head(r"/download/{id:\d+}/{name}", h.download_head)
        ]
    )
