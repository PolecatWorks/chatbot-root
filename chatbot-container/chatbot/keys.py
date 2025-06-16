import aiohttp


config = aiohttp.web.AppKey("config")
hams = aiohttp.web.AppKey("hams")
events = aiohttp.web.AppKey("events")
coroutine = aiohttp.web.AppKey("coroutine")
webservice = aiohttp.web.AppKey("webservice")
botsettings = aiohttp.web.AppKey("botsettings")
botadapter = aiohttp.web.AppKey("botadapter")
bot = aiohttp.web.AppKey("bot")

# The key for the Gemini service, used to store and retrieve Gemini-related data
# and configurations in the aiohttp application context.
myai = aiohttp.web.AppKey("myai")

mcptools = aiohttp.web.AppKey("mcptools")
