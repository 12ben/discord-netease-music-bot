import discord
import asyncio
import logging
import time
from configparser import ConfigParser
from discord.ext import commands
import neteaselib_local

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
bot = commands.Bot(command_prefix='$')
bot.remove_command("help")
queueList = neteaselib_local.Queue()
if not discord.opus.is_loaded():
    discord.opus.load_opus('opus')
config = ConfigParser()
config.read("config.ini", encoding="UTF-8")


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx: commands.Context, *, channel: discord.VoiceChannel):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()
    
    @commands.command()
    async def play(self, ctx: commands.Context):
        # 已在播放，忽略相同命令
        if ctx.voice_client.is_playing():
            return

        retry_count = 0
        while True:
            # 等待播放结束
            while ctx.voice_client.is_playing():
               await asyncio.sleep(1)

            # 判断队列中是否有未播放的歌曲
            if queueList.is_empty() is False:
                # 有，则计数清零
                retry_count = 0
                # 并且开始播放
                musicInfo = queueList.dequeue()
                embed = discord.Embed(title="Now Playing: " + musicInfo["musicArResult"] + " - " + musicInfo["musicTitle"])\
                    .add_field(name="Link", value="[Click Here](%s)" % musicInfo["163Url"], inline=False)\
                    .set_footer(text="Length: " + str(musicInfo["musicLength"] + " • " + time.asctime(time.localtime(time.time()))))\
                    .set_thumbnail(url=musicInfo["musicPic"])
                await ctx.send(embed=embed)
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(musicInfo["musicFileName"]), volume=0.4)
                ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)
            else:
                # 无，且计数达到阈值
                if retry_count >= 60:
                    # 退出
                    await ctx.voice_client.disconnect()
                    await ctx.send("没有歌曲可以播放")
                    return
                else:
                    # 未达到阈值，计数增加
                    retry_count += 1
                    await asyncio.sleep(1)

    @commands.command()
    async def add(self, ctx: commands.Context, music_name: str):
        print("Searching %s, user is %s" % (music_name, ctx.message.author))
        musicInfo = neteaselib_local.get_music_info(music_name)
        queueList.enqueue(musicInfo)
        await ctx.send("%s - %s 添加到列表" % (musicInfo["musicTitle"],musicInfo["musicArResult"]))

    @commands.command()
    async def skip(self, ctx: commands.Context):
        ctx.voice_client.stop()
        await ctx.send("已跳过")

    @commands.command()
    async def volume(self, ctx: commands.Context, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")
        ctx.voice_client.source.volume = volume / 100
        await ctx.send("音量调至 {}%".format(volume))

    @commands.command()
    async def stop(self, ctx: commands.Context):
        await ctx.send("已停止")
        if not queueList.is_empty():
            queueList.clear()
        await ctx.voice_client.disconnect()

    @commands.command()
    async def cleancache(self, ctx: commands.Context):
        if str(ctx.message.author) == config.get("config", "username"):
            await ctx.send("Command sent by `%s`, cleaning cache." % ctx.message.author)
            neteaselib_local.clean_cache()
        else:
            await ctx.send("Command sent by `%s`, you don't have permission to clean cache." % ctx.message.author)

    @commands.command()
    async def logout(self, ctx: commands.Context):
        if str(ctx.message.author) == config.get("config", "username"):
            await ctx.send("Command sent by `%s`, logging out." % ctx.message.author)
            await discord.Client.logout(bot)
        else:
            await ctx.send("Command sent by `%s`, you don't have permission to logout this bot." % ctx.message.author)

    @commands.command()
    async def help(self, ctx: commands.Context):
        await ctx.send("$play 播放音乐 $add 添加歌曲 $skip 跳过")

    @play.before_invoke
    async def ensure_voice(self, ctx: commands.Context):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))


bot.add_cog(Music(bot))
bot.run(config.get("config", "token"))
